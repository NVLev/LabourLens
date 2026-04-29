"""fix timestamp with timezone for translated_at columns

Revision ID: fc077d9a8cda
Revises: b14f29b6a3a7
Create Date: 2026-04-29 18:37:43.765617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fc077d9a8cda'
down_revision: Union[str, Sequence[str], None] = 'b14f29b6a3a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('section_paragraphs', 'translated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.TIMESTAMP(timezone=True),
               existing_nullable=True)
    op.alter_column('section_paragraphs', 'translated_ru_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.TIMESTAMP(timezone=True),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('section_paragraphs', 'translated_ru_at',
               existing_type=sa.TIMESTAMP(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('section_paragraphs', 'translated_at',
               existing_type=sa.TIMESTAMP(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
