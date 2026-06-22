import logging
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Agreement, TesClause, Union
from app.parsing.tes.pam import ParsedAgreement, ParsedTesClause
from app.parsing.topic_keywords import TOPIC_KEYWORDS, detect_topic
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

    async def upsert(
        self,
        parsed: ParsedAgreement,
        sector_fi: str | None = None,
    ) -> dict:
        """
        Сохраняет или обновляет договор и все его клаузулы.
        Возвращает статистику: created/updated + counts.
        """
        union = await self._get_or_create_union(parsed.union_key)
        agreement, status = await self._upsert_agreement(
            parsed, union.id, sector_fi=sector_fi
        )
        clause_stats = await self._upsert_clauses(parsed.clauses, agreement.id)
        await self.session.commit()

        logger.info(
            "TES upsert done: %s %s — %d clauses (%d linked, %d unlinked)",
            parsed.name_fi,
            status,
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
        self,
        parsed: ParsedAgreement,
        union_id: int,
        sector_fi: str | None = None,
    ) -> tuple[Agreement, str]:
        existing_by_url = await self.repo.get_agreement_by_url(parsed.source_url)
        current = await self.repo.get_current_agreement(parsed.key)

        # Тот же URL и тот же хеш — ничего не изменилось
        if existing_by_url and existing_by_url.content_hash == parsed.content_hash:
            changed = False
            if existing_by_url.valid_from is None and parsed.valid_from:
                existing_by_url.valid_from = self._parse_date(parsed.valid_from)
                changed = True
            if existing_by_url.valid_until is None and parsed.valid_until:
                existing_by_url.valid_until = self._parse_date(parsed.valid_until)
                changed = True
            if existing_by_url.name_fi != parsed.name_fi and parsed.name_fi:
                existing_by_url.name_fi = parsed.name_fi
                changed = True
            if not existing_by_url.is_parsed:
                existing_by_url.is_parsed = True
                existing_by_url.parsed_at = datetime.now(timezone.utc)
                changed = True
            return existing_by_url, "updated" if changed else "skipped"

        elif existing_by_url:
            # тот же URL, hash изменился — обновляем существующий
            existing_by_url.content_hash = parsed.content_hash
            existing_by_url.is_parsed = True
            existing_by_url.parsed_at = datetime.now(timezone.utc)
            # удаляем старые клаузы перед добавлением новых
            await self.repo.delete_clauses_for_agreement(existing_by_url.id)
            return existing_by_url, "updated"

        # Новый URL, но есть актуальный договор с тем же ключом — вытесняем его
        elif current:
            current.is_current = False
            status = "updated"
        # Совсем новый договор
        else:
            status = "created"

        agreement = Agreement(
            key=parsed.key,
            union_id=union_id,
            name_fi=parsed.name_fi,
            valid_from=self._parse_date(parsed.valid_from),
            valid_until=self._parse_date(parsed.valid_until),
            source_url=parsed.source_url,
            source_type="pdf",
            is_current=True,
            is_universally_binding=parsed.is_universally_binding,
            sector_fi=sector_fi,
            sector_en=None,
            content_hash=parsed.content_hash,
        )

        self.repo.add_agreement(agreement)
        await self.session.flush()

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
                    logger.warning("Topic not found for key '%s'", clause.topic_key)

            self.repo.add_clause(
                TesClause(
                    agreement_id=agreement_id,
                    topic_id=topic_id,
                    section_ref=clause.section_ref,
                    text_fi=clause.text_fi,
                    priority_over_law=False,
                )
            )

            if topic_id:
                linked += 1
            else:
                unlinked += 1

        return {
            "total": linked + unlinked,
            "linked": linked,
            "unlinked": unlinked,
        }

    async def upsert_clauses_for_agreement(
        self,
        agreement: Agreement,
        clauses: list,
    ) -> dict:
        """Сохраняет клаузулы для уже существующего agreement."""
        clause_stats = await self._upsert_clauses(clauses, agreement.id)
        logger.info(
            "Clauses saved for '%s': %d linked, %d unlinked",
            agreement.name_fi,
            clause_stats["linked"],
            clause_stats["unlinked"],
        )
        return clause_stats

    async def relink_topics(self) -> dict:
        result = await self.session.execute(select(TesClause))
        clauses = result.scalars().all()

        linked = unlinked = skipped = 0
        for clause in clauses:
            topic_key = detect_topic(clause.text_fi)

            if topic_key is None:
                if clause.topic_id is not None:
                    clause.topic_id = None
                    unlinked += 1
                else:
                    skipped += 1
                continue

            topic = await self.topic_repo.get_by_key(topic_key)
            if topic is None:
                skipped += 1
                continue

            if clause.topic_id != topic.id:
                clause.topic_id = topic.id
                linked += 1
            else:
                skipped += 1

        await self.session.commit()
        return {"linked": linked, "unlinked": unlinked, "skipped": skipped}

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            return None
