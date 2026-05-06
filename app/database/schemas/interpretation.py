from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .topic import TopicShort


class InterpretationBase(BaseModel):
    source: str  # "tyosuojelu" | "sak" | "pam" | "tek"
    source_url: Optional[str] = None
    title_fi: Optional[str] = None
    text_fi: str
    text_en: Optional[str] = None


class InterpretationCreate(InterpretationBase):
    topic_id: int
    content_hash: Optional[str] = None


class InterpretationResponse(InterpretationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    parsed_at: datetime
    content_hash: Optional[str] = None
