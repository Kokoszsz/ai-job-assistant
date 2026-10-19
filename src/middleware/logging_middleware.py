"""
Request Logging Middleware
===========================
Logs all incoming HTTP requests and responses in JSON format.
"""

import json
import logging
import time
from datetime import datetime

from flask import g, request
from werkzeug.exceptions import HTTPException


def setup_logging(app):
    """
    Configure JSON-formatted logging for all requests.

    Args:
        app: Flask application instance
    """
    # Configure logging format
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"))
    log_format = app.config.get("LOG_FORMAT", "json")

    # Create logger
    logger = logging.getLogger("jobassistant")
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    if log_format == "json":
        # JSON formatter
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }

                # Add exception info if present
                if record.exc_info:
                    log_data["exception"] = self.formatException(record.exc_info)

                # Add extra fields
                if hasattr(record, "request_id"):
                    log_data["request_id"] = record.request_id
                if hasattr(record, "user_id"):
                    log_data["user_id"] = record.user_id
                if hasattr(record, "duration_ms"):
                    log_data["duration_ms"] = record.duration_ms

                return json.dumps(log_data)

        handler.setFormatter(JsonFormatter())
    else:
        # Standard text formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

    logger.addHandler(handler)

    # Store logger in app
    app.logger = logger

    # Register before/after request handlers
    @app.before_request
    def before_request():
        """Log request start and store timing info."""
        g.start_time = time.time()
        g.request_id = request.headers.get("X-Request-ID", f"req_{int(time.time() * 1000)}")

        # Log incoming request
        extra = {
            "request_id": g.request_id,
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
        }

        app.logger.info(f"Incoming request: {request.method} {request.path}", extra=extra)

    @app.after_request
    def after_request(response):
        """Log request completion with timing and status."""
        # Calculate duration
        if hasattr(g, "start_time"):
            duration_ms = int((time.time() - g.start_time) * 1000)
        else:
            duration_ms = 0

        # Get request ID
        request_id = getattr(g, "request_id", "unknown")

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log response
        extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "content_length": response.content_length or 0,
        }

        log_message = (
            f"Request completed: {request.method} {request.path} - " f"{response.status_code} ({duration_ms}ms)"
        )

        # Log level based on status code
        if response.status_code >= 500:
            app.logger.error(log_message, extra=extra)
        elif response.status_code >= 400:
            app.logger.warning(log_message, extra=extra)
        else:
            app.logger.info(log_message, extra=extra)

        return response

    app.logger.info(f"Logging configured: level={log_level}, format={log_format}")

    return logger
