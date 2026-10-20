"""add tes_clause_topic_overrides

Revision ID: 78b9f5a76515
Revises: 903b7bd6666e
Create Date: 2026-10-20 19:59:14.754502

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78b9f5a76515'
down_revision: Union[str, Sequence[str], None] = '903b7bd6666e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tes_clause_topic_overrides',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('agreement_key', sa.String(length=300), nullable=False),
    sa.Column('text_hash', sa.String(length=32), nullable=False),
    sa.Column('topic_id', sa.Integer(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('agreement_key', 'text_hash', name='uq_clause_override_key_hash')
    )
    op.create_index(op.f('ix_tes_clause_topic_overrides_agreement_key'), 'tes_clause_topic_overrides', ['agreement_key'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tes_clause_topic_overrides_agreement_key'), table_name='tes_clause_topic_overrides')
    op.drop_table('tes_clause_topic_overrides')
