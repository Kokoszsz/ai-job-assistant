"""
Profile Models
==============
User's professional information including work experience, education, and skills.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Date,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from src.models.base import db, BaseModel


class Profile(BaseModel):
    """
    User's professional profile.

    Relationships:
    - One-to-One: User (parent)
    - One-to-Many: WorkExperience, Education, Skill
    """

    __tablename__ = "profiles"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    summary = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    location = Column(String(100), nullable=True)
    preferences_json = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True, default=dict
    )

    # Relationships
    user = relationship("User", back_populates="profile")
    work_experiences = relationship(
        "WorkExperience",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(WorkExperience.start_date)",
    )
    education = relationship(
        "Education",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(Education.start_date)",
    )
    skills = relationship(
        "Skill", back_populates="profile", cascade="all, delete-orphan"
    )
    certifications = relationship(
        "Certification",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(Certification.issue_date)",
    )
    projects = relationship(
        "Project",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(Project.start_date)",
    )
    languages = relationship(
        "Language", back_populates="profile", cascade="all, delete-orphan"
    )
    education = relationship(
        "Education",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="desc(Education.start_date)",
    )
    skills = relationship(
        "Skill", back_populates="profile", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_profile_user", "user_id"),)

    def __repr__(self):
        return f"<Profile(id={self.id}, user_id={self.user_id})>"

    def to_dict(self, include_details=False):
        """Convert to dictionary, optionally including related data."""
        from sqlalchemy import inspect
        from sqlalchemy.exc import ProgrammingError

        data = {
            "id": self.id,
            "user_id": self.user_id,
            "summary": self.summary,
            "phone": self.phone,
            "location": self.location,
            "preferences": self.preferences_json or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_details:
            data["work_experiences"] = [exp.to_dict() for exp in self.work_experiences]
            data["education"] = [edu.to_dict() for edu in self.education]
            data["skills"] = [skill.to_dict() for skill in self.skills]

            # Handle optional tables that may not exist yet (graceful degradation)
            # Check if the relationship is loaded or can be loaded
            try:
                # Attempt to access the relationship
                # If the table doesn't exist, this will raise ProgrammingError
                if hasattr(self, "certifications"):
                    data["certifications"] = [
                        cert.to_dict() for cert in self.certifications
                    ]
                else:
                    data["certifications"] = []
            except (ProgrammingError, Exception) as e:
                # Table doesn't exist or other error
                data["certifications"] = []
                # Rollback the failed query
                db.session.rollback()

            try:
                if hasattr(self, "projects"):
                    data["projects"] = [proj.to_dict() for proj in self.projects]
                else:
                    data["projects"] = []
            except (ProgrammingError, Exception) as e:
                data["projects"] = []
                db.session.rollback()

            try:
                if hasattr(self, "languages"):
                    data["languages"] = [lang.to_dict() for lang in self.languages]
                else:
                    data["languages"] = []
            except (ProgrammingError, Exception) as e:
                data["languages"] = []
                db.session.rollback()

        return data


class WorkExperience(BaseModel):
    """Employment history entry."""

    __tablename__ = "work_experiences"

    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    job_title = Column(String(100), nullable=False)
    company = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # NULL = current position
    description = Column(Text, nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="work_experiences")

    # Indexes
    __table_args__ = (
        Index("idx_experience_profile", "profile_id"),
        Index("idx_experience_dates", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<WorkExperience(id={self.id}, title='{self.job_title}', company='{self.company}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "job_title": self.job_title,
            "company": self.company,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.end_date is None,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }


class Education(BaseModel):
    """Educational background entry."""

    __tablename__ = "education"

    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    degree = Column(String(100), nullable=False)
    institution = Column(String(100), nullable=False)
    field_of_study = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="education")

    # Indexes
    __table_args__ = (Index("idx_education_profile", "profile_id"),)

    def __repr__(self):
        return f"<Education(id={self.id}, degree='{self.degree}', institution='{self.institution}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "degree": self.degree,
            "institution": self.institution,
            "field_of_study": self.field_of_study,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "created_at": self.created_at.isoformat(),
        }


class Skill(BaseModel):
    """User skill with proficiency level."""

    __tablename__ = "skills"

    PROFICIENCY_LEVELS = ["beginner", "intermediate", "advanced", "expert"]

    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(50), nullable=False)
    proficiency_level = Column(String(20), nullable=False, default="intermediate")

    # Relationships
    profile = relationship("Profile", back_populates="skills")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_skill_profile", "profile_id"),
        Index("idx_skill_name", "name"),
        UniqueConstraint("profile_id", "name", name="uq_skill_profile_name"),
    )

    def __repr__(self):
        return f"<Skill(id={self.id}, name='{self.name}', level='{self.proficiency_level}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "name": self.name,
            "proficiency_level": self.proficiency_level,
            "created_at": self.created_at.isoformat(),
        }


class Certification(BaseModel):
    """Professional certification or license."""

    __tablename__ = "certifications"

    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(200), nullable=False)
    issuing_organization = Column(String(200), nullable=False)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)  # NULL = no expiration
    credential_id = Column(String(100), nullable=True)
    credential_url = Column(String(500), nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="certifications")

    # Indexes
    __table_args__ = (Index("idx_certification_profile", "profile_id"),)

    def __repr__(self):
        return f"<Certification(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "name": self.name,
            "issuing_organization": self.issuing_organization,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "credential_id": self.credential_id,
            "credential_url": self.credential_url,
            "is_valid": self.is_valid,
            "created_at": self.created_at.isoformat(),
        }

    @property
    def is_valid(self):
        """Check if certification is still valid (not expired)."""
        if not self.expiry_date:
            return True
        from datetime import date as date_today

        return self.expiry_date >= date_today.today()


class Project(BaseModel):
    """Personal or professional project."""

    __tablename__ = "projects"

    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    technologies = Column(String(500), nullable=True)  # Comma-separated list
    url = Column(String(500), nullable=True)
    repository_url = Column(String(500), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_ongoing = Column(db.Boolean, nullable=False, default=False)

    # Relationships
    profile = relationship("Profile", back_populates="projects")

    # Indexes
    __table_args__ = (Index("idx_project_profile", "profile_id"),)

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "technologies": self.technologies.split(",") if self.technologies else [],
            "url": self.url,
            "repository_url": self.repository_url,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_ongoing": self.is_ongoing,
            "created_at": self.created_at.isoformat(),
        }


class Language(BaseModel):
    """Spoken language with proficiency level."""

    __tablename__ = "languages"

    PROFICIENCY_LEVELS = [
        "elementary",
        "limited_working",
        "professional_working",
        "full_professional",
        "native",
    ]
    PROFICIENCY_LABELS = {
        "elementary": "Elementary",
        "limited_working": "Limited Working",
        "professional_working": "Professional Working",
        "full_professional": "Full Professional",
        "native": "Native / Bilingual",
    }

    profile_id = Column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(
        String(50), nullable=False
    )  # Language name (e.g., "English", "Spanish")
    proficiency_level = Column(
        String(30), nullable=False, default="professional_working"
    )

    # Relationships
    profile = relationship("Profile", back_populates="languages")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_language_profile", "profile_id"),
        UniqueConstraint("profile_id", "name", name="uq_language_profile_name"),
    )

    def __repr__(self):
        return f"<Language(id={self.id}, name='{self.name}', level='{self.proficiency_level}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "name": self.name,
            "proficiency_level": self.proficiency_level,
            "proficiency_label": self.PROFICIENCY_LABELS.get(
                self.proficiency_level, self.proficiency_level
            ),
            "created_at": self.created_at.isoformat(),
        }
