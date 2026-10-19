"""
Jobs API Blueprint
==================
REST API endpoints for job search and favorites.
"""

import logging

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from src.middleware.auth_middleware import require_auth
from src.services.job_service import JobService

logger = logging.getLogger(__name__)

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


@jobs_bp.route("/search", methods=["GET"])
@require_auth
def search_jobs(user_id, email):
    """
    Search for jobs with filters.

    Requires authentication (JWT access token).

    Query Parameters:
        - q (str, optional): Search query for title, company, description, requirements
        - location (str, optional): Location filter (partial match)
        - job_type (str, optional): Comma-separated job types (e.g., "full-time,remote")
        - salary_min (int, optional): Minimum salary filter
        - salary_max (int, optional): Maximum salary filter
        - page (int, optional): Page number (default: 1)
        - page_size (int, optional): Results per page (default: 20, max: 100)
        - sort_by (str, optional): Sort option - relevance, date, salary_min, salary_max (default: relevance)

    Returns:
        200: Search results with pagination and favorite status
        400: Validation error
        401: Unauthorized (missing/invalid token)
        500: Server error
    """
    try:
        # Extract query parameters
        query = request.args.get("q")  # Changed from 'query' to 'q' for brevity
        location = request.args.get("location")
        job_type_str = request.args.get("job_type")
        sort_by = request.args.get("sort_by", "relevance")

        # Parse multiple job types (comma-separated)
        job_types = None
        if job_type_str:
            job_types = [jt.strip() for jt in job_type_str.split(",") if jt.strip()]

        # Parse numeric parameters
        try:
            salary_min = int(request.args.get("salary_min")) if request.args.get("salary_min") else None
            salary_max = int(request.args.get("salary_max")) if request.args.get("salary_max") else None
            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 20))
        except ValueError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "salary_min, salary_max, page, and page_size must be integers",
                        },
                    }
                ),
                400,
            )

        # Validate salary range
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "salary_min cannot be greater than salary_max",
                        },
                    }
                ),
                400,
            )

        # Search jobs with user_id for favorite status
        result = JobService.search_jobs(
            query=query,
            location=location,
            job_types=job_types,
            salary_min=salary_min,
            salary_max=salary_max,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            user_id=user_id,
        )

        # Transform to expected API format
        response = {
            "success": True,
            "data": {
                "data": result["jobs"],
                "total": result["pagination"]["total"],
                "limit": result["pagination"]["page_size"],
                "offset": (result["pagination"]["page"] - 1) * result["pagination"]["page_size"],
            },
        }

        return jsonify(response), 200

    except ValueError as e:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error in search_jobs: {str(e)}")
        return jsonify({"success": False, "error": {"code": "DATABASE_ERROR", "message": "Failed to search jobs"}}), 500
    except Exception as e:
        logger.error(f"Unexpected error in search_jobs: {str(e)}")
        return (
            jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}),
            500,
        )


@jobs_bp.route("/<int:job_id>", methods=["GET"])
@require_auth
def get_job(user_id, email, job_id):
    """
    Get job details by ID.

    Requires authentication (JWT access token).

    Path Parameters:
        - job_id (int): Job ID

    Returns:
        200: Job details with favorite status
        401: Unauthorized (missing/invalid token)
        404: Job not found
        500: Server error
    """
    try:
        # Get job with favorite status for current user
        job = JobService.get_job_by_id(job_id, user_id=user_id)

        if not job:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {"code": "NOT_FOUND", "message": "Job not found or no longer available"},
                    }
                ),
                404,
            )

        return jsonify({"success": True, "data": job}), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error getting job {job_id}: {str(e)}")
        return (
            jsonify({"success": False, "error": {"code": "DATABASE_ERROR", "message": "Failed to retrieve job"}}),
            500,
        )
    except Exception as e:
        logger.error(f"Unexpected error getting job {job_id}: {str(e)}")
        return (
            jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}),
            500,
        )


@jobs_bp.route("/favorites", methods=["GET"])
@require_auth
def get_favorites(user_id, email):
    """
    Get user's favorite jobs.

    Requires authentication (JWT access token).
    User ID is extracted from JWT token.

    Query Parameters:
        - page (int, optional): Page number (default: 1)
        - page_size (int, optional): Results per page (default: 20, max: 100)

    Returns:
        200: List of favorite jobs with pagination
        400: Validation error
        401: Unauthorized (missing/invalid token)
        500: Server error
    """
    try:
        try:
            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 20))
        except ValueError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {"code": "VALIDATION_ERROR", "message": "page and page_size must be integers"},
                    }
                ),
                400,
            )

        # Get favorites using user_id from JWT
        result = JobService.get_favorite_jobs(user_id=user_id, page=page, page_size=page_size)

        # Transform to expected API format
        response = {
            "success": True,
            "data": {
                "data": result["favorites"],
                "total": result["pagination"]["total_count"],
                "limit": result["pagination"]["page_size"],
                "offset": (result["pagination"]["page"] - 1) * result["pagination"]["page_size"],
            },
        }

        return jsonify(response), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error getting favorites: {str(e)}")
        return (
            jsonify({"success": False, "error": {"code": "DATABASE_ERROR", "message": "Failed to retrieve favorites"}}),
            500,
        )
    except Exception as e:
        logger.error(f"Unexpected error getting favorites: {str(e)}")
        return (
            jsonify({"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"}}),
            500,
        )


@jobs_bp.route("/<int:job_id>/favorite", methods=["POST"])
@require_auth
def add_favorite(user_id, email, job_id):
    """
    Add job to favorites.

    Requires authentication (JWT access token).
    User ID is extracted from JWT token.

    Path Parameters:
        - job_id (int): Job ID

    Request Body (optional):
        {
            "notes": "Optional user notes"
        }

    Returns:
        201: Job added to favorites
        400: Validation error or already favorited
        401: Unauthorized (missing/invalid token)
        404: User or job not found
        500: Server error
    """
    try:
        # Get optional notes from request body
        notes = None
        if request.content_type and "application/json" in request.content_type:
            data = request.get_json(silent=True) or {}
            notes = data.get("notes")

        # Validate notes length
        if notes and len(notes) > 1000:
            return jsonify({"error": "VALIDATION_ERROR", "message": "Notes cannot exceed 1000 characters"}), 400

        # Add to favorites using user_id from JWT
        favorite = JobService.add_favorite_job(user_id=user_id, job_id=job_id, notes=notes)

        return jsonify(favorite), 201

    except ValueError as e:
        error_msg = str(e)
        if "User not found" in error_msg or "Job not found" in error_msg:
            return jsonify({"error": "NOT_FOUND", "message": error_msg}), 404
        elif "already in favorites" in error_msg:
            return jsonify({"error": "VALIDATION_ERROR", "message": error_msg}), 400
        else:
            return jsonify({"error": "VALIDATION_ERROR", "message": error_msg}), 400
    except SQLAlchemyError as e:
        logger.error(f"Database error adding favorite: {str(e)}")
        return jsonify({"error": "DATABASE_ERROR", "message": "Failed to add job to favorites"}), 500
    except Exception as e:
        logger.error(f"Unexpected error adding favorite: {str(e)}")
        return jsonify({"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}), 500


@jobs_bp.route("/<int:job_id>/favorite", methods=["DELETE"])
@require_auth
def remove_favorite(user_id, email, job_id):
    """
    Remove job from favorites.

    Requires authentication (JWT access token).
    User ID is extracted from JWT token.

    Path Parameters:
        - job_id (int): Job ID

    Returns:
        204: Job removed from favorites
        401: Unauthorized (missing/invalid token)
        404: Favorite not found
        500: Server error
    """
    try:
        # Remove from favorites using user_id from JWT
        removed = JobService.remove_favorite_job(user_id=user_id, job_id=job_id)

        if not removed:
            return jsonify({"error": "NOT_FOUND", "message": "Favorite not found"}), 404

        return "", 204

    except SQLAlchemyError as e:
        logger.error(f"Database error removing favorite: {str(e)}")
        return jsonify({"error": "DATABASE_ERROR", "message": "Failed to remove job from favorites"}), 500
    except Exception as e:
        logger.error(f"Unexpected error removing favorite: {str(e)}")
        return jsonify({"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}), 500


@jobs_bp.route("/<int:job_id>/favorite/notes", methods=["PUT"])
@require_auth
def update_favorite_notes(user_id, email, job_id):
    """
    Update notes for a favorite job.

    Requires authentication (JWT access token).
    User ID is extracted from JWT token.

    Path Parameters:
        - job_id (int): Job ID

    Request Body:
        {
            "notes": "Updated notes"
        }

    Returns:
        200: Notes updated
        400: Validation error
        401: Unauthorized (missing/invalid token)
        404: Favorite not found
        500: Server error
    """
    try:
        # Get notes from request body
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "MISSING_REQUEST_BODY", "message": "Request body is required"}), 400
        except Exception:
            return jsonify({"error": "INVALID_JSON", "message": "Request body must be valid JSON"}), 400

        notes = data.get("notes", "")

        # Validate notes
        if not isinstance(notes, str):
            return jsonify({"error": "VALIDATION_ERROR", "message": "Notes must be a string"}), 400

        if len(notes) > 1000:
            return jsonify({"error": "VALIDATION_ERROR", "message": "Notes cannot exceed 1000 characters"}), 400

        # Update notes using user_id from JWT
        favorite = JobService.update_favorite_notes(user_id=user_id, job_id=job_id, notes=notes)

        if not favorite:
            return jsonify({"error": "NOT_FOUND", "message": "Favorite not found"}), 404

        return jsonify(favorite), 200

    except SQLAlchemyError as e:
        logger.error(f"Database error updating favorite notes: {str(e)}")
        return jsonify({"error": "DATABASE_ERROR", "message": "Failed to update notes"}), 500
    except Exception as e:
        logger.error(f"Unexpected error updating favorite notes: {str(e)}")
        return jsonify({"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"}), 500
