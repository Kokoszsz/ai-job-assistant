"""
Integration tests for JobService.

Tests job search functionality with actual database operations,
including search, filtering, sorting, pagination, and favorites.
"""

from datetime import datetime, timedelta

import pytest

from src.app import create_app
from src.models.base import db
from src.models.job import FavoriteJob, JobOffer
from src.models.user import User
from src.services.job_service import JobService


@pytest.fixture
def app():
    """Create test Flask app with a fresh database."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_jobs(app):
    """Create test job offers."""
    with app.app_context():
        jobs = [
            JobOffer(
                external_id="test-job-1",
                title="Senior Python Developer",
                company="TechCorp",
                location="San Francisco, CA",
                description="Looking for experienced Python developer with Django experience.",
                requirements="5+ years Python, Django, PostgreSQL",
                salary_min=120000,
                salary_max=180000,
                job_type="full-time",
                posted_date=datetime.utcnow() - timedelta(days=1),
                external_url="https://example.com/job1",
                is_active=True,
            ),
            JobOffer(
                external_id="test-job-2",
                title="Junior Python Developer",
                company="StartupXYZ",
                location="Remote",
                description="Entry-level Python developer position for recent graduates.",
                requirements="1-2 years Python, Flask or FastAPI",
                salary_min=70000,
                salary_max=90000,
                job_type="remote",
                posted_date=datetime.utcnow() - timedelta(days=3),
                external_url="https://example.com/job2",
                is_active=True,
            ),
            JobOffer(
                external_id="test-job-3",
                title="Data Scientist",
                company="DataCo",
                location="New York, NY",
                description="Data scientist position focusing on machine learning.",
                requirements="3+ years ML, Python, TensorFlow, Pandas",
                salary_min=100000,
                salary_max=150000,
                job_type="full-time",
                posted_date=datetime.utcnow() - timedelta(days=2),
                external_url="https://example.com/job3",
                is_active=True,
            ),
            JobOffer(
                external_id="test-job-4",
                title="Frontend Developer",
                company="WebDev Inc",
                location="Austin, TX",
                description="React developer for modern web applications.",
                requirements="3+ years React, TypeScript, CSS",
                salary_min=90000,
                salary_max=130000,
                job_type="full-time",
                posted_date=datetime.utcnow() - timedelta(days=5),
                external_url="https://example.com/job4",
                is_active=True,
            ),
            JobOffer(
                external_id="test-job-5",
                title="Part-time Python Tutor",
                company="EduTech",
                location="Remote",
                description="Teach Python to beginners online.",
                requirements="Strong Python knowledge, teaching experience",
                salary_min=30000,
                salary_max=50000,
                job_type="part-time",
                posted_date=datetime.utcnow() - timedelta(days=7),
                external_url="https://example.com/job5",
                is_active=True,
            ),
            JobOffer(
                external_id="test-job-6",
                title="Contract Python Developer",
                company="ConsultCorp",
                location="San Francisco, CA",
                description="6-month contract for Python automation project.",
                requirements="Expert Python, automation, APIs",
                salary_min=None,
                salary_max=None,
                job_type="contract",
                posted_date=datetime.utcnow() - timedelta(days=10),
                external_url="https://example.com/job6",
                is_active=True,
            ),
        ]

        db.session.bulk_save_objects(jobs)
        db.session.commit()

        # Return IDs for reference
        job_ids = [
            job.id
            for job in db.session.query(JobOffer)
            .filter(JobOffer.external_id.in_([f"test-job-{i}" for i in range(1, 7)]))
            .all()
        ]

        yield job_ids

        # Cleanup
        db.session.query(JobOffer).filter(JobOffer.external_id.like("test-job-%")).delete()
        db.session.commit()


@pytest.fixture
def test_user(app):
    """Create test user."""
    with app.app_context():
        user = User(email="testuser@example.com", password_hash="dummy_hash", name="Test User")
        db.session.add(user)
        db.session.commit()

        user_id = user.id

        yield user_id

        # Cleanup
        db.session.query(User).filter_by(id=user_id).delete()
        db.session.commit()


class TestJobServiceSearchIntegration:
    """Integration tests for job search functionality."""

    def test_search_jobs_basic_query(self, app, test_jobs):
        """Should search jobs by keyword."""
        with app.app_context():
            result = JobService.search_jobs(query="Python", page=1, page_size=20)

            assert result["pagination"]["total"] >= 4  # At least 4 Python jobs
            assert len(result["jobs"]) >= 4
            # The query matches title, company, description and requirements
            searchable = ("title", "company", "description", "requirements")
            assert all(
                any("python" in (job.get(field) or "").lower() for field in searchable) for job in result["jobs"]
            )

    def test_search_jobs_location_filter(self, app, test_jobs):
        """Should filter jobs by location."""
        with app.app_context():
            result = JobService.search_jobs(location="San Francisco", page=1, page_size=20)

            assert result["pagination"]["total"] == 2
            assert all("San Francisco" in job["location"] for job in result["jobs"])

    def test_search_jobs_location_partial_match(self, app, test_jobs):
        """Should support partial location matching."""
        with app.app_context():
            result = JobService.search_jobs(location="CA", page=1, page_size=20)

            # Should match "San Francisco, CA"
            assert result["pagination"]["total"] >= 2

    def test_search_jobs_job_types_filter(self, app, test_jobs):
        """Should filter by multiple job types."""
        with app.app_context():
            result = JobService.search_jobs(job_types=["remote", "part-time"], page=1, page_size=20)

            assert result["pagination"]["total"] >= 2
            assert all(job["job_type"] in ["remote", "part-time"] for job in result["jobs"])

    def test_search_jobs_salary_min_filter(self, app, test_jobs):
        """Should filter by minimum salary."""
        with app.app_context():
            result = JobService.search_jobs(salary_min=100000, page=1, page_size=20)

            # Should include jobs where salary_max >= 100000 or is None
            assert result["pagination"]["total"] >= 2
            for job in result["jobs"]:
                if job["salary_max"] is not None:
                    assert job["salary_max"] >= 100000

    def test_search_jobs_salary_max_filter(self, app, test_jobs):
        """Should filter by maximum salary."""
        with app.app_context():
            result = JobService.search_jobs(salary_max=100000, page=1, page_size=20)

            # Should include jobs where salary_min <= 100000 or is None
            assert result["pagination"]["total"] >= 2
            for job in result["jobs"]:
                if job["salary_min"] is not None:
                    assert job["salary_min"] <= 100000

    def test_search_jobs_combined_filters(self, app, test_jobs):
        """Should apply multiple filters together."""
        with app.app_context():
            result = JobService.search_jobs(
                query="Python", location="Remote", job_types=["remote", "part-time"], page=1, page_size=20
            )

            assert result["pagination"]["total"] >= 1
            for job in result["jobs"]:
                assert "python" in job["title"].lower() or "python" in job["description"].lower()
                assert job["location"] == "Remote"
                assert job["job_type"] in ["remote", "part-time"]

    def test_search_jobs_sort_by_date(self, app, test_jobs):
        """Should sort jobs by posted date."""
        with app.app_context():
            result = JobService.search_jobs(sort_by="date", page=1, page_size=10)

            # Most recent first
            dates = [datetime.fromisoformat(job["posted_date"]) for job in result["jobs"]]
            assert dates == sorted(dates, reverse=True)

    def test_search_jobs_sort_by_salary_min(self, app, test_jobs):
        """Should sort jobs by minimum salary descending."""
        with app.app_context():
            result = JobService.search_jobs(sort_by="salary_min", page=1, page_size=10)

            # Higher salaries first, nulls last
            salaries = [job["salary_min"] for job in result["jobs"] if job["salary_min"] is not None]
            assert salaries == sorted(salaries, reverse=True)

            # Nulls should be at the end
            null_count = sum(1 for job in result["jobs"] if job["salary_min"] is None)
            if null_count > 0:
                # Last jobs should have null salaries
                assert result["jobs"][-1]["salary_min"] is None

    def test_search_jobs_sort_by_salary_max(self, app, test_jobs):
        """Should sort jobs by maximum salary descending."""
        with app.app_context():
            result = JobService.search_jobs(sort_by="salary_max", page=1, page_size=10)

            # Higher salaries first, nulls last
            salaries = [job["salary_max"] for job in result["jobs"] if job["salary_max"] is not None]
            assert salaries == sorted(salaries, reverse=True)

    def test_search_jobs_pagination(self, app, test_jobs):
        """Should paginate results correctly."""
        with app.app_context():
            # Get first page
            result_page1 = JobService.search_jobs(page=1, page_size=3)

            assert len(result_page1["jobs"]) == 3
            assert result_page1["pagination"]["page"] == 1
            assert result_page1["pagination"]["has_next"] == True
            assert result_page1["pagination"]["has_prev"] == False

            # Get second page
            result_page2 = JobService.search_jobs(page=2, page_size=3)

            assert len(result_page2["jobs"]) == 3
            assert result_page2["pagination"]["page"] == 2
            assert result_page2["pagination"]["has_prev"] == True

            # Jobs should be different
            page1_ids = {job["id"] for job in result_page1["jobs"]}
            page2_ids = {job["id"] for job in result_page2["jobs"]}
            assert page1_ids.isdisjoint(page2_ids)

    def test_search_jobs_empty_results_includes_suggestions(self, app, test_jobs):
        """Should include suggestions when no results found."""
        with app.app_context():
            result = JobService.search_jobs(query="NonExistentJobTitle12345", page=1, page_size=20)

            assert result["pagination"]["total"] == 0
            assert "suggestions" in result
            assert "message" in result["suggestions"]
            assert len(result["suggestions"]["suggestions"]) > 0

    def test_search_jobs_with_favorites(self, app, test_jobs, test_user):
        """Should include favorite status for authenticated user."""
        with app.app_context():
            # Add job to favorites
            JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[0], notes="Interesting position")

            # Search with user_id
            result = JobService.search_jobs(query="Python", user_id=test_user, page=1, page_size=20)

            # Find the favorited job
            favorited_job = next((job for job in result["jobs"] if job["id"] == test_jobs[0]), None)

            assert favorited_job is not None
            assert favorited_job["is_favorited"] == True

            # Other jobs should not be favorited
            other_jobs = [job for job in result["jobs"] if job["id"] != test_jobs[0]]
            assert all(not job["is_favorited"] for job in other_jobs)

    def test_search_jobs_performance(self, app, test_jobs):
        """Should complete search within acceptable time."""
        import time

        with app.app_context():
            start_time = time.time()

            result = JobService.search_jobs(
                query="Python",
                location="San Francisco",
                job_types=["full-time", "remote"],
                salary_min=80000,
                salary_max=150000,
                sort_by="salary_max",
                page=1,
                page_size=20,
            )

            elapsed_time = time.time() - start_time

            # Should complete in under 200ms (requirement from JOB-001)
            assert elapsed_time < 0.2
            assert result is not None


class TestJobServiceGetJobByIdIntegration:
    """Integration tests for get_job_by_id."""

    def test_get_job_by_id_found(self, app, test_jobs):
        """Should retrieve job by ID."""
        with app.app_context():
            job = JobService.get_job_by_id(test_jobs[0])

            assert job is not None
            assert job["id"] == test_jobs[0]
            assert "title" in job
            assert "company" in job

    def test_get_job_by_id_not_found(self, app, test_jobs):
        """Should return None for non-existent job."""
        with app.app_context():
            job = JobService.get_job_by_id(999999)

            assert job is None

    def test_get_job_by_id_with_favorite_status(self, app, test_jobs, test_user):
        """Should include favorite status when user_id provided."""
        with app.app_context():
            # Add job to favorites
            JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[0])

            # Get job with user_id
            job = JobService.get_job_by_id(test_jobs[0], user_id=test_user)

            assert job is not None
            assert job["is_favorited"] == True

            # Get non-favorited job
            other_job = JobService.get_job_by_id(test_jobs[1], user_id=test_user)
            assert other_job["is_favorited"] == False


class TestJobServiceFavoritesIntegration:
    """Integration tests for favorite job management."""

    def test_add_favorite_job(self, app, test_jobs, test_user):
        """Should add job to favorites."""
        with app.app_context():
            result = JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[0], notes="Great opportunity")

            assert result is not None
            assert result["user_id"] == test_user
            assert result["job_id"] == test_jobs[0]
            assert result["notes"] == "Great opportunity"

    def test_add_favorite_job_duplicate(self, app, test_jobs, test_user):
        """Should not add duplicate favorite."""
        with app.app_context():
            # Add first time
            JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[0])

            # Try to add again
            with pytest.raises(ValueError, match="already in favorites"):
                JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[0])

    def test_remove_favorite_job(self, app, test_jobs, test_user):
        """Should remove job from favorites."""
        with app.app_context():
            # Add favorite
            JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[0])

            # Remove favorite
            result = JobService.remove_favorite_job(user_id=test_user, job_id=test_jobs[0])

            assert result == True

            # Verify removed
            favorites = JobService.get_favorite_jobs(user_id=test_user)["favorites"]
            assert len(favorites) == 0

    def test_update_favorite_notes(self, app, test_jobs, test_user):
        """Should update favorite notes."""
        with app.app_context():
            # Add favorite
            JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[0], notes="Initial notes")

            # Update notes
            result = JobService.update_favorite_notes(user_id=test_user, job_id=test_jobs[0], notes="Updated notes")

            assert result is not None
            assert result["notes"] == "Updated notes"

    def test_get_favorite_jobs(self, app, test_jobs, test_user):
        """Should retrieve all favorite jobs for user."""
        with app.app_context():
            # Add multiple favorites
            JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[0])
            JobService.add_favorite_job(user_id=test_user, job_id=test_jobs[1])

            # Get favorites
            favorites = JobService.get_favorite_jobs(user_id=test_user)["favorites"]

            assert len(favorites) == 2
            favorite_ids = {fav["job_id"] for fav in favorites}
            assert test_jobs[0] in favorite_ids
            assert test_jobs[1] in favorite_ids
