"""Add is_deleted field to conversations

Revision ID: 002
Revises: 001
Create Date: 2026-01-01 18:45:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Add is_deleted column to conversations table."""
    op.add_column('conversations', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('idx_conversation_deleted', 'conversations', ['is_deleted'])


def downgrade():
    """Remove is_deleted column from conversations table."""
    op.drop_index('idx_conversation_deleted', table_name='conversations')
    op.drop_column('conversations', 'is_deleted')
