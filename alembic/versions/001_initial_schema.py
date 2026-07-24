"""Initial database schema migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-07-24

Creates all 6 tables:
    - users
    - resumes
    - job_descriptions
    - analysis_history
    - reports
    - resume_embeddings
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        comment='Platform user accounts',
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── resumes ───────────────────────────────────────────────────────────────
    op.create_table(
        'resumes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_path', sa.String(length=512), nullable=False),
        sa.Column('file_type', sa.String(length=10), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('parsed_text', sa.Text(), nullable=True),
        sa.Column('candidate_name', sa.String(length=255), nullable=True),
        sa.Column('candidate_email', sa.String(length=255), nullable=True),
        sa.Column('candidate_phone', sa.String(length=50), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Uploaded resume files and their parsed content',
    )
    op.create_index('ix_resumes_user_id', 'resumes', ['user_id'])
    op.create_index('ix_resumes_created_at', 'resumes', ['created_at'])

    # ── job_descriptions ──────────────────────────────────────────────────────
    op.create_table(
        'job_descriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('company', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Job descriptions uploaded by users for analysis',
    )
    op.create_index('ix_jd_user_id', 'job_descriptions', ['user_id'])
    op.create_index('ix_jd_created_at', 'job_descriptions', ['created_at'])

    # ── analysis_history ──────────────────────────────────────────────────────
    op.create_table(
        'analysis_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_description_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ats_score', sa.Float(), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('keyword_match_count', sa.Integer(), nullable=True),
        sa.Column('missing_skills_json', sa.Text(), nullable=True),
        sa.Column('matched_skills_json', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_description_id'], ['job_descriptions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Historical log of all resume analysis runs',
    )
    op.create_index('ix_analysis_resume_id', 'analysis_history', ['resume_id'])
    op.create_index('ix_analysis_jd_id', 'analysis_history', ['job_description_id'])
    op.create_index('ix_analysis_created_at', 'analysis_history', ['created_at'])
    op.create_index('ix_analysis_status', 'analysis_history', ['status'])

    # ── reports ───────────────────────────────────────────────────────────────
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('strengths', sa.Text(), nullable=True),
        sa.Column('weaknesses', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('improved_resume', sa.Text(), nullable=True),
        sa.Column('interview_tips', sa.Text(), nullable=True),
        sa.Column('career_roadmap', sa.Text(), nullable=True),
        sa.Column('skill_gaps', sa.Text(), nullable=True),
        sa.Column('keyword_suggestions', sa.Text(), nullable=True),
        sa.Column('section_feedback', sa.Text(), nullable=True),
        sa.Column('recruiter_verdict', sa.Text(), nullable=True),
        sa.Column('full_report_json', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['analysis_id'], ['analysis_history.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('analysis_id'),
        comment='Full AI-generated intelligence reports per analysis',
    )
    op.create_index('ix_reports_analysis_id', 'reports', ['analysis_id'])
    op.create_index('ix_reports_generated_at', 'reports', ['generated_at'])

    # ── resume_embeddings ─────────────────────────────────────────────────────
    op.create_table(
        'resume_embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('embedding_model', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Chunk embeddings for RAG pipeline',
    )
    op.create_index('ix_embeddings_resume_id', 'resume_embeddings', ['resume_id'])


def downgrade() -> None:
    op.drop_table('resume_embeddings')
    op.drop_table('reports')
    op.drop_table('analysis_history')
    op.drop_table('job_descriptions')
    op.drop_table('resumes')
    op.drop_table('users')
