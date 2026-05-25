import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from hashlib import sha256

from app.database.models import Interpretation
from app.parsing.topic_keywords import detect_topic
from app.parsing.tyosuojelu import ParsedInterpretation
from app.repositories.interpretations import InterpretationRepository
from app.repositories.topics import TopicRepository
from app.parsing.tehy import ParsedTehySection


logger = logging.getLogger(__name__)


class InterpretationService:
    """
    Сохраняет и обновляет интерпретации с tyosuojelu.fi в БД.

    Использует hash-based change detection: если content_hash не изменился,
    запись не перезаписывается. При изменении финского текста сбрасывает
    переводы (text_en, text_ru) — они будут пересчитаны TranslationService.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = InterpretationRepository(session)
        self.topic_repo = TopicRepository(session)

    async def upsert_all(self, parsed: list[ParsedInterpretation]) -> dict[str, int]:
        created = updated = skipped = 0

        for item in parsed:
            result = await self._upsert_one(item)
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
            else:
                skipped += 1

        await self.session.commit()
        logger.info(
            "Interpretations upsert done: %d created, %d updated, %d skipped",
            created,
            updated,
            skipped,
        )
        return {"created": created, "updated": updated, "skipped": skipped}

    async def _upsert_one(self, item: ParsedInterpretation) -> str:
        # Резолвим topic_id через TopicRepository
        topic = await self.topic_repo.get_by_key(item.topic_key)
        if topic is None:
            logger.warning("Topic not found for key '%s', skipping", item.topic_key)
            return "skipped"
        if not item.full_text_fi:
            logger.warning(
                "Empty text for topic '%s' (%s), skipping",
                item.topic_key,
                item.source_url,
            )
            return "skipped"

        existing = await self.repo.get_by_topic_and_source(topic.id, item.source)

        if existing is not None:
            if existing.content_hash == item.content_hash:
                return "skipped"
            existing.title_fi = item.title_fi
            existing.text_fi = item.full_text_fi
            existing.source_url = item.source_url
            existing.content_hash = item.content_hash
            existing.parsed_at = datetime.now(timezone.utc)
            # Сбрасываем переводы — текст изменился
            existing.text_en = None
            existing.translated_at = None
            existing.text_ru = None
            existing.translated_ru_at = None
            logger.debug("Updated interpretation for topic '%s'", item.topic_key)
            return "updated"

        self.repo.add(
            Interpretation(
                topic_id=topic.id,
                source=item.source,
                source_url=item.source_url,
                title_fi=item.title_fi,
                text_fi=item.full_text_fi,
                content_hash=item.content_hash,
                parsed_at=datetime.now(timezone.utc),
            )
        )
        logger.debug("Created interpretation for topic '%s'", item.topic_key)
        return "created"

    async def upsert_tehy(self, parsed: list[ParsedTehySection]) -> dict[str, int]:
        created = updated = skipped_no_topic = skipped_unchanged = 0

        for item in parsed:
            result = await self._upsert_tehy_one(item)
            if result == "created":
                created += 1
            elif result == "updated":
                updated += 1
            elif result == "skipped_unchanged":
                skipped_unchanged += 1
            else:
                skipped_no_topic += 1

        await self.session.commit()
        logger.info(
            "Tehy upsert done: %d created, %d updated, %d unchanged, %d no_topic",
            created, updated, skipped_unchanged, skipped_no_topic,
        )
        return {"created": created, "updated": updated,
                "skipped_unchanged": skipped_unchanged, "skipped_no_topic": skipped_no_topic}

    async def _upsert_tehy_one(self, item: "ParsedTehySection") -> str:
        topic = await self.topic_repo.get_by_key(item.topic_key)
        if topic is None:
            logger.warning("Tehy: topic not found for key '%s', skipping", item.topic_key)
            return "skipped"

        content_hash = sha256(item.text_fi.encode()).hexdigest()

        # Ключ дедупликации: topic_id + source_url (уникален для каждой секции)
        existing = await self.repo.get_by_topic_and_url(topic.id, item.source_url, item.title_fi)

        if existing is not None:
            if existing.content_hash == content_hash:
                return "skipped"
            existing.title_fi = item.title_fi
            existing.text_fi = item.text_fi
            existing.content_hash = content_hash
            existing.parsed_at = datetime.now(timezone.utc)
            existing.text_en = None
            existing.translated_at = None
            existing.text_ru = None
            existing.translated_ru_at = None
            return "updated"

        self.repo.add(Interpretation(
            topic_id=topic.id,
            source="tehy",
            source_url=item.source_url,
            title_fi=f"{item.agreement_name_fi}: {item.title_fi}",
            text_fi=item.text_fi,
            sector_fi=item.sector_fi,
            content_hash=content_hash,
            parsed_at=datetime.now(timezone.utc),
        ))
        return "created"

    async def relink_topics(self, source: str | None = None) -> dict:
        """
        Переназначает topic_id для всех интерпретаций по актуальному TOPIC_KEYWORDS.
        source: фильтр по источнику ("tehy", "tyosuojelu" и т.д.), None = все
        """
        stmt = select(Interpretation)
        if source:
            stmt = stmt.where(Interpretation.source == source)
        result = await self.session.execute(stmt)
        interpretations = result.scalars().all()

        topic_cache: dict[str, int | None] = {}  # topic_key -> topic.id | None
        linked = unlinked = skipped = 0

        for interp in interpretations:
            raw_title = interp.title_fi or ""
            title_for_detect = raw_title.split(": ", 1)[-1] if ": " in raw_title else raw_title

            title_topic = detect_topic(title_for_detect)
            text_topic = detect_topic((interp.text_fi or "")[:1000])

            if title_topic and text_topic:
                topic_key = title_topic  # приоритет заголовка
            else:
                topic_key = title_topic or text_topic

            if topic_key is None:
                if interp.topic_id is not None:
                    interp.topic_id = None
                    unlinked += 1
                else:
                    skipped += 1
                continue

            if topic_key not in topic_cache:
                topic = await self.topic_repo.get_by_key(topic_key)
                topic_cache[topic_key] = topic.id if topic else None

            topic_id = topic_cache[topic_key]
            if topic_id is None:
                skipped += 1
                continue

            if interp.topic_id != topic_id:
                interp.topic_id = topic_id
                linked += 1
            else:
                skipped += 1

        await self.session.commit()
        logger.info(
            "Interpretations relink done: %d linked, %d unlinked, %d skipped",
            linked, unlinked, skipped,
        )
        return {"linked": linked, "unlinked": unlinked, "skipped": skipped}