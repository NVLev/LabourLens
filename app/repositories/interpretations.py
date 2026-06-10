from sqlalchemy import select, or_, null
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Interpretation, Topic


class InterpretationRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_topic_and_source(
        self, topic_id: int, source: str
    ) -> Interpretation | None:
        result = await self.session.execute(
            select(Interpretation).where(
                Interpretation.topic_id == topic_id,
                Interpretation.source == source,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_topic(self, topic_id: int) -> list[Interpretation]:
        result = await self.session.execute(
            select(Interpretation).where(Interpretation.topic_id == topic_id)
        )
        return list(result.scalars().all())

    async def get_by_topic_key(self, topic_key: str) -> list[Interpretation]:
        result = await self.session.execute(
            select(Interpretation).join(Topic).where(Topic.key == topic_key)
        )
        return list(result.scalars().all())

    async def get_by_topic_and_url(
        self, topic_id: int, source_url: str, title_fi: str
    ) -> Interpretation | None:
        result = await self.session.execute(
            select(Interpretation).where(
                Interpretation.topic_id == topic_id,
                Interpretation.source_url == source_url,
                Interpretation.title_fi.like(f"%{title_fi[:50]}%"),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_topic_key_filtered(
            self,
            topic_key: str,
            sector_fi_list: list[str] | None,
    ) -> list[Interpretation]:
        query = (
            select(Interpretation)
            .join(Topic)
            .where(Topic.key == topic_key)
        )
        if sector_fi_list:
            query = query.where(
                or_(
                    Interpretation.sector_fi.in_(sector_fi_list),
                    Interpretation.source == "tyosuojelu",
                )
            )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    def add(self, interpretation: Interpretation) -> None:
        self.session.add(interpretation)
