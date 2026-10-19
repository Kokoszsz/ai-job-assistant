"""
Test Flask Application Configuration
=====================================
Tests for Flask application factory and configuration management.
"""

import os

import pytest

from src.app import create_app
from src.config import DevelopmentConfig, ProductionConfig, TestingConfig, get_config


def test_get_config_default(monkeypatch):
    """Test default configuration."""
    # CI sets FLASK_ENV=testing; the default only applies when it is unset
    monkeypatch.delenv("FLASK_ENV", raising=False)
    config = get_config()
    assert isinstance(config, DevelopmentConfig)


def test_get_config_development():
    """Test development configuration."""
    config = get_config("development")
    assert isinstance(config, DevelopmentConfig)
    assert config.DEBUG is True
    assert config.TESTING is False


def test_get_config_testing():
    """Test testing configuration."""
    config = get_config("testing")
    assert isinstance(config, TestingConfig)
    assert config.DEBUG is True
    assert config.TESTING is True


def test_get_config_production():
    """Test production configuration."""
    # Set required environment variables for production
    os.environ["SECRET_KEY"] = "test-production-secret"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"

    config = get_config("production")
    assert isinstance(config, ProductionConfig)
    assert config.DEBUG is False
    assert config.TESTING is False

    # Cleanup
    del os.environ["SECRET_KEY"]
    del os.environ["JWT_SECRET_KEY"]


def test_create_app_development():
    """Test creating application with development config."""
    app = create_app("development")
    assert app is not None
    assert app.config["DEBUG"] is True
    assert app.config["TESTING"] is False
    assert "sqlalchemy" in app.extensions
    assert "migrate" in app.extensions


def test_create_app_testing():
    """Test creating application with testing config."""
    app = create_app("testing")
    assert app is not None
    assert app.config["DEBUG"] is True
    assert app.config["TESTING"] is True


def test_config_from_environment():
    """Test configuration can be loaded from environment."""
    # Test that config reads from environment
    config = get_config("development")

    # Verify config has been loaded (values will be from .env or defaults)
    assert config.SECRET_KEY is not None
    assert config.SQLALCHEMY_DATABASE_URI is not None
    assert config.REDIS_URL is not None

    # Verify specific values are from Config class
    assert hasattr(config, "SQLALCHEMY_TRACK_MODIFICATIONS")
    assert hasattr(config, "DEBUG")
    assert hasattr(config, "APP_NAME")
    assert hasattr(config, "APP_VERSION")


def test_cors_configuration():
    """Test CORS is properly configured."""
    app = create_app("testing")
    assert "CORS_ORIGINS" in app.config
    assert isinstance(app.config["CORS_ORIGINS"], list)


def test_database_configuration():
    """Test database connection settings."""
    config = get_config("development")
    assert "SQLALCHEMY_DATABASE_URI" in dir(config)
    assert "SQLALCHEMY_TRACK_MODIFICATIONS" in dir(config)
    assert config.SQLALCHEMY_TRACK_MODIFICATIONS is False
    assert "SQLALCHEMY_ENGINE_OPTIONS" in dir(config)


def test_logging_configuration():
    """Test logging settings are present."""
    config = get_config("development")
    assert hasattr(config, "LOG_LEVEL")
    assert hasattr(config, "LOG_FORMAT")
    assert config.LOG_LEVEL == "DEBUG"
    assert config.LOG_FORMAT == "json"


def test_rate_limiting_configuration():
    """Test rate limiting settings."""
    config = get_config("development")
    assert hasattr(config, "RATELIMIT_STORAGE_URL")
    assert hasattr(config, "RATELIMIT_DEFAULT")
    assert hasattr(config, "RATELIMIT_AUTH")
    assert hasattr(config, "RATELIMIT_CHAT")


def test_application_info():
    """Test application name and version are set."""
    config = get_config()
    assert hasattr(config, "APP_NAME")
    assert hasattr(config, "APP_VERSION")
    assert config.APP_NAME == "AI Job Search Assistant"
    assert config.APP_VERSION == "0.1.0"


def test_blueprints_registered():
    """Test that blueprints are registered."""
    app = create_app("testing")

    # Check that health blueprint is registered
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    assert "health" in blueprint_names


def test_error_handlers_registered():
    """Test that error handlers are registered."""
    app = create_app("testing")

    # Create test client
    with app.test_client() as client:
        # Test 404 error handler
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["success"] is False
        assert "request_id" in data
