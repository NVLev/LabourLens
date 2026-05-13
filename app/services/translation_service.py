import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Act, Chapter, Interpretation, Section, SectionParagraph, TesClause
from app.translation.nllb import MAX_CHUNK_CHARS, translate_batch_fi_en, translate_fi_en

logger = logging.getLogger(__name__)

BATCH_SIZE = 8


class TranslationService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Публичные методы

    async def translate_en(self, act_key: str | None = None) -> dict:
        """NLLB-600 fi→en. act_key=None — все законы."""
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
        """NLLB-600 fi→ru. act_key=None — все законы."""
        paragraphs = await self._get_untranslated(act_key, lang="ru")
        logger.info(
            "RU translation: %d paragraphs to translate%s",
            len(paragraphs),
            f" for {act_key}" if act_key else "",
        )
        translated = await self._translate_ru_paragraphs(paragraphs)
        await self.session.commit()
        return self._result(act_key, translated, len(paragraphs))

    async def _translate_ru_paragraphs(self, paragraphs: list[SectionParagraph]) -> int:
        from app.translation.nllb import translate_batch_fi_ru

        translated_count = 0
        short = [p for p in paragraphs if len(p.text_fi) <= MAX_CHUNK_CHARS]
        long_ = [p for p in paragraphs if len(p.text_fi) > MAX_CHUNK_CHARS]

        for i in range(0, len(short), BATCH_SIZE):
            batch = short[i : i + BATCH_SIZE]
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
                from app.translation.nllb import translate_fi_ru

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
            SectionParagraph.text_en if lang == "en" else SectionParagraph.text_ru
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

    async def _translate_en_paragraphs(self, paragraphs: list[SectionParagraph]) -> int:
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
                logger.error("NLLB batch failed: %s", e)
            await asyncio.sleep(0.05)

        # По одному для длинных — с разбивкой на чанки
        for paragraph in long_:
            try:
                translation = translate_fi_en(paragraph.text_fi)
                paragraph.text_en = translation
                paragraph.translated_at = datetime.now(timezone.utc)
                translated_count += 1
            except Exception as e:
                logger.error("NLLB failed for paragraph %d: %s", paragraph.id, e)

        return translated_count

    async def translate_interpretations_en(self) -> dict:
        """NLLB-600 fi→en для всех интерпретаций."""
        interpretations = await self._get_untranslated_interpretations(lang="en")
        logger.info(
            "EN translation: %d interpretations to translate", len(interpretations)
        )
        translated = await self._translate_interpretations(interpretations, lang="en")
        await self.session.commit()
        return {"translated": translated, "skipped": len(interpretations) - translated}

    async def translate_interpretations_ru(self) -> dict:
        """NLLB-600 fi→ru для всех интерпретаций."""
        interpretations = await self._get_untranslated_interpretations(lang="ru")
        logger.info(
            "RU translation: %d interpretations to translate", len(interpretations)
        )
        translated = await self._translate_interpretations(interpretations, lang="ru")
        await self.session.commit()
        return {"translated": translated, "skipped": len(interpretations) - translated}

    async def _get_untranslated_interpretations(
        self, lang: str
    ) -> list[Interpretation]:
        null_col = Interpretation.text_en if lang == "en" else Interpretation.text_ru
        result = await self.session.execute(
            select(Interpretation).where(null_col.is_(None))
        )
        return list(result.scalars().all())

    async def _translate_interpretations(
        self, interpretations: list[Interpretation], lang: str
    ) -> int:
        from app.translation.nllb import translate_fi_en, translate_fi_ru

        translate_fn = translate_fi_en if lang == "en" else translate_fi_ru
        now_field = "translated_at" if lang == "en" else "translated_ru_at"
        text_field = "text_en" if lang == "en" else "text_ru"

        translated_count = 0
        for interp in interpretations:
            try:
                translation = translate_fn(interp.text_fi)
                setattr(interp, text_field, translation)
                setattr(interp, now_field, datetime.now(timezone.utc))
                translated_count += 1
            except Exception as e:
                logger.error(
                    "Translation failed for interpretation %d: %s", interp.id, e
                )

        return translated_count

    async def translate_tes_en(self) -> dict:
        """NLLB fi→en для всех TesClause."""
        clauses = await self._get_untranslated_tes(lang="en")
        logger.info("EN translation: %d TES clauses to translate", len(clauses))
        translated = await self._translate_tes_clauses(clauses, lang="en")
        await self.session.commit()
        return {"translated": translated, "skipped": len(clauses) - translated}

    async def translate_tes_ru(self) -> dict:
        """NLLB fi→ru для всех TesClause."""
        clauses = await self._get_untranslated_tes(lang="ru")
        logger.info("RU translation: %d TES clauses to translate", len(clauses))
        translated = await self._translate_tes_clauses(clauses, lang="ru")
        await self.session.commit()
        return {"translated": translated, "skipped": len(clauses) - translated}

    async def _get_untranslated_tes(self, lang: str) -> list[TesClause]:
        from app.database.models import TesClause
        null_col = TesClause.text_en if lang == "en" else TesClause.text_ru
        result = await self.session.execute(
            select(TesClause).where(null_col.is_(None))
        )
        return list(result.scalars().all())

    async def _translate_tes_clauses(
            self, clauses: list[TesClause], lang: str
    ) -> int:
        from app.translation.nllb import translate_fi_en, translate_fi_ru
        translate_fn = translate_fi_en if lang == "en" else translate_fi_ru
        text_field = "text_en" if lang == "en" else "text_ru"
        translated_count = 0

        for clause in clauses:
            try:
                setattr(clause, text_field, translate_fn(clause.text_fi))
                translated_count += 1
            except Exception as e:
                logger.error("TES translation failed for clause %d: %s", clause.id, e)

        return translated_count

    async def translate_tes_en_by_key(self, agreement_key: str) -> dict:
        clauses = await self._get_untranslated_tes_by_key(agreement_key, lang="en")
        logger.info("EN translation: %d TES clauses for '%s'", len(clauses), agreement_key)
        translated = await self._translate_tes_clauses(clauses, lang="en")
        await self.session.commit()
        return {"agreement": agreement_key, "translated": translated, "skipped": len(clauses) - translated}

    async def translate_tes_ru_by_key(self, agreement_key: str) -> dict:
        clauses = await self._get_untranslated_tes_by_key(agreement_key, lang="ru")
        logger.info("RU translation: %d TES clauses for '%s'", len(clauses), agreement_key)
        translated = await self._translate_tes_clauses(clauses, lang="ru")
        await self.session.commit()
        return {"agreement": agreement_key, "translated": translated, "skipped": len(clauses) - translated}

    async def _get_untranslated_tes_by_key(self, agreement_key: str, lang: str) -> list[TesClause]:
        from app.database.models import Agreement
        null_col = TesClause.text_en if lang == "en" else TesClause.text_ru
        result = await self.session.execute(
            select(TesClause)
            .join(Agreement)
            .where(Agreement.key == agreement_key)
            .where(null_col.is_(None))
        )
        return list(result.scalars().all())

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
