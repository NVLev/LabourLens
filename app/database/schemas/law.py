from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# Paragraph

class ParagraphBase(BaseModel):
    order_index: int
    text_fi: str
    text_en: Optional[str] = None


class ParagraphCreate(ParagraphBase):
    section_id: int


class ParagraphResponse(ParagraphBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    translated_at: Optional[datetime] = None


# Section

class SectionBase(BaseModel):
    number: int
    title_fi: Optional[str] = None
    title_en: Optional[str] = None
    last_amended: Optional[str] = None
    anchor: str
    url: str


class SectionCreate(SectionBase):
    act_id: int
    chapter_id: int
    content_hash: Optional[str] = None


class SectionShort(BaseModel):
    """Для списков — без пунктов, только заголовок."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    title_fi: Optional[str] = None
    title_en: Optional[str] = None
    url: str


class SectionResponse(SectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    act_id: int
    chapter_id: int
    content_hash: Optional[str] = None
    paragraphs: list[ParagraphResponse] = []


# Chapter

class ChapterBase(BaseModel):
    number: int
    title_fi: Optional[str] = None
    title_en: Optional[str] = None


class ChapterCreate(ChapterBase):
    act_id: int


class ChapterShort(BaseModel):
    """Для списков — без параграфов."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    title_fi: Optional[str] = None
    title_en: Optional[str] = None


class ChapterResponse(ChapterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    act_id: int
    sections: list[SectionShort] = []


# Act

class ActBase(BaseModel):
    key: str
    name_fi: str
    name_en: Optional[str] = None
    code: str
    url: str


class ActCreate(ActBase):
    pass


class ActShort(BaseModel):
    """Для списков — только мета."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name_fi: str
    name_en: Optional[str] = None
    code: str
    last_parsed_at: Optional[datetime] = None


class ActResponse(ActBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_parsed_at: Optional[datetime] = None
    chapters: list[ChapterShort] = []