"""
Unit tests for JobService.

Tests job search business logic, validation, filtering, sorting,
and favorite management functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.models.job import FavoriteJob, JobOffer
from src.services.job_service import JobService


class TestJobServiceValidation:
    """Test validation of search parameters."""

    def test_validate_search_params_valid(self):
        """Should accept valid parameters."""
        # Should not raise any exception
        JobService._validate_search_params(page=1, page_size=20, sort_by="relevance", job_types=["full-time", "remote"])

    def test_validate_search_params_invalid_page(self):
        """Should reject page < 1."""
        with pytest.raises(ValueError, match="Page must be >= 1"):
            JobService._validate_search_params(page=0, page_size=20, sort_by="relevance", job_types=None)

    def test_validate_search_params_invalid_page_size_too_small(self):
        """Should reject page_size < 1."""
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            JobService._validate_search_params(page=1, page_size=0, sort_by="relevance", job_types=None)

    def test_validate_search_params_invalid_page_size_too_large(self):
        """Should reject page_size > 100."""
        with pytest.raises(ValueError, match="Page size must be between 1 and 100"):
            JobService._validate_search_params(page=1, page_size=101, sort_by="relevance", job_types=None)

    def test_validate_search_params_invalid_sort_by(self):
        """Should reject invalid sort_by value."""
        with pytest.raises(ValueError, match="Invalid sort_by"):
            JobService._validate_search_params(page=1, page_size=20, sort_by="popularity", job_types=None)  # Invalid

    def test_validate_search_params_invalid_job_types(self):
        """Should reject invalid job types."""
        with pytest.raises(ValueError, match="Invalid job types"):
            JobService._validate_search_params(
                page=1, page_size=20, sort_by="relevance", job_types=["full-time", "invalid-type"]
            )


class TestJobServiceSorting:
    """Test sorting logic."""

    def test_apply_sorting_relevance(self):
        """Should sort by date for relevance."""
        mock_query = Mock()
        mock_query.order_by = Mock(return_value=mock_query)

        # Call with actual query (sorting is applied to query, not to JobOffer model)
        result = JobService._apply_sorting(mock_query, "relevance", "python developer")

        # Should have called order_by on the query
        assert mock_query.order_by.called
        assert result == mock_query

    def test_apply_sorting_date(self):
        """Should sort by posted date."""
        mock_query = Mock()
        mock_query.order_by = Mock(return_value=mock_query)

        result = JobService._apply_sorting(mock_query, "date", None)

        assert mock_query.order_by.called
        assert result == mock_query

    def test_apply_sorting_salary_min(self):
        """Should sort by minimum salary descending with nulls last."""
        mock_query = Mock()
        mock_query.order_by = Mock(return_value=mock_query)

        result = JobService._apply_sorting(mock_query, "salary_min", None)

        assert mock_query.order_by.called
        assert result == mock_query

    def test_apply_sorting_salary_max(self):
        """Should sort by maximum salary descending with nulls last."""
        mock_query = Mock()
        mock_query.order_by = Mock(return_value=mock_query)

        result = JobService._apply_sorting(mock_query, "salary_max", None)

        assert mock_query.order_by.called
        assert result == mock_query


class TestJobServiceSearchSuggestions:
    """Test search suggestions for empty results."""

    @patch("src.services.job_service.db.session")
    def test_get_search_suggestions_with_location(self, mock_session):
        """Should suggest removing location filter."""
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = JobService.get_search_suggestions(query="python developer", location="New York")

        assert "message" in result
        assert "suggestions" in result
        assert "Try searching without location filter" in result["suggestions"]

    @patch("src.services.job_service.db.session")
    def test_get_search_suggestions_with_query(self, mock_session):
        """Should suggest broadening search query."""
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = JobService.get_search_suggestions(query="very specific rare job title", location=None)

        assert "Try using broader keywords" in result["suggestions"]
        assert "Check spelling of search terms" in result["suggestions"]

    @patch("src.services.job_service.db.session")
    def test_get_search_suggestions_with_popular_jobs(self, mock_session):
        """Should include popular job titles."""
        mock_job1 = Mock(title="Software Engineer")
        mock_job2 = Mock(title="Data Scientist")

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_job1, mock_job2]

        result = JobService.get_search_suggestions(query="test", location=None)

        assert "popular_searches" in result
        assert "Software Engineer" in result["popular_searches"]
        assert "Data Scientist" in result["popular_searches"]

    @patch("src.services.job_service.db.session")
    def test_get_search_suggestions_handles_database_error(self, mock_session):
        """Should return basic suggestions if database query fails."""
        mock_session.query.side_effect = SQLAlchemyError("Database error")

        result = JobService.get_search_suggestions(query="test", location=None)

        assert "message" in result
        assert "suggestions" in result
        assert len(result["suggestions"]) > 0


class TestJobServiceSearch:
    """Test search_jobs method."""

    @patch("src.services.job_service.db.session")
    @patch("src.services.job_service.JobService._validate_search_params")
    @patch("src.services.job_service.JobService._apply_sorting")
    def test_search_jobs_basic_query(self, mock_sort, mock_validate, mock_session):
        """Should perform basic search with query."""
        # Setup mocks
        mock_validate.return_value = None
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_sort.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        result = JobService.search_jobs(query="python developer", page=1, page_size=20)

        # Verify validation was called
        mock_validate.assert_called_once()

        # Verify result structure
        assert "jobs" in result
        assert "pagination" in result
        assert "filters_applied" in result
        assert result["pagination"]["total"] == 0

    @patch("src.services.job_service.db.session")
    @patch("src.services.job_service.JobService._validate_search_params")
    @patch("src.services.job_service.JobService._apply_sorting")
    @patch("src.services.job_service.JobService.get_search_suggestions")
    def test_search_jobs_no_results_includes_suggestions(
        self, mock_suggestions, mock_sort, mock_validate, mock_session
    ):
        """Should include suggestions when no results found."""
        # Setup mocks
        mock_validate.return_value = None
        mock_suggestions.return_value = {"message": "No jobs found", "suggestions": ["Try broader keywords"]}
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_sort.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        result = JobService.search_jobs(query="very rare job title", page=1, page_size=20)

        assert "suggestions" in result
        assert result["suggestions"]["message"] == "No jobs found"

    @patch("src.services.job_service.db.session")
    @patch("src.services.job_service.JobService._validate_search_params")
    @patch("src.services.job_service.JobService._apply_sorting")
    def test_search_jobs_with_location_filter(self, mock_sort, mock_validate, mock_session):
        """Should filter by location."""
        mock_validate.return_value = None
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_sort.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        result = JobService.search_jobs(query=None, location="San Francisco", page=1, page_size=20)

        # Verify filter was applied
        mock_query.filter.assert_called()
        assert result["filters_applied"]["location"] == "San Francisco"

    @patch("src.services.job_service.db.session")
    @patch("src.services.job_service.JobService._validate_search_params")
    @patch("src.services.job_service.JobService._apply_sorting")
    def test_search_jobs_with_job_types_filter(self, mock_sort, mock_validate, mock_session):
        """Should filter by multiple job types."""
        mock_validate.return_value = None
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_sort.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        result = JobService.search_jobs(query=None, job_types=["full-time", "remote"], page=1, page_size=20)

        assert result["filters_applied"]["job_types"] == ["full-time", "remote"]

    @patch("src.services.job_service.db.session")
    @patch("src.services.job_service.JobService._validate_search_params")
    @patch("src.services.job_service.JobService._apply_sorting")
    def test_search_jobs_with_salary_range(self, mock_sort, mock_validate, mock_session):
        """Should filter by salary range."""
        mock_validate.return_value = None
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_sort.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        result = JobService.search_jobs(query=None, salary_min=80000, salary_max=120000, page=1, page_size=20)

        assert result["filters_applied"]["salary_min"] == 80000
        assert result["filters_applied"]["salary_max"] == 120000

    @patch("src.services.job_service.db.session")
    @patch("src.services.job_service.JobService._validate_search_params")
    @patch("src.services.job_service.JobService._apply_sorting")
    def test_search_jobs_with_user_favorites(self, mock_sort, mock_validate, mock_session):
        """Should include favorite status for authenticated user."""
        mock_validate.return_value = None

        # Mock job result
        mock_job = Mock()
        mock_job.id = 1
        mock_job.to_dict.return_value = {"id": 1, "title": "Software Engineer"}

        # Mock favorite
        mock_favorite = Mock()
        mock_favorite.job_offer_id = 1

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_sort.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query

        # First all() returns jobs, second all() returns favorites
        mock_query.all.side_effect = [[mock_job], [mock_favorite]]

        result = JobService.search_jobs(query=None, user_id=123, page=1, page_size=20)

        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["is_favorited"] == True

    def test_search_jobs_raises_value_error_on_validation_failure(self):
        """Should propagate ValueError from validation."""
        with pytest.raises(ValueError, match="Page must be >= 1"):
            JobService.search_jobs(query=None, page=0, page_size=20)  # Invalid

    @patch("src.services.job_service.db.session")
    @patch("src.services.job_service.JobService._validate_search_params")
    def test_search_jobs_raises_sqlalchemy_error(self, mock_validate, mock_session):
        """Should propagate SQLAlchemy errors."""
        mock_validate.return_value = None
        mock_session.query.side_effect = SQLAlchemyError("Database connection failed")

        with pytest.raises(SQLAlchemyError):
            JobService.search_jobs(query=None, page=1, page_size=20)


class TestJobServiceGetJobById:
    """Test get_job_by_id method."""

    @patch("src.services.job_service.db.session")
    def test_get_job_by_id_found(self, mock_session):
        """Should return job when found."""
        mock_job = Mock()
        mock_job.id = 1
        mock_job.to_dict.return_value = {"id": 1, "title": "Software Engineer"}

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = mock_job

        result = JobService.get_job_by_id(1)

        assert result is not None
        assert result["id"] == 1

    @patch("src.services.job_service.db.session")
    def test_get_job_by_id_not_found(self, mock_session):
        """Should return None when job not found."""
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = None

        result = JobService.get_job_by_id(999)

        assert result is None

    @patch("src.services.job_service.db.session")
    def test_get_job_by_id_with_user_favorite_status(self, mock_session):
        """Should include favorite status for authenticated user."""
        mock_job = Mock()
        mock_job.id = 1
        mock_job.to_dict.return_value = {"id": 1, "title": "Software Engineer"}

        mock_favorite = Mock()
        mock_favorite.job_offer_id = 1

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query

        # First first() returns job, second first() returns favorite
        mock_query.first.side_effect = [mock_job, mock_favorite]

        result = JobService.get_job_by_id(1, user_id=123)

        assert result is not None
        assert result["is_favorited"] == True

    @patch("src.services.job_service.db.session")
    def test_get_job_by_id_handles_database_error(self, mock_session):
        """Should propagate SQLAlchemy errors."""
        mock_session.query.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            JobService.get_job_by_id(1)


class TestJobServiceFavorites:
    """Test favorite job management methods."""

    @patch("src.services.job_service.db.session")
    def test_add_favorite_job_success(self, mock_session):
        """Should add job to favorites successfully."""
        # Mock user query
        mock_user = Mock()
        mock_user.id = 123

        # Mock job query
        mock_job = Mock()
        mock_job.id = 1
        mock_job.to_dict.return_value = {"id": 1, "title": "Software Engineer"}

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query

        # First first() returns user, second returns job
        mock_query.first.side_effect = [mock_user, mock_job]

        mock_favorite = Mock()
        mock_favorite.saved_at = datetime.utcnow()
        mock_favorite.to_dict.return_value = {
            "id": 1,
            "user_id": 123,
            "job_offer_id": 1,
            "notes": "Interesting position",
            "saved_at": datetime.utcnow().isoformat(),
        }

        with patch("src.services.job_service.FavoriteJob", return_value=mock_favorite):
            result = JobService.add_favorite_job(user_id=123, job_id=1, notes="Interesting position")

        assert result is not None
        assert result["job_offer_id"] == 1
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch("src.services.job_service.db.session")
    def test_add_favorite_job_already_exists(self, mock_session):
        """Should raise ValueError if job already favorited."""
        # Mock user query
        mock_user = Mock()

        # Mock job query
        mock_job = Mock()

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query

        # Return user and job
        mock_query.first.side_effect = [mock_user, mock_job]

        # Mock IntegrityError for duplicate
        from sqlalchemy.exc import IntegrityError

        mock_session.add.side_effect = IntegrityError("", "", "uq_favorite_user_job")

        with pytest.raises(ValueError, match="Job already in favorites"):
            JobService.add_favorite_job(user_id=123, job_id=1)

    @patch("src.services.job_service.db.session")
    def test_remove_favorite_job_success(self, mock_session):
        """Should remove job from favorites successfully."""
        mock_favorite = Mock()

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = mock_favorite

        result = JobService.remove_favorite_job(user_id=123, job_id=1)

        assert result == True
        mock_session.delete.assert_called_once_with(mock_favorite)
        mock_session.commit.assert_called_once()

    @patch("src.services.job_service.db.session")
    def test_remove_favorite_job_not_found(self, mock_session):
        """Should return False if favorite not found."""
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = None

        result = JobService.remove_favorite_job(user_id=123, job_id=1)

        assert result == False
        mock_session.delete.assert_not_called()

    @patch("src.services.job_service.db.session")
    def test_update_favorite_notes_success(self, mock_session):
        """Should update favorite notes successfully."""
        mock_favorite = Mock()
        mock_favorite.notes = "Old notes"
        mock_favorite.to_dict.return_value = {"id": 1, "notes": "Updated notes"}

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = mock_favorite

        result = JobService.update_favorite_notes(user_id=123, job_id=1, notes="Updated notes")

        assert result is not None
        assert mock_favorite.notes == "Updated notes"
        mock_session.commit.assert_called_once()

    @patch("src.services.job_service.db.session")
    def test_update_favorite_notes_not_found(self, mock_session):
        """Should return None if favorite not found."""
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.first.return_value = None

        result = JobService.update_favorite_notes(user_id=123, job_id=1, notes="Updated notes")

        assert result is None
        mock_session.commit.assert_not_called()
