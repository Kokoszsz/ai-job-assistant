"""
Job Models
==========
Job offers and user's saved/favorite jobs.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import relationship
from src.models.base import db, BaseModel


class JobOffer(BaseModel):
    """
    Available job opportunity from external sources or dummy data.

    Relationships:
    - One-to-Many: FavoriteJob, InterviewPrep
    """

    __tablename__ = "job_offers"

    JOB_TYPES = ["full-time", "part-time", "contract", "remote", "internship"]

    external_id = Column(
        String(100), unique=True, nullable=True
    )  # External API ID (e.g., Remotive job ID)
    title = Column(String(200), nullable=False)
    company = Column(String(100), nullable=False)
    location = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    job_type = Column(String(50), nullable=False, default="full-time")
    posted_date = Column(Date, nullable=False)
    external_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # External sync fields (added for Remotive API integration)
    external_source = Column(String(50), nullable=True)  # e.g., "remotive", "adzuna"
    last_seen_at = Column(DateTime, nullable=True)  # Last time seen in API sync
    tags = Column(JSON, nullable=True)  # Skills/technologies as JSON array
    category = Column(String(100), nullable=True)  # Job category from source
    company_logo_url = Column(String(500), nullable=True)  # Company logo URL

    # Relationships
    favorited_by = relationship(
        "FavoriteJob", back_populates="job_offer", cascade="all, delete-orphan"
    )
    interview_preps = relationship("InterviewPrep", back_populates="job_offer")
    tailored_cvs = relationship(
        "CV", back_populates="job_offer", foreign_keys="CV.job_offer_id"
    )

    # Indexes for search and filtering
    __table_args__ = (
        Index("idx_job_external_id", "external_id"),
        Index("idx_job_location", "location"),
        Index("idx_job_type", "job_type"),
        Index("idx_job_posted", "posted_date", postgresql_using="btree"),
        Index("idx_job_active", "is_active"),
        Index("idx_job_salary", "salary_min", "salary_max"),
        Index("idx_job_company", "company"),
        Index("idx_job_external_source", "external_source"),
        Index("idx_job_last_seen", "last_seen_at"),
        # Full-text search index would be added via raw SQL or migration
    )

    def __repr__(self):
        return (
            f"<JobOffer(id={self.id}, title='{self.title}', company='{self.company}')>"
        )

    def to_dict(self, include_details=True):
        """Convert to dictionary."""
        posted = self.posted_date
        data = {
            "id": self.id,
            "external_id": self.external_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "job_type": self.job_type,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "posted_date": posted.isoformat() if posted else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "external_source": self.external_source,
            "tags": self.tags,
            "category": self.category,
            "company_logo_url": self.company_logo_url,
        }
        if include_details:
            data["description"] = self.description
            data["requirements"] = self.requirements
            data["external_url"] = self.external_url
        return data

    @property
    def salary_range(self):
        """Return formatted salary range string."""
        if self.salary_min and self.salary_max:
            return f"${self.salary_min:,} - ${self.salary_max:,}"
        elif self.salary_min:
            return f"From ${self.salary_min:,}"
        elif self.salary_max:
            return f"Up to ${self.salary_max:,}"
        return "Salary not specified"


class FavoriteJob(BaseModel):
    """
    User's saved/bookmarked jobs.
    Junction table between User and JobOffer.
    """

    __tablename__ = "favorite_jobs"

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_offer_id = Column(
        Integer, ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False
    )
    notes = Column(Text, nullable=True)
    saved_at = Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="favorite_jobs")
    job_offer = relationship("JobOffer", back_populates="favorited_by")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_favorite_user", "user_id"),
        Index("idx_favorite_job", "job_offer_id"),
        UniqueConstraint("user_id", "job_offer_id", name="uq_favorite_user_job"),
    )

    def __repr__(self):
        return f"<FavoriteJob(user_id={self.user_id}, job_id={self.job_offer_id})>"

    def to_dict(self, include_job=False):
        """Convert to dictionary, optionally including job details."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "job_id": self.job_offer_id,  # Frontend expects job_id, not job_offer_id
            "notes": self.notes,
            "saved_at": self.saved_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_job and self.job_offer:
            data["job"] = (
                self.job_offer.to_dict()
            )  # Frontend expects 'job', not 'job_offer'
        return data
