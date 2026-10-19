"""
Test Health Check Endpoint
===========================
Tests for the health check API endpoint.
"""

import pytest
from src.app import create_app


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_health_check_success(client):
    """Test health check endpoint returns success."""
    response = client.get('/api/health')
    
    # Should return 200 or 503 depending on services
    assert response.status_code in [200, 503]
    
    # Check JSON structure
    data = response.get_json()
    assert 'status' in data
    assert 'service' in data
    assert 'version' in data
    assert 'timestamp' in data
    assert 'services' in data
    
    # Verify service name and version
    assert data['service'] == 'backend'
    assert data['version'] == '0.1.0'
    
    # Verify services object
    services = data['services']
    assert set(services) == {'database', 'redis'}


def test_health_check_status_values(client):
    """Test health check status is one of expected values."""
    response = client.get('/api/health')
    data = response.get_json()
    
    assert data['status'] in ['healthy', 'degraded', 'unhealthy']


def test_health_check_timestamp_format(client):
    """Test health check timestamp is in ISO format."""
    response = client.get('/api/health')
    data = response.get_json()
    
    # Should end with Z (UTC)
    assert data['timestamp'].endswith('Z')
    
    # Should be parseable as ISO format
    from datetime import datetime
    timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
    assert isinstance(timestamp, datetime)


def test_health_check_has_request_id(client):
    """Test health check response includes X-Request-ID header."""
    response = client.get('/api/health')
    
    # Check for request ID in headers
    assert 'X-Request-ID' in response.headers
    assert response.headers['X-Request-ID'].startswith('req_')


def test_api_root(client):
    """Test API root endpoint."""
    response = client.get('/api/')
    
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'message' in data
    assert 'version' in data
    assert 'status' in data
    assert 'endpoints' in data
    
    # Verify endpoints
    endpoints = data['endpoints']
    assert 'health' in endpoints
    assert 'profile' in endpoints
    assert 'jobs' in endpoints
    assert endpoints['health'] == '/api/health'


def test_health_check_content_type(client):
    """Test health check returns JSON content type."""
    response = client.get('/api/health')
    
    assert response.content_type == 'application/json'


def test_health_check_multiple_calls(client):
    """Test health check can be called multiple times."""
    # Make multiple requests
    for _ in range(5):
        response = client.get('/api/health')
        assert response.status_code in [200, 503]
        data = response.get_json()
        assert 'status' in data


def test_404_error_handler(client):
    """Test 404 error returns consistent JSON format."""
    response = client.get('/api/nonexistent')
    
    assert response.status_code == 404
    
    data = response.get_json()
    assert 'success' in data
    assert data['success'] is False
    assert 'error' in data
    assert data['error']['code'] == 'NOT_FOUND'
    assert data['error']['status_code'] == 404
    assert 'request_id' in data


def test_405_error_handler(client):
    """Test 405 method not allowed returns consistent JSON format."""
    # POST to health endpoint (only GET is allowed)
    response = client.post('/api/health')
    
    assert response.status_code == 405
    
    data = response.get_json()
    assert 'success' in data
    assert data['success'] is False
    assert 'error' in data
    assert data['error']['code'] == 'METHOD_NOT_ALLOWED'
    assert data['error']['status_code'] == 405
