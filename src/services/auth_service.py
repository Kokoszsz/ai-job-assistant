"""
Authentication Service
======================
JWT token generation, validation, and management.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
import redis
from flask import current_app


class TokenError(Exception):
    """Base exception for token-related errors."""

    pass


class TokenExpiredError(TokenError):
    """Raised when token has expired."""

    pass


class TokenInvalidError(TokenError):
    """Raised when token is invalid."""

    pass


class TokenBlacklistedError(TokenError):
    """Raised when token has been blacklisted."""

    pass


class AuthService:
    """Service for JWT authentication operations."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize auth service.

        Args:
            redis_client: Optional Redis client for token blacklist
        """
        self.redis_client = redis_client

    def _get_redis(self) -> redis.Redis:
        """Get Redis client, creating if needed."""
        if self.redis_client is None:
            redis_url = current_app.config["REDIS_URL"]
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
        return self.redis_client

    def generate_access_token(self, user_id: int, email: str) -> str:
        """
        Generate JWT access token.

        Args:
            user_id: User ID
            email: User email

        Returns:
            JWT access token string
        """
        now = datetime.utcnow()
        expiry = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
        exp = now + expiry

        payload = {
            "user_id": user_id,
            "email": email,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }

        secret = current_app.config["JWT_SECRET_KEY"]
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token

    def generate_refresh_token(self, user_id: int, email: str) -> str:
        """
        Generate JWT refresh token.

        Args:
            user_id: User ID
            email: User email

        Returns:
            JWT refresh token string
        """
        now = datetime.utcnow()
        expiry = current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
        exp = now + expiry

        payload = {
            "user_id": user_id,
            "email": email,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }

        secret = current_app.config["JWT_SECRET_KEY"]
        token = jwt.encode(payload, secret, algorithm="HS256")
        return token

    def generate_tokens(self, user_id: int, email: str) -> Dict[str, str]:
        """
        Generate both access and refresh tokens.

        Args:
            user_id: User ID
            email: User email

        Returns:
            Dictionary with 'access_token' and 'refresh_token'
        """
        return {
            "access_token": self.generate_access_token(user_id, email),
            "refresh_token": self.generate_refresh_token(user_id, email),
        }

    def decode_token(self, token: str, verify: bool = True) -> Dict[str, Any]:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token string
            verify: Whether to verify signature and expiry

        Returns:
            Token payload dictionary

        Raises:
            TokenExpiredError: If token has expired
            TokenInvalidError: If token is invalid
            TokenBlacklistedError: If token is blacklisted
        """
        try:
            secret = current_app.config["JWT_SECRET_KEY"]

            # Decode token
            if verify:
                payload = jwt.decode(token, secret, algorithms=["HS256"])
            else:
                payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_signature": False})

            # Check if token is blacklisted
            if self._is_blacklisted(token):
                raise TokenBlacklistedError("Token has been revoked")

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError(f"Invalid token: {str(e)}")

    def validate_access_token(self, token: str) -> Dict[str, Any]:
        """
        Validate access token and return payload.

        Args:
            token: JWT access token

        Returns:
            Token payload if valid

        Raises:
            TokenError: If token is invalid, expired, or not an access token
        """
        payload = self.decode_token(token)

        if payload.get("type") != "access":
            raise TokenInvalidError("Token is not an access token")

        return payload

    def validate_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Validate refresh token and return payload.

        Args:
            token: JWT refresh token

        Returns:
            Token payload if valid

        Raises:
            TokenError: If token is invalid, expired, or not a refresh token
        """
        payload = self.decode_token(token)

        if payload.get("type") != "refresh":
            raise TokenInvalidError("Token is not a refresh token")

        return payload

    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dictionary with new 'access_token' and optionally new 'refresh_token'

        Raises:
            TokenError: If refresh token is invalid
        """
        payload = self.validate_refresh_token(refresh_token)

        user_id = payload["user_id"]
        email = payload["email"]

        # Generate new access token
        access_token = self.generate_access_token(user_id, email)

        return {"access_token": access_token, "refresh_token": refresh_token}  # Can optionally rotate this

    def blacklist_token(self, token: str) -> None:
        """
        Add token to blacklist (for logout).

        Args:
            token: Token to blacklist
        """
        try:
            # Decode without verification to get expiry
            payload = self.decode_token(token, verify=False)
            exp = payload.get("exp")

            if exp:
                # Calculate TTL (time until token expires)
                now = int(datetime.utcnow().timestamp())
                ttl = max(exp - now, 0)

                if ttl > 0:
                    # Store in Redis with TTL
                    redis_client = self._get_redis()
                    key = f"blacklist:{token}"
                    redis_client.setex(key, ttl, "1")
        except Exception:
            # If we can't blacklist, fail silently (token will expire anyway)
            pass

    def _is_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted.

        Args:
            token: Token to check

        Returns:
            True if blacklisted, False otherwise
        """
        try:
            redis_client = self._get_redis()
            key = f"blacklist:{token}"
            return redis_client.exists(key) > 0
        except Exception:
            # If Redis is down, assume not blacklisted
            return False

    def revoke_token(self, token: str) -> None:
        """
        Revoke a token (alias for blacklist_token).

        Args:
            token: Token to revoke
        """
        self.blacklist_token(token)

    def extract_user_from_token(self, token: str) -> Dict[str, Any]:
        """
        Extract user information from token.

        Args:
            token: JWT token

        Returns:
            Dictionary with user_id and email

        Raises:
            TokenError: If token is invalid
        """
        payload = self.validate_access_token(token)
        return {"user_id": payload["user_id"], "email": payload["email"]}

    def generate_password_reset_token(self, email: str) -> str:
        """
        Generate a secure password reset token.

        Args:
            email: User's email address

        Returns:
            Reset token (UUID4)
        """
        import uuid

        token = str(uuid.uuid4())

        # Store token in Redis with 1 hour expiry
        redis_client = self._get_redis()
        key = f"password_reset:{token}"
        redis_client.setex(key, 3600, email)  # 1 hour TTL

        return token

    def validate_password_reset_token(self, token: str) -> Optional[str]:
        """
        Validate password reset token and return associated email.

        Args:
            token: Reset token to validate

        Returns:
            Email address if token is valid, None otherwise
        """
        redis_client = self._get_redis()
        key = f"password_reset:{token}"
        email = redis_client.get(key)
        return email

    def delete_password_reset_token(self, token: str):
        """
        Delete a password reset token from Redis.

        Args:
            token: Reset token to delete
        """
        redis_client = self._get_redis()
        key = f"password_reset:{token}"
        redis_client.delete(key)
