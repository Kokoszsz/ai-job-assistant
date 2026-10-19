"""
Integration tests for Job API endpoints.

Tests job search, job details, and favorites functionality
with authentication and rate limiting.
"""

import pytest
import json
from datetime import datetime, timedelta
from src.models.job import JobOffer, FavoriteJob
from src.models.user import User
from src.models.profile import Profile
from src.models.base import db
from src.app import create_app
from src.services.auth_service import AuthService


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


@pytest.fixture
def test_user(app):
    """Create a test user with profile."""
    with app.app_context():
        user = User(
            email='jobseeker@example.com',
            name='Job Seeker',
            is_active=True
        )
        user.set_password('SecurePass123')
        db.session.add(user)
        db.session.commit()
        
        # Create profile
        profile = Profile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
        
        user_id = user.id
        
        yield user_id
        
        # Cleanup
        db.session.query(Profile).filter_by(user_id=user_id).delete()
        db.session.query(User).filter_by(id=user_id).delete()
        db.session.commit()


@pytest.fixture
def auth_headers(app, test_user):
    """Generate authentication headers for test user."""
    with app.app_context():
        user = db.session.query(User).filter_by(id=test_user).first()
        auth_service = AuthService()
        tokens = auth_service.generate_tokens(user.id, user.email)
        
        return {
            'Authorization': f"Bearer {tokens['access_token']}",
            'Content-Type': 'application/json'
        }


@pytest.fixture
def test_jobs(app):
    """Create test job offers."""
    with app.app_context():
        jobs = [
            JobOffer(
                external_id='api-test-1',
                title='Senior Python Developer',
                company='TechCorp',
                location='San Francisco, CA',
                description='Looking for experienced Python developer',
                requirements='5+ years Python, Django, PostgreSQL',
                salary_min=120000,
                salary_max=180000,
                job_type='full-time',
                posted_date=datetime.utcnow() - timedelta(days=1),
                external_url='https://example.com/job1',
                is_active=True
            ),
            JobOffer(
                external_id='api-test-2',
                title='Remote JavaScript Developer',
                company='StartupXYZ',
                location='Remote',
                description='Full-stack JavaScript developer position',
                requirements='3+ years JavaScript, React, Node.js',
                salary_min=90000,
                salary_max=130000,
                job_type='remote',
                posted_date=datetime.utcnow() - timedelta(days=2),
                external_url='https://example.com/job2',
                is_active=True
            ),
            JobOffer(
                external_id='api-test-3',
                title='Data Scientist',
                company='DataCo',
                location='New York, NY',
                description='Machine learning and data analysis',
                requirements='PhD or Masters in CS, Python, TensorFlow',
                salary_min=100000,
                salary_max=150000,
                job_type='full-time',
                posted_date=datetime.utcnow() - timedelta(days=3),
                external_url='https://example.com/job3',
                is_active=True
            ),
        ]
        
        db.session.bulk_save_objects(jobs)
        db.session.commit()
        
        # Get IDs
        job_ids = [j.id for j in db.session.query(JobOffer).filter(
            JobOffer.external_id.in_(['api-test-1', 'api-test-2', 'api-test-3'])
        ).all()]
        
        yield job_ids
        
        # Cleanup
        db.session.query(JobOffer).filter(
            JobOffer.external_id.like('api-test-%')
        ).delete()
        db.session.commit()


class TestJobSearch:
    """Test job search endpoint."""
    
    def test_search_jobs_requires_auth(self, client):
        """Should require authentication."""
        response = client.get('/api/jobs/search')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error']['code'] == 'NO_TOKEN'
    
    def test_search_jobs_basic(self, client, auth_headers, test_jobs):
        """Should search jobs successfully."""
        response = client.get(
            '/api/jobs/search',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'jobs' in data
        assert 'pagination' in data
        assert 'filters_applied' in data
        assert data['pagination']['total'] >= 3
        assert len(data['jobs']) >= 3
    
    def test_search_jobs_with_keyword(self, client, auth_headers, test_jobs):
        """Should filter by keyword."""
        response = client.get(
            '/api/jobs/search?q=Python',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['pagination']['total'] >= 1
        # Should find Python developer job
        titles = [job['title'] for job in data['jobs']]
        assert any('Python' in title for title in titles)
    
    def test_search_jobs_with_location(self, client, auth_headers, test_jobs):
        """Should filter by location."""
        response = client.get(
            '/api/jobs/search?location=San Francisco',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['pagination']['total'] >= 1
        for job in data['jobs']:
            assert 'San Francisco' in job['location']
    
    def test_search_jobs_with_multiple_job_types(self, client, auth_headers, test_jobs):
        """Should filter by multiple job types."""
        response = client.get(
            '/api/jobs/search?job_type=full-time,remote',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['pagination']['total'] >= 2
        for job in data['jobs']:
            assert job['job_type'] in ['full-time', 'remote']
    
    def test_search_jobs_with_salary_range(self, client, auth_headers, test_jobs):
        """Should filter by salary range."""
        response = client.get(
            '/api/jobs/search?salary_min=100000&salary_max=150000',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['pagination']['total'] >= 1
        for job in data['jobs']:
            if job['salary_max']:
                assert job['salary_max'] >= 100000
            if job['salary_min']:
                assert job['salary_min'] <= 150000
    
    def test_search_jobs_with_sorting(self, client, auth_headers, test_jobs):
        """Should sort jobs by specified field."""
        response = client.get(
            '/api/jobs/search?sort_by=salary_max',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['filters_applied']['sort_by'] == 'salary_max'
        
        # Check that salaries are in descending order (nulls last)
        salaries = [job['salary_max'] for job in data['jobs'] if job['salary_max'] is not None]
        assert salaries == sorted(salaries, reverse=True)
    
    def test_search_jobs_pagination(self, client, auth_headers, test_jobs):
        """Should paginate results."""
        # First page
        response = client.get(
            '/api/jobs/search?page=1&page_size=2',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['pagination']['page'] == 1
        assert data['pagination']['page_size'] == 2
        assert len(data['jobs']) <= 2
        
        # Second page
        response = client.get(
            '/api/jobs/search?page=2&page_size=2',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['pagination']['page'] == 2
    
    def test_search_jobs_invalid_salary_range(self, client, auth_headers):
        """Should reject invalid salary range."""
        response = client.get(
            '/api/jobs/search?salary_min=150000&salary_max=100000',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'salary_min cannot be greater than salary_max' in data['message']
    
    def test_search_jobs_invalid_parameters(self, client, auth_headers):
        """Should reject invalid numeric parameters."""
        response = client.get(
            '/api/jobs/search?page=invalid',
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'VALIDATION_ERROR'
    
    def test_search_jobs_includes_favorite_status(self, client, auth_headers, test_jobs, test_user):
        """Should include favorite status for authenticated user."""
        # Add one job to favorites
        with client.application.app_context():
            favorite = FavoriteJob(
                user_id=test_user,
                job_offer_id=test_jobs[0],
                notes='Interesting'
            )
            db.session.add(favorite)
            db.session.commit()
        
        try:
            response = client.get(
                '/api/jobs/search',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            # Find the favorited job
            favorited_job = next((j for j in data['jobs'] if j['id'] == test_jobs[0]), None)
            assert favorited_job is not None
            assert favorited_job['is_favorited'] == True
            
            # Other jobs should not be favorited
            other_jobs = [j for j in data['jobs'] if j['id'] != test_jobs[0]]
            for job in other_jobs:
                assert job['is_favorited'] == False
        
        finally:
            # Cleanup
            with client.application.app_context():
                db.session.query(FavoriteJob).filter_by(user_id=test_user).delete()
                db.session.commit()
    
    def test_search_jobs_empty_results(self, client, auth_headers):
        """Should handle empty results gracefully."""
        response = client.get(
            '/api/jobs/search?q=NonExistentJobTitle12345',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['pagination']['total'] == 0
        assert len(data['jobs']) == 0
        assert 'suggestions' in data


class TestJobDetails:
    """Test job details endpoint."""
    
    def test_get_job_requires_auth(self, client, test_jobs):
        """Should require authentication."""
        response = client.get(f'/api/jobs/{test_jobs[0]}')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error']['code'] == 'NO_TOKEN'
    
    def test_get_job_success(self, client, auth_headers, test_jobs):
        """Should retrieve job details."""
        response = client.get(
            f'/api/jobs/{test_jobs[0]}',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['id'] == test_jobs[0]
        assert 'title' in data
        assert 'company' in data
        assert 'description' in data
        assert 'requirements' in data
        assert 'is_favorited' in data
    
    def test_get_job_not_found(self, client, auth_headers):
        """Should return 404 for non-existent job."""
        response = client.get(
            '/api/jobs/999999',
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'NOT_FOUND'
    
    def test_get_job_includes_favorite_status(self, client, auth_headers, test_jobs, test_user):
        """Should include favorite status."""
        # Add job to favorites
        with client.application.app_context():
            favorite = FavoriteJob(
                user_id=test_user,
                job_offer_id=test_jobs[0]
            )
            db.session.add(favorite)
            db.session.commit()
        
        try:
            response = client.get(
                f'/api/jobs/{test_jobs[0]}',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['is_favorited'] == True
        
        finally:
            # Cleanup
            with client.application.app_context():
                db.session.query(FavoriteJob).filter_by(user_id=test_user).delete()
                db.session.commit()


class TestFavoriteJobs:
    """Test favorite jobs endpoints."""
    
    def test_get_favorites_requires_auth(self, client):
        """Should require authentication."""
        response = client.get('/api/jobs/favorites')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error']['code'] == 'NO_TOKEN'
    
    def test_get_favorites_empty(self, client, auth_headers):
        """Should return empty list when no favorites."""
        response = client.get(
            '/api/jobs/favorites',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'favorites' in data
        assert len(data['favorites']) == 0
        assert 'pagination' in data
    
    def test_add_favorite_requires_auth(self, client, test_jobs):
        """Should require authentication."""
        response = client.post(f'/api/jobs/{test_jobs[0]}/favorite')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error']['code'] == 'NO_TOKEN'
    
    def test_add_favorite_success(self, client, auth_headers, test_jobs, test_user):
        """Should add job to favorites."""
        response = client.post(
            f'/api/jobs/{test_jobs[0]}/favorite',
            headers=auth_headers,
            data=json.dumps({'notes': 'Great opportunity'}),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user_id'] == test_user
        assert data['job_offer_id'] == test_jobs[0]
        assert data['notes'] == 'Great opportunity'
        
        # Cleanup
        with client.application.app_context():
            db.session.query(FavoriteJob).filter_by(user_id=test_user).delete()
            db.session.commit()
    
    def test_add_favorite_without_notes(self, client, auth_headers, test_jobs, test_user):
        """Should add favorite without notes."""
        response = client.post(
            f'/api/jobs/{test_jobs[0]}/favorite',
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user_id'] == test_user
        assert data['job_offer_id'] == test_jobs[0]
        
        # Cleanup
        with client.application.app_context():
            db.session.query(FavoriteJob).filter_by(user_id=test_user).delete()
            db.session.commit()
    
    def test_add_favorite_duplicate(self, client, auth_headers, test_jobs, test_user):
        """Should reject duplicate favorites."""
        # Add first time
        response = client.post(
            f'/api/jobs/{test_jobs[0]}/favorite',
            headers=auth_headers
        )
        assert response.status_code == 201
        
        try:
            # Try to add again
            response = client.post(
                f'/api/jobs/{test_jobs[0]}/favorite',
                headers=auth_headers
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'already in favorites' in data['message']
        
        finally:
            # Cleanup
            with client.application.app_context():
                db.session.query(FavoriteJob).filter_by(user_id=test_user).delete()
                db.session.commit()
    
    def test_add_favorite_invalid_job(self, client, auth_headers):
        """Should return 404 for invalid job."""
        response = client.post(
            '/api/jobs/999999/favorite',
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'NOT_FOUND'
    
    def test_remove_favorite_success(self, client, auth_headers, test_jobs, test_user):
        """Should remove job from favorites."""
        # Add favorite first
        with client.application.app_context():
            favorite = FavoriteJob(
                user_id=test_user,
                job_offer_id=test_jobs[0]
            )
            db.session.add(favorite)
            db.session.commit()
        
        # Remove it
        response = client.delete(
            f'/api/jobs/{test_jobs[0]}/favorite',
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify removed
        with client.application.app_context():
            favorite = db.session.query(FavoriteJob).filter_by(
                user_id=test_user,
                job_offer_id=test_jobs[0]
            ).first()
            assert favorite is None
    
    def test_remove_favorite_not_found(self, client, auth_headers, test_jobs):
        """Should return 404 if favorite not found."""
        response = client.delete(
            f'/api/jobs/{test_jobs[0]}/favorite',
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'NOT_FOUND'
    
    def test_update_favorite_notes_success(self, client, auth_headers, test_jobs, test_user):
        """Should update favorite notes."""
        # Add favorite first
        with client.application.app_context():
            favorite = FavoriteJob(
                user_id=test_user,
                job_offer_id=test_jobs[0],
                notes='Initial notes'
            )
            db.session.add(favorite)
            db.session.commit()
        
        try:
            # Update notes
            response = client.put(
                f'/api/jobs/{test_jobs[0]}/favorite/notes',
                headers=auth_headers,
                data=json.dumps({'notes': 'Updated notes'}),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['notes'] == 'Updated notes'
        
        finally:
            # Cleanup
            with client.application.app_context():
                db.session.query(FavoriteJob).filter_by(user_id=test_user).delete()
                db.session.commit()
    
    def test_get_favorites_with_jobs(self, client, auth_headers, test_jobs, test_user):
        """Should return list of favorited jobs."""
        # Add multiple favorites
        with client.application.app_context():
            favorites = [
                FavoriteJob(user_id=test_user, job_offer_id=test_jobs[0]),
                FavoriteJob(user_id=test_user, job_offer_id=test_jobs[1])
            ]
            db.session.bulk_save_objects(favorites)
            db.session.commit()
        
        try:
            response = client.get(
                '/api/jobs/favorites',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert 'favorites' in data
            assert len(data['favorites']) == 2
            favorite_job_ids = [fav['job_offer_id'] for fav in data['favorites']]
            assert test_jobs[0] in favorite_job_ids
            assert test_jobs[1] in favorite_job_ids
        
        finally:
            # Cleanup
            with client.application.app_context():
                db.session.query(FavoriteJob).filter_by(user_id=test_user).delete()
                db.session.commit()
