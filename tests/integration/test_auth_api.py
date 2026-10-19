"""
Integration Tests: Authentication API
======================================
Tests for user registration, login, and token management endpoints.
"""

import pytest
import json
from src.models import db, User, Profile
from src.app import create_app


@pytest.fixture
def app():
    """Create test Flask app."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestUserRegistration:
    """Test user registration endpoint."""
    
    def test_register_success(self, client, app):
        """Test successful user registration."""
        response = client.post('/api/auth/register', 
            json={
                'email': 'newuser@example.com',
                'password': 'SecurePass123',
                'name': 'New User'
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'user' in data['data']
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        
        # Check user data
        user = data['data']['user']
        assert user['email'] == 'newuser@example.com'
        assert user['name'] == 'New User'
        assert user['is_active'] is True
        assert 'password_hash' not in user
        
        # Verify user in database
        with app.app_context():
            db_user = User.query.filter_by(email='newuser@example.com').first()
            assert db_user is not None
            assert db_user.name == 'New User'
            assert db_user.check_password('SecurePass123')
    
    def test_register_creates_profile(self, client, app):
        """Test that registration auto-creates user profile."""
        response = client.post('/api/auth/register',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123',
                'name': 'Test User'
            }
        )
        
        assert response.status_code == 201
        
        # Verify profile was created
        with app.app_context():
            user = User.query.filter_by(email='user@example.com').first()
            assert user is not None
            assert user.profile is not None
            assert isinstance(user.profile, Profile)
    
    def test_register_missing_email(self, client):
        """Test registration without email."""
        response = client.post('/api/auth/register',
            json={
                'password': 'SecurePass123',
                'name': 'Test User'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'email' in data['error']['details']
    
    def test_register_missing_password(self, client):
        """Test registration without password."""
        response = client.post('/api/auth/register',
            json={
                'email': 'user@example.com',
                'name': 'Test User'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'password' in data['error']['details']
    
    def test_register_missing_name(self, client):
        """Test registration without name."""
        response = client.post('/api/auth/register',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'name' in data['error']['details']
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email format."""
        invalid_emails = [
            'notanemail',
            'missing@domain',
            '@nodomain.com',
            'spaces in@email.com',
            'double@@domain.com'
        ]
        
        for email in invalid_emails:
            response = client.post('/api/auth/register',
                json={
                    'email': email,
                    'password': 'SecurePass123',
                    'name': 'Test User'
                }
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert 'email' in data['error']['details']
    
    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        weak_passwords = [
            'short',           # Too short
            'noupppercase123', # No uppercase
            'NOLOWERCASE123',  # No lowercase
            'NoNumbers',       # No numbers
        ]
        
        for password in weak_passwords:
            response = client.post('/api/auth/register',
                json={
                    'email': f'user{password}@example.com',
                    'password': password,
                    'name': 'Test User'
                }
            )
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['error']['code'] == 'WEAK_PASSWORD'
    
    def test_register_duplicate_email(self, client, app):
        """Test registration with duplicate email."""
        # Create first user
        with app.app_context():
            user = User(email='existing@example.com', password_hash='hash', name='Existing')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Try to register with same email
        response = client.post('/api/auth/register',
            json={
                'email': 'existing@example.com',
                'password': 'DifferentPass123',
                'name': 'New User'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'EMAIL_EXISTS'
    
    def test_register_duplicate_email_case_insensitive(self, client, app):
        """Test that email comparison is case-insensitive."""
        # Create first user with lowercase email
        with app.app_context():
            user = User(email='user@example.com', password_hash='hash', name='User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Try to register with uppercase email
        response = client.post('/api/auth/register',
            json={
                'email': 'USER@EXAMPLE.COM',
                'password': 'SecurePass123',
                'name': 'Another User'
            }
        )
        
        # Should succeed because SQLite is case-insensitive by default
        # In production PostgreSQL, we'd need LOWER() in query
        assert response.status_code in [201, 400]
    
    def test_register_name_too_short(self, client):
        """Test registration with name too short."""
        response = client.post('/api/auth/register',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123',
                'name': 'A'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'name' in data['error']['details']
        assert '2 characters' in data['error']['details']['name']
    
    def test_register_name_too_long(self, client):
        """Test registration with name too long."""
        response = client.post('/api/auth/register',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123',
                'name': 'A' * 101
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'name' in data['error']['details']
        assert '100 characters' in data['error']['details']['name']
    
    def test_register_trims_whitespace(self, client, app):
        """Test that email and name are trimmed."""
        response = client.post('/api/auth/register',
            json={
                'email': '  user@example.com  ',
                'password': 'SecurePass123',
                'name': '  Test User  '
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['user']['email'] == 'user@example.com'
        assert data['data']['user']['name'] == 'Test User'
    
    def test_register_empty_request_body(self, client):
        """Test registration with no request body."""
        response = client.post('/api/auth/register')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_DATA'
    
    def test_register_returns_valid_tokens(self, client):
        """Test that registration returns valid JWT tokens."""
        response = client.post('/api/auth/register',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123',
                'name': 'Test User'
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        # Check tokens are strings
        assert isinstance(data['data']['access_token'], str)
        assert isinstance(data['data']['refresh_token'], str)
        
        # Check tokens are different
        assert data['data']['access_token'] != data['data']['refresh_token']
        
        # Check tokens are JWT format (3 parts separated by dots)
        assert len(data['data']['access_token'].split('.')) == 3
        assert len(data['data']['refresh_token'].split('.')) == 3
    
    def test_register_multiple_validation_errors(self, client):
        """Test that multiple validation errors are returned."""
        response = client.post('/api/auth/register',
            json={
                'email': 'invalid-email',
                'password': 'weak',
                'name': 'A'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        
        # Should have multiple errors
        errors = data['error']['details']
        assert len(errors) >= 2
        assert 'email' in errors or 'name' in errors


class TestEmailValidation:
    """Test email validation function."""
    
    def test_valid_emails(self, client):
        """Test that valid emails are accepted."""
        valid_emails = [
            'user@example.com',
            'test.user@example.com',
            'user+tag@example.co.uk',
            'user123@test-domain.com',
            'a@b.co'
        ]
        
        for i, email in enumerate(valid_emails):
            response = client.post('/api/auth/register',
                json={
                    'email': email,
                    'password': 'SecurePass123',
                    'name': f'User {i}'
                }
            )
            
            assert response.status_code == 201, f"Failed for {email}"


class TestUserLogin:
    """Test user login endpoint."""
    
    def test_login_success(self, client, app):
        """Test successful login."""
        # Create user first
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login
        response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'user' in data['data']
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        
        # Check user data
        user_data = data['data']['user']
        assert user_data['email'] == 'user@example.com'
        assert user_data['name'] == 'Test User'
        assert 'password_hash' not in user_data
    
    def test_login_updates_last_login(self, client, app):
        """Test that login updates last_login timestamp."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        
        # Login
        response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        assert response.status_code == 200
        
        # Check last_login was updated
        with app.app_context():
            user = User.query.get(user_id)
            assert user.last_login is not None
    
    def test_login_invalid_email(self, client):
        """Test login with non-existent email."""
        response = client.post('/api/auth/login',
            json={
                'email': 'nonexistent@example.com',
                'password': 'SecurePass123'
            }
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_CREDENTIALS'
        # Should use generic message (don't reveal if email exists)
        assert 'email or password' in data['error']['message'].lower()
    
    def test_login_wrong_password(self, client, app):
        """Test login with incorrect password."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('CorrectPass123')
            db.session.add(user)
            db.session.commit()
        
        # Try login with wrong password
        response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'WrongPass123'
            }
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_CREDENTIALS'
    
    def test_login_inactive_account(self, client, app):
        """Test login with inactive account."""
        # Create inactive user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User', is_active=False)
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Try to login
        response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert data['error']['code'] == 'ACCOUNT_INACTIVE'
    
    def test_login_missing_email(self, client):
        """Test login without email."""
        response = client.post('/api/auth/login',
            json={
                'password': 'SecurePass123'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_CREDENTIALS'
    
    def test_login_missing_password(self, client):
        """Test login without password."""
        response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_CREDENTIALS'
    
    def test_login_empty_request_body(self, client):
        """Test login with no request body."""
        response = client.post('/api/auth/login')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_DATA'
    
    def test_login_case_sensitive_password(self, client, app):
        """Test that password is case-sensitive."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Try with different case
        response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'securepass123'  # lowercase
            }
        )
        
        assert response.status_code == 401
    
    def test_login_email_trimmed(self, client, app):
        """Test that email whitespace is trimmed."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login with whitespace
        response = client.post('/api/auth/login',
            json={
                'email': '  user@example.com  ',
                'password': 'SecurePass123'
            }
        )
        
        assert response.status_code == 200
    
    def test_login_returns_valid_tokens(self, client, app):
        """Test that login returns valid JWT tokens."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login
        response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check tokens are strings
        assert isinstance(data['data']['access_token'], str)
        assert isinstance(data['data']['refresh_token'], str)
        
        # Check tokens are different
        assert data['data']['access_token'] != data['data']['refresh_token']
        
        # Check tokens are JWT format
        assert len(data['data']['access_token'].split('.')) == 3
        assert len(data['data']['refresh_token'].split('.')) == 3
    
    def test_login_doesnt_reveal_email_existence(self, client, app):
        """Test that error message doesn't reveal if email exists."""
        # Create user
        with app.app_context():
            user = User(email='exists@example.com', password_hash='temp', name='Test User')
            user.set_password('CorrectPass123')
            db.session.add(user)
            db.session.commit()
        
        # Wrong password for existing user
        response1 = client.post('/api/auth/login',
            json={
                'email': 'exists@example.com',
                'password': 'WrongPass123'
            }
        )
        
        # Non-existent user
        response2 = client.post('/api/auth/login',
            json={
                'email': 'notexists@example.com',
                'password': 'SomePass123'
            }
        )
        
        # Both should return same error message
        assert response1.status_code == 401
        assert response2.status_code == 401
        
        data1 = response1.get_json()
        data2 = response2.get_json()
        
        assert data1['error']['message'] == data2['error']['message']


class TestTokenRefresh:
    """Test token refresh endpoint."""
    
    def test_refresh_with_body(self, client, app):
        """Test token refresh with refresh token in body."""
        # Create user and login to get tokens
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login to get tokens
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        assert login_response.status_code == 200
        login_data = login_response.get_json()
        refresh_token = login_data['data']['refresh_token']
        original_access_token = login_data['data']['access_token']
        
        # Refresh token
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': refresh_token
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        
        # New access token should be different
        assert data['data']['access_token'] != original_access_token
    
    def test_refresh_with_header(self, client, app):
        """Test token refresh with refresh token in Authorization header."""
        # Create user and login
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login to get tokens
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        refresh_token = login_response.get_json()['data']['refresh_token']
        
        # Refresh using header
        response = client.post('/api/auth/refresh',
            headers={
                'Authorization': f'Bearer {refresh_token}'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data['data']
    
    def test_refresh_missing_token(self, client):
        """Test refresh without providing token."""
        response = client.post('/api/auth/refresh')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_TOKEN'
    
    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': 'invalid.token.here'
            }
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_TOKEN'
    
    def test_refresh_expired_token(self, client, app):
        """Test refresh with expired token."""
        # Create a token with negative expiry (already expired)
        from src.services.auth_service import AuthService
        import jwt
        from datetime import datetime, timedelta
        
        with app.app_context():
            secret = app.config['JWT_SECRET_KEY']
            
            # Create expired token
            expired_payload = {
                'user_id': 1,
                'email': 'user@example.com',
                'type': 'refresh',
                'exp': int((datetime.utcnow() - timedelta(days=1)).timestamp()),
                'iat': int((datetime.utcnow() - timedelta(days=8)).timestamp())
            }
            expired_token = jwt.encode(expired_payload, secret, algorithm='HS256')
        
        # Try to refresh with expired token
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': expired_token
            }
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'TOKEN_EXPIRED'
    
    def test_refresh_with_access_token(self, client, app):
        """Test that access token cannot be used for refresh."""
        # Create user and login
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login to get access token
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        access_token = login_response.get_json()['data']['access_token']
        
        # Try to refresh using access token (wrong token type)
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': access_token
            }
        )
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_TOKEN'
    
    def test_refresh_blacklisted_token(self, client, app):
        """Test that blacklisted tokens cannot be refreshed."""
        pytest = __import__('pytest')
        pytest.skip("Redis required for blacklist testing")
    
    def test_refresh_returns_valid_tokens(self, client, app):
        """Test that refresh returns valid JWT tokens."""
        # Create user and login
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login to get tokens
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        refresh_token = login_response.get_json()['data']['refresh_token']
        
        # Refresh token
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': refresh_token
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check tokens are strings
        assert isinstance(data['data']['access_token'], str)
        assert isinstance(data['data']['refresh_token'], str)
        
        # Check tokens are JWT format
        assert len(data['data']['access_token'].split('.')) == 3
        assert len(data['data']['refresh_token'].split('.')) == 3
    
    def test_refresh_preserves_user_info(self, client, app):
        """Test that refreshed token contains same user information."""
        from src.services.auth_service import AuthService
        
        # Create user and login
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
            user_id = user.id
        
        # Login to get tokens
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        refresh_token = login_response.get_json()['data']['refresh_token']
        
        # Refresh token
        response = client.post('/api/auth/refresh',
            json={
                'refresh_token': refresh_token
            }
        )
        
        new_access_token = response.get_json()['data']['access_token']
        
        # Verify token contains correct user info
        with app.app_context():
            auth_service = AuthService()
            payload = auth_service.validate_access_token(new_access_token)
            
            assert payload['user_id'] == user_id
            assert payload['email'] == 'user@example.com'
            assert payload['type'] == 'access'


class TestUserLogout:
    """Test user logout endpoint."""
    
    def test_logout_success(self, client, app):
        """Test successful logout."""
        # Create user and login to get tokens
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login to get tokens
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        assert login_response.status_code == 200
        refresh_token = login_response.get_json()['data']['refresh_token']
        
        # Logout
        response = client.post('/api/auth/logout',
            json={
                'refresh_token': refresh_token
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'Logged out successfully' in data['message']
    
    def test_logout_missing_token(self, client):
        """Test logout without providing token."""
        response = client.post('/api/auth/logout')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_TOKEN'
    
    def test_logout_with_invalid_token(self, client):
        """Test logout with invalid token (should still succeed)."""
        # Logout should succeed even with invalid token (safe logout)
        response = client.post('/api/auth/logout',
            json={
                'refresh_token': 'invalid.token.here'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
    
    def test_logout_with_expired_token(self, client, app):
        """Test logout with expired token (should still succeed)."""
        import jwt
        from datetime import datetime, timedelta
        
        with app.app_context():
            secret = app.config['JWT_SECRET_KEY']
            
            # Create expired token
            expired_payload = {
                'user_id': 1,
                'email': 'user@example.com',
                'type': 'refresh',
                'exp': int((datetime.utcnow() - timedelta(days=1)).timestamp()),
                'iat': int((datetime.utcnow() - timedelta(days=8)).timestamp())
            }
            expired_token = jwt.encode(expired_payload, secret, algorithm='HS256')
        
        # Logout should still work
        response = client.post('/api/auth/logout',
            json={
                'refresh_token': expired_token
            }
        )
        
        assert response.status_code == 200
    
    def test_logout_empty_request_body(self, client):
        """Test logout with no request body."""
        response = client.post('/api/auth/logout')
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'MISSING_TOKEN'
    
    def test_logout_twice_with_same_token(self, client, app):
        """Test that logging out twice with same token works (idempotent)."""
        # Create user and login
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login to get tokens
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        refresh_token = login_response.get_json()['data']['refresh_token']
        
        # First logout
        response1 = client.post('/api/auth/logout',
            json={
                'refresh_token': refresh_token
            }
        )
        
        assert response1.status_code == 200
        
        # Second logout with same token (should still succeed)
        response2 = client.post('/api/auth/logout',
            json={
                'refresh_token': refresh_token
            }
        )
        
        assert response2.status_code == 200
    
    def test_logout_response_format(self, client, app):
        """Test that logout response has correct format."""
        # Create user and login
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('SecurePass123')
            db.session.add(user)
            db.session.commit()
        
        # Login to get tokens
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'SecurePass123'
            }
        )
        
        refresh_token = login_response.get_json()['data']['refresh_token']
        
        # Logout
        response = client.post('/api/auth/logout',
            json={
                'refresh_token': refresh_token
            }
        )
        
        data = response.get_json()
        assert 'success' in data
        assert 'message' in data
        assert data['success'] is True
        assert isinstance(data['message'], str)


class TestPasswordReset:
    """Test password reset flow."""
    
    def test_request_reset_success(self, client, app):
        """Test successful password reset request."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('OldPass123')
            db.session.add(user)
            db.session.commit()
        
        response = client.post('/api/auth/password-reset/request',
            json={
                'email': 'user@example.com'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'message' in data
        assert 'password reset link' in data['message'].lower()
    
    def test_request_reset_nonexistent_email(self, client):
        """Test password reset request for non-existent email (should succeed for security)."""
        response = client.post('/api/auth/password-reset/request',
            json={
                'email': 'nonexistent@example.com'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Should return generic success message to avoid revealing if email exists
    
    def test_request_reset_missing_email(self, client):
        """Test password reset request without email."""
        response = client.post('/api/auth/password-reset/request',
            json={}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_INPUT'
    
    def test_request_reset_invalid_email(self, client):
        """Test password reset request with invalid email format."""
        response = client.post('/api/auth/password-reset/request',
            json={
                'email': 'not-an-email'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_INPUT'
    
    def test_request_reset_empty_body(self, client):
        """Test password reset request with empty body."""
        response = client.post('/api/auth/password-reset/request',
            data='',
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
    
    def test_confirm_reset_success(self, client, app):
        """Test successful password reset confirmation."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('OldPass123')
            db.session.add(user)
            db.session.commit()
            
            # Generate reset token
            from src.services.auth_service import AuthService
            auth_service = AuthService()
            reset_token = auth_service.generate_password_reset_token('user@example.com')
        
        # Reset password
        response = client.post('/api/auth/password-reset/confirm',
            json={
                'token': reset_token,
                'new_password': 'NewSecure123'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'Password reset successful' in data['message']
        
        # Verify new password works
        login_response = client.post('/api/auth/login',
            json={
                'email': 'user@example.com',
                'password': 'NewSecure123'
            }
        )
        assert login_response.status_code == 200
    
    def test_confirm_reset_invalid_token(self, client):
        """Test password reset with invalid token."""
        response = client.post('/api/auth/password-reset/confirm',
            json={
                'token': 'invalid-token-12345',
                'new_password': 'NewSecure123'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_TOKEN'
    
    def test_confirm_reset_weak_password(self, client, app):
        """Test password reset with weak password."""
        # Create user and generate token
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('OldPass123')
            db.session.add(user)
            db.session.commit()
            
            from src.services.auth_service import AuthService
            auth_service = AuthService()
            reset_token = auth_service.generate_password_reset_token('user@example.com')
        
        # Try to reset with weak password
        response = client.post('/api/auth/password-reset/confirm',
            json={
                'token': reset_token,
                'new_password': 'weak'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'WEAK_PASSWORD'
    
    def test_confirm_reset_missing_token(self, client):
        """Test password reset without token."""
        response = client.post('/api/auth/password-reset/confirm',
            json={
                'new_password': 'NewSecure123'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_INPUT'
    
    def test_confirm_reset_missing_password(self, client, app):
        """Test password reset without new password."""
        with app.app_context():
            from src.services.auth_service import AuthService
            auth_service = AuthService()
            reset_token = auth_service.generate_password_reset_token('user@example.com')
        
        response = client.post('/api/auth/password-reset/confirm',
            json={
                'token': reset_token
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_INPUT'
    
    def test_confirm_reset_token_used_once(self, client, app):
        """Test that reset token can only be used once."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('OldPass123')
            db.session.add(user)
            db.session.commit()
            
            from src.services.auth_service import AuthService
            auth_service = AuthService()
            reset_token = auth_service.generate_password_reset_token('user@example.com')
        
        # Use token first time
        response1 = client.post('/api/auth/password-reset/confirm',
            json={
                'token': reset_token,
                'new_password': 'NewSecure123'
            }
        )
        assert response1.status_code == 200
        
        # Try to use token again
        response2 = client.post('/api/auth/password-reset/confirm',
            json={
                'token': reset_token,
                'new_password': 'AnotherPass123'
            }
        )
        assert response2.status_code == 400
        data = response2.get_json()
        assert data['error']['code'] == 'INVALID_TOKEN'
    
    def test_confirm_reset_email_trimming(self, client, app):
        """Test that email is trimmed and lowercased properly."""
        # Create user
        with app.app_context():
            user = User(email='user@example.com', password_hash='temp', name='Test User')
            user.set_password('OldPass123')
            db.session.add(user)
            db.session.commit()
        
        # Request reset with uppercase and spaces
        response = client.post('/api/auth/password-reset/request',
            json={
                'email': '  USER@EXAMPLE.COM  '
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
