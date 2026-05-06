from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class FaqRuleBase(BaseModel):
    question_en: str
    question_ru: Optional[str] = None
    conditions: dict[str, Any]
    # {"employment_type": "fixed", "tenure_months": {"lt": 6}}
    answer_en: str
    answer_ru: Optional[str] = None
    priority: int = 0


class FaqRuleCreate(FaqRuleBase):
    topic_id: int


class FaqRuleResponse(FaqRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int


class FaqSectionRefCreate(BaseModel):
    faq_id: int
    section_id: int
