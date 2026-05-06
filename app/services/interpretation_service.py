import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Interpretation
from app.parsing.tyosuojelu import ParsedInterpretation
from app.repositories.interpretations import InterpretationRepository
from app.repositories.topics import TopicRepository

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
