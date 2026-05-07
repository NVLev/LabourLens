"""add translation fields to tes_clauses, replace utcnow

Revision ID: 7c43c4263ffe
Revises: 5df29c69fc99
Create Date: 2026-05-08 00:01:18.910399

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '7c43c4263ffe'
down_revision: Union[str, Sequence[str], None] = '5df29c69fc99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tes_clauses', sa.Column('text_ru', sa.Text(), nullable=True))
    op.add_column('tes_clauses', sa.Column('translated_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('tes_clauses', sa.Column('translated_ru_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.alter_column('user_queries', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.TIMESTAMP(timezone=True),
               nullable=True)
    op.alter_column('users', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.TIMESTAMP(timezone=True),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'created_at',
               existing_type=sa.TIMESTAMP(timezone=True),
               type_=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('user_queries', 'created_at',
               existing_type=sa.TIMESTAMP(timezone=True),
               type_=postgresql.TIMESTAMP(),
               nullable=False)
    op.drop_column('tes_clauses', 'translated_ru_at')
    op.drop_column('tes_clauses', 'translated_at')
    op.drop_column('tes_clauses', 'text_ru')
