"""Add fields for external job sync (Remotive API integration)

Revision ID: 004
Revises: 003
Create Date: 2026-01-27 10:00:00

This migration adds:
1. external_source - identifies the job source (e.g., "remotive")
2. last_seen_at - timestamp when job was last seen in API sync
3. tags - JSON array of skills/technologies
4. category - job category from source
5. company_logo_url - URL to company logo
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    """Add job sync fields to job_offers table."""

    # Add external_source column
    op.add_column(
        "job_offers", sa.Column("external_source", sa.String(50), nullable=True)
    )

    # Add last_seen_at column
    op.add_column("job_offers", sa.Column("last_seen_at", sa.DateTime(), nullable=True))

    # Add tags column (JSON array for SQLite compatibility, use ARRAY for PostgreSQL)
    op.add_column("job_offers", sa.Column("tags", sa.JSON(), nullable=True))

    # Add category column
    op.add_column("job_offers", sa.Column("category", sa.String(100), nullable=True))

    # Add company_logo_url column
    op.add_column(
        "job_offers", sa.Column("company_logo_url", sa.String(500), nullable=True)
    )

    # Add index on external_source for filtering by source
    op.create_index("idx_job_external_source", "job_offers", ["external_source"])

    # Add index on last_seen_at for finding stale jobs
    op.create_index("idx_job_last_seen", "job_offers", ["last_seen_at"])


def downgrade():
    """Remove job sync fields from job_offers table."""

    # Drop indexes first
    op.drop_index("idx_job_last_seen", table_name="job_offers")
    op.drop_index("idx_job_external_source", table_name="job_offers")

    # Drop columns
    op.drop_column("job_offers", "company_logo_url")
    op.drop_column("job_offers", "category")
    op.drop_column("job_offers", "tags")
    op.drop_column("job_offers", "last_seen_at")
    op.drop_column("job_offers", "external_source")
