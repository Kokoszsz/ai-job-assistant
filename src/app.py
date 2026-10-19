"""
AI-Powered Job Search Assistant - Backend Application
=====================================================
Flask application factory with SQLAlchemy, migrations, and full middleware stack.
"""

import os

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from src.api import health_bp
from src.api.auth import auth_bp
from src.api.chat import chat_bp
from src.api.cv import cv_bp
from src.api.jobs import jobs_bp
from src.api.profile import profile_bp
from src.cli import register_cli_commands
from src.config import get_config
from src.middleware import register_error_handlers, setup_logging, setup_rate_limiting
from src.models import db

# Initialize Flask-Migrate globally
migrate = Migrate()


def create_app(config_name=None):
    """
    Application factory pattern.

    Args:
        config_name: Configuration environment ('development', 'testing', 'production')
                    If None, uses FLASK_ENV environment variable.

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Initialize logging first
    setup_logging(app)
    app.logger.info(f"Starting {app.config['APP_NAME']} v{app.config['APP_VERSION']}")
    app.logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")

    # Initialize database
    db.init_app(app)
    migrate.init_app(app, db)
    app.logger.info("Database initialized")

    # Initialize CORS
    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=app.config.get("CORS_SUPPORTS_CREDENTIALS", True),
    )
    app.logger.info(f"CORS configured for origins: {app.config['CORS_ORIGINS']}")

    # Register error handlers
    register_error_handlers(app)

    # Setup rate limiting
    limiter = setup_rate_limiting(app)
    app.limiter = limiter  # Store limiter instance for use in blueprints

    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(cv_bp)
    app.logger.info("Blueprints registered")

    # Apply rate limits to auth endpoints
    if limiter:
        register_func = auth_bp.view_functions.get("register")
        if register_func:
            limiter.limit("5/minute")(register_func)

        login_func = auth_bp.view_functions.get("login")
        if login_func:
            limiter.limit("5/minute")(login_func)

        refresh_func = auth_bp.view_functions.get("refresh")
        if refresh_func:
            limiter.limit("10/minute")(refresh_func)

        logout_func = auth_bp.view_functions.get("logout")
        if logout_func:
            limiter.limit("10/minute")(logout_func)

        # Password reset endpoints
        reset_request_func = auth_bp.view_functions.get("request_password_reset")
        if reset_request_func:
            limiter.limit("3 per 15 minutes")(reset_request_func)

        reset_confirm_func = auth_bp.view_functions.get("confirm_password_reset")
        if reset_confirm_func:
            limiter.limit("3 per 15 minutes")(reset_confirm_func)

        # Job endpoints - 60 requests per minute
        search_jobs_func = jobs_bp.view_functions.get("search_jobs")
        if search_jobs_func:
            limiter.limit("60/minute")(search_jobs_func)

        get_job_func = jobs_bp.view_functions.get("get_job")
        if get_job_func:
            limiter.limit("60/minute")(get_job_func)

        get_favorites_func = jobs_bp.view_functions.get("get_favorites")
        if get_favorites_func:
            limiter.limit("60/minute")(get_favorites_func)

        add_favorite_func = jobs_bp.view_functions.get("add_favorite")
        if add_favorite_func:
            limiter.limit("60/minute")(add_favorite_func)

        remove_favorite_func = jobs_bp.view_functions.get("remove_favorite")
        if remove_favorite_func:
            limiter.limit("60/minute")(remove_favorite_func)

        update_favorite_notes_func = jobs_bp.view_functions.get("update_favorite_notes")
        if update_favorite_notes_func:
            limiter.limit("60/minute")(update_favorite_notes_func)

        # Chat endpoints - 20 requests per minute
        create_conversation_func = chat_bp.view_functions.get("create_conversation")
        if create_conversation_func:
            limiter.limit("20/minute")(create_conversation_func)

        list_conversations_func = chat_bp.view_functions.get("list_conversations")
        if list_conversations_func:
            limiter.limit("20/minute")(list_conversations_func)

        get_messages_func = chat_bp.view_functions.get("get_messages")
        if get_messages_func:
            limiter.limit("20/minute")(get_messages_func)

        send_message_func = chat_bp.view_functions.get("send_message")
        if send_message_func:
            limiter.limit("20/minute")(send_message_func)

        # CV endpoints - 30 requests per minute for CRUD, 5 for generation
        list_cvs_func = cv_bp.view_functions.get("list_cvs")
        if list_cvs_func:
            limiter.limit("30/minute")(list_cvs_func)

        get_cv_func = cv_bp.view_functions.get("get_cv")
        if get_cv_func:
            limiter.limit("30/minute")(get_cv_func)

        create_cv_func = cv_bp.view_functions.get("create_cv")
        if create_cv_func:
            limiter.limit("10/minute")(create_cv_func)

        update_cv_func = cv_bp.view_functions.get("update_cv")
        if update_cv_func:
            limiter.limit("20/minute")(update_cv_func)

        delete_cv_func = cv_bp.view_functions.get("delete_cv")
        if delete_cv_func:
            limiter.limit("10/minute")(delete_cv_func)

        # AI generation has stricter limits
        generate_generic_func = cv_bp.view_functions.get("generate_generic_cv")
        if generate_generic_func:
            limiter.limit("5/minute")(generate_generic_func)

        generate_tailored_func = cv_bp.view_functions.get("generate_tailored_cv")
        if generate_tailored_func:
            limiter.limit("5/minute")(generate_tailored_func)

    # Log startup info
    app.logger.info(
        f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'not configured'}"
    )
    app.logger.info(f"Redis URL: {app.config['REDIS_URL']}")
    app.logger.info(f"Using dummy data: {app.config['USE_DUMMY_DATA']}")

    # Register CLI commands
    register_cli_commands(app)
    app.logger.info("CLI commands registered")

    app.logger.info("Application startup complete")

    return app


# For running with `flask run`
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
