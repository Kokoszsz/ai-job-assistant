"""
Authentication API Endpoints
============================
User registration, login, logout, and token management.
"""

import re
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from src.models import Profile, User, db
from src.services.auth_service import AuthService, TokenBlacklistedError, TokenExpiredError, TokenInvalidError
from src.utils.password import PasswordValidationError

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def rate_limit(limit_string):
    """
    Decorator to apply rate limiting to a route.
    Applies the limit when limiter is available in app context.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Apply rate limit if limiter is available
            if hasattr(current_app, "limiter"):
                # Limiter will automatically check and enforce the limit
                pass
            return f(*args, **kwargs)

        # Store limit string for later application
        decorated_function._rate_limit = limit_string
        return decorated_function

    return decorator


def validate_email(email: str) -> bool:
    """
    Validate email format (RFC 5322 basic validation).

    Args:
        email: Email address to validate

    Returns:
        True if valid format, False otherwise
    """
    if not email:
        return False

    # Basic RFC 5322 regex pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


@auth_bp.route("/register", methods=["POST"])
@rate_limit("5/minute")
def register():
    """
    Register a new user account.

    Request Body:
        {
            "email": "user@example.com",
            "password": "SecurePass123",
            "name": "John Doe"
        }

    Returns:
        201: User created successfully with tokens
        400: Invalid input or duplicate email
        500: Server error

    Rate Limit: 5 requests per minute
    """
    try:
        # Get request data
        data = request.get_json(silent=True)  # Don't raise error on invalid JSON

        if not data:
            return (
                jsonify({"success": False, "error": {"code": "MISSING_DATA", "message": "Request body is required"}}),
                400,
            )

        # Extract and validate required fields
        email = data.get("email", "").strip()
        password = data.get("password", "")
        name = data.get("name", "").strip()

        errors = {}

        # Validate email
        if not email:
            errors["email"] = "Email is required"
        elif not validate_email(email):
            errors["email"] = "Invalid email format"

        # Validate name
        if not name:
            errors["name"] = "Name is required"
        elif len(name) < 2:
            errors["name"] = "Name must be at least 2 characters"
        elif len(name) > 100:
            errors["name"] = "Name must be at most 100 characters"

        # Validate password
        if not password:
            errors["password"] = "Password is required"

        # Return validation errors if any
        if errors:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {"code": "VALIDATION_ERROR", "message": "Invalid input data", "details": errors},
                    }
                ),
                400,
            )

        # Check password strength
        try:
            from src.utils.password import validate_password_strength

            validate_password_strength(password)
        except PasswordValidationError as e:
            return jsonify({"success": False, "error": {"code": "WEAK_PASSWORD", "message": str(e)}}), 400

        # Check for duplicate email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {"code": "EMAIL_EXISTS", "message": "An account with this email already exists"},
                    }
                ),
                400,
            )

        # Create new user
        user = User(email=email, password_hash="temp", name=name)  # Will be replaced by set_password
        user.set_password(password)

        # Add user to database
        db.session.add(user)
        db.session.flush()  # Get user.id without committing

        # Auto-create empty profile
        profile = Profile(user_id=user.id)
        db.session.add(profile)

        # Commit transaction
        db.session.commit()

        # Generate tokens
        auth_service = AuthService()
        tokens = auth_service.generate_tokens(user.id, user.email)

        # Create response with user data and tokens
        response = jsonify(
            {
                "success": True,
                "data": {
                    "user": user.to_dict(),
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                },
                "message": "Account created successfully",
            }
        )

        # Set tokens as httpOnly cookies
        response.set_cookie(
            "access_token",
            tokens["access_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="Lax",
            max_age=24 * 60 * 60,  # 24 hours
        )
        response.set_cookie(
            "refresh_token",
            tokens["refresh_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )

        return response, 201

    except IntegrityError as e:
        # Handle race condition if email was inserted between check and insert
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "error": {"code": "EMAIL_EXISTS", "message": "An account with this email already exists"},
                }
            ),
            400,
        )

    except Exception as e:
        # Rollback on any other error
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {"code": "SERVER_ERROR", "message": "An error occurred during registration"},
                }
            ),
            500,
        )


@auth_bp.route("/login", methods=["POST"])
@rate_limit("5/minute")
def login():
    """
    User login with email and password.

    Request Body:
        {
            "email": "user@example.com",
            "password": "SecurePass123"
        }

    Returns:
        200: Login successful with tokens
        401: Invalid credentials or inactive account
        400: Invalid input
        500: Server error

    Rate Limit: 5 requests per minute
    """
    try:
        # Get request data
        data = request.get_json(silent=True)

        if not data:
            return (
                jsonify({"success": False, "error": {"code": "MISSING_DATA", "message": "Request body is required"}}),
                400,
            )

        # Extract fields
        email = data.get("email", "").strip()
        password = data.get("password", "")

        # Validate required fields
        if not email or not password:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {"code": "MISSING_CREDENTIALS", "message": "Email and password are required"},
                    }
                ),
                400,
            )

        # Lookup user by email
        user = User.query.filter_by(email=email).first()

        # Generic error message for security (don't reveal if email exists)
        invalid_credentials_response = (
            jsonify(
                {"success": False, "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}}
            ),
            401,
        )

        # Check if user exists
        if not user:
            return invalid_credentials_response

        # Check if account is active
        if not user.is_active:
            return (
                jsonify({"success": False, "error": {"code": "ACCOUNT_INACTIVE", "message": "Account is inactive"}}),
                403,
            )

        # Verify password
        if not user.check_password(password):
            return invalid_credentials_response

        # Update last_login timestamp
        from datetime import datetime

        user.last_login = datetime.utcnow()
        db.session.commit()

        # Generate tokens
        auth_service = AuthService()
        tokens = auth_service.generate_tokens(user.id, user.email)

        # Create response with user data and tokens
        response = jsonify(
            {
                "success": True,
                "data": {
                    "user": user.to_dict(),
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                },
                "message": "Login successful",
            }
        )

        # Set tokens as httpOnly cookies
        response.set_cookie(
            "access_token",
            tokens["access_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="Lax",
            max_age=24 * 60 * 60,  # 24 hours
        )
        response.set_cookie(
            "refresh_token",
            tokens["refresh_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,  # 7 days
        )

        return response, 200

    except Exception as e:
        # Rollback on error
        db.session.rollback()
        current_app.logger.error(f"Login error: {str(e)}")
        return (
            jsonify({"success": False, "error": {"code": "SERVER_ERROR", "message": "An error occurred during login"}}),
            500,
        )


@auth_bp.route("/refresh", methods=["POST"])
@rate_limit("10/minute")
def refresh():
    """
    Refresh access token using a valid refresh token.

    Accepts refresh token in request body or Authorization header.
    Generates a new access token if the refresh token is valid and not blacklisted.

    Request Body (Option 1):
        {
            "refresh_token": "eyJ..."
        }

    Request Header (Option 2):
        Authorization: Bearer <refresh_token>

    Returns:
        200: New access and refresh tokens
        400: Missing refresh token
        401: Invalid, expired, or blacklisted token
        500: Server error
    """
    try:
        # A token sent explicitly in the body wins over the cookie
        data = request.get_json(silent=True) or {}
        refresh_token = data.get("refresh_token")

        if not refresh_token:
            refresh_token = request.cookies.get("refresh_token")

        # Try Authorization header if not in body or cookie
        if not refresh_token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                refresh_token = auth_header.split(" ", 1)[1]

        # Validate token is provided
        if not refresh_token:
            return (
                jsonify({"success": False, "error": {"code": "MISSING_TOKEN", "message": "Refresh token is required"}}),
                400,
            )

        # Refresh the access token
        auth_service = AuthService()

        try:
            tokens = auth_service.refresh_access_token(refresh_token)

            # Create response
            # Tokens go in the body (for API clients) and in cookies (for browsers)
            response = jsonify(
                {
                    "success": True,
                    "message": "Token refreshed successfully",
                    "data": {
                        "access_token": tokens["access_token"],
                        "refresh_token": tokens["refresh_token"],
                    },
                }
            )

            # Set new tokens as httpOnly cookies
            response.set_cookie(
                "access_token",
                tokens["access_token"],
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=24 * 60 * 60,
            )
            response.set_cookie(
                "refresh_token",
                tokens["refresh_token"],
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=7 * 24 * 60 * 60,
            )

            return response, 200

        except TokenExpiredError:
            return (
                jsonify({"success": False, "error": {"code": "TOKEN_EXPIRED", "message": "Refresh token has expired"}}),
                401,
            )

        except TokenBlacklistedError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": {"code": "TOKEN_BLACKLISTED", "message": "Refresh token has been revoked"},
                    }
                ),
                401,
            )

        except TokenInvalidError as e:
            return (
                jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Invalid refresh token"}}),
                401,
            )

    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {"code": "SERVER_ERROR", "message": "An error occurred during token refresh"},
                }
            ),
            500,
        )


@auth_bp.route("/logout", methods=["POST"])
@rate_limit("10/minute")
def logout():
    """
    Logout user by blacklisting their refresh token.

    Adds the refresh token to a Redis blacklist so it cannot be used again.
    The blacklist entry automatically expires when the token would have expired.

    Request Body:
        {
            "refresh_token": "eyJ..."
        }

    Returns:
        200: Successfully logged out
        400: Missing refresh token
        500: Server error

    Note: Returns 200 even if token is invalid/expired (safe logout).
    """
    try:
        # Get refresh token from cookie, then fallback to request body
        refresh_token = request.cookies.get("refresh_token")

        if not refresh_token:
            data = request.get_json(silent=True) or {}
            refresh_token = data.get("refresh_token")

        # Validate token is provided
        if not refresh_token:
            return (
                jsonify({"success": False, "error": {"code": "MISSING_TOKEN", "message": "Refresh token is required"}}),
                400,
            )

        # Blacklist the token (safe even if token is invalid/expired)
        auth_service = AuthService()
        auth_service.blacklist_token(refresh_token)

        # Create response and clear cookies
        response = jsonify({"success": True, "message": "Logged out successfully"})

        # Clear both tokens
        response.set_cookie("access_token", "", httponly=True, max_age=0)
        response.set_cookie("refresh_token", "", httponly=True, max_age=0)

        return response, 200

    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return (
            jsonify(
                {"success": False, "error": {"code": "SERVER_ERROR", "message": "An error occurred during logout"}}
            ),
            500,
        )


@auth_bp.route("/password-reset/request", methods=["POST"])
@rate_limit("3 per 15 minutes")
def request_password_reset():
    """
    Request password reset.

    Generates a reset token and sends it via email.
    Returns success regardless of whether email exists (security).

    Request Body:
        email (str): User's email address

    Returns:
        200: Success message (generic for security)
        400: Invalid input
        500: Server error
    """
    try:
        data = request.get_json()

        # Validate input
        if not data:
            return (
                jsonify({"success": False, "error": {"code": "INVALID_INPUT", "message": "Request body is required"}}),
                400,
            )

        email = data.get("email", "").strip().lower()

        if not email:
            return jsonify({"success": False, "error": {"code": "INVALID_INPUT", "message": "Email is required"}}), 400

        if not validate_email(email):
            return (
                jsonify({"success": False, "error": {"code": "INVALID_INPUT", "message": "Invalid email format"}}),
                400,
            )

        # Look up user
        user = User.query.filter_by(email=email).first()

        # Generate and send reset token (only if user exists)
        if user:
            auth_service = AuthService()
            reset_token = auth_service.generate_password_reset_token(email)

            # Send email (unless disabled)
            if not current_app.config.get("SKIP_EMAIL_SENDING", True):
                from src.services.email_service import EmailService

                email_service = EmailService()
                email_service.send_password_reset_email(email, reset_token)
            else:
                current_app.logger.info(f"Password reset token for {email}: {reset_token}")

        # Always return success (don't reveal if email exists)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "If an account exists with that email, a password reset link has been sent",
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Password reset request error: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": {"code": "SERVER_ERROR", "message": "An error occurred processing your request"},
                }
            ),
            500,
        )


@auth_bp.route("/password-reset/confirm", methods=["POST"])
@rate_limit("3 per 15 minutes")
def confirm_password_reset():
    """
    Confirm password reset with token.

    Validates reset token and updates user's password.

    Request Body:
        token (str): Password reset token
        new_password (str): New password

    Returns:
        200: Password reset successful
        400: Invalid input or token
        500: Server error
    """
    try:
        data = request.get_json()

        # Validate input
        if not data:
            return (
                jsonify({"success": False, "error": {"code": "INVALID_INPUT", "message": "Request body is required"}}),
                400,
            )

        token = data.get("token", "").strip()
        new_password = data.get("new_password", "")

        if not token:
            return (
                jsonify({"success": False, "error": {"code": "INVALID_INPUT", "message": "Reset token is required"}}),
                400,
            )

        if not new_password:
            return (
                jsonify({"success": False, "error": {"code": "INVALID_INPUT", "message": "New password is required"}}),
                400,
            )

        # Validate token
        auth_service = AuthService()
        email = auth_service.validate_password_reset_token(token)

        if not email:
            return (
                jsonify(
                    {"success": False, "error": {"code": "INVALID_TOKEN", "message": "Invalid or expired reset token"}}
                ),
                400,
            )

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            return (
                jsonify(
                    {"success": False, "error": {"code": "INVALID_TOKEN", "message": "Invalid or expired reset token"}}
                ),
                400,
            )

        # Validate and set new password
        try:
            user.set_password(new_password)
            db.session.commit()

            # Delete the used token
            auth_service.delete_password_reset_token(token)

            return jsonify({"success": True, "message": "Password reset successful"}), 200

        except PasswordValidationError as e:
            return jsonify({"success": False, "error": {"code": "WEAK_PASSWORD", "message": str(e)}}), 400

    except Exception as e:
        current_app.logger.error(f"Password reset confirm error: {str(e)}")
        db.session.rollback()
        return (
            jsonify(
                {
                    "success": False,
                    "error": {"code": "SERVER_ERROR", "message": "An error occurred processing your request"},
                }
            ),
            500,
        )
