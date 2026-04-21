from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UnionBase(BaseModel):
    key: str
    name_fi: str
    sector_en: Optional[str] = None
    website: Optional[str] = None


class UnionCreate(UnionBase):
    pass


class UnionResponse(UnionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class AgreementBase(BaseModel):
    name_fi: str
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    source_url: Optional[str] = None
    source_type: str = "html"
    is_current: bool = True


class AgreementCreate(AgreementBase):
    union_id: int


class AgreementResponse(AgreementBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    union_id: int
    union: Optional[UnionResponse] = None


class TesClauseBase(BaseModel):
    section_ref: Optional[str] = None
    text_fi: str
    text_en: Optional[str] = None
    priority_over_law: bool = False
    priority_note: Optional[str] = None


class TesClauseCreate(TesClauseBase):
    agreement_id: int
    topic_id: Optional[int] = None


class TesClauseResponse(TesClauseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agreement_id: int
    topic_id: Optional[int] = None