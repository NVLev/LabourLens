from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Agreement, TesClause, Topic, Union


class TesRepository:
    """
    Репозиторий для работы с коллективными договорами (TES).
    Покрывает Union, Agreement и TesClause.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Union

    async def get_union_by_key(self, key: str) -> Union | None:
        result = await self.session.execute(
            select(Union).where(Union.key == key)
        )
        return result.scalar_one_or_none()

    def add_union(self, union: Union) -> None:
        self.session.add(union)

    # Agreement

    async def get_agreement_by_url(self, source_url: str) -> Agreement | None:
        result = await self.session.execute(
            select(Agreement).where(Agreement.source_url == source_url)
        )
        return result.scalar_one_or_none()

    async def get_agreements_by_union(self, union_id: int) -> list[Agreement]:
        result = await self.session.execute(
            select(Agreement).where(
                Agreement.union_id == union_id,
                Agreement.is_current == True,
            )
        )
        return list(result.scalars().all())

    async def get_agreement_with_clauses(
        self, agreement_id: int
    ) -> Agreement | None:
        result = await self.session.execute(
            select(Agreement)
            .options(selectinload(Agreement.clauses))
            .where(Agreement.id == agreement_id)
        )
        return result.scalar_one_or_none()

    def add_agreement(self, agreement: Agreement) -> None:
        self.session.add(agreement)

    # TesClause

    async def get_clauses_by_topic(self, topic_id: int) -> list[TesClause]:
        result = await self.session.execute(
            select(TesClause).where(TesClause.topic_id == topic_id)
        )
        return list(result.scalars().all())

    async def get_clauses_by_topic_key(self, topic_key: str) -> list[TesClause]:
        result = await self.session.execute(
            select(TesClause)
            .join(Topic)
            .where(Topic.key == topic_key)
        )
        return list(result.scalars().all())

    async def get_unlinked_clauses(
        self, agreement_id: int
    ) -> list[TesClause]:
        """Клаузулы без topic_id — для ручной линковки."""
        result = await self.session.execute(
            select(TesClause).where(
                TesClause.agreement_id == agreement_id,
                TesClause.topic_id.is_(None),
            )
        )
        return list(result.scalars().all())

    def add_clause(self, clause: TesClause) -> None:
        self.session.add(clause)

    async def get_all_unions(self) -> list[Union]:
        result = await self.session.execute(select(Union))
        return list(result.scalars().all())

    async def get_all_agreements(
            self,
            current_only: bool = True,
            union_key: str | None = None,
            sector_fi: str | None = None,
    ) -> list[Agreement]:
        query = select(Agreement)
        if current_only:
            query = query.where(Agreement.is_current == True)
        if union_key:
            query = query.join(Union).where(Union.key == union_key)
        if sector_fi:
            query = query.where(Agreement.sector_fi.ilike(f"%{sector_fi}%"))
        result = await self.session.execute(query)
        return list(result.scalars().all())