"""Add transcript metrics columns for cost analysis

Revision ID: 005
Revises: 004
Create Date: 2026-01-06

Adds duration_minutes and word_count to jobs table to enable
correlation analysis between transcript complexity and processing costs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add transcript metrics for cost analysis
    op.add_column(
        'jobs',
        sa.Column('duration_minutes', sa.Float(), nullable=True)
    )
    op.add_column(
        'jobs',
        sa.Column('word_count', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('jobs', 'word_count')
    op.drop_column('jobs', 'duration_minutes')
