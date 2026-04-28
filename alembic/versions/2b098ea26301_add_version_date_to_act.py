"""add version_date to Act

Revision ID: 2b098ea26301
Revises: bd638428d6b1
Create Date: 2026-04-23 22:37:25.816275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2b098ea26301'
down_revision: Union[str, Sequence[str], None] = 'bd638428d6b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('acts', sa.Column('version_date', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('acts', 'version_date')
