"""
Profile Service
===============
Business logic for profile management.
"""

import logging
from datetime import date
from typing import Optional, Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from src.models.base import db
from src.models.profile import (
    Profile,
    WorkExperience,
    Education,
    Skill,
    Certification,
    Project,
    Language,
)
from src.models.user import User

logger = logging.getLogger(__name__)


class ProfileService:
    """Service for managing user profiles."""

    @staticmethod
    def get_profile(
        user_id: int, include_details: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get user's profile.

        Args:
            user_id: User ID
            include_details: Whether to include work experience, education, and skills

        Returns:
            Profile data dictionary or None if not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return None

            return profile.to_dict(include_details=include_details)

        except SQLAlchemyError as e:
            # If there's a database error (e.g., missing tables), rollback and log
            db.session.rollback()
            logger.error(
                f"Database error getting profile for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def create_profile(
        user_id: int, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new profile for a user.

        Args:
            user_id: User ID
            data: Optional profile data (summary, phone, location, preferences)

        Returns:
            Created profile data

        Raises:
            ValueError: If profile already exists or user not found
        """
        try:
            # Check if user exists
            user = db.session.query(User).filter_by(id=user_id).first()
            if not user:
                raise ValueError(f"User with id={user_id} not found")

            # Check if profile already exists
            existing = db.session.query(Profile).filter_by(user_id=user_id).first()
            if existing:
                raise ValueError(f"Profile already exists for user_id={user_id}")

            data = data or {}
            profile = Profile(
                user_id=user_id,
                summary=data.get("summary"),
                phone=data.get("phone"),
                location=data.get("location"),
                preferences_json=data.get("preferences", {}),
            )

            db.session.add(profile)
            db.session.commit()

            logger.info(f"Created profile for user_id={user_id}")
            return profile.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error creating profile for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_profile(user_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update user's profile information.

        Args:
            user_id: User ID
            data: Profile data to update (summary, phone, location)

        Returns:
            Updated profile data or None if not found

        Raises:
            ValueError: If validation fails
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return None

            # Update allowed fields
            if "summary" in data:
                if data["summary"] and len(data["summary"]) > 5000:
                    raise ValueError("Summary must not exceed 5000 characters")
                profile.summary = data["summary"]

            if "phone" in data:
                if data["phone"] and len(data["phone"]) > 20:
                    raise ValueError("Phone number must not exceed 20 characters")
                profile.phone = data["phone"]

            if "location" in data:
                if data["location"] and len(data["location"]) > 100:
                    raise ValueError("Location must not exceed 100 characters")
                profile.location = data["location"]

            db.session.commit()

            logger.info(f"Updated profile for user_id={user_id}")
            return profile.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error updating profile for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def get_preferences(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user's job preferences.

        Args:
            user_id: User ID

        Returns:
            Preferences dictionary or None if profile not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return None

            return {"user_id": user_id, "preferences": profile.preferences_json or {}}

        except SQLAlchemyError as e:
            logger.error(
                f"Database error getting preferences for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_preferences(
        user_id: int, preferences: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update user's job preferences.

        Args:
            user_id: User ID
            preferences: Preferences dictionary
                - desired_roles: List of job titles
                - locations: List of preferred locations
                - job_types: List of job types (full-time, remote, contract, part-time)
                - min_salary: Minimum salary
                - max_salary: Maximum salary
                - experience_level: Preferred experience level

        Returns:
            Updated preferences or None if profile not found

        Raises:
            ValueError: If validation fails
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return None

            # Validate preferences structure
            if not isinstance(preferences, dict):
                raise ValueError("Preferences must be a dictionary")

            # Validate specific fields if provided
            if "job_types" in preferences:
                valid_types = ["full-time", "remote", "contract", "part-time"]
                job_types = preferences["job_types"]
                if not isinstance(job_types, list):
                    raise ValueError("job_types must be a list")
                for job_type in job_types:
                    if job_type not in valid_types:
                        raise ValueError(
                            f"Invalid job_type: {job_type}. Must be one of {valid_types}"
                        )

            if "min_salary" in preferences and preferences["min_salary"] is not None:
                if (
                    not isinstance(preferences["min_salary"], (int, float))
                    or preferences["min_salary"] < 0
                ):
                    raise ValueError("min_salary must be a non-negative number")

            if "max_salary" in preferences and preferences["max_salary"] is not None:
                if (
                    not isinstance(preferences["max_salary"], (int, float))
                    or preferences["max_salary"] < 0
                ):
                    raise ValueError("max_salary must be a non-negative number")

            if "min_salary" in preferences and "max_salary" in preferences:
                min_sal = preferences["min_salary"]
                max_sal = preferences["max_salary"]
                if min_sal is not None and max_sal is not None and min_sal > max_sal:
                    raise ValueError("min_salary cannot be greater than max_salary")

            # Update preferences
            profile.preferences_json = preferences
            db.session.commit()

            logger.info(f"Updated preferences for user_id={user_id}")
            return {"user_id": user_id, "preferences": profile.preferences_json}

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error updating preferences for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def delete_profile(user_id: int) -> bool:
        """
        Delete user's profile.

        Args:
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return False

            db.session.delete(profile)
            db.session.commit()

            logger.info(f"Deleted profile for user_id={user_id}")
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error deleting profile for user_id={user_id}: {str(e)}"
            )
            raise

    # Work Experience Methods

    @staticmethod
    def get_work_experiences(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all work experiences for a user.

        Args:
            user_id: User ID

        Returns:
            List of work experience dictionaries
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return []

            return [exp.to_dict() for exp in profile.work_experiences]

        except SQLAlchemyError as e:
            logger.error(
                f"Database error getting work experiences for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def add_work_experience(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a work experience entry.

        Args:
            user_id: User ID
            data: Work experience data

        Returns:
            Created work experience dictionary

        Raises:
            ValueError: If validation fails or profile not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                raise ValueError(f"Profile not found for user_id={user_id}")

            # Validate required fields
            required_fields = ["job_title", "company", "start_date"]
            missing_fields = [f for f in required_fields if not data.get(f)]
            if missing_fields:
                raise ValueError(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )

            # Validate field lengths
            if len(data["job_title"]) > 100:
                raise ValueError("Job title must be 100 characters or less")
            if len(data["company"]) > 100:
                raise ValueError("Company must be 100 characters or less")
            if data.get("description") and len(data["description"]) > 2000:
                raise ValueError("Description must be 2000 characters or less")

            # Parse dates
            start_date = (
                date.fromisoformat(data["start_date"])
                if isinstance(data["start_date"], str)
                else data["start_date"]
            )
            end_date = None
            if data.get("end_date"):
                end_date = (
                    date.fromisoformat(data["end_date"])
                    if isinstance(data["end_date"], str)
                    else data["end_date"]
                )

                # Validate date range
                if end_date < start_date:
                    raise ValueError("End date must be after start date")

            # Create work experience
            experience = WorkExperience(
                profile_id=profile.id,
                job_title=data["job_title"],
                company=data["company"],
                start_date=start_date,
                end_date=end_date,
                description=data.get("description"),
            )

            db.session.add(experience)
            db.session.commit()

            logger.info(
                f"Added work experience for user_id={user_id}, experience_id={experience.id}"
            )
            return experience.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error adding work experience for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_work_experience(
        user_id: int, experience_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a work experience entry.

        Args:
            user_id: User ID (for ownership verification)
            experience_id: Work experience ID
            data: Updated data

        Returns:
            Updated work experience dictionary or None if not found

        Raises:
            ValueError: If validation fails
        """
        try:
            # Get profile to verify ownership
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return None

            # Get work experience and verify ownership
            experience = (
                db.session.query(WorkExperience)
                .filter_by(id=experience_id, profile_id=profile.id)
                .first()
            )

            if not experience:
                logger.warning(
                    f"Work experience {experience_id} not found or not owned by user {user_id}"
                )
                return None

            # Validate and update fields
            if "job_title" in data:
                if not data["job_title"]:
                    raise ValueError("Job title cannot be empty")
                if len(data["job_title"]) > 100:
                    raise ValueError("Job title must be 100 characters or less")
                experience.job_title = data["job_title"]

            if "company" in data:
                if not data["company"]:
                    raise ValueError("Company cannot be empty")
                if len(data["company"]) > 100:
                    raise ValueError("Company must be 100 characters or less")
                experience.company = data["company"]

            if "description" in data:
                if data["description"] and len(data["description"]) > 2000:
                    raise ValueError("Description must be 2000 characters or less")
                experience.description = data["description"]

            if "start_date" in data:
                if not data["start_date"]:
                    raise ValueError("Start date cannot be empty")
                start_date = (
                    date.fromisoformat(data["start_date"])
                    if isinstance(data["start_date"], str)
                    else data["start_date"]
                )
                experience.start_date = start_date

            if "end_date" in data:
                if data["end_date"]:
                    end_date = (
                        date.fromisoformat(data["end_date"])
                        if isinstance(data["end_date"], str)
                        else data["end_date"]
                    )
                    if end_date < experience.start_date:
                        raise ValueError("End date must be after start date")
                    experience.end_date = end_date
                else:
                    experience.end_date = (
                        None  # Allow setting to None for current position
                    )

            db.session.commit()

            logger.info(
                f"Updated work experience {experience_id} for user_id={user_id}"
            )
            return experience.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error updating work experience {experience_id}: {str(e)}"
            )
            raise

    @staticmethod
    def delete_work_experience(user_id: int, experience_id: int) -> bool:
        """
        Delete a work experience entry.

        Args:
            user_id: User ID (for ownership verification)
            experience_id: Work experience ID

        Returns:
            True if deleted, False if not found
        """
        try:
            # Get profile to verify ownership
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return False

            # Get and verify ownership
            experience = (
                db.session.query(WorkExperience)
                .filter_by(id=experience_id, profile_id=profile.id)
                .first()
            )

            if not experience:
                logger.warning(
                    f"Work experience {experience_id} not found or not owned by user {user_id}"
                )
                return False

            db.session.delete(experience)
            db.session.commit()

            logger.info(
                f"Deleted work experience {experience_id} for user_id={user_id}"
            )
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error deleting work experience {experience_id}: {str(e)}"
            )
            raise

    # ===== Education Management =====

    @staticmethod
    def get_education(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all education entries for a user.

        Args:
            user_id: User ID

        Returns:
            List of education dictionaries (empty list if profile not found)
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return []

            return [edu.to_dict() for edu in profile.education]

        except SQLAlchemyError as e:
            logger.error(
                f"Database error retrieving education for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def add_education(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add education entry to user's profile.

        Args:
            user_id: User ID
            data: Education data (degree, institution, field_of_study, start_date, end_date)

        Returns:
            Created education dictionary

        Raises:
            ValueError: If validation fails or profile not found
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get profile
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                raise ValueError("Profile not found")

            # Validate required fields
            if not data.get("degree"):
                raise ValueError("degree is required")
            if not data.get("institution"):
                raise ValueError("institution is required")
            if not data.get("start_date"):
                raise ValueError("start_date is required")

            # Validate field lengths
            if len(data["degree"]) > 100:
                raise ValueError("degree must be 100 characters or less")
            if len(data["institution"]) > 100:
                raise ValueError("institution must be 100 characters or less")
            if data.get("field_of_study") and len(data["field_of_study"]) > 100:
                raise ValueError("field_of_study must be 100 characters or less")

            # Parse dates
            start_date = data["start_date"]
            if isinstance(start_date, str):
                start_date = date.fromisoformat(start_date)

            end_date = data.get("end_date")
            if end_date and isinstance(end_date, str):
                end_date = date.fromisoformat(end_date)

            # Validate date logic
            if end_date and end_date < start_date:
                raise ValueError("end_date must be after start_date")

            # Create education
            education = Education(
                profile_id=profile.id,
                degree=data["degree"],
                institution=data["institution"],
                field_of_study=data.get("field_of_study"),
                start_date=start_date,
                end_date=end_date,
            )

            db.session.add(education)
            db.session.commit()

            logger.info(
                f"Added education for user_id={user_id}: {education.degree} at {education.institution}"
            )
            return education.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error adding education for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_education(
        user_id: int, education_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update education entry.

        Args:
            user_id: User ID
            education_id: Education entry ID
            data: Updated education data (any fields to update)

        Returns:
            Updated education dictionary

        Raises:
            ValueError: If validation fails or education not found/not owned
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get profile
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                raise ValueError("Profile not found")

            # Get education (verify ownership)
            education = (
                db.session.query(Education)
                .filter_by(id=education_id, profile_id=profile.id)
                .first()
            )

            if not education:
                raise ValueError("Education not found")

            # Update degree
            if "degree" in data:
                if not data["degree"]:
                    raise ValueError("degree cannot be empty")
                if len(data["degree"]) > 100:
                    raise ValueError("degree must be 100 characters or less")
                education.degree = data["degree"]

            # Update institution
            if "institution" in data:
                if not data["institution"]:
                    raise ValueError("institution cannot be empty")
                if len(data["institution"]) > 100:
                    raise ValueError("institution must be 100 characters or less")
                education.institution = data["institution"]

            # Update field_of_study
            if "field_of_study" in data:
                if data["field_of_study"] and len(data["field_of_study"]) > 100:
                    raise ValueError("field_of_study must be 100 characters or less")
                education.field_of_study = data["field_of_study"]

            # Update start_date
            if "start_date" in data:
                start_date = data["start_date"]
                if isinstance(start_date, str):
                    start_date = date.fromisoformat(start_date)
                education.start_date = start_date

            # Update end_date
            if "end_date" in data:
                end_date = data["end_date"]
                if end_date and isinstance(end_date, str):
                    end_date = date.fromisoformat(end_date)
                education.end_date = end_date

            # Validate date logic after updates
            if education.end_date and education.end_date < education.start_date:
                raise ValueError("end_date must be after start_date")

            db.session.commit()

            logger.info(f"Updated education {education_id} for user_id={user_id}")
            return education.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error updating education {education_id} for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def delete_education(user_id: int, education_id: int) -> bool:
        """
        Delete education entry.

        Args:
            user_id: User ID
            education_id: Education entry ID

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get profile
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return False

            # Get education (verify ownership)
            education = (
                db.session.query(Education)
                .filter_by(id=education_id, profile_id=profile.id)
                .first()
            )

            if not education:
                logger.warning(
                    f"Education {education_id} not found for user_id={user_id}"
                )
                return False

            db.session.delete(education)
            db.session.commit()

            logger.info(f"Deleted education {education_id} for user_id={user_id}")
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error deleting education {education_id}: {str(e)}")
            raise

    # ===== Skills Management =====

    @staticmethod
    def get_skills(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all skills for a user.

        Args:
            user_id: User ID

        Returns:
            List of skill dictionaries (empty list if profile not found)
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return []

            return [skill.to_dict() for skill in profile.skills]

        except SQLAlchemyError as e:
            logger.error(
                f"Database error retrieving skills for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def add_skill(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add skill to user's profile.

        Args:
            user_id: User ID
            data: Skill data (name, proficiency_level)

        Returns:
            Created skill dictionary

        Raises:
            ValueError: If validation fails or profile not found or duplicate skill
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get profile
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                raise ValueError("Profile not found")

            # Validate required fields
            if not data.get("name"):
                raise ValueError("name is required")

            # Validate field length
            if len(data["name"]) > 50:
                raise ValueError("name must be 50 characters or less")

            # Validate proficiency level
            proficiency_level = data.get("proficiency_level", "intermediate")
            if proficiency_level not in Skill.PROFICIENCY_LEVELS:
                raise ValueError(
                    f"proficiency_level must be one of: {', '.join(Skill.PROFICIENCY_LEVELS)}"
                )

            # Create skill
            skill = Skill(
                profile_id=profile.id,
                name=data["name"],
                proficiency_level=proficiency_level,
            )

            db.session.add(skill)
            db.session.commit()

            logger.info(f"Added skill for user_id={user_id}: {skill.name}")
            return skill.to_dict()

        except IntegrityError as e:
            db.session.rollback()
            # Check if it's a duplicate skill
            if "uq_skill_profile_name" in str(
                e
            ) or "UNIQUE constraint failed: skills.profile_id, skills.name" in str(e):
                raise ValueError(f"Skill '{data.get('name')}' already exists")
            logger.error(
                f"Database integrity error adding skill for user_id={user_id}: {str(e)}"
            )
            raise SQLAlchemyError(str(e))
        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error adding skill for user_id={user_id}: {str(e)}")
            raise

    @staticmethod
    def add_skills_bulk(
        user_id: int, skills_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Add multiple skills to user's profile.

        Args:
            user_id: User ID
            skills_data: List of skill data dictionaries

        Returns:
            List of created skill dictionaries

        Raises:
            ValueError: If validation fails or profile not found
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get profile
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                raise ValueError("Profile not found")

            if not skills_data or not isinstance(skills_data, list):
                raise ValueError("skills must be a non-empty list")

            created_skills = []
            errors = []

            for idx, skill_data in enumerate(skills_data):
                try:
                    # Validate required fields
                    if not skill_data.get("name"):
                        errors.append(f"Skill {idx}: name is required")
                        continue

                    # Validate field length
                    if len(skill_data["name"]) > 50:
                        errors.append(
                            f"Skill {idx}: name must be 50 characters or less"
                        )
                        continue

                    # Validate proficiency level
                    proficiency_level = skill_data.get(
                        "proficiency_level", "intermediate"
                    )
                    if proficiency_level not in Skill.PROFICIENCY_LEVELS:
                        errors.append(f"Skill {idx}: invalid proficiency_level")
                        continue

                    # Check for duplicate in existing skills
                    existing = (
                        db.session.query(Skill)
                        .filter_by(profile_id=profile.id, name=skill_data["name"])
                        .first()
                    )

                    if existing:
                        errors.append(
                            f"Skill {idx}: '{skill_data['name']}' already exists"
                        )
                        continue

                    # Create skill
                    skill = Skill(
                        profile_id=profile.id,
                        name=skill_data["name"],
                        proficiency_level=proficiency_level,
                    )
                    db.session.add(skill)
                    created_skills.append(skill)

                except Exception as e:
                    errors.append(f"Skill {idx}: {str(e)}")

            if errors and not created_skills:
                # All skills failed
                raise ValueError("; ".join(errors))

            db.session.commit()

            result = [skill.to_dict() for skill in created_skills]
            if errors:
                logger.warning(
                    f"Bulk add skills for user_id={user_id}: {len(created_skills)} succeeded, {len(errors)} failed"
                )
            else:
                logger.info(
                    f"Bulk added {len(created_skills)} skills for user_id={user_id}"
                )

            return result

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error bulk adding skills for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def delete_skill(user_id: int, skill_id: int) -> bool:
        """
        Delete skill.

        Args:
            user_id: User ID
            skill_id: Skill ID

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get profile
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return False

            # Get skill (verify ownership)
            skill = (
                db.session.query(Skill)
                .filter_by(id=skill_id, profile_id=profile.id)
                .first()
            )

            if not skill:
                logger.warning(f"Skill {skill_id} not found for user_id={user_id}")
                return False

            db.session.delete(skill)
            db.session.commit()

            logger.info(f"Deleted skill {skill_id} for user_id={user_id}")
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error deleting skill {skill_id}: {str(e)}")
            raise

    @staticmethod
    def delete_skills_bulk(user_id: int, skill_ids: List[int]) -> Dict[str, Any]:
        """
        Delete multiple skills.

        Args:
            user_id: User ID
            skill_ids: List of skill IDs to delete

        Returns:
            Dictionary with deleted count and failed IDs

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get profile
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return {"deleted": 0, "failed": skill_ids}

            if not skill_ids or not isinstance(skill_ids, list):
                raise ValueError("skill_ids must be a non-empty list")

            deleted_count = 0
            failed_ids = []

            for skill_id in skill_ids:
                skill = (
                    db.session.query(Skill)
                    .filter_by(id=skill_id, profile_id=profile.id)
                    .first()
                )

                if skill:
                    db.session.delete(skill)
                    deleted_count += 1
                else:
                    failed_ids.append(skill_id)

            db.session.commit()

            logger.info(f"Bulk deleted {deleted_count} skills for user_id={user_id}")
            return {"deleted": deleted_count, "failed": failed_ids}

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error bulk deleting skills for user_id={user_id}: {str(e)}"
            )
            raise

    # ===== Certifications Management =====

    @staticmethod
    def get_certifications(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all certifications for a user.

        Args:
            user_id: User ID

        Returns:
            List of certification dictionaries
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return []

            return [cert.to_dict() for cert in profile.certifications]

        except SQLAlchemyError as e:
            logger.error(
                f"Database error retrieving certifications for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def add_certification(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a certification to user's profile.

        Args:
            user_id: User ID
            data: Certification data (name, issuing_organization, issue_date, expiry_date, credential_id, credential_url)

        Returns:
            Created certification dictionary

        Raises:
            ValueError: If validation fails or profile not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                raise ValueError("Profile not found")

            # Validate required fields
            if not data.get("name"):
                raise ValueError("Certification name is required")
            if not data.get("issuing_organization"):
                raise ValueError("Issuing organization is required")
            if not data.get("issue_date"):
                raise ValueError("Issue date is required")

            # Validate field lengths
            if len(data["name"]) > 200:
                raise ValueError("Certification name must be 200 characters or less")
            if len(data["issuing_organization"]) > 200:
                raise ValueError("Issuing organization must be 200 characters or less")

            # Parse dates
            issue_date = data["issue_date"]
            if isinstance(issue_date, str):
                issue_date = date.fromisoformat(issue_date)

            expiry_date = data.get("expiry_date")
            if expiry_date and isinstance(expiry_date, str):
                expiry_date = date.fromisoformat(expiry_date)

            # Create certification
            certification = Certification(
                profile_id=profile.id,
                name=data["name"],
                issuing_organization=data["issuing_organization"],
                issue_date=issue_date,
                expiry_date=expiry_date,
                credential_id=data.get("credential_id"),
                credential_url=data.get("credential_url"),
            )

            db.session.add(certification)
            db.session.commit()

            logger.info(
                f"Added certification for user_id={user_id}: {certification.name}"
            )
            return certification.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error adding certification for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_certification(
        user_id: int, certification_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a certification.

        Args:
            user_id: User ID
            certification_id: Certification ID
            data: Updated data

        Returns:
            Updated certification dictionary or None if not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                return None

            certification = (
                db.session.query(Certification)
                .filter_by(id=certification_id, profile_id=profile.id)
                .first()
            )

            if not certification:
                return None

            # Update fields
            if "name" in data:
                if len(data["name"]) > 200:
                    raise ValueError(
                        "Certification name must be 200 characters or less"
                    )
                certification.name = data["name"]

            if "issuing_organization" in data:
                if len(data["issuing_organization"]) > 200:
                    raise ValueError(
                        "Issuing organization must be 200 characters or less"
                    )
                certification.issuing_organization = data["issuing_organization"]

            if "issue_date" in data:
                issue_date = data["issue_date"]
                if isinstance(issue_date, str):
                    issue_date = date.fromisoformat(issue_date)
                certification.issue_date = issue_date

            if "expiry_date" in data:
                expiry_date = data["expiry_date"]
                if expiry_date and isinstance(expiry_date, str):
                    expiry_date = date.fromisoformat(expiry_date)
                certification.expiry_date = expiry_date

            if "credential_id" in data:
                certification.credential_id = data["credential_id"]

            if "credential_url" in data:
                certification.credential_url = data["credential_url"]

            db.session.commit()

            logger.info(
                f"Updated certification {certification_id} for user_id={user_id}"
            )
            return certification.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error updating certification {certification_id}: {str(e)}"
            )
            raise

    @staticmethod
    def delete_certification(user_id: int, certification_id: int) -> bool:
        """
        Delete a certification.

        Args:
            user_id: User ID
            certification_id: Certification ID

        Returns:
            True if deleted, False if not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                return False

            certification = (
                db.session.query(Certification)
                .filter_by(id=certification_id, profile_id=profile.id)
                .first()
            )

            if not certification:
                return False

            db.session.delete(certification)
            db.session.commit()

            logger.info(
                f"Deleted certification {certification_id} for user_id={user_id}"
            )
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error deleting certification {certification_id}: {str(e)}"
            )
            raise

    # ===== Projects Management =====

    @staticmethod
    def get_projects(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all projects for a user.

        Args:
            user_id: User ID

        Returns:
            List of project dictionaries
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return []

            return [proj.to_dict() for proj in profile.projects]

        except SQLAlchemyError as e:
            logger.error(
                f"Database error retrieving projects for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def add_project(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a project to user's profile.

        Args:
            user_id: User ID
            data: Project data (name, description, technologies, url, repository_url, start_date, end_date, is_ongoing)

        Returns:
            Created project dictionary

        Raises:
            ValueError: If validation fails or profile not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                raise ValueError("Profile not found")

            # Validate required fields
            if not data.get("name"):
                raise ValueError("Project name is required")

            # Validate field lengths
            if len(data["name"]) > 200:
                raise ValueError("Project name must be 200 characters or less")

            # Handle technologies - can be list or comma-separated string
            technologies = data.get("technologies")
            if isinstance(technologies, list):
                technologies = ",".join(technologies)

            # Parse dates
            start_date = data.get("start_date")
            if start_date and isinstance(start_date, str):
                start_date = date.fromisoformat(start_date)

            end_date = data.get("end_date")
            if end_date and isinstance(end_date, str):
                end_date = date.fromisoformat(end_date)

            # Create project
            project = Project(
                profile_id=profile.id,
                name=data["name"],
                description=data.get("description"),
                technologies=technologies,
                url=data.get("url"),
                repository_url=data.get("repository_url"),
                start_date=start_date,
                end_date=end_date,
                is_ongoing=data.get("is_ongoing", False),
            )

            db.session.add(project)
            db.session.commit()

            logger.info(f"Added project for user_id={user_id}: {project.name}")
            return project.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error adding project for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_project(
        user_id: int, project_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a project.

        Args:
            user_id: User ID
            project_id: Project ID
            data: Updated data

        Returns:
            Updated project dictionary or None if not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                return None

            project = (
                db.session.query(Project)
                .filter_by(id=project_id, profile_id=profile.id)
                .first()
            )

            if not project:
                return None

            # Update fields
            if "name" in data:
                if len(data["name"]) > 200:
                    raise ValueError("Project name must be 200 characters or less")
                project.name = data["name"]

            if "description" in data:
                project.description = data["description"]

            if "technologies" in data:
                technologies = data["technologies"]
                if isinstance(technologies, list):
                    technologies = ",".join(technologies)
                project.technologies = technologies

            if "url" in data:
                project.url = data["url"]

            if "repository_url" in data:
                project.repository_url = data["repository_url"]

            if "start_date" in data:
                start_date = data["start_date"]
                if start_date and isinstance(start_date, str):
                    start_date = date.fromisoformat(start_date)
                project.start_date = start_date

            if "end_date" in data:
                end_date = data["end_date"]
                if end_date and isinstance(end_date, str):
                    end_date = date.fromisoformat(end_date)
                project.end_date = end_date

            if "is_ongoing" in data:
                project.is_ongoing = data["is_ongoing"]

            db.session.commit()

            logger.info(f"Updated project {project_id} for user_id={user_id}")
            return project.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating project {project_id}: {str(e)}")
            raise

    @staticmethod
    def delete_project(user_id: int, project_id: int) -> bool:
        """
        Delete a project.

        Args:
            user_id: User ID
            project_id: Project ID

        Returns:
            True if deleted, False if not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                return False

            project = (
                db.session.query(Project)
                .filter_by(id=project_id, profile_id=profile.id)
                .first()
            )

            if not project:
                return False

            db.session.delete(project)
            db.session.commit()

            logger.info(f"Deleted project {project_id} for user_id={user_id}")
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error deleting project {project_id}: {str(e)}")
            raise

    # ===== Languages Management =====

    @staticmethod
    def get_languages(user_id: int) -> List[Dict[str, Any]]:
        """
        Get all languages for a user.

        Args:
            user_id: User ID

        Returns:
            List of language dictionaries
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()

            if not profile:
                logger.warning(f"Profile not found for user_id={user_id}")
                return []

            return [lang.to_dict() for lang in profile.languages]

        except SQLAlchemyError as e:
            logger.error(
                f"Database error retrieving languages for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def add_language(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a language to user's profile.

        Args:
            user_id: User ID
            data: Language data (name, proficiency_level)

        Returns:
            Created language dictionary

        Raises:
            ValueError: If validation fails or profile not found or duplicate language
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                raise ValueError("Profile not found")

            # Validate required fields
            if not data.get("name"):
                raise ValueError("Language name is required")

            # Validate field length
            if len(data["name"]) > 50:
                raise ValueError("Language name must be 50 characters or less")

            # Validate proficiency level
            proficiency_level = data.get("proficiency_level", "professional_working")
            if proficiency_level not in Language.PROFICIENCY_LEVELS:
                raise ValueError(
                    f"proficiency_level must be one of: {', '.join(Language.PROFICIENCY_LEVELS)}"
                )

            # Check for duplicate
            existing = (
                db.session.query(Language)
                .filter_by(profile_id=profile.id, name=data["name"])
                .first()
            )

            if existing:
                raise ValueError(f"Language '{data['name']}' already exists")

            # Create language
            language = Language(
                profile_id=profile.id,
                name=data["name"],
                proficiency_level=proficiency_level,
            )

            db.session.add(language)
            db.session.commit()

            logger.info(f"Added language for user_id={user_id}: {language.name}")
            return language.to_dict()

        except IntegrityError as e:
            db.session.rollback()
            if "uq_language_profile_name" in str(e):
                raise ValueError(f"Language '{data.get('name')}' already exists")
            raise
        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error adding language for user_id={user_id}: {str(e)}"
            )
            raise

    @staticmethod
    def update_language(
        user_id: int, language_id: int, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a language.

        Args:
            user_id: User ID
            language_id: Language ID
            data: Updated data

        Returns:
            Updated language dictionary or None if not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                return None

            language = (
                db.session.query(Language)
                .filter_by(id=language_id, profile_id=profile.id)
                .first()
            )

            if not language:
                return None

            # Update fields
            if "name" in data:
                if len(data["name"]) > 50:
                    raise ValueError("Language name must be 50 characters or less")
                language.name = data["name"]

            if "proficiency_level" in data:
                if data["proficiency_level"] not in Language.PROFICIENCY_LEVELS:
                    raise ValueError(
                        f"proficiency_level must be one of: {', '.join(Language.PROFICIENCY_LEVELS)}"
                    )
                language.proficiency_level = data["proficiency_level"]

            db.session.commit()

            logger.info(f"Updated language {language_id} for user_id={user_id}")
            return language.to_dict()

        except ValueError:
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error updating language {language_id}: {str(e)}")
            raise

    @staticmethod
    def delete_language(user_id: int, language_id: int) -> bool:
        """
        Delete a language.

        Args:
            user_id: User ID
            language_id: Language ID

        Returns:
            True if deleted, False if not found
        """
        try:
            profile = db.session.query(Profile).filter_by(user_id=user_id).first()
            if not profile:
                return False

            language = (
                db.session.query(Language)
                .filter_by(id=language_id, profile_id=profile.id)
                .first()
            )

            if not language:
                return False

            db.session.delete(language)
            db.session.commit()

            logger.info(f"Deleted language {language_id} for user_id={user_id}")
            return True

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error deleting language {language_id}: {str(e)}")
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(
                f"Database error bulk deleting skills for user_id={user_id}: {str(e)}"
            )
            raise
