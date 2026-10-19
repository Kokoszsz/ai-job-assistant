"""
Rate Limiting Middleware
========================
Flask-Limiter integration for API rate limiting with Redis storage.
"""

from flask import Flask, g, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def _should_skip_rate_limit():
    """Check if current request should skip rate limiting."""
    # Exempt health check endpoint
    return request.endpoint == "health.health_check"


def setup_rate_limiting(app: Flask) -> Limiter:
    """
    Configure rate limiting for the Flask application.

    Args:
        app: Flask application instance

    Returns:
        Configured Limiter instance
    """
    # Check if rate limiting is enabled
    if not app.config.get("RATELIMIT_ENABLED", True):
        app.logger.info("Rate limiting disabled")
        return None

    # Initialize limiter with Redis storage
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=app.config.get("RATELIMIT_STORAGE_URL"),
        default_limits=[app.config.get("RATELIMIT_DEFAULT", "100/hour")],
        default_limits_exempt_when=_should_skip_rate_limit,  # Skip health check
        storage_options={"socket_connect_timeout": 30},
        strategy="fixed-window",
        headers_enabled=True,
    )

    # Custom error handler for rate limit exceeded
    @app.errorhandler(429)
    def ratelimit_handler(error):
        """Handle rate limit exceeded errors."""
        request_id = getattr(g, "request_id", "unknown")

        # Extract retry-after from error description if available
        retry_after = None
        if hasattr(error, "description"):
            # Flask-Limiter includes retry info in description
            try:
                # Description format: "X per Y"
                retry_after = getattr(error, "retry_after", None)
            except:
                pass

        response = {
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded. Please try again later.",
                "status_code": 429,
            },
            "request_id": request_id,
        }

        # Add retry-after if available
        if retry_after:
            response["error"]["retry_after"] = retry_after

        # Log rate limit violation
        app.logger.warning(
            f"Rate limit exceeded: {request.method} {request.path}",
            extra={
                "request_id": request_id,
                "remote_addr": request.remote_addr,
                "path": request.path,
                "method": request.method,
            },
        )

        # Create response with Retry-After header
        resp = jsonify(response)
        resp.status_code = 429
        if retry_after:
            resp.headers["Retry-After"] = str(int(retry_after))

        return resp

    app.logger.info(
        f"Rate limiting configured: default={app.config.get('RATELIMIT_DEFAULT')}, "
        f"storage={app.config.get('RATELIMIT_STORAGE_URL')}"
    )

    return limiter
