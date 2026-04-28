"""add content_hash to sections

Revision ID: cf68647dbeeb
Revises: 2b098ea26301
Create Date: 2026-04-27 23:45:54.161155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'cf68647dbeeb'
down_revision: Union[str, Sequence[str], None] = '2b098ea26301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('sections', sa.Column('content_hash', sa.String(length=64), nullable=False))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('sections', 'content_hash')
