"""
Unit Tests: Authentication Middleware
=====================================
Tests for JWT authentication decorator.
"""

import pytest
from flask import Flask, jsonify
from unittest.mock import patch, MagicMock
from src.middleware.auth_middleware import require_auth, optional_auth
from src.services.auth_service import (
    TokenExpiredError,
    TokenInvalidError,
    TokenBlacklistedError
)


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    
    # Test route with required auth
    @app.route('/protected')
    @require_auth
    def protected_route(user_id, email):
        return jsonify({'user_id': user_id, 'email': email})
    
    # Test route with optional auth
    @app.route('/optional')
    @optional_auth
    def optional_route(user_id=None, email=None):
        return jsonify({'user_id': user_id, 'email': email})
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestRequireAuth:
    """Test require_auth decorator."""
    
    def test_no_authorization_header(self, client):
        """Test request without Authorization header."""
        response = client.get('/protected')
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NO_TOKEN'
    
    def test_invalid_authorization_format(self, client):
        """Test request with invalid Authorization format."""
        # Missing Bearer prefix
        response = client.get('/protected', headers={
            'Authorization': 'InvalidToken'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_HEADER'
    
    def test_missing_token_after_bearer(self, client):
        """Test Bearer without token."""
        response = client.get('/protected', headers={
            'Authorization': 'Bearer'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_HEADER'
    
    @patch('src.middleware.auth_middleware.AuthService')
    def test_valid_token(self, mock_auth_service_class, client):
        """Test request with valid token."""
        # Mock AuthService
        mock_service = MagicMock()
        mock_service.extract_user_from_token.return_value = {
            'user_id': 123,
            'email': 'test@example.com'
        }
        mock_auth_service_class.return_value = mock_service
        
        response = client.get('/protected', headers={
            'Authorization': 'Bearer valid.token.here'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 123
        assert data['email'] == 'test@example.com'
    
    @patch('src.middleware.auth_middleware.AuthService')
    def test_expired_token(self, mock_auth_service_class, client):
        """Test request with expired token."""
        mock_service = MagicMock()
        mock_service.extract_user_from_token.side_effect = TokenExpiredError("Token expired")
        mock_auth_service_class.return_value = mock_service
        
        response = client.get('/protected', headers={
            'Authorization': 'Bearer expired.token'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'TOKEN_EXPIRED'
    
    @patch('src.middleware.auth_middleware.AuthService')
    def test_blacklisted_token(self, mock_auth_service_class, client):
        """Test request with blacklisted token."""
        mock_service = MagicMock()
        mock_service.extract_user_from_token.side_effect = TokenBlacklistedError("Token revoked")
        mock_auth_service_class.return_value = mock_service
        
        response = client.get('/protected', headers={
            'Authorization': 'Bearer blacklisted.token'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'TOKEN_REVOKED'
    
    @patch('src.middleware.auth_middleware.AuthService')
    def test_invalid_token(self, mock_auth_service_class, client):
        """Test request with invalid token."""
        mock_service = MagicMock()
        mock_service.extract_user_from_token.side_effect = TokenInvalidError("Invalid token")
        mock_auth_service_class.return_value = mock_service
        
        response = client.get('/protected', headers={
            'Authorization': 'Bearer invalid.token'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_TOKEN'
    
    @patch('src.middleware.auth_middleware.AuthService')
    def test_case_insensitive_bearer(self, mock_auth_service_class, client):
        """Test that Bearer keyword is case-insensitive."""
        mock_service = MagicMock()
        mock_service.extract_user_from_token.return_value = {
            'user_id': 123,
            'email': 'test@example.com'
        }
        mock_auth_service_class.return_value = mock_service
        
        # Test lowercase
        response = client.get('/protected', headers={
            'Authorization': 'bearer valid.token'
        })
        assert response.status_code == 200
        
        # Test mixed case
        response = client.get('/protected', headers={
            'Authorization': 'BeArEr valid.token'
        })
        assert response.status_code == 200


class TestOptionalAuth:
    """Test optional_auth decorator."""
    
    def test_no_authorization_header(self, client):
        """Test request without Authorization header (should succeed)."""
        response = client.get('/optional')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] is None
        assert data['email'] is None
    
    def test_invalid_authorization_format(self, client):
        """Test request with invalid format (should succeed without auth)."""
        response = client.get('/optional', headers={
            'Authorization': 'InvalidFormat'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] is None
        assert data['email'] is None
    
    @patch('src.middleware.auth_middleware.AuthService')
    def test_valid_token(self, mock_auth_service_class, client):
        """Test request with valid token."""
        mock_service = MagicMock()
        mock_service.extract_user_from_token.return_value = {
            'user_id': 456,
            'email': 'user@example.com'
        }
        mock_auth_service_class.return_value = mock_service
        
        response = client.get('/optional', headers={
            'Authorization': 'Bearer valid.token'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] == 456
        assert data['email'] == 'user@example.com'
    
    @patch('src.middleware.auth_middleware.AuthService')
    def test_invalid_token(self, mock_auth_service_class, client):
        """Test request with invalid token (should succeed without auth)."""
        mock_service = MagicMock()
        mock_service.extract_user_from_token.side_effect = TokenInvalidError("Invalid")
        mock_auth_service_class.return_value = mock_service
        
        response = client.get('/optional', headers={
            'Authorization': 'Bearer invalid.token'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] is None
        assert data['email'] is None
    
    @patch('src.middleware.auth_middleware.AuthService')
    def test_expired_token(self, mock_auth_service_class, client):
        """Test request with expired token (should succeed without auth)."""
        mock_service = MagicMock()
        mock_service.extract_user_from_token.side_effect = TokenExpiredError("Expired")
        mock_auth_service_class.return_value = mock_service
        
        response = client.get('/optional', headers={
            'Authorization': 'Bearer expired.token'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_id'] is None
        assert data['email'] is None


class TestDecoratorPreservesFunction:
    """Test that decorators preserve function metadata."""
    
    def test_require_auth_preserves_name(self):
        """Test that require_auth preserves function name."""
        @require_auth
        def my_function(user_id, email):
            pass
        
        assert my_function.__name__ == 'my_function'
    
    def test_optional_auth_preserves_name(self):
        """Test that optional_auth preserves function name."""
        @optional_auth
        def my_function(user_id=None, email=None):
            pass
        
        assert my_function.__name__ == 'my_function'
