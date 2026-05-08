"""add sector fields to agreements, remove sector_en from unions

Revision ID: 22c20a842b74
Revises: 7c43c4263ffe
Create Date: 2026-05-08 22:06:19.900681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '22c20a842b74'
down_revision: Union[str, Sequence[str], None] = '7c43c4263ffe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('agreements', sa.Column('sector_fi', sa.String(length=200), nullable=True))
    op.add_column('agreements', sa.Column('sector_en', sa.String(length=200), nullable=True))
    op.drop_column('unions', 'sector_en')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('unions', sa.Column('sector_en', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
    op.drop_column('agreements', 'sector_en')
    op.drop_column('agreements', 'sector_fi')
