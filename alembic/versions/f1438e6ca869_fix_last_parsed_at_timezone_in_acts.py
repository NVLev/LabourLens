"""fix last_parsed_at timezone in acts

Revision ID: f1438e6ca869
Revises: d932e4da25a8
Create Date: 2026-05-05 22:38:00.037221

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f1438e6ca869"
down_revision: Union[str, Sequence[str], None] = "d932e4da25a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "acts",
        "last_parsed_at",
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.TIMESTAMP(timezone=True),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "acts",
        "last_parsed_at",
        existing_type=sa.TIMESTAMP(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
