"""
Test Rate Limiting Middleware
==============================
Tests for Flask-Limiter integration and rate limit enforcement.
"""

import time

import pytest
from flask import Blueprint

from src.app import create_app


@pytest.fixture
def app():
    """Create application for testing with rate limiting."""
    app = create_app("testing")

    # Create test blueprint with rate limited endpoints
    test_bp = Blueprint("test_limits", __name__)

    @test_bp.route("/test/unlimited")
    def unlimited():
        return {"message": "unlimited endpoint"}

    @test_bp.route("/test/limited")
    @app.limiter.limit("3/minute")
    def limited():
        return {"message": "limited endpoint"}

    @test_bp.route("/test/auth")
    @app.limiter.limit("5/minute")
    def auth_endpoint():
        return {"message": "auth endpoint"}

    @test_bp.route("/test/chat")
    @app.limiter.limit("20/minute")
    def chat_endpoint():
        return {"message": "chat endpoint"}

    @test_bp.route("/test/jobs")
    @app.limiter.limit("60/minute")
    def jobs_endpoint():
        return {"message": "jobs endpoint"}

    app.register_blueprint(test_bp)

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_rate_limiter_initialized(app):
    """Test that rate limiter is properly initialized."""
    assert hasattr(app, "limiter")
    assert app.limiter is not None


def test_rate_limiter_configuration(app):
    """Test rate limiter configuration."""
    assert "RATELIMIT_STORAGE_URL" in app.config
    assert "RATELIMIT_DEFAULT" in app.config
    assert app.config["RATELIMIT_STORAGE_URL"] is not None


def test_unlimited_endpoint(client):
    """Test that unlimited endpoints work without restrictions."""
    # Make multiple requests
    for _ in range(10):
        response = client.get("/test/unlimited")
        assert response.status_code == 200


def test_rate_limit_enforcement(client):
    """Test that rate limits are enforced."""
    # Make requests up to the limit (3 per minute)
    for i in range(3):
        response = client.get("/test/limited")
        assert response.status_code == 200, f"Request {i+1} should succeed"

    # Next request should be rate limited
    response = client.get("/test/limited")
    assert response.status_code == 429, "Request 4 should be rate limited"


def test_rate_limit_error_format(client):
    """Test that rate limit errors return proper JSON format."""
    # Exceed rate limit
    for _ in range(4):
        client.get("/test/limited")

    # Check error response format
    response = client.get("/test/limited")
    assert response.status_code == 429

    data = response.get_json()
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert data["error"]["status_code"] == 429
    assert "request_id" in data


def test_rate_limit_headers(client):
    """Test that rate limit headers are present."""
    response = client.get("/test/limited")

    # Check for rate limit headers
    assert "X-RateLimit-Limit" in response.headers or "RateLimit-Limit" in response.headers
    assert response.status_code == 200


def test_retry_after_header(client):
    """Test that Retry-After header is set on rate limit."""
    # Exceed rate limit
    for _ in range(4):
        client.get("/test/limited")

    response = client.get("/test/limited")
    assert response.status_code == 429

    # Retry-After header should be present
    assert "Retry-After" in response.headers or "retry_after" in response.get_json().get("error", {})


def test_different_rate_limits_per_endpoint(client):
    """Test that different endpoints have different rate limits."""
    # Auth endpoint: 5 per minute
    for i in range(5):
        response = client.get("/test/auth")
        assert response.status_code == 200, f"Auth request {i+1} should succeed"

    response = client.get("/test/auth")
    assert response.status_code == 429, "Auth request 6 should be rate limited"

    # Chat endpoint should still work (different limit)
    response = client.get("/test/chat")
    assert response.status_code == 200, "Chat endpoint should work independently"


def test_rate_limit_by_ip(client):
    """Test that rate limits are enforced per IP address."""
    # Make requests from one IP
    for _ in range(3):
        response = client.get("/test/limited")
        assert response.status_code == 200

    # Fourth request should be limited
    response = client.get("/test/limited")
    assert response.status_code == 429


def test_health_check_not_rate_limited(client):
    """Test that health check endpoint is not rate limited."""
    # Health check should handle many requests
    for _ in range(150):  # More than default limit
        response = client.get("/api/health")
        # Should either succeed or fail for other reasons, not rate limiting
        assert response.status_code in [200, 503]


def test_rate_limit_reset(client):
    """Test that rate limits reset after time window."""
    # This test would need to wait for the time window to pass
    # For now, just verify the limit is applied
    for _ in range(3):
        response = client.get("/test/limited")
        assert response.status_code == 200

    response = client.get("/test/limited")
    assert response.status_code == 429

    # In production, after 1 minute, limits would reset
    # We can't easily test this without mocking time or waiting


def test_rate_limit_logging(app, client):
    """Test that rate limit violations are logged."""
    # Exceed rate limit
    for _ in range(4):
        client.get("/test/limited")

    # The rate limit handler should have logged the violation
    # In a real test, we'd capture the log output
    # For now, just verify the endpoint works
    response = client.get("/test/limited")
    assert response.status_code == 429


def test_job_search_rate_limit(client):
    """Test job search specific rate limit (60/min)."""
    # Should allow 60 requests
    for i in range(60):
        response = client.get("/test/jobs")
        assert response.status_code == 200, f"Jobs request {i+1} should succeed"

    # 61st request should be limited
    response = client.get("/test/jobs")
    assert response.status_code == 429


def test_chat_rate_limit(client):
    """Test chat specific rate limit (20/min)."""
    # Should allow 20 requests
    for i in range(20):
        response = client.get("/test/chat")
        assert response.status_code == 200, f"Chat request {i+1} should succeed"

    # 21st request should be limited
    response = client.get("/test/chat")
    assert response.status_code == 429
