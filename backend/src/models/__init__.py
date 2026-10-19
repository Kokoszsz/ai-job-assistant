"""
SQLAlchemy Models for AI Job Search Assistant
=============================================
All database models are exported from this module.
"""

from src.models.base import db, BaseModel
from src.models.user import User
from src.models.profile import (
    Profile,
    WorkExperience,
    Education,
    Skill,
    Certification,
    Project,
    Language,
)
from src.models.conversation import Conversation, Message
from src.models.job import JobOffer, FavoriteJob
from src.models.cv import CV
from src.models.interview import InterviewPrep

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
