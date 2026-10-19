"""
SQLAlchemy Models for AI Job Search Assistant
=============================================
All database models are exported from this module.
"""

from src.models.base import BaseModel, db
from src.models.conversation import Conversation, Message
from src.models.cv import CV
from src.models.interview import InterviewPrep
from src.models.job import FavoriteJob, JobOffer
from src.models.profile import Certification, Education, Language, Profile, Project, Skill, WorkExperience
from src.models.user import User

__all__ = [
    "db",
    "BaseModel",
    "User",
    "Profile",
    "WorkExperience",
    "Education",
    "Skill",
    "Certification",
    "Project",
    "Language",
    "Conversation",
    "Message",
    "JobOffer",
    "FavoriteJob",
    "CV",
    "InterviewPrep",
]
