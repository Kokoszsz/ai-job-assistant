"""Add CV enhancements and new profile models (certifications, projects, languages)

Revision ID: 003
Revises: 002
Create Date: 2026-01-25 12:00:00

This migration adds:
1. New columns to cvs table: job_offer_id, is_ai_generated, generation_prompt
2. New tables: certifications, projects, languages
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    """Apply CV and profile enhancements."""

    # 1. Add new columns to cvs table
    op.add_column("cvs", sa.Column("job_offer_id", sa.Integer(), nullable=True))
    op.add_column(
        "cvs",
        sa.Column(
            "is_ai_generated", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column("cvs", sa.Column("generation_prompt", sa.Text(), nullable=True))

    # Add foreign key constraint for job_offer_id
    op.create_foreign_key(
        "fk_cv_job_offer",
        "cvs",
        "job_offers",
        ["job_offer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for job_offer_id
    op.create_index("idx_cv_job_offer", "cvs", ["job_offer_id"])

    # 2. Create certifications table
    op.create_table(
        "certifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("issuing_organization", sa.String(200), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("credential_id", sa.String(100), nullable=True),
        sa.Column("credential_url", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_certification_profile", "certifications", ["profile_id"])

    # 3. Create projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("technologies", sa.String(500), nullable=True),  # Comma-separated
        sa.Column("url", sa.String(500), nullable=True),
        sa.Column("repository_url", sa.String(500), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_ongoing", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_project_profile", "projects", ["profile_id"])

    # 4. Create languages table
    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column(
            "proficiency_level",
            sa.String(30),
            nullable=False,
            server_default="professional_working",
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_language_profile", "languages", ["profile_id"])
    op.create_unique_constraint(
        "uq_language_profile_name", "languages", ["profile_id", "name"]
    )


def downgrade():
    """Revert CV and profile enhancements."""

    # Drop languages table
    op.drop_constraint("uq_language_profile_name", "languages", type_="unique")
    op.drop_index("idx_language_profile", table_name="languages")
    op.drop_table("languages")

    # Drop projects table
    op.drop_index("idx_project_profile", table_name="projects")
    op.drop_table("projects")

    # Drop certifications table
    op.drop_index("idx_certification_profile", table_name="certifications")
    op.drop_table("certifications")

    # Remove cvs table enhancements
    op.drop_index("idx_cv_job_offer", table_name="cvs")
    op.drop_constraint("fk_cv_job_offer", "cvs", type_="foreignkey")
    op.drop_column("cvs", "generation_prompt")
    op.drop_column("cvs", "is_ai_generated")
    op.drop_column("cvs", "job_offer_id")
