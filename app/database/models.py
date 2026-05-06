from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# СЛОЙ ЗАКОНОВ


class Act(Base):
    """Закон целиком — Työsopimuslaki, Vuosilomalaki и т.д."""

    __tablename__ = "acts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # "tyosopimuslaki"
    name_fi: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    # "2001/55"
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    last_parsed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    version_date: Mapped[Optional[date]] = mapped_column()

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="act", cascade="all, delete-orphan"
    )


class Chapter(Base):
    """Глава закона."""

    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("act_id", "number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    act_id: Mapped[int] = mapped_column(ForeignKey("acts.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title_fi: Mapped[Optional[str]] = mapped_column(String(300))
    title_en: Mapped[Optional[str]] = mapped_column(String(300))

    act: Mapped["Act"] = relationship(back_populates="chapters")
    sections: Mapped[list["Section"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )


class Section(Base):
    """Параграф (§)."""

    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("act_id", "chapter_id", "number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    act_id: Mapped[int] = mapped_column(ForeignKey("acts.id", ondelete="CASCADE"))
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE")
    )
    number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title_fi: Mapped[Optional[str]] = mapped_column(String(300))
    title_en: Mapped[Optional[str]] = mapped_column(String(300))
    last_amended: Mapped[Optional[str]] = mapped_column(String(50))
    # "(21.12.2010/1224)"
    anchor: Mapped[str] = mapped_column(String(100), nullable=False)
    # "chp_1__sec_3"
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    act: Mapped["Act"] = relationship()
    chapter: Mapped["Chapter"] = relationship(back_populates="sections")
    paragraphs: Mapped[list["SectionParagraph"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="SectionParagraph.order_index",
    )
    topic_links: Mapped[list["TopicSection"]] = relationship(back_populates="section")


class SectionParagraph(Base):
    """Пункт параграфа — один <subsection> в HTML finlex."""

    __tablename__ = "section_paragraphs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE")
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text_fi: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[Optional[str]] = mapped_column(Text)
    translated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    text_ru: Mapped[Optional[str]] = mapped_column(Text)
    translated_ru_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    section: Mapped["Section"] = relationship(back_populates="paragraphs")


# СЛОЙ ТЕМ


class Topic(Base):
    """
    Тематический якорь: 'dismissal', 'overtime', 'sick_leave'.
    Всё остальное крутится вокруг него.
    """

    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ru: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)

    section_links: Mapped[list["TopicSection"]] = relationship(back_populates="topic")
    interpretations: Mapped[list["Interpretation"]] = relationship(
        back_populates="topic"
    )
    tes_clauses: Mapped[list["TesClause"]] = relationship(back_populates="topic")
    faq_rules: Mapped[list["FaqRule"]] = relationship(back_populates="topic")


class TopicSection(Base):
    """M2M: тема ↔ параграф, с весом релевантности."""

    __tablename__ = "topic_sections"

    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), primary_key=True)
    relevance: Mapped[int] = mapped_column(SmallInteger, default=1)
    # 1=упоминает, 2=основной, 3=ключевой

    topic: Mapped["Topic"] = relationship(back_populates="section_links")
    section: Mapped["Section"] = relationship(back_populates="topic_links")


# СЛОЙ ИНТЕРПРЕТАЦИЙ


class Interpretation(Base):
    """Объяснение от Työsuojelu или профсоюза."""

    __tablename__ = "interpretations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    # "tyosuojelu" | "sak" | "pam" | "tek"
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    title_fi: Mapped[Optional[str]] = mapped_column(String(300))
    text_fi: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[Optional[str]] = mapped_column(Text)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    text_ru: Mapped[Optional[str]] = mapped_column(Text)
    translated_ru_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True)
    )
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    # SHA-256 для детекта изменений при повторном парсинге

    topic: Mapped["Topic"] = relationship(back_populates="interpretations")


# СЛОЙ TES


class Union(Base):
    """Профсоюз."""

    __tablename__ = "unions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # "pam" | "rakennusliitto" | "tek"
    name_fi: Mapped[str] = mapped_column(String(200), nullable=False)
    sector_en: Mapped[Optional[str]] = mapped_column(String(200))
    website: Mapped[Optional[str]] = mapped_column(String(200))

    agreements: Mapped[list["Agreement"]] = relationship(back_populates="union")


class Agreement(Base):
    """Конкретный TES с датами действия."""

    __tablename__ = "agreements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    union_id: Mapped[int] = mapped_column(ForeignKey("unions.id", ondelete="CASCADE"))
    name_fi: Mapped[str] = mapped_column(String(300), nullable=False)
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_until: Mapped[Optional[date]] = mapped_column(Date)
    # NULL = действует сейчас
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(20), default="html")
    # "html" | "pdf"
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    is_universally_binding: Mapped[bool] = mapped_column(Boolean, default=False)
    # yleissitova — обязателен для всех работодателей отрасли,
    # независимо от членства в профсоюзе

    union: Mapped["Union"] = relationship(back_populates="agreements")
    clauses: Mapped[list["TesClause"]] = relationship(back_populates="agreement")


class TesClause(Base):
    """Клауза TES, привязанная к теме."""

    __tablename__ = "tes_clauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agreement_id: Mapped[int] = mapped_column(
        ForeignKey("agreements.id", ondelete="CASCADE")
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    section_ref: Mapped[Optional[str]] = mapped_column(String(100))
    # "§ 12" внутри TES
    text_fi: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[Optional[str]] = mapped_column(Text)
    priority_over_law: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_note: Mapped[Optional[str]] = mapped_column(Text)
    # объяснение почему TES лучше закона

    agreement: Mapped["Agreement"] = relationship(back_populates="clauses")
    topic: Mapped[Optional["Topic"]] = relationship(back_populates="tes_clauses")


# СЛОЙ APPLICATION


class FaqRule(Base):
    """Rule-based FAQ: условия → готовый ответ со ссылками."""

    __tablename__ = "faq_rules"
    __table_args__ = (
        Index("ix_faq_rules_conditions", "conditions", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    question_en: Mapped[str] = mapped_column(Text, nullable=False)
    question_ru: Mapped[Optional[str]] = mapped_column(Text)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {"employment_type": "fixed", "tenure_months": {"lt": 6}}
    answer_en: Mapped[str] = mapped_column(Text, nullable=False)
    answer_ru: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(SmallInteger, default=0)

    topic: Mapped["Topic"] = relationship(back_populates="faq_rules")
    section_refs: Mapped[list["FaqSectionRef"]] = relationship(
        back_populates="faq_rule"
    )


class FaqSectionRef(Base):
    """FAQ → конкретные параграфы закона."""

    __tablename__ = "faq_section_refs"

    faq_id: Mapped[int] = mapped_column(ForeignKey("faq_rules.id"), primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id"), primary_key=True)

    faq_rule: Mapped["FaqRule"] = relationship(back_populates="section_refs")
    section: Mapped["Section"] = relationship()


# СЛОЙ ПОЛЬЗОВАТЕЛЕЙ


class User(Base):
    """Telegram-пользователь."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # telegram user_id — не autoincrement
    language: Mapped[str] = mapped_column(String(5), default="en")
    union_key: Mapped[Optional[str]] = mapped_column(String(50))
    employment_type: Mapped[Optional[str]] = mapped_column(String(20))
    # "permanent" | "fixed"
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    queries: Mapped[list["UserQuery"]] = relationship(back_populates="user")


class UserQuery(Base):
    """История запросов — для анализа и улучшения FAQ."""

    __tablename__ = "user_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    topic_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("topics.id"), nullable=True
    )
    raw_query: Mapped[Optional[str]] = mapped_column(Text)
    matched_faq_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("faq_rules.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="queries")
