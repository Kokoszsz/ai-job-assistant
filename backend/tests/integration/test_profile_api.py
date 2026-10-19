"""
Test Profile API Endpoints
===========================
Integration tests for profile management endpoints.
"""

import pytest
from src.app import create_app
from src.models.base import db
from src.models.user import User
from src.models.profile import Profile
from src.services.auth_service import AuthService


@pytest.fixture
def app():
    """Create application for testing."""
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


@pytest.fixture
def test_user(app):
    """Create a test user with profile."""
    with app.app_context():
        user = User(
            email='test@example.com',
            password_hash='hashed_password',
            name='Test User'
        )
        db.session.add(user)
        db.session.commit()
        
        profile = Profile(
            user_id=user.id,
            summary='Test summary',
            phone='+1234567890',
            location='New York, NY',
            preferences_json={
                'desired_roles': ['Software Engineer'],
                'locations': ['New York, NY'],
                'job_types': ['full-time']
            }
        )
        db.session.add(profile)
        db.session.commit()
        
        return user.id


@pytest.fixture
def user_without_profile(app):
    """Create a test user without profile."""
    with app.app_context():
        user = User(
            email='noprofile@example.com',
            password_hash='hashed_password',
            name='No Profile User'
        )
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def auth_headers(app, test_user):
    """Create JWT auth headers for test user."""
    with app.app_context():
        auth_service = AuthService()
        user = User.query.get(test_user)
        access_token = auth_service.generate_access_token(user.id, user.email)
        return {'Authorization': f'Bearer {access_token}'}


# ============================================================================
# GET /api/profile - Get Profile
# ============================================================================

def test_get_profile_success(client, test_user, auth_headers):
    """Test getting user profile successfully."""
    response = client.get('/api/profile', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['user_id'] == test_user
    assert data['summary'] == 'Test summary'
    assert data['phone'] == '+1234567890'
    assert data['location'] == 'New York, NY'
    assert 'preferences' in data
    assert data['preferences']['desired_roles'] == ['Software Engineer']
    assert 'created_at' in data
    assert 'updated_at' in data


def test_get_profile_with_details(client, test_user, auth_headers):
    """Test getting profile with work experience, education, and skills."""
    response = client.get('/api/profile?include_details=true', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert 'work_experiences' in data
    assert 'education' in data
    assert 'skills' in data
    assert isinstance(data['work_experiences'], list)
    assert isinstance(data['education'], list)
    assert isinstance(data['skills'], list)


def test_get_profile_not_found(client, user_without_profile, app):
    """Test getting profile that doesn't exist."""
    with app.app_context():
        auth_service = AuthService()
        user = User.query.get(user_without_profile)
        access_token = auth_service.generate_access_token(user.id, user.email)
        auth_headers = {'Authorization': f'Bearer {access_token}'}
    
    response = client.get('/api/profile', headers=auth_headers)
    
    assert response.status_code == 404
    data = response.get_json()
    
    assert data['error'] == 'PROFILE_NOT_FOUND'
    assert 'message' in data


def test_get_profile_missing_user_id(client):
    """Test getting profile without authentication header."""
    response = client.get('/api/profile')
    
    assert response.status_code == 401
    data = response.get_json()
    
    assert data['error']['code'] == 'NO_TOKEN'
    assert 'message' in data['error']


def test_get_profile_invalid_user_id(client, app):
    """Test getting profile with invalid JWT token."""
    with app.app_context():
        auth_service = AuthService()
        # Create token for non-existent user
        access_token = auth_service.generate_access_token(99999, 'invalid@test.com')
        auth_headers = {'Authorization': f'Bearer {access_token}'}
    
    response = client.get('/api/profile', headers=auth_headers)
    
    assert response.status_code == 404
    data = response.get_json()
    
    assert data['error'] == 'PROFILE_NOT_FOUND'


# ============================================================================
# PUT /api/profile - Update Profile
# ============================================================================

def test_update_profile_success(client, test_user, auth_headers):
    """Test updating profile successfully."""
    update_data = {
        'summary': 'Updated summary',
        'phone': '+9876543210',
        'location': 'San Francisco, CA'
    }
    
    response = client.put(
        '/api/profile',
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['summary'] == 'Updated summary'
    assert data['phone'] == '+9876543210'
    assert data['location'] == 'San Francisco, CA'
    assert data['user_id'] == test_user


def test_update_profile_partial(client, test_user, auth_headers):
    """Test updating only some profile fields."""
    update_data = {
        'summary': 'Only updating summary'
    }
    
    response = client.put(
        '/api/profile',
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['summary'] == 'Only updating summary'
    # Phone and location should remain unchanged
    assert data['phone'] == '+1234567890'
    assert data['location'] == 'New York, NY'


def test_update_profile_not_found(client, user_without_profile, app):
    """Test updating profile that doesn't exist."""
    with app.app_context():
        auth_service = AuthService()
        user = User.query.get(user_without_profile)
        access_token = auth_service.generate_access_token(user.id, user.email)
        auth_headers = {'Authorization': f'Bearer {access_token}'}
    update_data = {'summary': 'Test'}
    
    response = client.put(
        '/api/profile',
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 404
    data = response.get_json()
    
    assert data['error'] == 'PROFILE_NOT_FOUND'


def test_update_profile_missing_user_id(client):
    """Test updating profile without authentication header."""
    update_data = {'summary': 'Test'}
    
    response = client.put('/api/profile', json=update_data)
    
    assert response.status_code == 401
    data = response.get_json()
    
    assert data['error']['code'] == 'NO_TOKEN'


def test_update_profile_missing_body(client, test_user, auth_headers):
    """Test updating profile without request body."""
    response = client.put('/api/profile', headers=auth_headers)
    
    assert response.status_code == 400
    data = response.get_json()
    
    assert data['error'] == 'MISSING_DATA'


def test_update_profile_invalid_fields(client, test_user, auth_headers):
    """Test updating profile with invalid fields."""
    update_data = {
        'summary': 'Valid',
        'invalid_field': 'Should not be allowed'
    }
    
    response = client.put(
        '/api/profile',
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    data = response.get_json()
    
    assert data['error'] == 'INVALID_FIELDS'
    assert 'invalid_field' in data['message']


def test_update_profile_validation_errors(client, test_user, auth_headers):
    """Test validation errors for profile fields."""
    # Test summary too long
    update_data = {'summary': 'x' * 5001}
    response = client.put(
        '/api/profile',
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'VALIDATION_ERROR'
    assert 'Summary' in data['message']
    
    # Test phone too long
    update_data = {'phone': '1' * 21}
    response = client.put(
        '/api/profile',
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'VALIDATION_ERROR'
    assert 'Phone' in data['message']
    
    # Test location too long
    update_data = {'location': 'x' * 101}
    response = client.put(
        '/api/profile',
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'VALIDATION_ERROR'
    assert 'Location' in data['message']


# ============================================================================
# GET /api/profile/preferences - Get Preferences
# ============================================================================

def test_get_preferences_success(client, test_user, auth_headers):
    """Test getting job preferences successfully."""
    response = client.get('/api/profile/preferences', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['user_id'] == test_user
    assert 'preferences' in data
    assert data['preferences']['desired_roles'] == ['Software Engineer']
    assert data['preferences']['locations'] == ['New York, NY']
    assert data['preferences']['job_types'] == ['full-time']


def test_get_preferences_not_found(client, user_without_profile, app):
    """Test getting preferences for non-existent profile."""
    with app.app_context():
        auth_service = AuthService()
        user = User.query.get(user_without_profile)
        access_token = auth_service.generate_access_token(user.id, user.email)
        auth_headers = {'Authorization': f'Bearer {access_token}'}
    response = client.get('/api/profile/preferences', headers=auth_headers)
    
    assert response.status_code == 404
    data = response.get_json()
    
    assert data['error'] == 'PROFILE_NOT_FOUND'


def test_get_preferences_missing_user_id(client):
    """Test getting preferences without authentication header."""
    response = client.get('/api/profile/preferences')
    
    assert response.status_code == 401
    data = response.get_json()
    
    assert data['error']['code'] == 'NO_TOKEN'


# ============================================================================
# PUT /api/profile/preferences - Update Preferences
# ============================================================================

def test_update_preferences_success(client, test_user, auth_headers):
    """Test updating job preferences successfully."""
    preferences = {
        'desired_roles': ['Senior Software Engineer', 'Tech Lead'],
        'locations': ['Remote', 'San Francisco, CA'],
        'job_types': ['full-time', 'remote'],
        'min_salary': 120000,
        'max_salary': 180000,
        'experience_level': 'senior'
    }
    
    response = client.put(
        '/api/profile/preferences',
        json=preferences,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['user_id'] == test_user
    assert data['preferences']['desired_roles'] == preferences['desired_roles']
    assert data['preferences']['locations'] == preferences['locations']
    assert data['preferences']['job_types'] == preferences['job_types']
    assert data['preferences']['min_salary'] == 120000
    assert data['preferences']['max_salary'] == 180000


def test_update_preferences_partial(client, test_user, auth_headers):
    """Test updating only some preferences."""
    preferences = {
        'desired_roles': ['Data Scientist']
    }
    
    response = client.put(
        '/api/profile/preferences',
        json=preferences,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['preferences']['desired_roles'] == ['Data Scientist']


def test_update_preferences_not_found(client, user_without_profile, app):
    """Test updating preferences for non-existent profile."""
    with app.app_context():
        auth_service = AuthService()
        user = User.query.get(user_without_profile)
        access_token = auth_service.generate_access_token(user.id, user.email)
        auth_headers = {'Authorization': f'Bearer {access_token}'}
    preferences = {'desired_roles': ['Engineer']}
    
    response = client.put(
        '/api/profile/preferences',
        json=preferences,
        headers=auth_headers
    )
    
    assert response.status_code == 404
    data = response.get_json()
    
    assert data['error'] == 'PROFILE_NOT_FOUND'


def test_update_preferences_missing_user_id(client):
    """Test updating preferences without authentication header."""
    preferences = {'desired_roles': ['Engineer']}
    
    response = client.put('/api/profile/preferences', json=preferences)
    
    assert response.status_code == 401
    data = response.get_json()
    
    assert data['error']['code'] == 'NO_TOKEN'


def test_update_preferences_missing_body(client, test_user, auth_headers):
    """Test updating preferences without request body."""
    response = client.put('/api/profile/preferences', headers=auth_headers)
    
    assert response.status_code == 400
    data = response.get_json()
    
    assert data['error'] == 'MISSING_DATA'


def test_update_preferences_validation_errors(client, test_user, auth_headers):
    """Test validation errors for preferences."""
    # Test invalid job_type
    preferences = {'job_types': ['invalid-type']}
    response = client.put(
        '/api/profile/preferences',
        json=preferences,
        headers=auth_headers
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'VALIDATION_ERROR'
    assert 'Invalid job_type' in data['message']
    
    # Test negative min_salary
    preferences = {'min_salary': -1000}
    response = client.put(
        '/api/profile/preferences',
        json=preferences,
        headers=auth_headers
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'VALIDATION_ERROR'
    assert 'min_salary' in data['message']
    
    # Test min_salary > max_salary
    preferences = {'min_salary': 150000, 'max_salary': 100000}
    response = client.put(
        '/api/profile/preferences',
        json=preferences,
        headers=auth_headers
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'VALIDATION_ERROR'
    assert 'min_salary cannot be greater than max_salary' in data['message']


def test_update_preferences_not_dict(client, test_user, auth_headers):
    """Test updating preferences with non-dictionary data."""
    response = client.put(
        '/api/profile/preferences',
        json="not a dict",
        headers=auth_headers
    )
    
    assert response.status_code == 400
    data = response.get_json()
    
    assert data['error'] == 'VALIDATION_ERROR'
    assert 'dictionary' in data['message']


# Work Experience Tests

def test_get_work_experiences_empty(client, test_user, auth_headers):
    """Test getting work experiences when none exist."""
    response = client.get('/api/profile/experience', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_add_work_experience_success(client, test_user, auth_headers):
    """Test adding a work experience entry."""
    experience_data = {
        'job_title': 'Senior Software Engineer',
        'company': 'Tech Corp',
        'start_date': '2020-01-01',
        'end_date': '2023-12-31',
        'description': 'Led development of microservices architecture'
    }
    
    response = client.post(
        '/api/profile/experience',
        json=experience_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['job_title'] == 'Senior Software Engineer'
    assert data['company'] == 'Tech Corp'
    assert data['start_date'] == '2020-01-01'
    assert data['end_date'] == '2023-12-31'
    assert data['is_current'] is False
    assert 'id' in data


def test_add_work_experience_current_position(client, test_user, auth_headers):
    """Test adding a current position (no end date)."""
    experience_data = {
        'job_title': 'Lead Engineer',
        'company': 'Current Company',
        'start_date': '2024-01-01',
        'description': 'Current role'
    }
    
    response = client.post(
        '/api/profile/experience',
        json=experience_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['end_date'] is None
    assert data['is_current'] is True


def test_add_work_experience_missing_required_fields(client, test_user, auth_headers):
    """Test adding work experience with missing required fields."""
    # Missing job_title
    response = client.post(
        '/api/profile/experience',
        json={'company': 'Tech Corp', 'start_date': '2020-01-01'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'job_title' in response.get_json()['message']
    
    # Missing company
    response = client.post(
        '/api/profile/experience',
        json={'job_title': 'Engineer', 'start_date': '2020-01-01'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'company' in response.get_json()['message']
    
    # Missing start_date
    response = client.post(
        '/api/profile/experience',
        json={'job_title': 'Engineer', 'company': 'Tech Corp'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'start_date' in response.get_json()['message']


def test_add_work_experience_invalid_dates(client, test_user, auth_headers):
    """Test adding work experience with end date before start date."""
    experience_data = {
        'job_title': 'Engineer',
        'company': 'Tech Corp',
        'start_date': '2023-01-01',
        'end_date': '2022-01-01'
    }
    
    response = client.post(
        '/api/profile/experience',
        json=experience_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'VALIDATION_ERROR'
    assert 'after start date' in data['message']


def test_add_work_experience_validation_errors(client, test_user, auth_headers):
    """Test field length validation."""
    # Job title too long
    response = client.post(
        '/api/profile/experience',
        json={
            'job_title': 'A' * 101,
            'company': 'Tech Corp',
            'start_date': '2020-01-01'
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'Job title' in response.get_json()['message']
    
    # Company too long
    response = client.post(
        '/api/profile/experience',
        json={
            'job_title': 'Engineer',
            'company': 'C' * 101,
            'start_date': '2020-01-01'
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'Company' in response.get_json()['message']
    
    # Description too long
    response = client.post(
        '/api/profile/experience',
        json={
            'job_title': 'Engineer',
            'company': 'Tech Corp',
            'start_date': '2020-01-01',
            'description': 'D' * 2001
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'Description' in response.get_json()['message']


def test_add_work_experience_missing_user_id(client):
    """Test adding work experience without authentication header."""
    response = client.post(
        '/api/profile/experience',
        json={'job_title': 'Engineer', 'company': 'Tech', 'start_date': '2020-01-01'}
    )
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['error']['code'] == 'NO_TOKEN'


def test_add_work_experience_missing_body(client, test_user, auth_headers):
    """Test adding work experience without request body."""
    response = client.post('/api/profile/experience', headers=auth_headers)
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'MISSING_DATA'


def test_get_work_experiences_success(client, test_user, auth_headers):
    """Test getting work experiences after adding some."""
    # Add two experiences
    exp1 = {
        'job_title': 'Junior Engineer',
        'company': 'StartUp Inc',
        'start_date': '2018-01-01',
        'end_date': '2020-01-01'
    }
    exp2 = {
        'job_title': 'Senior Engineer',
        'company': 'Big Tech',
        'start_date': '2020-01-01'
    }
    
    client.post('/api/profile/experience', json=exp1, headers=auth_headers)
    client.post('/api/profile/experience', json=exp2, headers=auth_headers)
    
    response = client.get('/api/profile/experience', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    # Should be ordered by start_date descending
    assert data[0]['job_title'] in ['Junior Engineer', 'Senior Engineer']


def test_update_work_experience_success(client, test_user, auth_headers):
    """Test updating a work experience entry."""
    # Add an experience
    exp_data = {
        'job_title': 'Engineer',
        'company': 'Tech Corp',
        'start_date': '2020-01-01',
        'description': 'Original description'
    }
    response = client.post('/api/profile/experience', json=exp_data, headers=auth_headers)
    exp_id = response.get_json()['id']
    
    # Update it
    update_data = {
        'job_title': 'Senior Engineer',
        'description': 'Updated description',
        'end_date': '2023-12-31'
    }
    response = client.put(
        f'/api/profile/experience/{exp_id}',
        json=update_data,
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['job_title'] == 'Senior Engineer'
    assert data['description'] == 'Updated description'
    assert data['end_date'] == '2023-12-31'
    assert data['company'] == 'Tech Corp'  # Unchanged


def test_update_work_experience_not_found(client, test_user, auth_headers):
    """Test updating a non-existent work experience."""
    response = client.put(
        '/api/profile/experience/99999',
        json={'job_title': 'New Title'},
        headers=auth_headers
    )
    
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'NOT_FOUND'


def test_update_work_experience_validation_errors(client, test_user, auth_headers):
    """Test update validation."""
    # Add an experience
    exp_data = {
        'job_title': 'Engineer',
        'company': 'Tech Corp',
        'start_date': '2020-01-01'
    }
    response = client.post('/api/profile/experience', json=exp_data, headers=auth_headers)
    exp_id = response.get_json()['id']
    
    # Try invalid update (empty job_title)
    response = client.put(
        f'/api/profile/experience/{exp_id}',
        json={'job_title': ''},
        headers=auth_headers
    )
    assert response.status_code == 400
    
    # Try invalid dates
    response = client.put(
        f'/api/profile/experience/{exp_id}',
        json={'end_date': '2019-01-01'},  # Before start_date
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'after start date' in response.get_json()['message']


def test_update_work_experience_missing_user_id(client, test_user):
    """Test updating without authentication header."""
    response = client.put(
        '/api/profile/experience/1',
        json={'job_title': 'New Title'}
    )
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['error']['code'] == 'NO_TOKEN'


def test_update_work_experience_missing_body(client, test_user, auth_headers):
    """Test updating without request body."""
    response = client.put('/api/profile/experience/1', headers=auth_headers)
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == 'MISSING_DATA'


def test_delete_work_experience_success(client, test_user, auth_headers):
    """Test deleting a work experience entry."""
    # Add an experience
    exp_data = {
        'job_title': 'Engineer',
        'company': 'Tech Corp',
        'start_date': '2020-01-01'
    }
    response = client.post('/api/profile/experience', json=exp_data, headers=auth_headers)
    exp_id = response.get_json()['id']
    
    # Delete it
    response = client.delete(f'/api/profile/experience/{exp_id}', headers=auth_headers)
    assert response.status_code == 204
    
    # Verify it's gone
    response = client.get('/api/profile/experience', headers=auth_headers)
    data = response.get_json()
    assert len(data) == 0


def test_delete_work_experience_not_found(client, test_user, auth_headers):
    """Test deleting a non-existent work experience."""
    response = client.delete('/api/profile/experience/99999', headers=auth_headers)
    
    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'NOT_FOUND'


def test_delete_work_experience_missing_user_id(client):
    """Test deleting without authentication header."""
    response = client.delete('/api/profile/experience/1')
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['error']['code'] == 'NO_TOKEN'


def test_work_experience_ownership(client, test_user, user_without_profile, app):
    """Test that users can only access their own work experiences."""
    with app.app_context():
        auth_service = AuthService()
        user1 = User.query.get(test_user)
        user2 = User.query.get(user_without_profile)
        auth_headers_user1 = {'Authorization': f'Bearer {auth_service.generate_access_token(user1.id, user1.email)}'}
        auth_headers_user2 = {'Authorization': f'Bearer {auth_service.generate_access_token(user2.id, user2.email)}'}
    
    # User 1 adds an experience
    exp_data = {
        'job_title': 'Engineer',
        'company': 'Tech Corp',
        'start_date': '2020-01-01'
    }
    response = client.post('/api/profile/experience', json=exp_data, headers=auth_headers_user1)
    exp_id = response.get_json()['id']
    
    # User 2 tries to update it
    response = client.put(
        f'/api/profile/experience/{exp_id}',
        json={'job_title': 'Hacked'},
        headers=auth_headers_user2
    )
    assert response.status_code == 404  # Not found (because it doesn't belong to user 2)
    
    # User 2 tries to delete it
    response = client.delete(f'/api/profile/experience/{exp_id}', headers=auth_headers_user2)
    assert response.status_code == 404
    
    # Verify it still exists for user 1
    response = client.get('/api/profile/experience', headers=auth_headers_user1)
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['job_title'] == 'Engineer'


# ===== Education Endpoint Tests =====

def test_get_education_empty(client, test_user, auth_headers):
    """Test getting education when none exist."""
    response = client.get('/api/profile/education', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_add_education_success(client, test_user, auth_headers):
    """Test adding education with all fields."""
    education_data = {
        'degree': 'Bachelor of Science',
        'institution': 'MIT',
        'field_of_study': 'Computer Science',
        'start_date': '2015-09-01',
        'end_date': '2019-05-15'
    }
    
    response = client.post(
        '/api/profile/education',
        json=education_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['degree'] == 'Bachelor of Science'
    assert data['institution'] == 'MIT'
    assert data['field_of_study'] == 'Computer Science'
    assert data['start_date'] == '2015-09-01'
    assert data['end_date'] == '2019-05-15'
    assert 'id' in data


def test_add_education_ongoing(client, test_user, auth_headers):
    """Test adding ongoing education (no end_date)."""
    education_data = {
        'degree': 'Master of Science',
        'institution': 'Stanford',
        'field_of_study': 'Artificial Intelligence',
        'start_date': '2023-09-01'
    }
    
    response = client.post(
        '/api/profile/education',
        json=education_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['degree'] == 'Master of Science'
    assert data['end_date'] is None


def test_add_education_missing_required_fields(client, test_user, auth_headers):
    """Test adding education without required fields."""
    # Missing degree
    response = client.post(
        '/api/profile/education',
        json={'institution': 'MIT', 'start_date': '2015-09-01'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'degree' in response.get_json()['message']
    
    # Missing institution
    response = client.post(
        '/api/profile/education',
        json={'degree': 'BS', 'start_date': '2015-09-01'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'institution' in response.get_json()['message']
    
    # Missing start_date
    response = client.post(
        '/api/profile/education',
        json={'degree': 'BS', 'institution': 'MIT'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'start_date' in response.get_json()['message']


def test_add_education_invalid_dates(client, test_user, auth_headers):
    """Test adding education with end_date before start_date."""
    education_data = {
        'degree': 'BS',
        'institution': 'MIT',
        'start_date': '2019-09-01',
        'end_date': '2015-05-15'
    }
    
    response = client.post(
        '/api/profile/education',
        json=education_data,
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'after start_date' in response.get_json()['message']


def test_add_education_validation_errors(client, test_user, auth_headers):
    """Test field length validation."""
    # Degree too long
    response = client.post(
        '/api/profile/education',
        json={
            'degree': 'X' * 101,
            'institution': 'MIT',
            'start_date': '2015-09-01'
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    assert '100 characters' in response.get_json()['message']
    
    # Institution too long
    response = client.post(
        '/api/profile/education',
        json={
            'degree': 'BS',
            'institution': 'X' * 101,
            'start_date': '2015-09-01'
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    
    # Field of study too long
    response = client.post(
        '/api/profile/education',
        json={
            'degree': 'BS',
            'institution': 'MIT',
            'field_of_study': 'X' * 101,
            'start_date': '2015-09-01'
        },
        headers=auth_headers
    )
    assert response.status_code == 400


def test_add_education_missing_user_id(client):
    """Test adding education without authentication header."""
    response = client.post(
        '/api/profile/education',
        json={'degree': 'BS', 'institution': 'MIT', 'start_date': '2015-09-01'}
    )
    assert response.status_code == 401
    assert response.get_json()['error']['code'] == 'NO_TOKEN'


def test_add_education_missing_body(client, test_user, auth_headers):
    """Test adding education without request body."""
    response = client.post('/api/profile/education', headers=auth_headers)
    assert response.status_code == 400
    assert response.get_json()['error'] == 'MISSING_DATA'


def test_get_education_success(client, test_user, auth_headers):
    """Test getting multiple education entries."""
    # Add first education
    client.post(
        '/api/profile/education',
        json={
            'degree': 'BS',
            'institution': 'MIT',
            'start_date': '2015-09-01',
            'end_date': '2019-05-15'
        },
        headers=auth_headers
    )
    
    # Add second education
    client.post(
        '/api/profile/education',
        json={
            'degree': 'MS',
            'institution': 'Stanford',
            'start_date': '2020-09-01',
            'end_date': '2022-05-15'
        },
        headers=auth_headers
    )
    
    # Get all education
    response = client.get('/api/profile/education', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2


def test_update_education_success(client, test_user, auth_headers):
    """Test updating education entry."""
    # Add education
    response = client.post(
        '/api/profile/education',
        json={
            'degree': 'BS',
            'institution': 'MIT',
            'field_of_study': 'CS',
            'start_date': '2015-09-01',
            'end_date': '2019-05-15'
        },
        headers=auth_headers
    )
    edu_id = response.get_json()['id']
    
    # Update education
    response = client.put(
        f'/api/profile/education/{edu_id}',
        json={
            'degree': 'Bachelor of Science',
            'field_of_study': 'Computer Science',
            'end_date': '2019-06-01'
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['degree'] == 'Bachelor of Science'
    assert data['institution'] == 'MIT'  # Unchanged
    assert data['field_of_study'] == 'Computer Science'
    assert data['end_date'] == '2019-06-01'


def test_update_education_not_found(client, test_user, auth_headers):
    """Test updating non-existent education."""
    response = client.put(
        '/api/profile/education/99999',
        json={'degree': 'MS'},
        headers=auth_headers
    )
    assert response.status_code == 404
    assert response.get_json()['error'] == 'NOT_FOUND'


def test_update_education_validation_errors(client, test_user, auth_headers):
    """Test update validation."""
    # Add education
    response = client.post(
        '/api/profile/education',
        json={
            'degree': 'BS',
            'institution': 'MIT',
            'start_date': '2015-09-01',
            'end_date': '2019-05-15'
        },
        headers=auth_headers
    )
    edu_id = response.get_json()['id']
    
    # Try to set degree to empty
    response = client.put(
        f'/api/profile/education/{edu_id}',
        json={'degree': ''},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'cannot be empty' in response.get_json()['message']
    
    # Try to set end_date before start_date
    response = client.put(
        f'/api/profile/education/{edu_id}',
        json={'end_date': '2014-01-01'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'after start_date' in response.get_json()['message']


def test_update_education_missing_user_id(client, test_user):
    """Test updating education without authentication header."""
    response = client.put('/api/profile/education/1', json={'degree': 'MS'})
    assert response.status_code == 401
    assert response.get_json()['error']['code'] == 'NO_TOKEN'


def test_update_education_missing_body(client, test_user, auth_headers):
    """Test updating education without request body."""
    # Add education first
    response = client.post(
        '/api/profile/education',
        json={'degree': 'BS', 'institution': 'MIT', 'start_date': '2015-09-01'},
        headers=auth_headers
    )
    edu_id = response.get_json()['id']
    
    response = client.put(f'/api/profile/education/{edu_id}', headers=auth_headers)
    assert response.status_code == 400
    assert response.get_json()['error'] == 'MISSING_DATA'


def test_delete_education_success(client, test_user, auth_headers):
    """Test deleting education entry."""
    # Add education
    response = client.post(
        '/api/profile/education',
        json={
            'degree': 'BS',
            'institution': 'MIT',
            'start_date': '2015-09-01'
        },
        headers=auth_headers
    )
    edu_id = response.get_json()['id']
    
    # Delete education
    response = client.delete(f'/api/profile/education/{edu_id}', headers=auth_headers)
    assert response.status_code == 204
    
    # Verify it's deleted
    response = client.get('/api/profile/education', headers=auth_headers)
    data = response.get_json()
    assert len(data) == 0


def test_delete_education_not_found(client, test_user, auth_headers):
    """Test deleting non-existent education."""
    response = client.delete('/api/profile/education/99999', headers=auth_headers)
    assert response.status_code == 404
    assert response.get_json()['error'] == 'NOT_FOUND'


def test_delete_education_missing_user_id(client):
    """Test deleting education without authentication header."""
    response = client.delete('/api/profile/education/1')
    assert response.status_code == 401
    assert response.get_json()['error']['code'] == 'NO_TOKEN'


def test_education_ownership(client, test_user, user_without_profile, app):
    """Test that users can only modify their own education."""
    from src.services.auth_service import AuthService
    with app.app_context():
        auth_service = AuthService()
        user1 = User.query.get(test_user)
        user2 = User.query.get(user_without_profile)
        auth_headers_user1 = {'Authorization': f'Bearer {auth_service.generate_access_token(user1.id, user1.email)}'}
        auth_headers_user2 = {'Authorization': f'Bearer {auth_service.generate_access_token(user2.id, user2.email)}'}
    
    # User 1 adds education
    response = client.post(
        '/api/profile/education',
        json={
            'degree': 'BS',
            'institution': 'MIT',
            'start_date': '2015-09-01'
        },
        headers=auth_headers_user1
    )
    edu_id = response.get_json()['id']
    
    # User 2 tries to update it
    response = client.put(
        f'/api/profile/education/{edu_id}',
        json={'degree': 'Hacked'},
        headers=auth_headers_user2
    )
    assert response.status_code == 404  # Not found (because it doesn't belong to user 2)
    
    # User 2 tries to delete it
    response = client.delete(f'/api/profile/education/{edu_id}', headers=auth_headers_user2)
    assert response.status_code == 404
    
    # Verify it still exists for user 1
    response = client.get('/api/profile/education', headers=auth_headers_user1)
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['degree'] == 'BS'


# ===== Skills Endpoint Tests =====

def test_get_skills_empty(client, test_user, auth_headers):
    """Test getting skills when none exist."""
    response = client.get('/api/profile/skills', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_add_skill_success(client, test_user, auth_headers):
    """Test adding a single skill."""
    skill_data = {
        'name': 'Python',
        'proficiency_level': 'advanced'
    }
    
    response = client.post(
        '/api/profile/skills',
        json=skill_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Python'
    assert data['proficiency_level'] == 'advanced'
    assert 'id' in data


def test_add_skill_default_proficiency(client, test_user, auth_headers):
    """Test adding skill with default proficiency level."""
    skill_data = {'name': 'JavaScript'}
    
    response = client.post(
        '/api/profile/skills',
        json=skill_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'JavaScript'
    assert data['proficiency_level'] == 'intermediate'  # default


def test_add_skill_duplicate(client, test_user, auth_headers):
    """Test adding duplicate skill."""
    skill_data = {'name': 'Python'}
    
    # Add first time
    client.post('/api/profile/skills', json=skill_data, headers=auth_headers)
    
    # Try to add again
    response = client.post('/api/profile/skills', json=skill_data, headers=auth_headers)
    assert response.status_code == 400
    assert 'already exists' in response.get_json()['message']


def test_add_skill_missing_name(client, test_user, auth_headers):
    """Test adding skill without name."""
    response = client.post(
        '/api/profile/skills',
        json={'proficiency_level': 'expert'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'name' in response.get_json()['message']


def test_add_skill_invalid_proficiency(client, test_user, auth_headers):
    """Test adding skill with invalid proficiency level."""
    response = client.post(
        '/api/profile/skills',
        json={'name': 'Python', 'proficiency_level': 'master'},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert 'proficiency_level' in response.get_json()['message']


def test_add_skill_name_too_long(client, test_user, auth_headers):
    """Test adding skill with name exceeding max length."""
    response = client.post(
        '/api/profile/skills',
        json={'name': 'X' * 51},
        headers=auth_headers
    )
    assert response.status_code == 400
    assert '50 characters' in response.get_json()['message']


def test_add_skill_missing_user_id(client):
    """Test adding skill without authentication header."""
    response = client.post('/api/profile/skills', json={'name': 'Python'})
    assert response.status_code == 401
    assert response.get_json()['error']['code'] == 'NO_TOKEN'


def test_add_skill_missing_body(client, test_user, auth_headers):
    """Test adding skill without request body."""
    response = client.post('/api/profile/skills', headers=auth_headers)
    assert response.status_code == 400
    assert response.get_json()['error'] == 'MISSING_DATA'


def test_add_skills_bulk_success(client, test_user, auth_headers):
    """Test adding multiple skills at once."""
    skills_data = {
        'skills': [
            {'name': 'Python', 'proficiency_level': 'advanced'},
            {'name': 'JavaScript', 'proficiency_level': 'intermediate'},
            {'name': 'SQL', 'proficiency_level': 'expert'}
        ]
    }
    
    response = client.post(
        '/api/profile/skills',
        json=skills_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.get_json()
    assert len(data) == 3
    assert data[0]['name'] == 'Python'
    assert data[1]['name'] == 'JavaScript'
    assert data[2]['name'] == 'SQL'


def test_add_skills_bulk_partial_success(client, test_user, auth_headers):
    """Test bulk add with some duplicates (partial success)."""
    # Add one skill first
    client.post(
        '/api/profile/skills',
        json={'name': 'Python'},
        headers=auth_headers
    )
    
    # Try to bulk add including the duplicate
    skills_data = {
        'skills': [
            {'name': 'Python'},  # duplicate
            {'name': 'JavaScript'},  # new
            {'name': 'SQL'}  # new
        ]
    }
    
    response = client.post(
        '/api/profile/skills',
        json=skills_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.get_json()
    # Should only create the 2 new skills
    assert len(data) == 2


def test_get_skills_success(client, test_user, auth_headers):
    """Test getting all skills."""
    # Add skills
    client.post(
        '/api/profile/skills',
        json={'name': 'Python', 'proficiency_level': 'advanced'},
        headers=auth_headers
    )
    client.post(
        '/api/profile/skills',
        json={'name': 'JavaScript', 'proficiency_level': 'intermediate'},
        headers=auth_headers
    )
    
    # Get all skills
    response = client.get('/api/profile/skills', headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    skill_names = [s['name'] for s in data]
    assert 'Python' in skill_names
    assert 'JavaScript' in skill_names


def test_delete_skill_success(client, test_user, auth_headers):
    """Test deleting a skill."""
    # Add skill
    response = client.post(
        '/api/profile/skills',
        json={'name': 'Python'},
        headers=auth_headers
    )
    skill_id = response.get_json()['id']
    
    # Delete skill
    response = client.delete(f'/api/profile/skills/{skill_id}', headers=auth_headers)
    assert response.status_code == 204
    
    # Verify it's deleted
    response = client.get('/api/profile/skills', headers=auth_headers)
    data = response.get_json()
    assert len(data) == 0


def test_delete_skill_not_found(client, test_user, auth_headers):
    """Test deleting non-existent skill."""
    response = client.delete('/api/profile/skills/99999', headers=auth_headers)
    assert response.status_code == 404
    assert response.get_json()['error'] == 'NOT_FOUND'


def test_delete_skill_missing_user_id(client):
    """Test deleting skill without authentication header."""
    response = client.delete('/api/profile/skills/1')
    assert response.status_code == 401
    assert response.get_json()['error']['code'] == 'NO_TOKEN'


def test_delete_skills_bulk_success(client, test_user, auth_headers):
    """Test bulk deleting skills."""
    # Add multiple skills
    response1 = client.post(
        '/api/profile/skills',
        json={'name': 'Python'},
        headers=auth_headers
    )
    skill1_id = response1.get_json()['id']
    
    response2 = client.post(
        '/api/profile/skills',
        json={'name': 'JavaScript'},
        headers=auth_headers
    )
    skill2_id = response2.get_json()['id']
    
    response3 = client.post(
        '/api/profile/skills',
        json={'name': 'SQL'},
        headers=auth_headers
    )
    skill3_id = response3.get_json()['id']
    
    # Bulk delete
    response = client.post(
        '/api/profile/skills/bulk-delete',
        json={'skill_ids': [skill1_id, skill2_id]},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['deleted'] == 2
    assert len(data['failed']) == 0
    
    # Verify only one skill remains
    response = client.get('/api/profile/skills', headers=auth_headers)
    skills = response.get_json()
    assert len(skills) == 1
    assert skills[0]['id'] == skill3_id


def test_delete_skills_bulk_partial(client, test_user, auth_headers):
    """Test bulk delete with some non-existent IDs."""
    # Add one skill
    response = client.post(
        '/api/profile/skills',
        json={'name': 'Python'},
        headers=auth_headers
    )
    skill_id = response.get_json()['id']
    
    # Try to delete existing and non-existent
    response = client.post(
        '/api/profile/skills/bulk-delete',
        json={'skill_ids': [skill_id, 99999, 99998]},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['deleted'] == 1
    assert len(data['failed']) == 2
    assert 99999 in data['failed']
    assert 99998 in data['failed']


def test_delete_skills_bulk_missing_user_id(client):
    """Test bulk delete without authentication header."""
    response = client.post('/api/profile/skills/bulk-delete', json={'skill_ids': [1, 2]})
    assert response.status_code == 401
    assert response.get_json()['error']['code'] == 'NO_TOKEN'


def test_delete_skills_bulk_missing_body(client, test_user, auth_headers):
    """Test bulk delete without request body."""
    response = client.post('/api/profile/skills/bulk-delete', headers=auth_headers)
    assert response.status_code == 400
    assert response.get_json()['error'] == 'MISSING_DATA'


def test_skills_ownership(client, test_user, user_without_profile, app):
    """Test that users can only modify their own skills."""
    from src.services.auth_service import AuthService
    with app.app_context():
        auth_service = AuthService()
        user1 = User.query.get(test_user)
        user2 = User.query.get(user_without_profile)
        auth_headers_user1 = {'Authorization': f'Bearer {auth_service.generate_access_token(user1.id, user1.email)}'}
        auth_headers_user2 = {'Authorization': f'Bearer {auth_service.generate_access_token(user2.id, user2.email)}'}
    
    # User 1 adds skill
    response = client.post(
        '/api/profile/skills',
        json={'name': 'Python'},
        headers=auth_headers_user1
    )
    skill_id = response.get_json()['id']
    
    # User 2 tries to delete it
    response = client.delete(f'/api/profile/skills/{skill_id}', headers=auth_headers_user2)
    assert response.status_code == 404  # Not found (doesn't belong to user 2)
    
    # Verify it still exists for user 1
    response = client.get('/api/profile/skills', headers=auth_headers_user1)
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['name'] == 'Python'
