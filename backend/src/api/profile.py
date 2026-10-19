"""
Profile API Endpoints
=====================
API endpoints for user profile management.
"""

import logging
from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from src.services.profile_service import ProfileService
from src.middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.route("", methods=["GET"])
@require_auth
def get_profile(user_id, email):
    """
    Get user's profile information.

    Authentication: Required (JWT)

    Query Parameters:
        include_details (bool): Include work experience, education, and skills (default: false)

    Returns:
        200: Profile data
        401: Unauthorized
        404: Profile not found
        500: Server error

    Example Response:
        {
            "id": 1,
            "user_id": 123,
            "summary": "Experienced software engineer...",
            "phone": "+1234567890",
            "location": "New York, NY",
            "preferences": {...},
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-10T12:00:00"
        }
    """
    try:
        # user_id is automatically injected from JWT token by @require_auth
        include_details = request.args.get("include_details", "false").lower() == "true"

        profile = ProfileService.get_profile(user_id, include_details=include_details)

        if not profile:
            return jsonify(
                {"error": "PROFILE_NOT_FOUND", "message": f"Profile not found for user"}
            ), 404

        return jsonify(profile), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_profile: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while retrieving the profile",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_profile: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("", methods=["PUT"])
@require_auth
def update_profile(user_id, email):
    """
    Update user's profile information.

    Authentication: Required (JWT)

    Request Body:
        {
            "summary": "Professional summary (optional)",
            "phone": "Phone number (optional)",
            "location": "Location (optional)"
        }

    Returns:
        200: Updated profile data
        400: Validation error
        401: Unauthorized
        404: Profile not found
        500: Server error

    Example Response:
        {
            "id": 1,
            "user_id": 123,
            "summary": "Updated summary",
            "phone": "+1234567890",
            "location": "San Francisco, CA",
            "preferences": {...},
            "updated_at": "2025-01-15T14:30:00"
        }
    """
    try:
        # Get request data
        try:
            data = request.get_json()
        except Exception:
            # Handle missing or invalid Content-Type
            data = None

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        # Validate that only allowed fields are provided
        allowed_fields = {"summary", "phone", "location"}
        extra_fields = set(data.keys()) - allowed_fields
        if extra_fields:
            return jsonify(
                {
                    "error": "INVALID_FIELDS",
                    "message": f"Invalid fields: {', '.join(extra_fields)}. Allowed: {', '.join(allowed_fields)}",
                }
            ), 400

        profile = ProfileService.update_profile(user_id, data)

        if not profile:
            return jsonify(
                {
                    "error": "PROFILE_NOT_FOUND",
                    "message": f"Profile not found for user_id={user_id}",
                }
            ), 404

        return jsonify(profile), 200

    except ValueError as e:
        logger.warning(f"Validation error in update_profile: {str(e)}")
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_profile: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while updating the profile",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in update_profile: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/preferences", methods=["GET"])
@require_auth
def get_preferences(user_id, email):
    """
    Get user's job search preferences.

    Authentication: Required (JWT)

    Returns:
        200: Preferences data
        401: Unauthorized
        404: Profile not found
        500: Server error

    Example Response:
        {
            "user_id": 123,
            "preferences": {
                "desired_roles": ["Software Engineer", "Backend Developer"],
                "locations": ["New York, NY", "Remote"],
                "job_types": ["full-time", "remote"],
                "min_salary": 100000,
                "max_salary": 150000,
                "experience_level": "senior"
            }
        }
    """
    try:
        preferences = ProfileService.get_preferences(user_id)

        if not preferences:
            return jsonify(
                {
                    "error": "PROFILE_NOT_FOUND",
                    "message": f"Profile not found for user_id={user_id}",
                }
            ), 404

        return jsonify(preferences), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_preferences: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while retrieving preferences",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_preferences: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/preferences", methods=["PUT"])
@require_auth
def update_preferences(user_id, email):
    """
    Update user's job search preferences.

    Authentication: Required (JWT)

    Request Body:
        {
            "desired_roles": ["Job Title 1", "Job Title 2"],
            "locations": ["City 1", "City 2"],
            "job_types": ["full-time", "remote", "contract", "part-time"],
            "min_salary": 80000,
            "max_salary": 120000,
            "experience_level": "mid-level"
        }

    Returns:
        200: Updated preferences
        400: Validation error
        401: Unauthorized
        404: Profile not found
        500: Server error

    Example Response:
        {
            "user_id": 123,
            "preferences": {
                "desired_roles": ["Software Engineer"],
                "locations": ["Remote"],
                "job_types": ["remote", "full-time"],
                "min_salary": 100000,
                "max_salary": 150000
            }
        }
    """
    try:
        # Get preferences data
        try:
            preferences = request.get_json()
        except Exception:
            # Handle missing or invalid Content-Type
            preferences = None

        if not preferences:
            return jsonify(
                {
                    "error": "MISSING_DATA",
                    "message": "Request body with preferences is required",
                }
            ), 400

        result = ProfileService.update_preferences(user_id, preferences)

        if not result:
            return jsonify(
                {
                    "error": "PROFILE_NOT_FOUND",
                    "message": f"Profile not found for user_id={user_id}",
                }
            ), 404

        return jsonify(result), 200

    except ValueError as e:
        logger.warning(f"Validation error in update_preferences: {str(e)}")
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_preferences: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while updating preferences",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in update_preferences: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


# Work Experience Endpoints


@profile_bp.route("/experience", methods=["GET"])
@require_auth
def get_work_experiences(user_id, email):
    """
    Get all work experiences for a user.

    Authentication: Required (JWT)

    Returns:
        200: List of work experiences
        401: Unauthorized
        500: Server error

    Example Response:
        [
            {
                "id": 1,
                "profile_id": 123,
                "job_title": "Senior Software Engineer",
                "company": "Tech Corp",
                "start_date": "2020-01-01",
                "end_date": "2023-12-31",
                "is_current": false,
                "description": "Led development of...",
                "created_at": "2025-01-01T00:00:00"
            }
        ]
    """
    try:
        experiences = ProfileService.get_work_experiences(user_id)
        return jsonify(experiences), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_work_experiences: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while retrieving work experiences",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_work_experiences: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/experience", methods=["POST"])
@require_auth
def add_work_experience(user_id, email):
    """
    Add a work experience entry.

    Authentication: Required (JWT)

    Request Body:
        {
            "job_title": "Senior Software Engineer",
            "company": "Tech Corp",
            "start_date": "2020-01-01",
            "end_date": "2023-12-31",  # Optional, null for current position
            "description": "Led development of..."  # Optional
        }

    Returns:
        201: Created work experience
        400: Validation error or missing required fields
        401: Unauthorized
        404: Profile not found
        500: Server error
    """
    try:
        try:
            data = request.get_json()
        except Exception:
            data = None

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        experience = ProfileService.add_work_experience(user_id, data)
        return jsonify(experience), 201

    except ValueError as e:
        logger.warning(f"Validation error in add_work_experience: {str(e)}")
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in add_work_experience: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while adding work experience",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_work_experience: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/experience/<int:experience_id>", methods=["PUT"])
@require_auth
def update_work_experience(user_id, email, experience_id):
    """
    Update a work experience entry.

    Authentication: Required (JWT)

    Path Parameters:
        experience_id (int): Work experience ID

    Request Body (all fields optional):
        {
            "job_title": "Lead Software Engineer",
            "company": "New Tech Corp",
            "start_date": "2020-01-01",
            "end_date": "2024-01-01",
            "description": "Updated description..."
        }

    Returns:
        200: Updated work experience
        400: Validation error
        401: Unauthorized
        404: Work experience not found or not owned by user
        500: Server error
    """
    try:
        try:
            data = request.get_json()
        except Exception:
            data = None

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        experience = ProfileService.update_work_experience(user_id, experience_id, data)

        if not experience:
            return jsonify(
                {
                    "error": "NOT_FOUND",
                    "message": f"Work experience {experience_id} not found or not owned by user",
                }
            ), 404

        return jsonify(experience), 200

    except ValueError as e:
        logger.warning(f"Validation error in update_work_experience: {str(e)}")
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_work_experience: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while updating work experience",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in update_work_experience: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/experience/<int:experience_id>", methods=["DELETE"])
@require_auth
def delete_work_experience(user_id, email, experience_id):
    """
    Delete a work experience entry.

    Authentication: Required (JWT)

    Path Parameters:
        experience_id (int): Work experience ID

    Returns:
        204: Successfully deleted
        401: Unauthorized
        404: Work experience not found or not owned by user
        500: Server error
    """
    try:
        deleted = ProfileService.delete_work_experience(user_id, experience_id)

        if not deleted:
            return jsonify(
                {
                    "error": "NOT_FOUND",
                    "message": f"Work experience {experience_id} not found or not owned by user",
                }
            ), 404

        return "", 204

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_work_experience: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while deleting work experience",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in delete_work_experience: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


# ===== Education Endpoints =====


@profile_bp.route("/education", methods=["GET"])
@require_auth
def get_education(user_id, email):
    """
    Get all education entries for a user.

    Authentication: Required (JWT)

    Returns:
        200: List of education entries
        401: Unauthorized
        500: Server error
    """
    try:
        education_list = ProfileService.get_education(user_id)
        return jsonify(education_list), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_education: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while retrieving education",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_education: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/education", methods=["POST"])
@require_auth
def add_education(user_id, email):
    """
    Add education entry to user's profile.

    Authentication: Required (JWT)

    Request Body:
        degree (str): Degree name (required, max 100 chars)
        institution (str): Institution name (required, max 100 chars)
        field_of_study (str): Field of study (optional, max 100 chars)
        start_date (str): Start date in ISO format YYYY-MM-DD (required)
        end_date (str): End date in ISO format YYYY-MM-DD (optional)

    Returns:
        201: Education entry created
        400: Validation error or missing data
        401: Unauthorized
        404: Profile not found
        500: Server error
    """
    try:
        try:
            data = request.get_json()
        except Exception:
            data = None

        if not data:
            return jsonify(
                {
                    "error": "MISSING_DATA",
                    "message": "Request body with education data is required",
                }
            ), 400

        education = ProfileService.add_education(user_id, data)
        return jsonify(education), 201

    except ValueError as e:
        logger.warning(f"Validation error in add_education: {str(e)}")
        error_msg = str(e)
        if "Profile not found" in error_msg:
            return jsonify({"error": "PROFILE_NOT_FOUND", "message": error_msg}), 404
        return jsonify({"error": "VALIDATION_ERROR", "message": error_msg}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in add_education: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while adding education",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_education: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/education/<int:education_id>", methods=["PUT"])
@require_auth
def update_education(user_id, email, education_id):
    """
    Update education entry.

    Authentication: Required (JWT)

    Path Parameters:
        education_id (int): Education entry ID

    Request Body (all fields optional for partial update):
        degree (str): Degree name (max 100 chars)
        institution (str): Institution name (max 100 chars)
        field_of_study (str): Field of study (max 100 chars)
        start_date (str): Start date in ISO format YYYY-MM-DD
        end_date (str): End date in ISO format YYYY-MM-DD

    Returns:
        200: Education entry updated
        400: Validation error or missing data
        401: Unauthorized
        404: Education not found or not owned by user
        500: Server error
    """
    try:
        try:
            data = request.get_json()
        except Exception:
            data = None

        if not data:
            return jsonify(
                {
                    "error": "MISSING_DATA",
                    "message": "Request body with education data is required",
                }
            ), 400

        education = ProfileService.update_education(user_id, education_id, data)
        return jsonify(education), 200

    except ValueError as e:
        logger.warning(f"Validation error in update_education: {str(e)}")
        error_msg = str(e)
        if "not found" in error_msg.lower():
            return jsonify({"error": "NOT_FOUND", "message": error_msg}), 404
        return jsonify({"error": "VALIDATION_ERROR", "message": error_msg}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_education: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while updating education",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in update_education: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/education/<int:education_id>", methods=["DELETE"])
@require_auth
def delete_education(user_id, email, education_id):
    """
    Delete education entry.

    Authentication: Required (JWT)

    Path Parameters:
        education_id (int): Education entry ID

    Returns:
        204: Education entry deleted (no content)
        401: Unauthorized
        404: Education not found or not owned by user
        500: Server error
    """
    try:
        deleted = ProfileService.delete_education(user_id, education_id)

        if not deleted:
            return jsonify(
                {
                    "error": "NOT_FOUND",
                    "message": f"Education entry {education_id} not found or not owned by user",
                }
            ), 404

        return "", 204

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_education: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while deleting education",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in delete_education: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


# ===== Skills Endpoints =====


@profile_bp.route("/skills", methods=["GET"])
@require_auth
def get_skills(user_id, email):
    """
    Get all skills for a user.

    Authentication: Required (JWT)

    Returns:
        200: List of skills
        401: Unauthorized
        500: Server error
    """
    try:
        skills_list = ProfileService.get_skills(user_id)
        return jsonify(skills_list), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_skills: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while retrieving skills",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_skills: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/skills", methods=["POST"])
@require_auth
def add_skills(user_id, email):
    """
    Add skill(s) to user's profile. Supports both single skill and bulk add.

    Authentication: Required (JWT)

    Request Body (Single Skill):
        name (str): Skill name (required, max 50 chars)
        proficiency_level (str): Proficiency level (optional, default: intermediate)
                                 Values: beginner, intermediate, advanced, expert

    Request Body (Bulk Add):
        skills (list): Array of skill objects with name and optional proficiency_level

    Returns:
        201: Skill(s) created
        400: Validation error or missing data
        401: Unauthorized
        404: Profile not found
        500: Server error
    """
    try:
        try:
            data = request.get_json()
        except Exception:
            data = None

        if not data:
            return jsonify(
                {
                    "error": "MISSING_DATA",
                    "message": "Request body with skill data is required",
                }
            ), 400

        # Check if bulk add (has 'skills' array) or single add
        if "skills" in data and isinstance(data["skills"], list):
            # Bulk add
            skills = ProfileService.add_skills_bulk(user_id, data["skills"])
            return jsonify(skills), 201
        else:
            # Single add
            skill = ProfileService.add_skill(user_id, data)
            return jsonify(skill), 201

    except ValueError as e:
        logger.warning(f"Validation error in add_skills: {str(e)}")
        error_msg = str(e)
        if "Profile not found" in error_msg:
            return jsonify({"error": "PROFILE_NOT_FOUND", "message": error_msg}), 404
        return jsonify({"error": "VALIDATION_ERROR", "message": error_msg}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in add_skills: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while adding skills",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_skills: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/skills/<int:skill_id>", methods=["DELETE"])
@require_auth
def delete_skill(user_id, email, skill_id):
    """
    Delete skill.

    Authentication: Required (JWT)

    Path Parameters:
        skill_id (int): Skill ID

    Returns:
        204: Skill deleted (no content)
        401: Unauthorized
        404: Skill not found or not owned by user
        500: Server error
    """
    try:
        deleted = ProfileService.delete_skill(user_id, skill_id)

        if not deleted:
            return jsonify(
                {
                    "error": "NOT_FOUND",
                    "message": f"Skill {skill_id} not found or not owned by user",
                }
            ), 404

        return "", 204

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_skill: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while deleting skill",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in delete_skill: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/skills/bulk-delete", methods=["POST"])
@require_auth
def delete_skills_bulk(user_id, email):
    """
    Delete multiple skills.

    Authentication: Required (JWT)

    Request Body:
        skill_ids (list): Array of skill IDs to delete

    Returns:
        200: Bulk delete result with deleted count and failed IDs
        400: Validation error or missing data
        401: Unauthorized
        500: Server error
    """
    try:
        try:
            data = request.get_json()
        except Exception:
            data = None

        if not data or "skill_ids" not in data:
            return jsonify(
                {
                    "error": "MISSING_DATA",
                    "message": "Request body with skill_ids array is required",
                }
            ), 400

        result = ProfileService.delete_skills_bulk(user_id, data["skill_ids"])
        return jsonify(result), 200

    except ValueError as e:
        logger.warning(f"Validation error in delete_skills_bulk: {str(e)}")
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_skills_bulk: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while deleting skills",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in delete_skills_bulk: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


# ===== Certifications Endpoints =====


@profile_bp.route("/certifications", methods=["GET"])
@require_auth
def get_certifications(user_id, email):
    """
    Get all certifications for a user.

    Authentication: Required (JWT)

    Returns:
        200: List of certifications
        401: Unauthorized
        500: Server error
    """
    try:
        certifications = ProfileService.get_certifications(user_id)
        return jsonify(certifications), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_certifications: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while retrieving certifications",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_certifications: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/certifications", methods=["POST"])
@require_auth
def add_certification(user_id, email):
    """
    Add a certification to user's profile.

    Authentication: Required (JWT)

    Request Body:
        name (str): Certification name (required)
        issuing_organization (str): Issuing organization (required)
        issue_date (str): Issue date in ISO format YYYY-MM-DD (required)
        expiry_date (str): Expiry date in ISO format YYYY-MM-DD (optional)
        credential_id (str): Credential ID (optional)
        credential_url (str): Credential URL (optional)

    Returns:
        201: Certification created
        400: Validation error
        401: Unauthorized
        404: Profile not found
        500: Server error
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        certification = ProfileService.add_certification(user_id, data)
        return jsonify(certification), 201

    except ValueError as e:
        error_msg = str(e)
        if "Profile not found" in error_msg:
            return jsonify({"error": "PROFILE_NOT_FOUND", "message": error_msg}), 404
        return jsonify({"error": "VALIDATION_ERROR", "message": error_msg}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in add_certification: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while adding certification",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_certification: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/certifications/<int:certification_id>", methods=["PUT"])
@require_auth
def update_certification(user_id, email, certification_id):
    """
    Update a certification.

    Authentication: Required (JWT)

    Returns:
        200: Updated certification
        400: Validation error
        401: Unauthorized
        404: Certification not found
        500: Server error
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        certification = ProfileService.update_certification(
            user_id, certification_id, data
        )

        if not certification:
            return jsonify(
                {
                    "error": "NOT_FOUND",
                    "message": f"Certification {certification_id} not found",
                }
            ), 404

        return jsonify(certification), 200

    except ValueError as e:
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_certification: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while updating certification",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in update_certification: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/certifications/<int:certification_id>", methods=["DELETE"])
@require_auth
def delete_certification(user_id, email, certification_id):
    """
    Delete a certification.

    Authentication: Required (JWT)

    Returns:
        204: Certification deleted
        401: Unauthorized
        404: Certification not found
        500: Server error
    """
    try:
        deleted = ProfileService.delete_certification(user_id, certification_id)

        if not deleted:
            return jsonify(
                {
                    "error": "NOT_FOUND",
                    "message": f"Certification {certification_id} not found",
                }
            ), 404

        return "", 204

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_certification: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while deleting certification",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in delete_certification: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


# ===== Projects Endpoints =====


@profile_bp.route("/projects", methods=["GET"])
@require_auth
def get_projects(user_id, email):
    """
    Get all projects for a user.

    Authentication: Required (JWT)

    Returns:
        200: List of projects
        401: Unauthorized
        500: Server error
    """
    try:
        projects = ProfileService.get_projects(user_id)
        return jsonify(projects), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_projects: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while retrieving projects",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_projects: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/projects", methods=["POST"])
@require_auth
def add_project(user_id, email):
    """
    Add a project to user's profile.

    Authentication: Required (JWT)

    Request Body:
        name (str): Project name (required)
        description (str): Project description (optional)
        technologies (list or str): Technologies used (optional)
        url (str): Project URL (optional)
        repository_url (str): Repository URL (optional)
        start_date (str): Start date in ISO format YYYY-MM-DD (optional)
        end_date (str): End date in ISO format YYYY-MM-DD (optional)
        is_ongoing (bool): Whether project is ongoing (optional)

    Returns:
        201: Project created
        400: Validation error
        401: Unauthorized
        404: Profile not found
        500: Server error
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        project = ProfileService.add_project(user_id, data)
        return jsonify(project), 201

    except ValueError as e:
        error_msg = str(e)
        if "Profile not found" in error_msg:
            return jsonify({"error": "PROFILE_NOT_FOUND", "message": error_msg}), 404
        return jsonify({"error": "VALIDATION_ERROR", "message": error_msg}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in add_project: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while adding project",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_project: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/projects/<int:project_id>", methods=["PUT"])
@require_auth
def update_project(user_id, email, project_id):
    """
    Update a project.

    Authentication: Required (JWT)

    Returns:
        200: Updated project
        400: Validation error
        401: Unauthorized
        404: Project not found
        500: Server error
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        project = ProfileService.update_project(user_id, project_id, data)

        if not project:
            return jsonify(
                {"error": "NOT_FOUND", "message": f"Project {project_id} not found"}
            ), 404

        return jsonify(project), 200

    except ValueError as e:
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_project: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while updating project",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in update_project: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/projects/<int:project_id>", methods=["DELETE"])
@require_auth
def delete_project(user_id, email, project_id):
    """
    Delete a project.

    Authentication: Required (JWT)

    Returns:
        204: Project deleted
        401: Unauthorized
        404: Project not found
        500: Server error
    """
    try:
        deleted = ProfileService.delete_project(user_id, project_id)

        if not deleted:
            return jsonify(
                {"error": "NOT_FOUND", "message": f"Project {project_id} not found"}
            ), 404

        return "", 204

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_project: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while deleting project",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in delete_project: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


# ===== Languages Endpoints =====


@profile_bp.route("/languages", methods=["GET"])
@require_auth
def get_languages(user_id, email):
    """
    Get all languages for a user.

    Authentication: Required (JWT)

    Returns:
        200: List of languages
        401: Unauthorized
        500: Server error
    """
    try:
        languages = ProfileService.get_languages(user_id)
        return jsonify(languages), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_languages: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while retrieving languages",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in get_languages: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/languages", methods=["POST"])
@require_auth
def add_language(user_id, email):
    """
    Add a language to user's profile.

    Authentication: Required (JWT)

    Request Body:
        name (str): Language name (required)
        proficiency_level (str): Proficiency level (optional)
            Values: elementary, limited_working, professional_working, full_professional, native

    Returns:
        201: Language created
        400: Validation error or duplicate language
        401: Unauthorized
        404: Profile not found
        500: Server error
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        language = ProfileService.add_language(user_id, data)
        return jsonify(language), 201

    except ValueError as e:
        error_msg = str(e)
        if "Profile not found" in error_msg:
            return jsonify({"error": "PROFILE_NOT_FOUND", "message": error_msg}), 404
        return jsonify({"error": "VALIDATION_ERROR", "message": error_msg}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in add_language: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while adding language",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in add_language: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/languages/<int:language_id>", methods=["PUT"])
@require_auth
def update_language(user_id, email, language_id):
    """
    Update a language.

    Authentication: Required (JWT)

    Returns:
        200: Updated language
        400: Validation error
        401: Unauthorized
        404: Language not found
        500: Server error
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(
                {"error": "MISSING_DATA", "message": "Request body is required"}
            ), 400

        language = ProfileService.update_language(user_id, language_id, data)

        if not language:
            return jsonify(
                {"error": "NOT_FOUND", "message": f"Language {language_id} not found"}
            ), 404

        return jsonify(language), 200

    except ValueError as e:
        return jsonify({"error": "VALIDATION_ERROR", "message": str(e)}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in update_language: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while updating language",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in update_language: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500


@profile_bp.route("/languages/<int:language_id>", methods=["DELETE"])
@require_auth
def delete_language(user_id, email, language_id):
    """
    Delete a language.

    Authentication: Required (JWT)

    Returns:
        204: Language deleted
        401: Unauthorized
        404: Language not found
        500: Server error
    """
    try:
        deleted = ProfileService.delete_language(user_id, language_id)

        if not deleted:
            return jsonify(
                {"error": "NOT_FOUND", "message": f"Language {language_id} not found"}
            ), 404

        return "", 204

    except SQLAlchemyError as e:
        logger.error(f"Database error in delete_language: {str(e)}")
        return jsonify(
            {
                "error": "DATABASE_ERROR",
                "message": "An error occurred while deleting language",
            }
        ), 500
    except Exception as e:
        logger.error(f"Unexpected error in delete_language: {str(e)}")
        return jsonify(
            {"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}
        ), 500
