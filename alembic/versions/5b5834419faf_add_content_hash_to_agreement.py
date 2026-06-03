"""add content-hash to Agreement

Revision ID: 5b5834419faf
Revises: c8cb118cd0c1
Create Date: 2026-05-12 23:07:01.802510

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "5b5834419faf"
down_revision: Union[str, Sequence[str], None] = "c8cb118cd0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "agreements",
        sa.Column("is_parsed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "agreements", sa.Column("parsed_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "agreements", sa.Column("content_hash", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("agreements", "content_hash")
    op.drop_column("agreements", "parsed_at")
    op.drop_column("agreements", "is_parsed")
