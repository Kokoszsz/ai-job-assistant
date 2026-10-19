"""
Unit Tests: AI Service
=======================
Tests for core AI service functionality.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask

from src.ai.agents.base_agent import BaseAgent
from src.ai.tools.database_tools import DatabaseTools
from src.services.ai_service import AIService, get_ai_service, init_ai_service


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config["OPENAI_API_KEY"] = "test-api-key"
    app.config["OPENAI_MODEL"] = "gpt-4-turbo-preview"
    app.config["OPENAI_TEMPERATURE"] = 0.7
    app.config["OPENAI_MAX_TOKENS"] = 1500
    app.config["OPENAI_TIMEOUT"] = 30
    return app


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def ai_service(app, mock_db_session):
    """Create AIService instance."""
    service = AIService(app, mock_db_session)
    return service


class TestAIServiceInitialization:
    """Test AI service initialization."""

    def test_initialization_with_app(self, app, mock_db_session):
        """Test initialization with Flask app."""
        service = AIService(app, mock_db_session)

        assert service.app == app
        assert service.db_session == mock_db_session

    def test_initialization_without_app(self):
        """Test initialization without Flask app."""
        service = AIService()

        assert service.app is None
        assert service.db_session is None

    def test_init_app(self, app, mock_db_session):
        """Test init_app method."""
        service = AIService()
        service.init_app(app, mock_db_session)

        assert service.app == app
        assert service.db_session == mock_db_session

    def test_initialization_without_api_key(self):
        """Test initialization warning when no API key."""
        app = Flask(__name__)
        # No OPENAI_API_KEY in config

        with patch("src.services.ai_service.logger") as mock_logger:
            service = AIService(app)
            mock_logger.warning.assert_called()


class TestCreateAgent:
    """Test agent creation."""

    def test_create_agent_with_defaults(self, ai_service):
        """Test creating agent with default configuration."""
        with patch("src.services.ai_service.BaseAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent

            agent = ai_service.create_agent()

            # Verify BaseAgent called with config values
            mock_agent_class.assert_called_once()
            call_kwargs = mock_agent_class.call_args[1]
            assert call_kwargs["api_key"] == "test-api-key"
            assert call_kwargs["model"] == "gpt-4-turbo-preview"
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["max_tokens"] == 1500

    def test_create_agent_with_custom_params(self, ai_service):
        """Test creating agent with custom parameters."""
        with patch("src.services.ai_service.BaseAgent") as mock_agent_class:
            ai_service.create_agent(
                model="gpt-3.5-turbo",
                temperature=0.5,
                max_tokens=1000,
            )

            call_kwargs = mock_agent_class.call_args[1]
            assert call_kwargs["model"] == "gpt-3.5-turbo"
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["max_tokens"] == 1000

    def test_create_agent_without_api_key(self, app, mock_db_session):
        """Test creating agent fails without API key."""
        app.config["OPENAI_API_KEY"] = None
        service = AIService(app, mock_db_session)

        with pytest.raises(ValueError, match="API key not configured"):
            service.create_agent()


class TestDatabaseTools:
    """Test database tools access."""

    def test_get_db_tools(self, ai_service, mock_db_session):
        """Test getting database tools."""
        tools = ai_service.get_db_tools()

        assert isinstance(tools, DatabaseTools)
        assert tools.db == mock_db_session

    def test_get_db_tools_caches_instance(self, ai_service):
        """Test that db tools instance is cached."""
        tools1 = ai_service.get_db_tools()
        tools2 = ai_service.get_db_tools()

        assert tools1 is tools2

    def test_get_db_tools_without_session(self, app):
        """Test getting db tools fails without session."""
        service = AIService(app, db_session=None)

        with pytest.raises(ValueError, match="Database session not configured"):
            service.get_db_tools()


class TestAvailability:
    """Test AI service availability."""

    def test_is_available_with_working_service(self, ai_service):
        """Test availability when OpenAI accessible."""
        with patch.object(ai_service, "create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.is_available.return_value = True
            mock_create.return_value = mock_agent

            assert ai_service.is_available() is True

    def test_is_available_without_api_key(self, app, mock_db_session):
        """Test availability when no API key."""
        app.config["OPENAI_API_KEY"] = None
        service = AIService(app, mock_db_session)

        assert service.is_available() is False

    def test_is_available_with_error(self, ai_service):
        """Test availability when error occurs."""
        with patch.object(ai_service, "create_agent", side_effect=Exception("Connection error")):
            assert ai_service.is_available() is False


class TestFallbackResponse:
    """Test fallback responses."""

    def test_fallback_chat_context(self, ai_service):
        """Test fallback response for chat context."""
        response = ai_service.get_fallback_response(context="chat")

        assert response["success"] is False
        assert "error" in response
        assert "unavailable" in response["error"]["message"].lower()
        assert "browse" in response["error"]["message"].lower()

    def test_fallback_job_search_context(self, ai_service):
        """Test fallback response for job search context."""
        response = ai_service.get_fallback_response(context="job_search")

        assert "filters" in response["error"]["message"].lower()

    def test_fallback_cv_context(self, ai_service):
        """Test fallback response for CV context."""
        response = ai_service.get_fallback_response(context="cv")

        assert "cv generation" in response["error"]["message"].lower()

    def test_fallback_generic_context(self, ai_service):
        """Test fallback response for generic context."""
        response = ai_service.get_fallback_response()

        assert response["error"]["code"] == "AI_SERVICE_UNAVAILABLE"


class TestConfigAccess:
    """Test configuration access."""

    def test_get_config_with_app(self, ai_service):
        """Test getting config value."""
        value = ai_service._get_config("OPENAI_MODEL")

        assert value == "gpt-4-turbo-preview"

    def test_get_config_with_default(self, ai_service):
        """Test getting config with default."""
        value = ai_service._get_config("NONEXISTENT_KEY", "default_value")

        assert value == "default_value"

    def test_get_config_without_app(self):
        """Test getting config without app."""
        service = AIService()
        value = service._get_config("SOME_KEY", "default")

        assert value == "default"


class TestGlobalService:
    """Test global service functions."""

    def test_get_ai_service(self):
        """Test getting global AI service."""
        # Reset global service
        import src.services.ai_service

        src.services.ai_service._ai_service = None

        service = get_ai_service()

        assert isinstance(service, AIService)

    def test_get_ai_service_returns_same_instance(self):
        """Test that get_ai_service returns same instance."""
        service1 = get_ai_service()
        service2 = get_ai_service()

        assert service1 is service2

    def test_init_ai_service(self, app, mock_db_session):
        """Test initializing global AI service."""
        service = init_ai_service(app, mock_db_session)

        assert isinstance(service, AIService)
        assert service.app == app
        assert service.db_session == mock_db_session


class TestUtilityMethods:
    """Test utility methods."""

    def test_repr(self, ai_service):
        """Test string representation."""
        with patch.object(ai_service, "is_available", return_value=True):
            repr_str = repr(ai_service)

            assert "AIService" in repr_str
            assert "available" in repr_str
