"""
Unit Tests: JWT Authentication Service
======================================
Tests for JWT token generation, validation, and management.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import jwt
import pytest

from src.services.auth_service import (
    AuthService,
    TokenBlacklistedError,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
)


@pytest.fixture
def app_context():
    """Create mock Flask app context."""
    from flask import Flask

    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test-secret-key"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)
    app.config["REDIS_URL"] = "redis://localhost:6379/0"

    with app.app_context():
        yield app


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.setex = Mock()
    redis_mock.exists = Mock(return_value=0)
    return redis_mock


@pytest.fixture
def auth_service(mock_redis):
    """Create AuthService instance with mock Redis."""
    return AuthService(redis_client=mock_redis)


class TestTokenGeneration:
    """Test JWT token generation."""

    def test_generate_access_token(self, app_context, auth_service):
        """Test access token generation."""
        token = auth_service.generate_access_token(1, "test@example.com")

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify payload
        payload = jwt.decode(token, app_context.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        assert payload["user_id"] == 1
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_generate_refresh_token(self, app_context, auth_service):
        """Test refresh token generation."""
        token = auth_service.generate_refresh_token(1, "test@example.com")

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify payload
        payload = jwt.decode(token, app_context.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        assert payload["user_id"] == 1
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "refresh"
        assert "iat" in payload
        assert "exp" in payload

    def test_generate_tokens(self, app_context, auth_service):
        """Test generating both tokens at once."""
        tokens = auth_service.generate_tokens(1, "test@example.com")

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert isinstance(tokens["access_token"], str)
        assert isinstance(tokens["refresh_token"], str)
        assert tokens["access_token"] != tokens["refresh_token"]

    def test_access_token_expiry(self, app_context, auth_service):
        """Test access token has correct expiry."""
        token = auth_service.generate_access_token(1, "test@example.com")
        payload = jwt.decode(token, app_context.config["JWT_SECRET_KEY"], algorithms=["HS256"])

        # Check expiry is ~24 hours from now
        exp = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        diff = exp - now

        # Should be close to 24 hours (within 1 minute tolerance)
        assert 23.98 * 3600 < diff.total_seconds() < 24.02 * 3600

    def test_refresh_token_expiry(self, app_context, auth_service):
        """Test refresh token has correct expiry."""
        token = auth_service.generate_refresh_token(1, "test@example.com")
        payload = jwt.decode(token, app_context.config["JWT_SECRET_KEY"], algorithms=["HS256"])

        # Check expiry is ~7 days from now
        exp = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        diff = exp - now

        # Should be close to 7 days (within 1 minute tolerance)
        assert 6.99 * 86400 < diff.total_seconds() < 7.01 * 86400

    def test_tokens_are_different_each_time(self, app_context, auth_service):
        """Test that tokens are different each time due to iat."""
        token1 = auth_service.generate_access_token(1, "test@example.com")
        time.sleep(1)  # Wait 1 second to ensure different timestamp
        token2 = auth_service.generate_access_token(1, "test@example.com")

        assert token1 != token2


class TestTokenValidation:
    """Test JWT token validation."""

    def test_decode_valid_token(self, app_context, auth_service):
        """Test decoding a valid token."""
        token = auth_service.generate_access_token(1, "test@example.com")
        payload = auth_service.decode_token(token)

        assert payload["user_id"] == 1
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_decode_invalid_token(self, app_context, auth_service):
        """Test decoding an invalid token."""
        with pytest.raises(TokenInvalidError):
            auth_service.decode_token("invalid.token.here")

    def test_decode_expired_token(self, app_context, auth_service):
        """Test decoding an expired token."""
        # Create token with past expiry
        now = datetime.utcnow()
        payload = {
            "user_id": 1,
            "email": "test@example.com",
            "type": "access",
            "iat": int((now - timedelta(hours=25)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, app_context.config["JWT_SECRET_KEY"], algorithm="HS256")

        with pytest.raises(TokenExpiredError):
            auth_service.decode_token(token)

    def test_decode_wrong_signature(self, app_context, auth_service):
        """Test decoding token with wrong signature."""
        # Create token with different secret
        payload = {
            "user_id": 1,
            "email": "test@example.com",
            "type": "access",
            "iat": int(datetime.utcnow().timestamp()),
            "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        with pytest.raises(TokenInvalidError):
            auth_service.decode_token(token)

    def test_validate_access_token(self, app_context, auth_service):
        """Test validating access token."""
        token = auth_service.generate_access_token(1, "test@example.com")
        payload = auth_service.validate_access_token(token)

        assert payload["user_id"] == 1
        assert payload["type"] == "access"

    def test_validate_access_token_with_refresh_token(self, app_context, auth_service):
        """Test that refresh token fails access token validation."""
        token = auth_service.generate_refresh_token(1, "test@example.com")

        with pytest.raises(TokenInvalidError) as exc_info:
            auth_service.validate_access_token(token)
        assert "not an access token" in str(exc_info.value)

    def test_validate_refresh_token(self, app_context, auth_service):
        """Test validating refresh token."""
        token = auth_service.generate_refresh_token(1, "test@example.com")
        payload = auth_service.validate_refresh_token(token)

        assert payload["user_id"] == 1
        assert payload["type"] == "refresh"

    def test_validate_refresh_token_with_access_token(self, app_context, auth_service):
        """Test that access token fails refresh token validation."""
        token = auth_service.generate_access_token(1, "test@example.com")

        with pytest.raises(TokenInvalidError) as exc_info:
            auth_service.validate_refresh_token(token)
        assert "not a refresh token" in str(exc_info.value)


class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_access_token(self, app_context, auth_service):
        """Test refreshing access token."""
        refresh_token = auth_service.generate_refresh_token(1, "test@example.com")
        result = auth_service.refresh_access_token(refresh_token)

        assert "access_token" in result
        assert "refresh_token" in result
        assert isinstance(result["access_token"], str)

        # Verify new access token is valid
        payload = auth_service.validate_access_token(result["access_token"])
        assert payload["user_id"] == 1
        assert payload["email"] == "test@example.com"

    def test_refresh_with_invalid_token(self, app_context, auth_service):
        """Test refreshing with invalid token."""
        with pytest.raises(TokenInvalidError):
            auth_service.refresh_access_token("invalid.token")

    def test_refresh_with_access_token(self, app_context, auth_service):
        """Test refreshing with access token (should fail)."""
        access_token = auth_service.generate_access_token(1, "test@example.com")

        with pytest.raises(TokenInvalidError):
            auth_service.refresh_access_token(access_token)


class TestTokenBlacklist:
    """Test token blacklist functionality."""

    def test_blacklist_token(self, app_context, auth_service, mock_redis):
        """Test adding token to blacklist."""
        token = auth_service.generate_access_token(1, "test@example.com")

        auth_service.blacklist_token(token)

        # Verify Redis was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0].startswith("blacklist:")
        assert call_args[0][2] == "1"

    def test_blacklist_token_calculates_ttl(self, app_context, auth_service, mock_redis):
        """Test that blacklist TTL matches token expiry."""
        token = auth_service.generate_access_token(1, "test@example.com")

        auth_service.blacklist_token(token)

        # Get TTL from Redis call
        call_args = mock_redis.setex.call_args
        ttl = call_args[0][1]

        # TTL should be close to 24 hours
        assert 23.9 * 3600 < ttl < 24.1 * 3600

    def test_is_blacklisted(self, app_context, auth_service, mock_redis):
        """Test checking if token is blacklisted."""
        token = auth_service.generate_access_token(1, "test@example.com")

        # Not blacklisted
        mock_redis.exists.return_value = 0
        assert auth_service._is_blacklisted(token) is False

        # Blacklisted
        mock_redis.exists.return_value = 1
        assert auth_service._is_blacklisted(token) is True

    def test_decode_blacklisted_token(self, app_context, auth_service, mock_redis):
        """Test that blacklisted tokens are rejected."""
        token = auth_service.generate_access_token(1, "test@example.com")

        # Blacklist the token
        mock_redis.exists.return_value = 1

        with pytest.raises(TokenBlacklistedError):
            auth_service.decode_token(token)

    def test_revoke_token(self, app_context, auth_service, mock_redis):
        """Test revoking a token (alias for blacklist)."""
        token = auth_service.generate_access_token(1, "test@example.com")

        auth_service.revoke_token(token)

        # Verify Redis was called
        mock_redis.setex.assert_called_once()


class TestUserExtraction:
    """Test extracting user info from tokens."""

    def test_extract_user_from_token(self, app_context, auth_service):
        """Test extracting user info from valid token."""
        token = auth_service.generate_access_token(123, "user@example.com")
        user_info = auth_service.extract_user_from_token(token)

        assert user_info["user_id"] == 123
        assert user_info["email"] == "user@example.com"

    def test_extract_user_from_invalid_token(self, app_context, auth_service):
        """Test extracting user from invalid token."""
        with pytest.raises(TokenInvalidError):
            auth_service.extract_user_from_token("invalid.token")

    def test_extract_user_from_refresh_token(self, app_context, auth_service):
        """Test that extract fails with refresh token."""
        token = auth_service.generate_refresh_token(123, "user@example.com")

        with pytest.raises(TokenInvalidError):
            auth_service.extract_user_from_token(token)
