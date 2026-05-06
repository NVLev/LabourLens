"""add text_ru to section_paragraphs

Revision ID: b14f29b6a3a7
Revises: cf68647dbeeb
Create Date: 2026-04-28 22:54:05.858720

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b14f29b6a3a7"
down_revision: Union[str, Sequence[str], None] = "cf68647dbeeb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("section_paragraphs", sa.Column("text_ru", sa.Text(), nullable=True))
    op.add_column(
        "section_paragraphs",
        sa.Column("translated_ru_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("section_paragraphs", "translated_ru_at")
    op.drop_column("section_paragraphs", "text_ru")
