"""
CV API Endpoints
================
Manage CV documents and AI-powered CV generation.
"""

import logging
from functools import wraps
from flask import Blueprint, request, jsonify, current_app, Response
from src.middleware.auth_middleware import require_auth
from src.services.cv_service import CVService
from src.services.pdf_service import PDFService

logger = logging.getLogger(__name__)

cv_bp = Blueprint("cv", __name__, url_prefix="/api/cv")


def rate_limit(limit_string):
    """
    Decorator to apply rate limiting to a route.
    Applies the limit when limiter is available in app context.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if hasattr(current_app, "limiter"):
                # Limiter will be applied via decorator in app.py
                pass
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ===== CV CRUD Endpoints =====


@cv_bp.route("", methods=["GET"])
@require_auth
@rate_limit("30 per minute")
def list_cvs(user_id, email):
    """
    List user's CVs.

    Query Parameters:
        - include_content: Include full CV content (default: false)
        - limit: Number of results (default 20, max 100)
        - offset: Pagination offset (default 0)

    Returns:
        200: { "success": true, "data": { "cvs": [...], "total": N } }
    """
    try:
        # Parse query parameters
        include_content = request.args.get("include_content", "false").lower() == "true"
        limit = min(int(request.args.get("limit", 20)), 100)
        offset = int(request.args.get("offset", 0))

        result = CVService.get_user_cvs(
            user_id=user_id, include_content=include_content, limit=limit, offset=offset
        )

        return jsonify({"success": True, "data": result}), 200

    except ValueError as e:
        return jsonify(
            {
                "success": False,
                "error": {"code": "INVALID_PARAMETERS", "message": str(e)},
            }
        ), 400
    except Exception as e:
        logger.error(f"Error listing CVs for user {user_id}: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": {"code": "CV_LIST_FAILED", "message": "Failed to list CVs"},
            }
        ), 500


@cv_bp.route("/<int:cv_id>", methods=["GET"])
@require_auth
@rate_limit("30 per minute")
def get_cv(user_id, email, cv_id):
    """
    Get a specific CV by ID.

    Returns:
        200: { "success": true, "data": { "cv": {...} } }
        404: { "success": false, "error": { "code": "CV_NOT_FOUND", "message": "..." } }
    """
    try:
        cv = CVService.get_cv(cv_id=cv_id, user_id=user_id, include_content=True)

        if not cv:
            return jsonify(
                {
                    "success": False,
                    "error": {"code": "CV_NOT_FOUND", "message": "CV not found"},
                }
            ), 404

        return jsonify({"success": True, "data": {"cv": cv}}), 200

    except Exception as e:
        logger.error(f"Error getting CV {cv_id}: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": {"code": "CV_GET_FAILED", "message": "Failed to get CV"},
            }
        ), 500


@cv_bp.route("", methods=["POST"])
@require_auth
@rate_limit("10 per minute")
def create_cv(user_id, email):
    """
    Create a new CV manually.

    Request Body:
        {
            "title": "CV Title",
            "content": { ... CV content ... },
            "target_position": "Optional target position"
        }

    Returns:
        201: { "success": true, "data": { "cv": {...} } }
        400: { "success": false, "error": { "code": "...", "message": "..." } }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MISSING_REQUEST_BODY",
                        "message": "Request body is required",
                    },
                }
            ), 400

        title = data.get("title")
        content = data.get("content")
        target_position = data.get("target_position")

        if not title:
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MISSING_TITLE",
                        "message": "CV title is required",
                    },
                }
            ), 400

        if not content:
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MISSING_CONTENT",
                        "message": "CV content is required",
                    },
                }
            ), 400

        cv = CVService.create_cv(
            user_id=user_id,
            title=title,
            content_json=content,
            target_position=target_position,
            is_ai_generated=False,
        )

        logger.info(f"Created CV {cv['id']} for user {user_id}")

        return jsonify({"success": True, "data": {"cv": cv}}), 201

    except ValueError as e:
        return jsonify(
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        ), 400
    except Exception as e:
        logger.error(f"Error creating CV: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": {"code": "CV_CREATE_FAILED", "message": "Failed to create CV"},
            }
        ), 500


@cv_bp.route("/<int:cv_id>", methods=["PUT"])
@require_auth
@rate_limit("20 per minute")
def update_cv(user_id, email, cv_id):
    """
    Update a CV.

    Request Body:
        {
            "title": "Updated title (optional)",
            "content": { ... updated content ... } (optional),
            "target_position": "Updated position (optional)"
        }

    Returns:
        200: { "success": true, "data": { "cv": {...} } }
        404: { "success": false, "error": { "code": "CV_NOT_FOUND", "message": "..." } }
        400: { "success": false, "error": { "code": "...", "message": "..." } }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "MISSING_REQUEST_BODY",
                        "message": "Request body is required",
                    },
                }
            ), 400

        cv = CVService.update_cv(cv_id=cv_id, user_id=user_id, updates=data)

        if not cv:
            return jsonify(
                {
                    "success": False,
                    "error": {"code": "CV_NOT_FOUND", "message": "CV not found"},
                }
            ), 404

        logger.info(f"Updated CV {cv_id} for user {user_id}")

        return jsonify({"success": True, "data": {"cv": cv}}), 200

    except ValueError as e:
        return jsonify(
            {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        ), 400
    except Exception as e:
        logger.error(f"Error updating CV {cv_id}: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": {"code": "CV_UPDATE_FAILED", "message": "Failed to update CV"},
            }
        ), 500


@cv_bp.route("/<int:cv_id>", methods=["DELETE"])
@require_auth
@rate_limit("10 per minute")
def delete_cv(user_id, email, cv_id):
    """
    Delete a CV.

    Returns:
        200: { "success": true, "message": "CV deleted successfully" }
        404: { "success": false, "error": { "code": "CV_NOT_FOUND", "message": "..." } }
    """
    try:
        deleted = CVService.delete_cv(cv_id=cv_id, user_id=user_id)

        if not deleted:
            return jsonify(
                {
                    "success": False,
                    "error": {"code": "CV_NOT_FOUND", "message": "CV not found"},
                }
            ), 404

        logger.info(f"Deleted CV {cv_id} for user {user_id}")

        return jsonify({"success": True, "message": "CV deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting CV {cv_id}: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": {"code": "CV_DELETE_FAILED", "message": "Failed to delete CV"},
            }
        ), 500


# ===== AI Generation Endpoints =====


@cv_bp.route("/generate/generic", methods=["POST"])
@require_auth
@rate_limit("5 per minute")
def generate_generic_cv(user_id, email):
    """
    Generate a generic CV from user's profile using AI.

    Request Body (optional):
        {
            "title": "Optional CV title (default: Professional CV)"
        }

    Returns:
        201: { "success": true, "data": { "cv": {...} } }
        400: { "success": false, "error": { "code": "...", "message": "..." } }
        503: { "success": false, "error": { "code": "AI_UNAVAILABLE", "message": "..." } }
    """
    try:
        data = request.get_json() or {}
        title = data.get("title")

        cv = CVService.generate_generic_cv(user_id=user_id, title=title)

        logger.info(f"Generated generic CV {cv['id']} for user {user_id}")

        return jsonify(
            {
                "success": True,
                "data": {"cv": cv},
                "message": "CV generated successfully",
            }
        ), 201

    except ValueError as e:
        error_msg = str(e)

        # Check if it's an AI availability issue
        if "unavailable" in error_msg.lower():
            return jsonify(
                {
                    "success": False,
                    "error": {"code": "AI_UNAVAILABLE", "message": error_msg},
                }
            ), 503

        # Check if it's a profile completeness issue
        if "profile" in error_msg.lower():
            return jsonify(
                {
                    "success": False,
                    "error": {"code": "INCOMPLETE_PROFILE", "message": error_msg},
                }
            ), 400

        return jsonify(
            {
                "success": False,
                "error": {"code": "GENERATION_FAILED", "message": error_msg},
            }
        ), 400

    except Exception as e:
        logger.error(f"Error generating generic CV for user {user_id}: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "CV_GENERATION_FAILED",
                    "message": "Failed to generate CV",
                },
            }
        ), 500


@cv_bp.route("/<int:cv_id>/pdf", methods=["GET"])
@require_auth
@rate_limit("20 per minute")
def export_cv_pdf(user_id, email, cv_id):
    """
    Export a CV as a PDF document.

    Returns:
        200: PDF file download
        404: { "success": false, "error": { "code": "CV_NOT_FOUND", "message": "..." } }
        500: { "success": false, "error": { "code": "PDF_GENERATION_FAILED", "message": "..." } }
    """
    try:
        # Get the CV with content
        cv = CVService.get_cv(cv_id=cv_id, user_id=user_id, include_content=True)

        if not cv:
            return jsonify(
                {
                    "success": False,
                    "error": {"code": "CV_NOT_FOUND", "message": "CV not found"},
                }
            ), 404

        # Get CV content
        content = cv.get("content")
        if not content:
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "CV_NO_CONTENT",
                        "message": "CV has no content to export",
                    },
                }
            ), 400

        # Generate PDF
        title = cv.get("title", "CV")
        pdf_bytes = PDFService.generate_cv_pdf(content, title)

        # Create filename from CV title
        safe_title = "".join(
            c if c.isalnum() or c in " -_" else "_" for c in title
        ).strip()
        filename = f"{safe_title}.pdf" if safe_title else "cv.pdf"

        # Return PDF as download
        response = Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
            },
        )

        logger.info(f"Exported CV {cv_id} as PDF for user {user_id}")
        return response

    except Exception as e:
        logger.error(f"Error exporting CV {cv_id} as PDF: {str(e)}")
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "PDF_GENERATION_FAILED",
                    "message": "Failed to generate PDF",
                },
            }
        ), 500


@cv_bp.route("/generate/job/<int:job_id>", methods=["POST"])
@require_auth
@rate_limit("5 per minute")
def generate_tailored_cv(user_id, email, job_id):
    """
    Generate a CV tailored to a specific job offer.

    Request Body (optional):
        {
            "title": "Optional CV title (default: CV for [Job Title] at [Company])"
        }

    Returns:
        201: { "success": true, "data": { "cv": {...} } }
        400: { "success": false, "error": { "code": "...", "message": "..." } }
        404: { "success": false, "error": { "code": "JOB_NOT_FOUND", "message": "..." } }
        503: { "success": false, "error": { "code": "AI_UNAVAILABLE", "message": "..." } }
    """
    try:
        data = request.get_json() or {}
        title = data.get("title")

        cv = CVService.generate_tailored_cv(
            user_id=user_id, job_offer_id=job_id, title=title
        )

        logger.info(
            f"Generated tailored CV {cv['id']} for user {user_id}, job {job_id}"
        )

        return jsonify(
            {
                "success": True,
                "data": {"cv": cv},
                "message": "Tailored CV generated successfully",
            }
        ), 201

    except ValueError as e:
        error_msg = str(e)

        # Check if job not found
        if "job offer not found" in error_msg.lower():
            return jsonify(
                {
                    "success": False,
                    "error": {
                        "code": "JOB_NOT_FOUND",
                        "message": "Job offer not found",
                    },
                }
            ), 404

        # Check if it's an AI availability issue
        if "unavailable" in error_msg.lower():
            return jsonify(
                {
                    "success": False,
                    "error": {"code": "AI_UNAVAILABLE", "message": error_msg},
                }
            ), 503

        # Check if it's a profile completeness issue
        if "profile" in error_msg.lower():
            return jsonify(
                {
                    "success": False,
                    "error": {"code": "INCOMPLETE_PROFILE", "message": error_msg},
                }
            ), 400

        return jsonify(
            {
                "success": False,
                "error": {"code": "GENERATION_FAILED", "message": error_msg},
            }
        ), 400

    except Exception as e:
        logger.error(
            f"Error generating tailored CV for user {user_id}, job {job_id}: {str(e)}"
        )
        return jsonify(
            {
                "success": False,
                "error": {
                    "code": "CV_GENERATION_FAILED",
                    "message": "Failed to generate tailored CV",
                },
            }
        ), 500
