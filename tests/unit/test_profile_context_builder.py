"""
Unit Tests for ProfileContextBuilder
=====================================
Tests profile context formatting logic.
"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from src.services.profile_context_builder import ProfileContextBuilder


class TestCalculateExperienceLevel:
    """Test experience level calculation."""

    def test_entry_level_for_zero_years(self):
        """Should return Entry level for 0 years."""
        experiences = []
        result = ProfileContextBuilder.calculate_experience_level(experiences)
        assert result == "Entry level"

    def test_entry_level_for_one_year(self):
        """Should return Entry level for 1 year."""
        experiences = [
            {
                "start_date": "2023-01-01",
                "end_date": "2024-01-01",
            }
        ]
        result = ProfileContextBuilder.calculate_experience_level(experiences)
        assert result == "Entry level"

    def test_junior_for_three_years(self):
        """Should return Junior for 3 years."""
        experiences = [
            {
                "start_date": "2021-01-01",
                "end_date": "2024-01-01",
            }
        ]
        result = ProfileContextBuilder.calculate_experience_level(experiences)
        assert result == "Junior"

    def test_mid_level_for_six_years(self):
        """Should return Mid-level for 6 years."""
        experiences = [
            {
                "start_date": "2018-01-01",
                "end_date": "2024-01-01",
            }
        ]
        result = ProfileContextBuilder.calculate_experience_level(experiences)
        assert result == "Mid-level"

    def test_senior_for_ten_years(self):
        """Should return Senior for 10 years."""
        experiences = [
            {
                "start_date": "2014-01-01",
                "end_date": "2024-01-01",
            }
        ]
        result = ProfileContextBuilder.calculate_experience_level(experiences)
        assert result == "Senior"

    def test_lead_for_fifteen_years(self):
        """Should return Lead for 15 years."""
        experiences = [
            {
                "start_date": "2009-01-01",
                "end_date": "2024-01-01",
            }
        ]
        result = ProfileContextBuilder.calculate_experience_level(experiences)
        assert result == "Lead"

    def test_current_position_counts_until_today(self):
        """Should count current position (no end_date) until today."""
        experiences = [
            {
                "start_date": "2021-01-01",
                "end_date": None,  # Current position
            }
        ]
        result = ProfileContextBuilder.calculate_experience_level(experiences)
        # Should be at least Junior (2+ years) as of 2024
        assert result in ["Junior", "Mid-level", "Senior", "Lead"]


class TestFormatSkills:
    """Test skill formatting."""

    def test_format_empty_skills(self):
        """Should handle empty skills list."""
        result = ProfileContextBuilder.format_skills([])
        assert "No skills listed" in result

    def test_format_single_skill(self):
        """Should format single skill."""
        skills = [{"name": "Python", "proficiency_level": "expert"}]
        result = ProfileContextBuilder.format_skills(skills)
        assert "Python (Expert)" in result
        assert "1 total" in result

    def test_format_multiple_skills(self):
        """Should format multiple skills."""
        skills = [
            {"name": "Python", "proficiency_level": "expert"},
            {"name": "JavaScript", "proficiency_level": "advanced"},
            {"name": "SQL", "proficiency_level": "intermediate"},
        ]
        result = ProfileContextBuilder.format_skills(skills)
        assert "Python (Expert)" in result
        assert "JavaScript (Advanced)" in result
        assert "SQL (Intermediate)" in result
        assert "3 total" in result

    def test_prioritize_expert_skills(self):
        """Should prioritize expert skills over beginner."""
        skills = [
            {"name": "Beginner1", "proficiency_level": "beginner"},
            {"name": "Expert1", "proficiency_level": "expert"},
            {"name": "Intermediate1", "proficiency_level": "intermediate"},
            {"name": "Advanced1", "proficiency_level": "advanced"},
        ]
        result = ProfileContextBuilder.format_skills(skills, max_skills=2)
        # Expert and Advanced should appear first
        assert "Expert1" in result
        assert "Advanced1" in result

    def test_limit_max_skills(self):
        """Should limit to max_skills parameter."""
        skills = [{"name": f"Skill{i}", "proficiency_level": "intermediate"} for i in range(20)]
        result = ProfileContextBuilder.format_skills(skills, max_skills=5)
        # Should show total count but limit displayed skills
        assert "20 total" in result
        lines = result.split("\n")
        # Header + 5 skills
        assert len(lines) == 6


class TestFormatEducation:
    """Test education formatting."""

    def test_format_empty_education(self):
        """Should handle empty education list."""
        result = ProfileContextBuilder.format_education([])
        assert "Not specified" in result

    def test_format_single_education(self):
        """Should format single education entry."""
        education = [
            {
                "degree": "BS",
                "field_of_study": "Computer Science",
                "institution": "Stanford University",
                "end_date": "2020-05-15",
            }
        ]
        result = ProfileContextBuilder.format_education(education)
        assert "BS Computer Science" in result
        assert "Stanford University" in result
        assert "2020" in result

    def test_format_education_without_field(self):
        """Should format education without field of study."""
        education = [
            {
                "degree": "MBA",
                "institution": "Harvard Business School",
                "end_date": "2018-06-01",
            }
        ]
        result = ProfileContextBuilder.format_education(education)
        assert "MBA" in result
        assert "Harvard Business School" in result

    def test_format_multiple_education(self):
        """Should format multiple education entries."""
        education = [
            {
                "degree": "PhD",
                "field_of_study": "Physics",
                "institution": "MIT",
                "end_date": "2022-01-01",
            },
            {
                "degree": "MS",
                "field_of_study": "Physics",
                "institution": "Caltech",
                "end_date": "2018-01-01",
            },
        ]
        result = ProfileContextBuilder.format_education(education)
        assert "PhD Physics" in result
        assert "MS Physics" in result


class TestBuildUserContext:
    """Test complete user context building."""

    @patch("src.models.user.User")
    @patch("src.models.base.db")
    def test_build_complete_context(self, mock_db, mock_user_class):
        """Should build complete context with all profile data."""
        # Mock user
        mock_user = Mock()
        mock_user.name = "John Doe"
        mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user

        profile_data = {
            "location": "San Francisco, CA",
            "work_experiences": [
                {
                    "job_title": "Senior Engineer",
                    "company": "TechCorp",
                    "start_date": "2020-01-01",
                    "end_date": None,
                    "is_current": True,
                }
            ],
            "skills": [
                {"name": "Python", "proficiency_level": "expert"},
                {"name": "React", "proficiency_level": "advanced"},
            ],
            "education": [
                {
                    "degree": "BS",
                    "field_of_study": "Computer Science",
                    "institution": "Stanford",
                    "end_date": "2018-05-01",
                }
            ],
            "preferences": {
                "desired_roles": ["Backend Engineer", "Full Stack Developer"],
                "locations": ["San Francisco", "Remote"],
                "job_types": ["full-time", "remote"],
                "min_salary": 120000,
                "max_salary": 180000,
            },
        }

        result = ProfileContextBuilder.build_user_context(1, profile_data)

        # Verify key components
        assert "=== USER PROFILE ===" in result
        assert "John Doe" in result
        assert "San Francisco, CA" in result
        assert "Senior Engineer at TechCorp" in result
        assert "Python (Expert)" in result
        assert "React (Advanced)" in result
        assert "BS Computer Science" in result
        assert "Backend Engineer" in result
        assert "$120,000 - $180,000" in result

    @patch("src.models.user.User")
    @patch("src.models.base.db")
    def test_build_context_with_partial_profile(self, mock_db, mock_user_class):
        """Should handle partial profile data gracefully."""
        mock_user = Mock()
        mock_user.name = "Jane Smith"
        mock_db.session.query.return_value.filter_by.return_value.first.return_value = mock_user

        profile_data = {
            "location": None,  # Missing
            "work_experiences": [],  # Empty
            "skills": [{"name": "Java", "proficiency_level": "intermediate"}],
            "education": [],  # Empty
            "preferences": {},  # Empty
        }

        result = ProfileContextBuilder.build_user_context(2, profile_data)

        assert "Jane Smith" in result
        assert "Not specified" in result  # For location
        assert "Java (Intermediate)" in result

    def test_build_context_with_no_profile(self):
        """Should return empty string for no profile."""
        result = ProfileContextBuilder.build_user_context(3, None)
        assert result == ""

    @patch("src.models.user.User")
    @patch("src.models.base.db")
    def test_build_context_handles_errors_gracefully(self, mock_db, mock_user_class):
        """Should handle errors and return empty string."""
        mock_db.session.query.side_effect = Exception("Database error")

        profile_data = {"location": "NYC"}

        result = ProfileContextBuilder.build_user_context(4, profile_data)
        assert result == ""


class TestHelperMethods:
    """Test helper methods."""

    def test_calculate_total_years_single_job(self):
        """Should calculate years for single job."""
        experiences = [{"start_date": "2020-01-01", "end_date": "2023-01-01"}]
        years = ProfileContextBuilder._calculate_total_years(experiences)
        assert years == 3

    def test_calculate_total_years_multiple_jobs(self):
        """Should sum years across multiple jobs."""
        experiences = [
            {"start_date": "2018-01-01", "end_date": "2020-01-01"},  # 2 years
            {"start_date": "2020-06-01", "end_date": "2023-06-01"},  # 3 years
        ]
        years = ProfileContextBuilder._calculate_total_years(experiences)
        assert years == 5

    def test_get_current_role_with_current_position(self):
        """Should return current role."""
        experiences = [
            {
                "job_title": "Senior Dev",
                "company": "Acme Inc",
                "is_current": True,
            }
        ]
        role = ProfileContextBuilder._get_current_role(experiences)
        assert "Senior Dev at Acme Inc (Current)" in role

    def test_get_current_role_with_past_position(self):
        """Should return most recent past role."""
        experiences = [
            {
                "job_title": "Junior Dev",
                "company": "Old Corp",
                "is_current": False,
            }
        ]
        role = ProfileContextBuilder._get_current_role(experiences)
        assert "Junior Dev at Old Corp" in role
        assert "(Current)" not in role

    def test_format_preferences_with_all_fields(self):
        """Should format all preference fields."""
        preferences = {
            "desired_roles": ["Engineer", "Architect"],
            "locations": ["NYC", "SF"],
            "job_types": ["full-time", "remote"],
            "min_salary": 100000,
            "max_salary": 150000,
            "experience_level": "senior",
        }
        lines = ProfileContextBuilder._format_preferences(preferences)
        result = "\n".join(lines)

        assert "Engineer, Architect" in result
        assert "NYC, SF" in result
        assert "Full-time, Remote" in result
        assert "$100,000 - $150,000" in result
        assert "Senior" in result

    def test_format_preferences_with_missing_fields(self):
        """Should show 'Not specified' for missing fields."""
        preferences = {}
        lines = ProfileContextBuilder._format_preferences(preferences)
        result = "\n".join(lines)

        assert "Not specified" in result
