"""
Unit Tests for SQLAlchemy Models
================================
Tests model instantiation, relationships, and to_dict methods.
"""

import pytest
from datetime import datetime, date
from src.models import (
    db, User, Profile, WorkExperience, Education, Skill,
    Conversation, Message, JobOffer, FavoriteJob, CV, InterviewPrep
)
from src.utils.password import PasswordValidationError


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self):
        """Test creating a User instance."""
        user = User(
            email='test@example.com',
            password_hash='hashed_password',
            name='Test User'
        )
        assert user.email == 'test@example.com'
        assert user.name == 'Test User'
        assert user.is_active is True  # default

    def test_user_set_password(self):
        """Test User.set_password() method."""
        user = User(
            email='test@example.com',
            password_hash='temp',
            name='Test User'
        )
        
        # Set a valid password
        user.set_password('SecurePass123')
        
        # Password should be hashed (not plaintext)
        assert user.password_hash != 'SecurePass123'
        assert user.password_hash.startswith('$2b$')
        assert len(user.password_hash) == 60

    def test_user_set_weak_password(self):
        """Test that weak passwords are rejected."""
        user = User(
            email='test@example.com',
            password_hash='temp',
            name='Test User'
        )
        
        # Should raise PasswordValidationError
        with pytest.raises(PasswordValidationError):
            user.set_password('weak')

    def test_user_check_password_correct(self):
        """Test User.check_password() with correct password."""
        user = User(
            email='test@example.com',
            password_hash='temp',
            name='Test User'
        )
        
        user.set_password('SecurePass123')
        assert user.check_password('SecurePass123') is True

    def test_user_check_password_incorrect(self):
        """Test User.check_password() with incorrect password."""
        user = User(
            email='test@example.com',
            password_hash='temp',
            name='Test User'
        )
        
        user.set_password('SecurePass123')
        assert user.check_password('WrongPass123') is False

    def test_user_check_password_case_sensitive(self):
        """Test that password checking is case-sensitive."""
        user = User(
            email='test@example.com',
            password_hash='temp',
            name='Test User'
        )
        
        user.set_password('SecurePass123')
        assert user.check_password('securepass123') is False

    def test_user_to_dict(self):
        """Test User.to_dict() method."""
        user = User(
            id=1,
            email='test@example.com',
            password_hash='hashed_password',
            name='Test User',
            is_active=True
        )
        user.created_at = datetime(2025, 1, 1, 12, 0, 0)
        user.updated_at = datetime(2025, 1, 1, 12, 0, 0)
        
        result = user.to_dict()
        
        assert result['id'] == 1
        assert result['email'] == 'test@example.com'
        assert result['name'] == 'Test User'
        assert 'password_hash' not in result  # Should not expose password


class TestProfileModel:
    """Tests for Profile and related models."""

    def test_profile_creation(self):
        """Test creating a Profile instance."""
        profile = Profile(
            user_id=1,
            summary='Experienced developer',
            location='New York',
            preferences_json={'job_types': ['full-time', 'remote']}
        )
        assert profile.summary == 'Experienced developer'
        assert profile.preferences_json['job_types'] == ['full-time', 'remote']

    def test_work_experience_creation(self):
        """Test creating a WorkExperience instance."""
        exp = WorkExperience(
            profile_id=1,
            job_title='Software Engineer',
            company='Tech Corp',
            start_date=date(2020, 1, 1),
            end_date=None  # Current position
        )
        assert exp.job_title == 'Software Engineer'
        assert exp.end_date is None

    def test_education_creation(self):
        """Test creating an Education instance."""
        edu = Education(
            profile_id=1,
            degree='Bachelor of Science',
            institution='State University',
            field_of_study='Computer Science',
            start_date=date(2016, 9, 1),
            end_date=date(2020, 5, 15)
        )
        assert edu.degree == 'Bachelor of Science'

    def test_skill_proficiency_levels(self):
        """Test Skill proficiency level values."""
        skill = Skill(
            profile_id=1,
            name='Python',
            proficiency_level='advanced'
        )
        assert skill.proficiency_level == 'advanced'
        assert 'advanced' in Skill.PROFICIENCY_LEVELS


class TestConversationModel:
    """Tests for Conversation and Message models."""

    def test_conversation_creation(self):
        """Test creating a Conversation instance."""
        conv = Conversation(
            user_id=1,
            title='Job Search Discussion'
        )
        assert conv.title == 'Job Search Discussion'
        assert conv.is_archived is False  # default

    def test_message_creation(self):
        """Test creating a Message instance."""
        msg = Message(
            conversation_id=1,
            role='user',
            content='Hello, I need help finding a job',
            metadata_json={'intent': 'job_search'}
        )
        assert msg.role == 'user'
        assert msg.role in Message.ROLES

    def test_message_roles(self):
        """Test valid message roles."""
        assert 'user' in Message.ROLES
        assert 'assistant' in Message.ROLES


class TestJobModel:
    """Tests for JobOffer and FavoriteJob models."""

    def test_job_offer_creation(self):
        """Test creating a JobOffer instance."""
        job = JobOffer(
            title='Senior Python Developer',
            company='Tech Startup',
            location='Remote',
            description='Great opportunity...',
            job_type='remote',
            salary_min=100000,
            salary_max=150000,
            posted_date=date(2025, 1, 1)
        )
        assert job.title == 'Senior Python Developer'
        assert job.job_type == 'remote'

    def test_job_salary_range(self):
        """Test JobOffer salary_range property."""
        job = JobOffer(
            title='Developer',
            company='Company',
            location='NYC',
            description='...',
            job_type='full-time',
            salary_min=80000,
            salary_max=120000,
            posted_date=date(2025, 1, 1)
        )
        assert '$80,000 - $120,000' in job.salary_range

    def test_job_types(self):
        """Test valid job types."""
        valid_types = JobOffer.JOB_TYPES
        assert 'full-time' in valid_types
        assert 'remote' in valid_types
        assert 'contract' in valid_types

    def test_favorite_job_creation(self):
        """Test creating a FavoriteJob instance."""
        fav = FavoriteJob(
            user_id=1,
            job_offer_id=1,
            notes='Great opportunity, need to follow up'
        )
        assert fav.notes is not None


class TestCVModel:
    """Tests for CV model."""

    def test_cv_creation(self):
        """Test creating a CV instance."""
        cv = CV(
            user_id=1,
            title='Software Engineer CV',
            target_position='Senior Developer',
            content_json={
                'summary': 'Experienced developer...',
                'experience': [],
                'education': [],
                'skills': []
            }
        )
        assert cv.title == 'Software Engineer CV'
        assert 'summary' in cv.content_json

    def test_cv_get_section(self):
        """Test CV.get_section() method."""
        cv = CV(
            user_id=1,
            title='Test CV',
            content_json={
                'summary': 'Test summary',
                'skills': ['Python', 'JavaScript']
            }
        )
        assert cv.get_section('summary') == 'Test summary'
        assert cv.get_section('skills') == ['Python', 'JavaScript']
        assert cv.get_section('nonexistent') is None


class TestInterviewPrepModel:
    """Tests for InterviewPrep model."""

    def test_interview_prep_creation(self):
        """Test creating an InterviewPrep instance."""
        prep = InterviewPrep(
            user_id=1,
            job_offer_id=1,
            questions_json=[
                {'id': 1, 'type': 'behavioral', 'question': 'Tell me about yourself'}
            ]
        )
        assert len(prep.questions_json) == 1

    def test_interview_is_complete(self):
        """Test InterviewPrep.is_complete property."""
        prep = InterviewPrep(
            user_id=1,
            questions_json=[
                {'id': 1, 'question': 'Q1'},
                {'id': 2, 'question': 'Q2'}
            ],
            answers_json={
                '1': 'Answer 1',
                '2': 'Answer 2'
            }
        )
        assert prep.is_complete is True

        # Incomplete case
        prep_incomplete = InterviewPrep(
            user_id=1,
            questions_json=[{'id': 1, 'question': 'Q1'}],
            answers_json={}
        )
        assert prep_incomplete.is_complete is False
