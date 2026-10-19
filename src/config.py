"""
Configuration Management
========================
Flask application configuration for different environments.
"""

import os
from datetime import timedelta


class Config:
    """Base configuration with common settings."""

    # Flask Core
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/jobassistant")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", 5)),
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 10)),
    }

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS_SUPPORTS_CREDENTIALS = True

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", 3600))

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 86400)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 604800)))

    # Rate Limiting
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "redis://redis:6379/1")
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "100/hour")
    RATELIMIT_AUTH = os.getenv("RATELIMIT_AUTH", "5/minute")
    RATELIMIT_CHAT = os.getenv("RATELIMIT_CHAT", "20/minute")
    RATELIMIT_JOB_SEARCH = os.getenv("RATELIMIT_JOB_SEARCH", "60/minute")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", 1500))
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", 0.7))
    OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", 30))

    # AI Conversation Memory
    CONVERSATION_MAX_MESSAGES = int(os.getenv("CONVERSATION_MAX_MESSAGES", 20))
    CONVERSATION_MAX_TOKENS = int(os.getenv("CONVERSATION_MAX_TOKENS", 4000))

    # External APIs
    ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
    ADZUNA_API_KEY = os.getenv("ADZUNA_API_KEY", "")
    ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "us")

    # Email
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@jobassistant.com")

    # Frontend
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

    # Feature Flags
    USE_DUMMY_DATA = os.getenv("USE_DUMMY_DATA", "true").lower() == "true"
    SKIP_EMAIL_SENDING = os.getenv("SKIP_EMAIL_SENDING", "true").lower() == "true"

    # Application
    APP_NAME = "AI Job Search Assistant"
    APP_VERSION = "0.1.0"


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    """Testing environment configuration."""

    TESTING = True
    DEBUG = True

    # Use SQLite in-memory database for tests (faster, no external dependencies)
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")

    # Override engine options for SQLite (no pool_size/max_overflow)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "echo": False,
        "connect_args": {"check_same_thread": False},  # Allow multi-threading with SQLite
    }

    # Enable rate limiting in tests but use in-memory storage
    RATELIMIT_ENABLED = True

    # Use in-memory storage for rate limiting in tests (no Redis needed)
    REDIS_URL = "redis://localhost:6379/15"
    RATELIMIT_STORAGE_URL = "memory://"  # Use in-memory storage for tests


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False

    # Ensure critical configs are set in production
    def __init__(self):
        super().__init__()
        # Validate critical settings
        if self.SECRET_KEY == "dev-secret-key-change-in-production":
            raise ValueError("SECRET_KEY must be set in production")
        if self.JWT_SECRET_KEY == self.SECRET_KEY and self.SECRET_KEY == "dev-secret-key-change-in-production":
            raise ValueError("JWT_SECRET_KEY must be set in production")


# Configuration mapping
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name=None):
    """
    Get configuration class by name.

    Args:
        config_name: Configuration environment name

    Returns:
        Configuration class instance
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    config_class = config_map.get(config_name, DevelopmentConfig)
    return config_class()
