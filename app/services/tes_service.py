import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Agreement, TesClause, Union
from app.parsing.tes import ParsedAgreement, ParsedTesClause
from app.repositories.tes import TesRepository
from app.repositories.topics import TopicRepository

logger = logging.getLogger(__name__)


class TesService:
    """
    Сохраняет распарсенные коллективные договоры (TES) в БД.

    Стратегия upsert:
    - Union: get_or_create по key
    - Agreement: идентифицируется по source_url
      если уже есть — помечает старый is_current=False, создаёт новый
    - TesClause: пересоздаются при каждом upsert agreement
    - topic_id проставляется через TopicRepository по topic_key из парсера
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TesRepository(session)
        self.topic_repo = TopicRepository(session)

    async def upsert(self, parsed: ParsedAgreement) -> dict:
        """
        Сохраняет или обновляет договор и все его клаузулы.
        Возвращает статистику: created/updated + counts.
        """
        union = await self._get_or_create_union(parsed.union_key)
        agreement, status = await self._upsert_agreement(parsed, union.id)
        clause_stats = await self._upsert_clauses(parsed.clauses, agreement.id)
        await self.session.commit()

        logger.info(
            "TES upsert done: %s %s — %d clauses (%d linked, %d unlinked)",
            parsed.name_fi, status,
            clause_stats["total"],
            clause_stats["linked"],
            clause_stats["unlinked"],
        )
        return {
            "agreement": parsed.name_fi,
            "status": status,
            **clause_stats,
        }

    # Union

    async def _get_or_create_union(self, union_key: str) -> Union:
        union = await self.repo.get_union_by_key(union_key)
        if union is None:
            union = Union(
                key=union_key,
                name_fi=union_key.upper(),
            )
            self.repo.add_union(union)
            await self.session.flush()
            logger.info("Created union: %s", union_key)
        return union

    # Agreement

    async def _upsert_agreement(
        self, parsed: ParsedAgreement, union_id: int
    ) -> tuple[Agreement, str]:
        existing = await self.repo.get_agreement_by_url(parsed.source_url)

        if existing is not None:
            existing.is_current = False
            status = "updated"
        else:
            status = "created"

        agreement = Agreement(
            union_id=union_id,
            name_fi=parsed.name_fi,
            valid_from=self._parse_date(parsed.valid_from),
            valid_until=self._parse_date(parsed.valid_until),
            source_url=parsed.source_url,
            source_type="pdf",
            is_current=True,
            is_universally_binding=parsed.is_universally_binding,
        )
        self.repo.add_agreement(agreement)
        await self.session.flush()  # получаем agreement.id
        return agreement, status

    # Clauses

    async def _upsert_clauses(
        self, clauses: list[ParsedTesClause], agreement_id: int
    ) -> dict:
        linked = unlinked = 0

        for clause in clauses:
            topic_id = None
            if clause.topic_key:
                topic = await self.topic_repo.get_by_key(clause.topic_key)
                if topic:
                    topic_id = topic.id
                else:
                    logger.warning(
                        "Topic not found for key '%s'", clause.topic_key
                    )

            self.repo.add_clause(TesClause(
                agreement_id=agreement_id,
                topic_id=topic_id,
                section_ref=clause.section_ref,
                text_fi=clause.text_fi,
                priority_over_law=False,
            ))

            if topic_id:
                linked += 1
            else:
                unlinked += 1

        return {
            "total": linked + unlinked,
            "linked": linked,
            "unlinked": unlinked,
        }


    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            return None