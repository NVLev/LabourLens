"""initialб create tables

Revision ID: bd638428d6b1
Revises:
Create Date: 2026-04-21 22:28:11.725591

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd638428d6b1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "acts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("name_fi", sa.String(length=200), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=True),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("last_parsed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("name_en", sa.String(length=200), nullable=False),
        sa.Column("name_ru", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "unions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("name_fi", sa.String(length=200), nullable=False),
        sa.Column("sector_en", sa.String(length=200), nullable=True),
        sa.Column("website", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("union_key", sa.String(length=50), nullable=True),
        sa.Column("employment_type", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "agreements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("union_id", sa.Integer(), nullable=False),
        sa.Column("name_fi", sa.String(length=300), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["union_id"], ["unions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("act_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.SmallInteger(), nullable=False),
        sa.Column("title_fi", sa.String(length=300), nullable=True),
        sa.Column("title_en", sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(["act_id"], ["acts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("act_id", "number"),
    )
    op.create_table(
        "faq_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("question_en", sa.Text(), nullable=False),
        sa.Column("question_ru", sa.Text(), nullable=True),
        sa.Column(
            "conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("answer_en", sa.Text(), nullable=False),
        sa.Column("answer_ru", sa.Text(), nullable=True),
        sa.Column("priority", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_faq_rules_conditions",
        "faq_rules",
        ["conditions"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_table(
        "interpretations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("title_fi", sa.String(length=300), nullable=True),
        sa.Column("text_fi", sa.Text(), nullable=False),
        sa.Column("text_en", sa.Text(), nullable=True),
        sa.Column("parsed_at", sa.DateTime(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("act_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.SmallInteger(), nullable=False),
        sa.Column("title_fi", sa.String(length=300), nullable=True),
        sa.Column("title_en", sa.String(length=300), nullable=True),
        sa.Column("last_amended", sa.String(length=50), nullable=True),
        sa.Column("anchor", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.ForeignKeyConstraint(["act_id"], ["acts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("act_id", "chapter_id", "number"),
    )
    op.create_table(
        "tes_clauses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agreement_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("section_ref", sa.String(length=100), nullable=True),
        sa.Column("text_fi", sa.Text(), nullable=False),
        sa.Column("text_en", sa.Text(), nullable=True),
        sa.Column("priority_over_law", sa.Boolean(), nullable=False),
        sa.Column("priority_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["agreement_id"], ["agreements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_queries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("raw_query", sa.Text(), nullable=True),
        sa.Column("matched_faq_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["matched_faq_id"],
            ["faq_rules.id"],
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "faq_section_refs",
        sa.Column("faq_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["faq_id"],
            ["faq_rules.id"],
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
        ),
        sa.PrimaryKeyConstraint("faq_id", "section_id"),
    )
    op.create_table(
        "section_paragraphs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("text_fi", sa.Text(), nullable=False),
        sa.Column("text_en", sa.Text(), nullable=True),
        sa.Column("translated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "topic_sections",
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("relevance", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
        ),
        sa.PrimaryKeyConstraint("topic_id", "section_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("topic_sections")
    op.drop_table("section_paragraphs")
    op.drop_table("faq_section_refs")
    op.drop_table("user_queries")
    op.drop_table("tes_clauses")
    op.drop_table("sections")
    op.drop_table("interpretations")
    op.drop_index(
        "ix_faq_rules_conditions", table_name="faq_rules", postgresql_using="gin"
    )
    op.drop_table("faq_rules")
    op.drop_table("chapters")
    op.drop_table("agreements")
    op.drop_table("users")
    op.drop_table("unions")
    op.drop_table("topics")
    op.drop_table("acts")
