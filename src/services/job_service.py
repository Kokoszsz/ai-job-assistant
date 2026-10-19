"""
Job Service
===========
Business logic for job search and favorites management.

Provides comprehensive job search with:
- Full-text search on titles, descriptions, requirements
- Multi-filter support (location, job_type, salary range)
- Multiple sorting options (relevance, date, salary)
- Pagination and result ranking
- Favorite job management
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, nullslast, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.models.base import db
from src.models.job import FavoriteJob, JobOffer
from src.models.user import User

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing job search and favorites."""

    # Valid options for sorting and filtering
    VALID_SORT_OPTIONS = ["relevance", "date", "salary_min", "salary_max"]
    VALID_JOB_TYPES = ["full-time", "part-time", "contract", "remote", "internship"]

    @staticmethod
    def search_jobs(
        query: Optional[str] = None,
        location: Optional[str] = None,
        job_types: Optional[List[str]] = None,  # Changed from job_type to support multiple
        salary_min: Optional[int] = None,
        salary_max: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "relevance",  # New parameter
        user_id: Optional[int] = None,  # For including favorite status
    ) -> Dict[str, Any]:
        """
        Search for jobs with comprehensive filters and pagination.

        Args:
            query: Search query for title, company, description, requirements (optional)
            location: Filter by location (optional, case-insensitive partial match)
            job_types: List of job types to filter by (optional)
            salary_min: Minimum salary filter (optional)
            salary_max: Maximum salary filter (optional)
            page: Page number (1-indexed)
            page_size: Results per page (max 100)
            sort_by: Sort option (relevance, date, salary_min, salary_max)
            user_id: Optional user ID to include favorite status in results

        Returns:
            Dictionary with jobs list, pagination info, and filters applied

        Raises:
            ValueError: If invalid parameters provided
        """
        try:
            # Validate parameters
            JobService._validate_search_params(page, page_size, sort_by, job_types)

            # Start with base query for active jobs
            jobs_query = db.session.query(JobOffer).filter_by(is_active=True)

            # Apply search query (title, company, description, requirements)
            if query and query.strip():
                search_pattern = f"%{query.strip()}%"
                jobs_query = jobs_query.filter(
                    or_(
                        JobOffer.title.ilike(search_pattern),
                        JobOffer.company.ilike(search_pattern),
                        JobOffer.description.ilike(search_pattern),
                        JobOffer.requirements.ilike(search_pattern),
                    )
                )

            # Apply location filter (partial match)
            if location and location.strip():
                location_pattern = f"%{location.strip()}%"
                jobs_query = jobs_query.filter(JobOffer.location.ilike(location_pattern))

            # Apply job types filter (multiple values supported)
            if job_types and len(job_types) > 0:
                jobs_query = jobs_query.filter(JobOffer.job_type.in_(job_types))

            # Apply salary filters
            if salary_min is not None:
                # Job's max salary should be >= min requested salary
                jobs_query = jobs_query.filter(or_(JobOffer.salary_max >= salary_min, JobOffer.salary_max.is_(None)))

            if salary_max is not None:
                # Job's min salary should be <= max requested salary
                jobs_query = jobs_query.filter(or_(JobOffer.salary_min <= salary_max, JobOffer.salary_min.is_(None)))

            # Get total count before pagination
            total_count = jobs_query.count()

            # Apply sorting
            jobs_query = JobService._apply_sorting(jobs_query, sort_by, query)

            # Validate pagination params
            page = max(1, page)  # Ensure page >= 1
            page_size = min(max(1, page_size), 100)  # Clamp between 1 and 100

            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            offset = (page - 1) * page_size

            # Apply pagination
            jobs = jobs_query.limit(page_size).offset(offset).all()

            # Get favorite job IDs if user_id provided
            favorite_job_ids = set()
            if user_id:
                favorites = db.session.query(FavoriteJob.job_offer_id).filter(FavoriteJob.user_id == user_id).all()
                favorite_job_ids = {fav.job_offer_id for fav in favorites}

            logger.info(
                f"Job search: query='{query}', location='{location}', types={job_types}, "
                f"sort='{sort_by}', found {total_count} jobs, returning page {page}/{total_pages}"
            )

            result = {
                "jobs": [
                    {**job.to_dict(include_details=True), "is_favorited": job.id in favorite_job_ids} for job in jobs
                ],
                "pagination": {
                    "total": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
                "filters_applied": {
                    "query": query,
                    "location": location,
                    "job_types": job_types,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "sort_by": sort_by,
                },
            }

            # Add suggestions if no results found
            if total_count == 0:
                result["suggestions"] = JobService.get_search_suggestions(query, location)

            return result

        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error searching jobs: {str(e)}")
            raise

    @staticmethod
    def get_job_by_id(job_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get job details by ID with optional favorite status.

        Args:
            job_id: Job ID
            user_id: Optional user ID to include favorite status

        Returns:
            Job dictionary with full details or None if not found
        """
        try:
            job = db.session.query(JobOffer).filter_by(id=job_id, is_active=True).first()

            if not job:
                logger.warning(f"Job {job_id} not found or not active")
                return None

            job_dict = job.to_dict(include_details=True)

            # Add favorite status if user_id provided
            if user_id:
                is_favorited = (
                    db.session.query(FavoriteJob)
                    .filter(FavoriteJob.user_id == user_id, FavoriteJob.job_offer_id == job_id)
                    .first()
                    is not None
                )
                job_dict["is_favorited"] = is_favorited
            else:
                job_dict["is_favorited"] = False

            return job_dict

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving job {job_id}: {str(e)}")
            raise

    @staticmethod
    def get_favorite_jobs(user_id: int, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """
        Get user's favorite jobs with pagination.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Results per page (max 100)

        Returns:
            Dictionary with favorite jobs list and pagination info
        """
        try:
            # Query favorites with job details
            favorites_query = db.session.query(FavoriteJob).filter_by(user_id=user_id)
            favorites_query = favorites_query.order_by(FavoriteJob.saved_at.desc())

            # Get total count
            total_count = favorites_query.count()

            # Validate pagination params
            page = max(1, page)
            page_size = min(max(1, page_size), 100)

            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            offset = (page - 1) * page_size

            # Apply pagination
            favorites = favorites_query.limit(page_size).offset(offset).all()

            logger.info(f"Retrieved {len(favorites)} favorite jobs for user_id={user_id} (page {page}/{total_pages})")

            return {
                "favorites": [fav.to_dict(include_job=True) for fav in favorites],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            }

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving favorite jobs for user_id={user_id}: {str(e)}")
            raise

    @staticmethod
    def add_favorite_job(user_id: int, job_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Add job to user's favorites.

        Args:
            user_id: User ID
            job_id: Job ID
            notes: Optional user notes

        Returns:
            Created favorite dictionary

        Raises:
            ValueError: If user not found, job not found, or already favorited
        """
        try:
            # Verify user exists
            user = db.session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError("User not found")

            # Verify job exists and is active
            job = db.session.query(JobOffer).filter_by(id=job_id, is_active=True).first()
            if not job:
                raise ValueError("Job not found or no longer available")

            # Create favorite
            favorite = FavoriteJob(user_id=user_id, job_offer_id=job_id, notes=notes)

            db.session.add(favorite)
            db.session.commit()

            logger.info(f"User {user_id} favorited job {job_id}")
            return favorite.to_dict(include_job=True)

        except IntegrityError as e:
            db.session.rollback()
            # Check if it's a duplicate favorite
            if "uq_favorite_user_job" in str(e) or "UNIQUE constraint failed" in str(e):
                raise ValueError("Job already in favorites")
            logger.error(f"Database integrity error adding favorite: {str(e)}")
            raise SQLAlchemyError(str(e))
        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error adding favorite: {str(e)}")
            raise

    @staticmethod
    def remove_favorite_job(user_id: int, job_id: int) -> bool:
        """
        Remove job from user's favorites.

        Args:
            user_id: User ID
            job_id: Job ID

        Returns:
            True if removed, False if not found
        """
        try:
            favorite = db.session.query(FavoriteJob).filter_by(user_id=user_id, job_offer_id=job_id).first()

            if not favorite:
                logger.warning(f"Favorite not found for user {user_id}, job {job_id}")
                return False

            db.session.delete(favorite)
            db.session.commit()

            logger.info(f"User {user_id} removed favorite job {job_id}")
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error removing favorite: {str(e)}")
            raise

    @staticmethod
    def update_favorite_notes(user_id: int, job_id: int, notes: str) -> Optional[Dict[str, Any]]:
        """
        Update notes for a favorite job.

        Args:
            user_id: User ID
            job_id: Job ID
            notes: New notes

        Returns:
            Updated favorite dictionary or None if not found
        """
        try:
            favorite = db.session.query(FavoriteJob).filter_by(user_id=user_id, job_offer_id=job_id).first()

            if not favorite:
                logger.warning(f"Favorite not found for user {user_id}, job {job_id}")
                return None

            favorite.notes = notes
            db.session.commit()

            logger.info(f"Updated notes for user {user_id}, job {job_id}")
            return favorite.to_dict(include_job=True)

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating favorite notes: {str(e)}")
            raise

    @staticmethod
    def _validate_search_params(page: int, page_size: int, sort_by: str, job_types: Optional[List[str]]) -> None:
        """
        Validate search parameters.

        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate pagination
        if page < 1:
            raise ValueError("Page must be >= 1")

        if page_size < 1 or page_size > 100:
            raise ValueError("Page size must be between 1 and 100")

        # Validate sort option
        if sort_by not in JobService.VALID_SORT_OPTIONS:
            raise ValueError(f"Invalid sort_by. Must be one of: {', '.join(JobService.VALID_SORT_OPTIONS)}")

        # Validate job types
        if job_types:
            invalid_types = [jt for jt in job_types if jt not in JobService.VALID_JOB_TYPES]
            if invalid_types:
                raise ValueError(
                    f"Invalid job types: {', '.join(invalid_types)}. "
                    f"Must be one of: {', '.join(JobService.VALID_JOB_TYPES)}"
                )

    @staticmethod
    def _apply_sorting(query, sort_by: str, search_query: Optional[str]):
        """
        Apply sorting to query based on sort_by parameter.

        Args:
            query: SQLAlchemy query object
            sort_by: Sort option (relevance, date, salary_min, salary_max)
            search_query: Original search query (for relevance sorting)

        Returns:
            Query with sorting applied
        """
        if sort_by == "relevance":
            # If there's a search query, relevance is implicit in LIKE matching
            # Otherwise, sort by most recent date
            return query.order_by(desc(JobOffer.posted_date))

        elif sort_by == "date":
            return query.order_by(desc(JobOffer.posted_date))

        elif sort_by == "salary_min":
            # Handle NULL salaries by putting them last
            return query.order_by(nullslast(desc(JobOffer.salary_min)))

        elif sort_by == "salary_max":
            # Handle NULL salaries by putting them last
            return query.order_by(nullslast(desc(JobOffer.salary_max)))

        # Default to date if somehow invalid sort_by made it through
        return query.order_by(desc(JobOffer.posted_date))

    @staticmethod
    def get_search_suggestions(query: Optional[str] = None, location: Optional[str] = None) -> Dict[str, Any]:
        """
        Get helpful suggestions when no search results found.

        Args:
            query: Original search query
            location: Original location filter

        Returns:
            Dictionary with helpful suggestions and popular searches
        """
        try:
            suggestions = {"message": "No jobs found matching your criteria", "suggestions": []}

            # Suggest trying without location filter
            if location:
                suggestions["suggestions"].append("Try searching without location filter")

            # Suggest broadening search query
            if query:
                suggestions["suggestions"].append("Try using broader keywords")
                suggestions["suggestions"].append("Check spelling of search terms")

            # Get popular job titles as suggestions
            popular_jobs = (
                db.session.query(JobOffer.title, func.count(JobOffer.id).label("count"))
                .filter(JobOffer.is_active == True)
                .group_by(JobOffer.title)
                .order_by(desc("count"))
                .limit(5)
                .all()
            )

            if popular_jobs:
                suggestions["popular_searches"] = [job.title for job in popular_jobs]

            return suggestions

        except SQLAlchemyError as e:
            logger.error(f"Database error getting search suggestions: {str(e)}")
            # Return basic suggestions even if query fails
            return {
                "message": "No jobs found matching your criteria",
                "suggestions": ["Try using broader keywords", "Try searching without filters"],
            }
