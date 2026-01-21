"""Add download tracking columns to available_files

Revision ID: 007
Revises: 006
Create Date: 2026-01-21

Adds columns for tracking downloaded transcripts:
- local_path: Path where the file was saved locally
- downloaded_at: Timestamp of when the file was downloaded
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add local_path column for tracking downloaded transcripts
    op.add_column(
        'available_files',
        sa.Column('local_path', sa.Text(), nullable=True)
    )

    # Add downloaded_at timestamp
    op.add_column(
        'available_files',
        sa.Column('downloaded_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('available_files', 'downloaded_at')
    op.drop_column('available_files', 'local_path')
