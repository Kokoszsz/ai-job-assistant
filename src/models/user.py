"""
User Model
==========
Authentication and account management.
"""

from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from src.models.base import db, BaseModel
from src.utils.password import hash_password, verify_password, validate_password_strength


class User(BaseModel):
    """
    User entity for authentication and account management.
    
    Relationships:
    - One-to-One: Profile
    - One-to-Many: Conversation, CV, FavoriteJob, InterviewPrep
    """
    __tablename__ = 'users'

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    def __init__(self, **kwargs):
        # Set default for is_active if not provided
        kwargs.setdefault('is_active', True)
        super().__init__(**kwargs)


    # Relationships
    profile = relationship(
        'Profile',
        back_populates='user',
        uselist=False,
        cascade='all, delete-orphan'
    )
    conversations = relationship(
        'Conversation',
        back_populates='user',
        cascade='all, delete-orphan',
        order_by='desc(Conversation.updated_at)'
    )
    cvs = relationship(
        'CV',
        back_populates='user',
        cascade='all, delete-orphan',
        order_by='desc(CV.created_at)'
    )
    favorite_jobs = relationship(
        'FavoriteJob',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    interview_preps = relationship(
        'InterviewPrep',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    # Indexes
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_created', 'created_at'),
        Index('idx_user_active', 'is_active'),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

    def set_password(self, password: str) -> None:
        """
        Set user password with validation and hashing.
        
        Args:
            password: The plaintext password to set
            
        Raises:
            PasswordValidationError: If password doesn't meet strength requirements
        """
        self.password_hash = hash_password(password)

    def check_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        
        Args:
            password: The plaintext password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return verify_password(password, self.password_hash)

    def to_dict(self, include_profile=False):
        """Convert to dictionary, optionally including profile."""
        data = {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_active': self.is_active,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
        if include_profile and self.profile:
            data['profile'] = self.profile.to_dict()
        return data
