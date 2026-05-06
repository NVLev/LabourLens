from typing import Optional

from pydantic import BaseModel, ConfigDict

from .law import SectionShort


class TopicBase(BaseModel):
    key: str
    name_en: str
    name_ru: Optional[str] = None
    description: Optional[str] = None


class TopicCreate(TopicBase):
    pass


class TopicShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name_en: str
    name_ru: Optional[str] = None


class TopicResponse(TopicBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sections: list[SectionShort] = []


class TopicSectionCreate(BaseModel):
    topic_id: int
    section_id: int
    relevance: int = 1
