from datetime import date

from sqlalchemy import null, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TesRate

class TesRateRepository:
    def __init__(self, session):
        self.session = session

    async def get_by_unique_key(
            self,
            agreement_id: int,
            rate_type: str,
            wage_group: str | None,
            effective_from: date,
            rate_type_context: str | None
    ) -> TesRate | None:
        stmt = select(TesRate).where(
                TesRate.agreement_id == agreement_id,
                TesRate.rate_type == rate_type,
                TesRate.wage_group == wage_group,
                TesRate.effective_from == effective_from,
                TesRate.rate_type_context == rate_type_context
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def add(self, tes_rate: TesRate) -> None:
        self.session.add(tes_rate)

