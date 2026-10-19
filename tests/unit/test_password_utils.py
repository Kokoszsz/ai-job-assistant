"""
Unit Tests: Password Utilities
===============================
Tests for password hashing, verification, and validation.
"""

import pytest
from src.utils.password import (
    hash_password,
    verify_password,
    validate_password_strength,
    PasswordValidationError
)


class TestPasswordValidation:
    """Test password strength validation."""

    def test_valid_password(self):
        """Test that valid passwords pass validation."""
        # Should not raise any exception
        validate_password_strength("SecurePass123")
        validate_password_strength("MyP@ssw0rd")
        validate_password_strength("TestUser1234")

    def test_password_too_short(self):
        """Test that passwords under 8 characters are rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("Test123")
        assert "at least 8 characters" in str(exc_info.value)

    def test_password_no_uppercase(self):
        """Test that passwords without uppercase are rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("testpass123")
        assert "uppercase letter" in str(exc_info.value)

    def test_password_no_lowercase(self):
        """Test that passwords without lowercase are rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("TESTPASS123")
        assert "lowercase letter" in str(exc_info.value)

    def test_password_no_number(self):
        """Test that passwords without numbers are rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("TestPassword")
        assert "number" in str(exc_info.value)

    def test_empty_password(self):
        """Test that empty passwords are rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength("")
        assert "required" in str(exc_info.value)

    def test_none_password(self):
        """Test that None passwords are rejected."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(None)
        assert "required" in str(exc_info.value)


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password_returns_string(self):
        """Test that hash_password returns a string."""
        hashed = hash_password("SecurePass123")
        assert isinstance(hashed, str)

    def test_hash_password_not_plaintext(self):
        """Test that hashed password doesn't contain plaintext."""
        password = "SecurePass123"
        hashed = hash_password(password)
        assert password not in hashed

    def test_hash_password_different_each_time(self):
        """Test that same password produces different hashes (salt)."""
        password = "SecurePass123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_hash_password_starts_with_bcrypt_prefix(self):
        """Test that bcrypt hashes have correct prefix."""
        hashed = hash_password("SecurePass123")
        assert hashed.startswith("$2b$")

    def test_hash_password_validates_strength(self):
        """Test that hash_password validates password strength."""
        with pytest.raises(PasswordValidationError):
            hash_password("weak")

    def test_hash_password_length(self):
        """Test that bcrypt hash has expected length."""
        hashed = hash_password("SecurePass123")
        # Bcrypt hashes are 60 characters
        assert len(hashed) == 60


class TestPasswordVerification:
    """Test password verification functionality."""

    def test_verify_correct_password(self):
        """Test that correct password verifies successfully."""
        password = "SecurePass123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test that incorrect password fails verification."""
        password = "SecurePass123"
        hashed = hash_password(password)
        assert verify_password("WrongPass123", hashed) is False

    def test_verify_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "SecurePass123"
        hashed = hash_password(password)
        assert verify_password("securepass123", hashed) is False

    def test_verify_empty_password(self):
        """Test that empty password fails verification."""
        hashed = hash_password("SecurePass123")
        assert verify_password("", hashed) is False

    def test_verify_empty_hash(self):
        """Test that empty hash fails verification."""
        assert verify_password("SecurePass123", "") is False

    def test_verify_none_password(self):
        """Test that None password fails verification."""
        hashed = hash_password("SecurePass123")
        assert verify_password(None, hashed) is False

    def test_verify_none_hash(self):
        """Test that None hash fails verification."""
        assert verify_password("SecurePass123", None) is False

    def test_verify_invalid_hash_format(self):
        """Test that invalid hash format fails gracefully."""
        assert verify_password("SecurePass123", "invalid_hash") is False

    def test_verify_multiple_passwords(self):
        """Test verifying multiple different passwords."""
        passwords = ["Password123", "AnotherPass456", "ThirdPass789"]
        hashes = [hash_password(p) for p in passwords]
        
        # Each password should verify against its own hash
        for password, hashed in zip(passwords, hashes):
            assert verify_password(password, hashed) is True
        
        # Each password should fail against other hashes
        assert verify_password(passwords[0], hashes[1]) is False
        assert verify_password(passwords[1], hashes[2]) is False
        assert verify_password(passwords[2], hashes[0]) is False


class TestPasswordEdgeCases:
    """Test edge cases and special characters."""

    def test_password_with_special_characters(self):
        """Test passwords with special characters."""
        passwords = [
            "P@ssw0rd!",
            "Test#Pass123",
            "My$ecure1",
            "Valid&Pass9"
        ]
        for password in passwords:
            hashed = hash_password(password)
            assert verify_password(password, hashed) is True

    def test_password_with_spaces(self):
        """Test passwords containing spaces."""
        password = "My Pass 123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_very_long_password(self):
        """Test that very long passwords work correctly."""
        password = "SecurePassword123" * 10  # 170 characters
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_password_with_unicode(self):
        """Test passwords with unicode characters."""
        password = "Pássw0rd123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_minimum_valid_password(self):
        """Test minimum valid password (8 chars, 1 upper, 1 lower, 1 number)."""
        password = "Abcdef12"
        validate_password_strength(password)
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
