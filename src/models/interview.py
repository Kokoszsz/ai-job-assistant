"""
Interview Prep Model
====================
Interview preparation sessions with generated questions and feedback.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from src.models.base import db, BaseModel


class InterviewPrep(BaseModel):
    """
    Interview preparation session for a user.
    
    JSON structures:
    
    questions_json:
    [
        {
            "id": 1,
            "type": "behavioral",
            "question": "Tell me about a time...",
            "tips": "Use STAR method..."
        },
        ...
    ]
    
    answers_json:
    {
        "1": "My answer to question 1...",
        "2": "My answer to question 2...",
        ...
    }
    
    feedback_json:
    {
        "overall_score": 85,
        "strengths": ["Good structure", "Clear examples"],
        "improvements": ["Add more metrics", "Be more concise"],
        "question_feedback": {
            "1": {"score": 90, "feedback": "Great use of STAR..."},
            ...
        }
    }
    """
    __tablename__ = 'interview_preps'

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    job_offer_id = Column(Integer, ForeignKey('job_offers.id', ondelete='SET NULL'), nullable=True)
    questions_json = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False, default=list)
    answers_json = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=True, default=dict)
    feedback_json = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=True, default=dict)

    # Relationships
    user = relationship('User', back_populates='interview_preps')
    job_offer = relationship('JobOffer', back_populates='interview_preps')

    # Indexes
    __table_args__ = (
        Index('idx_interview_user', 'user_id'),
        Index('idx_interview_job', 'job_offer_id'),
        Index('idx_interview_created', 'created_at'),
    )

    def __repr__(self):
        return f"<InterviewPrep(id={self.id}, user_id={self.user_id}, job_id={self.job_offer_id})>"

    def to_dict(self, include_details=False):
        """Convert to dictionary, optionally including questions and feedback."""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'job_offer_id': self.job_offer_id,
            'question_count': len(self.questions_json) if self.questions_json else 0,
            'has_answers': bool(self.answers_json),
            'has_feedback': bool(self.feedback_json),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
        if include_details:
            data['questions'] = self.questions_json or []
            data['answers'] = self.answers_json or {}
            data['feedback'] = self.feedback_json or {}
        if self.job_offer:
            data['job_title'] = self.job_offer.title
            data['company'] = self.job_offer.company
        return data

    @property
    def overall_score(self):
        """Get overall score from feedback."""
        if self.feedback_json:
            return self.feedback_json.get('overall_score')
        return None

    @property
    def is_complete(self):
        """Check if all questions have been answered."""
        if not self.questions_json or not self.answers_json:
            return False
        question_ids = {str(q.get('id')) for q in self.questions_json}
        return question_ids <= set(self.answers_json.keys())
