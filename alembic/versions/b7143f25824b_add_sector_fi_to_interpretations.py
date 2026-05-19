"""add sector_fi to interpretations

Revision ID: b7143f25824b
Revises: 5b5834419faf
Create Date: 2026-05-19 21:57:13.251480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7143f25824b'
down_revision: Union[str, Sequence[str], None] = '5b5834419faf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('agreements', 'is_parsed',
               existing_type=sa.BOOLEAN(),
               server_default=None,
               existing_nullable=False)
    op.add_column('interpretations', sa.Column('sector_fi', sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('interpretations', 'sector_fi')
    op.alter_column('agreements', 'is_parsed',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('false'),
               existing_nullable=False)
