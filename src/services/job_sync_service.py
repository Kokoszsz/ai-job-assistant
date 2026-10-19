"""
Job Sync Service
================
Service for synchronizing jobs from external APIs to the local database.

Handles:
- Fetching jobs from Remotive API
- Upserting jobs to database (insert new, update existing)
- Soft-deleting jobs no longer available in the API
- Tracking sync statistics
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError

from src.models.base import db
from src.models.job import JobOffer
from src.services.remotive_client import RemotiveClient, RemotiveAPIError

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    """Statistics from a job sync operation."""

    jobs_fetched: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    jobs_deactivated: int = 0
    jobs_skipped: int = 0
    errors: int = 0
    total_active: int = 0

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return {
            "jobs_fetched": self.jobs_fetched,
            "jobs_created": self.jobs_created,
            "jobs_updated": self.jobs_updated,
            "jobs_deactivated": self.jobs_deactivated,
            "jobs_skipped": self.jobs_skipped,
            "errors": self.errors,
            "total_active": self.total_active,
        }


class JobSyncService:
    """
    Service for syncing jobs from external APIs to the database.

    Example usage:
        stats = JobSyncService.sync_from_remotive()
        print(f"Created {stats.jobs_created} new jobs")
    """

    @staticmethod
    def sync_from_remotive(
        clear_existing: bool = False, category: Optional[str] = None
    ) -> SyncStats:
        """
        Sync jobs from Remotive API to the database.

        Args:
            clear_existing: If True, delete all existing Remotive jobs first
            category: Optional category filter for Remotive API

        Returns:
            SyncStats with counts of created, updated, deactivated jobs

        Raises:
            RemotiveAPIError: If API request fails
            SQLAlchemyError: If database operation fails
        """
        stats = SyncStats()
        sync_start_time = datetime.utcnow()

        logger.info(f"Starting Remotive job sync (clear_existing={clear_existing})")

        try:
            # Clear existing Remotive jobs if requested
            if clear_existing:
                deleted_count = JobSyncService._clear_remotive_jobs()
                logger.info(f"Cleared {deleted_count} existing Remotive jobs")

            # Fetch jobs from API
            client = RemotiveClient()
            api_jobs = client.fetch_jobs(category=category)
            stats.jobs_fetched = len(api_jobs)

            if not api_jobs:
                logger.warning("No jobs returned from Remotive API")
                stats.total_active = JobSyncService._count_active_jobs()
                return stats

            # Track which external IDs we've seen in this sync
            seen_external_ids = set()

            # Process each job
            for api_job in api_jobs:
                try:
                    # Map API response to model fields
                    job_data = RemotiveClient.map_job_to_model(api_job)
                    external_id = job_data.get("external_id")

                    if not external_id:
                        logger.warning(
                            f"Skipping job with no ID: {api_job.get('title')}"
                        )
                        stats.jobs_skipped += 1
                        continue

                    seen_external_ids.add(external_id)

                    # Check if job already exists
                    existing_job = (
                        db.session.query(JobOffer)
                        .filter_by(external_id=external_id)
                        .first()
                    )

                    if existing_job:
                        # Update existing job
                        JobSyncService._update_job(existing_job, job_data)
                        stats.jobs_updated += 1
                    else:
                        # Create new job
                        JobSyncService._create_job(job_data)
                        stats.jobs_created += 1

                except Exception as e:
                    logger.error(f"Error processing job {api_job.get('id')}: {e}")
                    stats.errors += 1
                    continue

            # Commit all changes
            db.session.commit()

            # Soft-delete jobs not seen in this sync
            stats.jobs_deactivated = JobSyncService._deactivate_stale_jobs(
                sync_start_time, seen_external_ids
            )

            # Get final count of active jobs
            stats.total_active = JobSyncService._count_active_jobs()

            logger.info(
                f"Remotive sync complete: "
                f"fetched={stats.jobs_fetched}, "
                f"created={stats.jobs_created}, "
                f"updated={stats.jobs_updated}, "
                f"deactivated={stats.jobs_deactivated}, "
                f"errors={stats.errors}, "
                f"total_active={stats.total_active}"
            )

            return stats

        except RemotiveAPIError:
            db.session.rollback()
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during sync: {e}")
            raise

    @staticmethod
    def _create_job(job_data: Dict[str, Any]) -> JobOffer:
        """Create a new job in the database."""
        job = JobOffer(
            external_id=job_data["external_id"],
            external_source=job_data["external_source"],
            title=job_data["title"],
            company=job_data["company"],
            location=job_data["location"],
            description=job_data["description"],
            requirements=job_data.get("requirements"),
            salary_min=job_data.get("salary_min"),
            salary_max=job_data.get("salary_max"),
            job_type=job_data["job_type"],
            posted_date=job_data["posted_date"],
            external_url=job_data.get("external_url"),
            is_active=True,
            tags=job_data.get("tags"),
            category=job_data.get("category"),
            company_logo_url=job_data.get("company_logo_url"),
            last_seen_at=job_data["last_seen_at"],
        )
        db.session.add(job)
        return job

    @staticmethod
    def _update_job(job: JobOffer, job_data: Dict[str, Any]) -> None:
        """Update an existing job with new data."""
        job.title = job_data["title"]
        job.company = job_data["company"]
        job.location = job_data["location"]
        job.description = job_data["description"]
        job.requirements = job_data.get("requirements")
        job.salary_min = job_data.get("salary_min")
        job.salary_max = job_data.get("salary_max")
        job.job_type = job_data["job_type"]
        job.posted_date = job_data["posted_date"]
        job.external_url = job_data.get("external_url")
        job.is_active = True  # Re-activate if it was deactivated
        job.tags = job_data.get("tags")
        job.category = job_data.get("category")
        job.company_logo_url = job_data.get("company_logo_url")
        job.last_seen_at = job_data["last_seen_at"]

    @staticmethod
    def _deactivate_stale_jobs(
        sync_start_time: datetime, seen_external_ids: set
    ) -> int:
        """
        Deactivate jobs from Remotive that weren't seen in this sync.

        Args:
            sync_start_time: When the sync started
            seen_external_ids: Set of external IDs that were in the API response

        Returns:
            Number of jobs deactivated
        """
        # Find active Remotive jobs not seen in this sync
        stale_jobs = (
            db.session.query(JobOffer)
            .filter(
                JobOffer.external_source == "remotive",
                JobOffer.is_active == True,
                JobOffer.external_id.notin_(seen_external_ids)
                if seen_external_ids
                else True,
            )
            .all()
        )

        deactivated_count = 0
        for job in stale_jobs:
            job.is_active = False
            deactivated_count += 1
            logger.debug(f"Deactivated stale job: {job.external_id} - {job.title}")

        if deactivated_count > 0:
            db.session.commit()
            logger.info(f"Deactivated {deactivated_count} stale Remotive jobs")

        return deactivated_count

    @staticmethod
    def _clear_remotive_jobs() -> int:
        """
        Delete all jobs from Remotive source.

        Returns:
            Number of jobs deleted
        """
        deleted = (
            db.session.query(JobOffer)
            .filter(JobOffer.external_source == "remotive")
            .delete()
        )
        db.session.commit()
        return deleted

    @staticmethod
    def _count_active_jobs(source: Optional[str] = None) -> int:
        """
        Count active jobs, optionally filtered by source.

        Args:
            source: Optional external source filter

        Returns:
            Count of active jobs
        """
        query = db.session.query(JobOffer).filter(JobOffer.is_active == True)
        if source:
            query = query.filter(JobOffer.external_source == source)
        return query.count()

    @staticmethod
    def get_sync_status() -> Dict[str, Any]:
        """
        Get current status of job data.

        Returns:
            Dictionary with job counts by source and status
        """
        total_jobs = db.session.query(JobOffer).count()
        active_jobs = (
            db.session.query(JobOffer).filter(JobOffer.is_active == True).count()
        )

        remotive_total = (
            db.session.query(JobOffer)
            .filter(JobOffer.external_source == "remotive")
            .count()
        )
        remotive_active = (
            db.session.query(JobOffer)
            .filter(JobOffer.external_source == "remotive", JobOffer.is_active == True)
            .count()
        )

        # Get last sync time from most recently seen job
        last_sync_job = (
            db.session.query(JobOffer)
            .filter(
                JobOffer.external_source == "remotive",
                JobOffer.last_seen_at.isnot(None),
            )
            .order_by(JobOffer.last_seen_at.desc())
            .first()
        )

        last_sync_at = None
        if last_sync_job and last_sync_job.last_seen_at:
            last_sync_at = last_sync_job.last_seen_at.isoformat()

        # Dummy data (no external_source)
        dummy_total = (
            db.session.query(JobOffer)
            .filter(JobOffer.external_source.is_(None))
            .count()
        )

        return {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "sources": {
                "remotive": {
                    "total": remotive_total,
                    "active": remotive_active,
                    "last_sync_at": last_sync_at,
                },
                "dummy": {
                    "total": dummy_total,
                    "active": dummy_total,  # Dummy jobs are always active
                },
            },
        }
