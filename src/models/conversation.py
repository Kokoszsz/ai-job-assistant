"""
Conversation Models
===================
Chat sessions and messages with AI assistant.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

from src.models.base import BaseModel, db


class Conversation(BaseModel):
    """
    Chat session with AI assistant.

    Relationships:
    - Many-to-One: User (parent)
    - One-to-Many: Message
    """

    __tablename__ = "conversations"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __init__(self, **kwargs):
        # Set defaults if not provided
        kwargs.setdefault("is_archived", False)
        kwargs.setdefault("is_deleted", False)
        super().__init__(**kwargs)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )

    # Indexes
    __table_args__ = (
        Index("idx_conversation_user", "user_id"),
        Index("idx_conversation_updated", "updated_at", postgresql_using="btree"),
        Index("idx_conversation_archived", "is_archived"),
        Index("idx_conversation_deleted", "is_deleted"),
    )

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title='{self.title}')>"

    def to_dict(self, include_messages=False):
        """Convert to dictionary, optionally including messages."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "is_deleted": self.is_deleted,
            "is_archived": self.is_archived,
            "message_count": len(self.messages) if self.messages else 0,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_messages:
            data["messages"] = [msg.to_dict() for msg in self.messages]
        return data

    @property
    def last_message(self):
        """Get the most recent message in this conversation."""
        if self.messages:
            return self.messages[-1]
        return None


class Message(BaseModel):
    """
    Individual chat message within a conversation.
    """

    __tablename__ = "messages"

    ROLES = ["user", "assistant"]
    MAX_CONTENT_LENGTH = 10000

    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True, default=dict)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Indexes
    __table_args__ = (
        Index("idx_message_conversation", "conversation_id"),
        Index("idx_message_created", "created_at"),
        Index("idx_message_role", "role"),
    )

    def __repr__(self):
        preview = self.content[:30] + "..." if len(self.content) > 30 else self.content
        return f"<Message(id={self.id}, role='{self.role}', preview='{preview}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata_json or {},
            "created_at": self.created_at.isoformat(),
        }
