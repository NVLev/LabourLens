from datetime import date
from typing import Any

from sqlalchemy import null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import TesRate, Agreement, Topic, Union


class TesRateRepository:
    def __init__(self, session):
        self.session = session

    async def get_rate_by_topic(
            self,
            topic_key: str,
            union_key: str | None = None,
    ) -> list[Any]:
        stmt = (
            select(TesRate)
            .options(
                selectinload(TesRate.topic),
                selectinload(TesRate.agreement).selectinload(Agreement.union)
            )
            .join(TesRate.agreement)
            .join(TesRate.topic)
            .join(Agreement.union)
            .where(Topic.key == topic_key)
        )
        if union_key:
            stmt = stmt.where(Union.key == union_key)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_unique_key(
        self,
        agreement_id: int,
        rate_type: str,
        wage_group: str | None,
        effective_from: date,
        rate_type_context: str | None,
    ) -> TesRate | None:
        stmt = select(TesRate).where(
            TesRate.agreement_id == agreement_id,
            TesRate.rate_type == rate_type,
            TesRate.wage_group == wage_group,
            TesRate.effective_from == effective_from,
            TesRate.rate_type_context == rate_type_context,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def add(self, tes_rate: TesRate) -> None:
        self.session.add(tes_rate)
