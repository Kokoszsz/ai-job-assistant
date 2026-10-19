"""
CV Model
========
Generated curriculum vitae documents.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from src.models.base import BaseModel, db


class CV(BaseModel):
    """
    Generated CV document for a user.

    The content_json field stores structured CV data:
    {
        "personal": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "location": "San Francisco, CA",
            "linkedin": "linkedin.com/in/johndoe",
            "website": "johndoe.com"
        },
        "summary": "Professional summary...",
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "location": "San Francisco, CA",
                "start_date": "2020-01",
                "end_date": null,
                "current": true,
                "highlights": ["Led team of 5 engineers", "Increased performance by 40%"]
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science",
                "field": "Computer Science",
                "institution": "Stanford University",
                "start_date": "2012-09",
                "end_date": "2016-06",
                "gpa": "3.8"
            }
        ],
        "skills": {
            "technical": ["Python", "React", "PostgreSQL"],
            "soft": ["Leadership", "Communication"]
        },
        "sections": {
            "certifications": [...],
            "projects": [...],
            "languages": [...]
        }
    }
    """

    __tablename__ = "cvs"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    content_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    target_position = Column(String(100), nullable=True)

    # Link to job offer if CV was tailored for a specific job
    job_offer_id = Column(Integer, ForeignKey("job_offers.id", ondelete="SET NULL"), nullable=True)

    # Generation metadata
    is_ai_generated = Column(Boolean, nullable=False, default=False)
    generation_prompt = Column(Text, nullable=True)  # Store the prompt used to generate

    # Relationships
    user = relationship("User", back_populates="cvs")
    job_offer = relationship("JobOffer", back_populates="tailored_cvs")

    # Indexes
    __table_args__ = (
        Index("idx_cv_user", "user_id"),
        Index("idx_cv_created", "created_at", postgresql_using="btree"),
        Index("idx_cv_job_offer", "job_offer_id"),
    )

    def __repr__(self):
        return f"<CV(id={self.id}, user_id={self.user_id}, title='{self.title}')>"

    def to_dict(self, include_content=False, include_job=False):
        """Convert to dictionary, optionally including full content and job details."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "target_position": self.target_position,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        # Handle fields that might not exist in old schema
        try:
            data["job_offer_id"] = self.job_offer_id
        except AttributeError:
            data["job_offer_id"] = None

        try:
            data["is_ai_generated"] = self.is_ai_generated
        except AttributeError:
            data["is_ai_generated"] = False

        if include_content:
            data["content"] = self.content_json or {}

        if include_job:
            try:
                if self.job_offer:
                    data["job_offer"] = {
                        "id": self.job_offer.id,
                        "title": self.job_offer.title,
                        "company": self.job_offer.company,
                    }
            except AttributeError:
                pass

        return data

    @property
    def sections(self):
        """Get custom sections from content."""
        return (self.content_json or {}).get("sections", {})

    def get_section(self, section_name):
        """Get a specific section from the CV content."""
        return (self.content_json or {}).get(section_name)
