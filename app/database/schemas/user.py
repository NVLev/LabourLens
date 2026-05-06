from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    language: str = "en"
    union_key: Optional[str] = None
    employment_type: Optional[str] = None
    # "permanent" | "fixed"


class UserCreate(UserBase):
    id: int  # telegram user_id — приходит снаружи, не autoincrement


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class UserQueryCreate(BaseModel):
    user_id: int
    topic_id: Optional[int] = None
    raw_query: Optional[str] = None
    matched_faq_id: Optional[int] = None


class UserQueryResponse(UserQueryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
