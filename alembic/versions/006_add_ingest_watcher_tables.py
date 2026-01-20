"""Add ingest watcher tables for remote file monitoring

Revision ID: 006
Revises: 005
Create Date: 2026-01-12

Adds tables for:
- available_files: Track files discovered on remote ingest server
- screengrab_attachments: Audit log for Airtable attachment operations
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create available_files table for tracking remote server files
    op.create_table(
        'available_files',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),

        # File identification
        sa.Column('remote_url', sa.Text(), nullable=False, unique=True),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('directory_path', sa.Text(), nullable=True),

        # File type routing
        sa.Column('file_type', sa.Text(), nullable=False),  # 'transcript' or 'screengrab'

        # Extracted metadata
        sa.Column('media_id', sa.Text(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('remote_modified_at', sa.DateTime(), nullable=True),

        # Tracking timestamps
        sa.Column('first_seen_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('last_seen_at', sa.DateTime(), server_default=sa.func.current_timestamp()),

        # Status workflow: new / queued / attached / no_match / ignored / missing
        sa.Column('status', sa.Text(), nullable=False, server_default='new'),
        sa.Column('status_changed_at', sa.DateTime(), nullable=True),

        # Linking (after action taken)
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id'), nullable=True),
        sa.Column('airtable_record_id', sa.Text(), nullable=True),
        sa.Column('attached_at', sa.DateTime(), nullable=True),
    )

    # Indexes for common queries
    op.create_index('idx_available_files_status', 'available_files', ['status'])
    op.create_index('idx_available_files_media_id', 'available_files', ['media_id'])
    op.create_index('idx_available_files_file_type', 'available_files', ['file_type'])
    op.create_index('idx_available_files_first_seen', 'available_files', ['first_seen_at'])

    # Create screengrab_attachments audit log table
    op.create_table(
        'screengrab_attachments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('available_file_id', sa.Integer(), sa.ForeignKey('available_files.id'), nullable=True),
        sa.Column('sst_record_id', sa.Text(), nullable=False),
        sa.Column('media_id', sa.Text(), nullable=False),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('remote_url', sa.Text(), nullable=False),
        sa.Column('attached_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('attachments_before', sa.Integer(), nullable=True),
        sa.Column('attachments_after', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), server_default='1'),
        sa.Column('error_message', sa.Text(), nullable=True),
    )

    op.create_index('idx_screengrab_attachments_media_id', 'screengrab_attachments', ['media_id'])
    op.create_index('idx_screengrab_attachments_sst_record', 'screengrab_attachments', ['sst_record_id'])


def downgrade() -> None:
    op.drop_table('screengrab_attachments')
    op.drop_table('available_files')
