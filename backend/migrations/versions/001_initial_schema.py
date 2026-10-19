"""
Initial database schema with all 11 entities.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-12-14

Entities:
- User
- Profile, WorkExperience, Education, Skill
- Conversation, Message
- JobOffer, FavoriteJob
- CV
- InterviewPrep
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # === Users ===
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email')
    )
    op.create_index('idx_user_email', 'users', ['email'])
    op.create_index('idx_user_created', 'users', ['created_at'])
    op.create_index('idx_user_active', 'users', ['is_active'])

    # === Profiles ===
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('preferences_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uq_profiles_user_id')
    )
    op.create_index('idx_profile_user', 'profiles', ['user_id'])

    # === Work Experiences ===
    op.create_table(
        'work_experiences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('job_title', sa.String(100), nullable=False),
        sa.Column('company', sa.String(100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE')
    )
    op.create_index('idx_experience_profile', 'work_experiences', ['profile_id'])
    op.create_index('idx_experience_dates', 'work_experiences', ['start_date', 'end_date'])

    # === Education ===
    op.create_table(
        'education',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('degree', sa.String(100), nullable=False),
        sa.Column('institution', sa.String(100), nullable=False),
        sa.Column('field_of_study', sa.String(100), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE')
    )
    op.create_index('idx_education_profile', 'education', ['profile_id'])

    # === Skills ===
    op.create_table(
        'skills',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('proficiency_level', sa.String(20), nullable=False, default='intermediate'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('profile_id', 'name', name='uq_skill_profile_name')
    )
    op.create_index('idx_skill_profile', 'skills', ['profile_id'])
    op.create_index('idx_skill_name', 'skills', ['name'])

    # === Conversations ===
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_conversation_user', 'conversations', ['user_id'])
    op.create_index('idx_conversation_updated', 'conversations', ['updated_at'])
    op.create_index('idx_conversation_archived', 'conversations', ['is_archived'])

    # === Messages ===
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE')
    )
    op.create_index('idx_message_conversation', 'messages', ['conversation_id'])
    op.create_index('idx_message_created', 'messages', ['created_at'])
    op.create_index('idx_message_role', 'messages', ['role'])

    # === Job Offers ===
    op.create_table(
        'job_offers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('external_id', sa.String(100), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('company', sa.String(100), nullable=False),
        sa.Column('location', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirements', sa.Text(), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('job_type', sa.String(50), nullable=False, default='full-time'),
        sa.Column('posted_date', sa.Date(), nullable=False),
        sa.Column('external_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', name='uq_job_external_id')
    )
    op.create_index('idx_job_external_id', 'job_offers', ['external_id'])
    op.create_index('idx_job_location', 'job_offers', ['location'])
    op.create_index('idx_job_type', 'job_offers', ['job_type'])
    op.create_index('idx_job_posted', 'job_offers', ['posted_date'])
    op.create_index('idx_job_active', 'job_offers', ['is_active'])
    op.create_index('idx_job_salary', 'job_offers', ['salary_min', 'salary_max'])
    op.create_index('idx_job_company', 'job_offers', ['company'])
    
    # Full-text search index on job_offers
    op.execute("""
        CREATE INDEX idx_job_fulltext ON job_offers 
        USING gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || coalesce(requirements, '')))
    """)

    # === Favorite Jobs ===
    op.create_table(
        'favorite_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_offer_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('saved_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_offer_id'], ['job_offers.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'job_offer_id', name='uq_favorite_user_job')
    )
    op.create_index('idx_favorite_user', 'favorite_jobs', ['user_id'])
    op.create_index('idx_favorite_job', 'favorite_jobs', ['job_offer_id'])

    # === CVs ===
    op.create_table(
        'cvs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('target_position', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_cv_user', 'cvs', ['user_id'])
    op.create_index('idx_cv_created', 'cvs', ['created_at'])

    # === Interview Preps ===
    op.create_table(
        'interview_preps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('job_offer_id', sa.Integer(), nullable=True),
        sa.Column('questions_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('answers_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('feedback_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_offer_id'], ['job_offers.id'], ondelete='SET NULL')
    )
    op.create_index('idx_interview_user', 'interview_preps', ['user_id'])
    op.create_index('idx_interview_job', 'interview_preps', ['job_offer_id'])
    op.create_index('idx_interview_created', 'interview_preps', ['created_at'])


def downgrade():
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('interview_preps')
    op.drop_table('cvs')
    op.drop_table('favorite_jobs')
    op.drop_index('idx_job_fulltext', table_name='job_offers')
    op.drop_table('job_offers')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('skills')
    op.drop_table('education')
    op.drop_table('work_experiences')
    op.drop_table('profiles')
    op.drop_table('users')
