"""add is_universally_binding to agreements

Revision ID: 5df29c69fc99
Revises: f1438e6ca869
Create Date: 2026-05-07 00:01:25.022843

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5df29c69fc99'
down_revision: Union[str, Sequence[str], None] = 'f1438e6ca869'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('agreements', sa.Column('is_universally_binding', sa.Boolean(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('agreements', 'is_universally_binding')
