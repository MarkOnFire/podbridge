"""Add phases column for step-level tracking

Revision ID: 003
Revises: 002
Create Date: 2024-12-23 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add phases column to jobs table
    # Stores JSON array of JobPhase objects for step-level tracking
    op.add_column(
        'jobs',
        sa.Column('phases', sa.Text(), nullable=True)
    )

    # Initialize phases for existing jobs with default structure
    # The _row_to_job function will handle backward compatibility for
    # rows where phases is still NULL by generating phases from agent_phases
    # This migration just adds the column - no data migration needed


def downgrade() -> None:
    op.drop_column('jobs', 'phases')
