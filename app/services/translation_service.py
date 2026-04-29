import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Act, Chapter, Section, SectionParagraph
from app.translation.helsinki_nlp import translate_fi_en, MAX_CHUNK_CHARS, translate_batch_fi_en

logger = logging.getLogger(__name__)

BATCH_SIZE = 8  # Helsinki-NLP батч


class TranslationService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Публичные методы

    async def translate_en(self, act_key: str | None = None) -> dict:
        """Helsinki-NLP fi→en. act_key=None — все законы."""
        paragraphs = await self._get_untranslated(act_key, lang="en")
        logger.info(
            "EN translation: %d paragraphs to translate%s",
            len(paragraphs),
            f" for {act_key}" if act_key else "",
        )
        translated = await self._translate_en_paragraphs(paragraphs)
        await self.session.commit()
        return self._result(act_key, translated, len(paragraphs))

    async def translate_ru(self, act_key: str | None = None) -> dict:
            """Helsinki-NLP fi→ru. act_key=None — все законы."""
            paragraphs = await self._get_untranslated(act_key, lang="ru")
            logger.info(
                "RU translation: %d paragraphs to translate%s",
                len(paragraphs),
                f" for {act_key}" if act_key else "",
            )
            translated = await self._translate_ru_paragraphs(paragraphs)
            await self.session.commit()
            return self._result(act_key, translated, len(paragraphs))

    async def _translate_ru_paragraphs(
            self, paragraphs: list[SectionParagraph]
    ) -> int:
        from app.translation.helsinki_nlp import translate_batch_fi_ru

        translated_count = 0
        short = [p for p in paragraphs if len(p.text_fi) <= MAX_CHUNK_CHARS]
        long_ = [p for p in paragraphs if len(p.text_fi) > MAX_CHUNK_CHARS]

        for i in range(0, len(short), BATCH_SIZE):
            batch = short[i: i + BATCH_SIZE]
            try:
                translations = translate_batch_fi_ru([p.text_fi for p in batch])
                now = datetime.now(timezone.utc)
                for paragraph, translation in zip(batch, translations):
                    paragraph.text_ru = translation
                    paragraph.translated_ru_at = now
                    translated_count += 1
            except Exception as e:
                logger.error("fi→ru batch failed: %s", e)
            await asyncio.sleep(0.05)

        for paragraph in long_:
            try:
                from app.translation.helsinki_nlp import translate_fi_ru
                paragraph.text_ru = translate_fi_ru(paragraph.text_fi)
                paragraph.translated_ru_at = datetime.now(timezone.utc)
                translated_count += 1
            except Exception as e:
                logger.error("fi→ru failed for paragraph %d: %s", paragraph.id, e)

        return translated_count

    # Получение непереведённых

    async def _get_untranslated(
        self,
        act_key: str | None,
        lang: str,  # "en" | "ru"
    ) -> list[SectionParagraph]:
        """Параграфы где text_en или text_ru IS NULL."""
        null_col = (
            SectionParagraph.text_en
            if lang == "en"
            else SectionParagraph.text_ru
        )

        query = (
            select(SectionParagraph)
            .join(Section)
            .join(Chapter)
            .where(null_col.is_(None))
        )

        if act_key:
            query = query.join(Act).where(Act.key == act_key)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # Helsinki-NLP fi→en

    async def _translate_en_paragraphs(
        self, paragraphs: list[SectionParagraph]
    ) -> int:
        translated_count = 0

        short = [p for p in paragraphs if len(p.text_fi) <= MAX_CHUNK_CHARS]
        long_ = [p for p in paragraphs if len(p.text_fi) > MAX_CHUNK_CHARS]

        # Батч для коротких
        for i in range(0, len(short), BATCH_SIZE):
            batch = short[i : i + BATCH_SIZE]
            try:
                translations = translate_batch_fi_en([p.text_fi for p in batch])
                now = datetime.now(timezone.utc)
                for paragraph, translation in zip(batch, translations):
                    paragraph.text_en = translation
                    paragraph.translated_at = now
                    translated_count += 1
            except Exception as e:
                logger.error("Helsinki-NLP batch failed: %s", e)
            await asyncio.sleep(0.05)

        # По одному для длинных — с разбивкой на чанки
        for paragraph in long_:
            try:
                translation = translate_fi_en(paragraph.text_fi)
                paragraph.text_en = translation
                paragraph.translated_at = datetime.now(timezone.utc)
                translated_count += 1
            except Exception as e:
                logger.error("Helsinki-NLP failed for paragraph %d: %s", paragraph.id, e)

        return translated_count

    def _result(
        self,
        act_key: str | None,
        translated: int,
        total: int,
    ) -> dict:
        result = {
            "act": act_key or "all",
            "translated": translated,
            "skipped": total - translated,
        }

        return result