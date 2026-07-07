from sqlalchemy import select, update, delete, func
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
        result = await self.session.execute(select(Union).where(Union.key == key))
        return result.scalar_one_or_none()

    async def get_all_unions(self) -> list[Union] | None:
        result = await self.session.execute(select(Union))
        return list(result.scalars().all())

    def add_union(self, union: Union) -> None:
        self.session.add(union)

    # Agreement
    async def get_current_agreement(self, key: str) -> Agreement | None:
        result = await self.session.execute(
            select(Agreement)
            .where(Agreement.key == key)
            .where(Agreement.is_current == True)
        )
        return result.scalar_one_or_none()

    async def get_agreement_by_url(self, source_url: str) -> Agreement | None:
        result = await self.session.execute(
            select(Agreement)
            .where(Agreement.source_url == source_url)
            .order_by(Agreement.id.desc())
            .limit(1)
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

    async def get_agreement_with_clauses(self, agreement_id: int) -> Agreement | None:
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

    async def get_clauses_by_topic_key(
        self,
        topic_key: str,
        union_key: str | None = None,
        sector_fi: str | None = None,
        agreement_key: str | None = None,
    ) -> list[TesClause]:

        query = (
            select(TesClause)
            .options(
            selectinload(TesClause.topic),
            selectinload(TesClause.agreement).selectinload(Agreement.union),
        )
            .join(TesClause.topic)
            .join(TesClause.agreement)
            .join(Agreement.union)
            .where(Topic.key == topic_key)
        )

        if union_key:
            query = query.where(Union.key == union_key)

        if sector_fi:
            query = query.where(Agreement.sector_fi.ilike(f"%{sector_fi}%"))

        if agreement_key:
            query = query.where(Agreement.key == agreement_key)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_unlinked_clauses(self, agreement_id: int) -> list[TesClause]:
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

    async def get_all_agreements(
        self,
        current_only: bool = True,
        union_key: str | None = None,
        sector_fi: str | None = None,
        is_parsed: bool | None = None,
    ) -> list[Agreement]:
        query = select(Agreement)
        if current_only:
            query = query.where(Agreement.is_current == True)
        if union_key:
            query = query.join(Agreement.union).where(Union.key == union_key)
        if sector_fi:
            query = query.where(Agreement.sector_fi.ilike(f"%{sector_fi}%"))
        if is_parsed is not None:
            query = query.where(Agreement.is_parsed == is_parsed)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_agreement_by_key(self, key: str) -> Agreement | None:
        result = await self.session.execute(
            select(Agreement).where(Agreement.key == key)
        )
        return result.scalar_one_or_none()

    async def get_agreement_by_key_with_union(self, key: str) -> Agreement | None:
        result = await self.session.execute(
            select(Agreement)
            .options(selectinload(Agreement.union))
            .where(Agreement.key == key)
        )
        return result.scalar_one_or_none()

    async def get_agreement_with_clauses_by_key(self, key: str) -> Agreement | None:
        result = await self.session.execute(
            select(Agreement)
            .options(selectinload(Agreement.clauses))
            .where(Agreement.key == key)
        )
        return result.scalar_one_or_none()

    async def get_clauses_by_union(self, union_key: str) -> list[TesClause]:
        result = await self.session.execute(
            select(TesClause).join(Agreement).join(Union).where(Union.key == union_key)
        )
        clauses = list(result.scalars().all())
        return clauses

    async def get_untranslated_tes_by_key(
        self, agreement_key: str, lang: str
    ) -> list[TesClause]:
        from app.database.models import Agreement

        null_col = TesClause.text_en if lang == "en" else TesClause.text_ru
        result = await self.session.execute(
            select(TesClause)
            .join(Agreement)
            .where(Agreement.key == agreement_key)
            .where(null_col.is_(None))
        )
        return list(result.scalars().all())

    async def get_untranslated_tes(self, lang: str) -> list[TesClause]:

        null_col = TesClause.text_en if lang == "en" else TesClause.text_ru
        result = await self.session.execute(select(TesClause).where(null_col.is_(None)))
        return list(result.scalars().all())

    async def get_untranslated_clauses_by_union(
        self,
        union_key: str,
        lang: str,
    ) -> list[TesClause]:
        null_col = TesClause.text_en if lang == "en" else TesClause.text_ru

        result = await self.session.execute(
            select(TesClause)
            .join(Agreement, TesClause.agreement_id == Agreement.id)
            .join(Union, Agreement.union_id == Union.id)
            .where(Union.key == union_key)
            .where(null_col.is_(None))
        )
        return list(result.scalars().all())

    async def get_untranslated_agreements_by_union(
        self,
        union_key: str,
        lang: str,
    ) -> list[tuple[Agreement, int]]:
        null_col = TesClause.text_en if lang == "en" else TesClause.text_ru

        result = await self.session.execute(
            select(
                Agreement,
                func.count(TesClause.id).label('untranslated_count')
            )
            .join(TesClause, TesClause.agreement_id == Agreement.id)
            .join(Union, Agreement.union_id == Union.id)
            .where(Union.key == union_key)
            .where(null_col.is_(None))
            .group_by(Agreement.id)
        )
        return list(result.all())


    async def get_distinct_untranslated_sectors(self) -> list[str]:
        """Уникальные sector_fi где sector_en IS NULL."""
        result = await self.session.execute(
            select(Agreement.sector_fi)
            .where(Agreement.sector_fi.is_not(None))
            .where(Agreement.sector_en.is_(None))
            .distinct()
        )
        return [row[0] for row in result.all()]

    async def set_sector_en(self, sector_fi: str, sector_en: str) -> None:
        """Заполняет sector_en для всех agreements с данным sector_fi."""
        await self.session.execute(
            update(Agreement)
            .where(Agreement.sector_fi == sector_fi)
            .values(sector_en=sector_en)
        )

    async def delete_clauses_for_agreement(self, agreement_id: int) -> None:
        await self.session.execute(delete(TesClause).where(
            TesClause.agreement_id == agreement_id
        ))

