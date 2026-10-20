import logging
import hashlib
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Agreement, TesClause, Union
from app.parsing.tes.pam import ParsedAgreement, ParsedTesClause
from app.parsing.topic_keywords import TOPIC_KEYWORDS, detect_topic
from app.repositories.tes import TesRepository
from app.repositories.topics import TopicRepository

logger = logging.getLogger(__name__)

def clause_text_hash(text: str) -> str:
    """Отпечаток текста клаузы для ручных переопределений топика."""
    return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()

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
        clause_stats = await self._upsert_clauses(parsed.clauses, agreement)
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
        self, clauses: list[ParsedTesClause], agreement: Agreement
    ) -> dict:
        linked = unlinked = overridden = 0
        overrides = await self.repo.get_topic_overrides(agreement.key)

        for clause in clauses:
            text_hash = clause_text_hash(clause.text_fi)
            if text_hash in overrides:
                # ручное закрепление важнее автодетекции (в т.ч. «топика нет»)
                topic_id = overrides[text_hash]
                overridden += 1
            else:
                topic_id = None
                if clause.topic_key:
                    topic = await self.topic_repo.get_by_key(clause.topic_key)
                    if topic:
                        topic_id = topic.id
                    else:
                        logger.warning(
                            "Topic not found for key '%s'", clause.topic_key
                        )

            self.repo.add_clause(
                TesClause(
                    agreement_id=agreement.id,
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
            "overridden": overridden,
        }

    async def upsert_clauses_for_agreement(
        self,
        agreement: Agreement,
        clauses: list,
    ) -> dict:
        """Сохраняет клаузулы для уже существующего agreement."""
        clause_stats = await self._upsert_clauses(clauses, agreement)
        logger.info(
            "Clauses saved for '%s': %d linked, %d unlinked",
            agreement.name_fi,
            clause_stats["linked"],
            clause_stats["unlinked"],
        )
        return clause_stats

    async def relink_topics(
        self, dry_run: bool = False, max_chars: int | None = None
    ) -> dict:
        """
        Пересчитывает topic_id для всех клауз.
        - ручные переопределения (agreement_key + md5 текста) главнее detect_topic;
        - dry_run=True: ничего не пишет, возвращает список изменений;
        - max_chars: смотреть только первые N символов (как при парсинге, 500).
        """
        rows = await self.repo.get_clauses_with_agreement_key()
        overrides = await self.repo.get_all_topic_overrides()
        topic_key_by_id = await self.repo.get_topic_key_map()
        topic_id_by_key = {key: id_ for id_, key in topic_key_by_id.items()}

        linked = unlinked = skipped = overridden = 0
        changes: list[dict] = []
        transitions: dict[str, int] = {}

        for clause, agreement_key in rows:
            override_key = (agreement_key, clause_text_hash(clause.text_fi))

            if override_key in overrides:
                new_topic_id = overrides[override_key]
                overridden += 1
            else:
                text = clause.text_fi[:max_chars] if max_chars else clause.text_fi
                topic_key = detect_topic(text)
                if topic_key is None:
                    new_topic_id = None
                else:
                    new_topic_id = topic_id_by_key.get(topic_key)
                    if new_topic_id is None:
                        skipped += 1  # ключ есть в словаре, но нет в таблице topics
                        continue

            if clause.topic_id == new_topic_id:
                skipped += 1
                continue

            old_key = topic_key_by_id.get(clause.topic_id)
            new_key = topic_key_by_id.get(new_topic_id)
            label = f"{old_key} -> {new_key}"
            transitions[label] = transitions.get(label, 0) + 1
            changes.append(
                {
                    "id": clause.id,
                    "agreement_key": agreement_key,
                    "section_ref": clause.section_ref,
                    "old_topic": old_key,
                    "new_topic": new_key,
                }
            )

            if new_topic_id is None:
                unlinked += 1
            else:
                linked += 1
            if not dry_run:
                clause.topic_id = new_topic_id

        result = {
            "dry_run": dry_run,
            "linked": linked,
            "unlinked": unlinked,
            "skipped": skipped,
            "overridden": overridden,
        }
        if dry_run:
            result["transitions"] = dict(
                sorted(transitions.items(), key=lambda kv: -kv[1])
            )
            result["changes"] = changes
            return result

        await self.session.commit()
        return result

    @staticmethod
    def _parse_date(date_str: str | None) -> date | None:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str)
        except ValueError:
            return None
