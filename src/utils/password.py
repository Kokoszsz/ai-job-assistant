"""
Password Utilities
==================
Password hashing, verification, and validation utilities.
"""

import re

import bcrypt


class PasswordValidationError(ValueError):
    """Raised when password validation fails."""

    pass


def validate_password_strength(password: str) -> None:
    """
    Validate password meets strength requirements.

    Requirements per spec:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number

    Args:
        password: The password to validate

    Raises:
        PasswordValidationError: If password doesn't meet requirements
    """
    if not password:
        raise PasswordValidationError("Password is required")

    if len(password) < 8:
        raise PasswordValidationError("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", password):
        raise PasswordValidationError("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        raise PasswordValidationError("Password must contain at least one lowercase letter")

    if not re.search(r"[0-9]", password):
        raise PasswordValidationError("Password must contain at least one number")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with cost factor 12.

    Note: bcrypt has a 72-byte limit. Longer passwords are truncated.

    Args:
        password: The plaintext password to hash

    Returns:
        The hashed password as a string

    Raises:
        PasswordValidationError: If password doesn't meet strength requirements
    """
    # Validate password strength first
    validate_password_strength(password)

    # Hash with bcrypt (cost factor 12)
    # Truncate to 72 bytes if necessary (bcrypt limitation)
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)

    # Return as string for database storage
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a bcrypt hash.

    Args:
        password: The plaintext password to verify
        password_hash: The bcrypt hash to verify against

    Returns:
        True if password matches hash, False otherwise
    """
    if not password or not password_hash:
        return False

    try:
        # Truncate to 72 bytes if necessary (bcrypt limitation)
        password_bytes = password.encode("utf-8")[:72]
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except (ValueError, AttributeError):
        # Invalid hash format or other bcrypt errors
        return False
