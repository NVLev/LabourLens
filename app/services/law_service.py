import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Act, Chapter, Section, SectionParagraph
from app.parsing.finlex import ParsedAct, ParsedChapter, ParsedSection
from app.repositories.laws import LawRepository

logger = logging.getLogger(__name__)


class LawService:
    """
    Принимает ParsedAct от парсера и делает upsert в БД.
    Безопасно запускать повторно — обновляет только изменившиеся параграфы.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LawRepository(session)

    # Публичный метод

    async def upsert_act(self, parsed: ParsedAct) -> Act:
        """Основной метод — upsert закона целиком."""
        act = await self._upsert_act(parsed)
        await self.session.flush()  # получаем act.id до работы с главами

        for parsed_chapter in parsed.chapters:
            chapter = await self._upsert_chapter(parsed_chapter, act.id)
            await self.session.flush()

            for parsed_section in parsed_chapter.sections:
                await self._upsert_section(parsed_section, act.id, chapter.id)

        act.last_parsed_at = datetime.now(timezone.utc)
        await self.session.commit()

        logger.info(
            "Upserted act %s: %d chapters, %d sections",
            parsed.key,
            len(parsed.chapters),
            sum(len(ch.sections) for ch in parsed.chapters),
        )
        return act

    # Act

    async def _upsert_act(self, parsed: ParsedAct) -> Act:
        act = await self.repo.get_act_by_key_plain(parsed.key)

        if act is None:
            act = Act(
                key=parsed.key,
                name_fi=parsed.name_fi,
                code=parsed.code,
                url=parsed.url,
            )
            self.session.add(act)
            logger.debug("Created act: %s", parsed.key)
        else:
            # Обновляем мета — название могло измениться
            act.name_fi = parsed.name_fi
            act.url = parsed.url
            logger.debug("Updated act: %s", parsed.key)

        # version_date из parsed если передана
        if parsed.version_date:
            act.version_date = parsed.version_date

        return act

    # Chapter

    async def _upsert_chapter(self, parsed: ParsedChapter, act_id: int) -> Chapter:
        chapter = await self.repo.get_chapter_plain(act_id, parsed.number)
        if chapter is None:
            chapter = Chapter(
                act_id=act_id,
                number=parsed.number,
                title_fi=parsed.title_fi,
            )
            self.session.add(chapter)
            logger.debug("Created chapter %d", parsed.number)
        else:
            chapter.title_fi = parsed.title_fi

        return chapter

    # Section
    async def _upsert_section(
        self,
        parsed: ParsedSection,
        act_id: int,
        chapter_id: int,
    ) -> Section:
        section = await self.repo.get_section_plain(act_id, chapter_id, parsed.number)
        if section is None:
            section = Section(
                act_id=act_id,
                chapter_id=chapter_id,
                number=parsed.number,
                title_fi=parsed.title_fi,
                anchor=parsed.anchor,
                url=parsed.url,
                content_hash=parsed.content_hash,
            )
            self.session.add(section)
            await self.session.flush()  # нужен section.id для параграфов
            await self._create_paragraphs(parsed, section.id)
            logger.debug("Created section %d §%d", chapter_id, parsed.number)

        elif section.content_hash is None or parsed.content_hash != section.content_hash:
            # Текст изменился — обновляем секцию и перезаписываем параграфы
            section.title_fi = parsed.title_fi
            section.anchor = parsed.anchor
            section.url = parsed.url
            section.content_hash = parsed.content_hash
            await self._replace_paragraphs(parsed, section.id)
            logger.info(
                "Updated section §%d (hash changed)", parsed.number
            )
        else:
            logger.debug("Section §%d unchanged, skipping", parsed.number)

        return section

    # Paragraphs

    async def _create_paragraphs(
        self, parsed: ParsedSection, section_id: int
    ) -> None:
        for p in parsed.paragraphs:
            self.session.add(SectionParagraph(
                section_id=section_id,
                order_index=p.order_index,
                text_fi=p.text_fi,
            ))

    async def _replace_paragraphs(
        self, parsed: ParsedSection, section_id: int
    ) -> None:
        """Удаляем старые пункты и создаём новые — проще чем diff."""
        result = await self.session.execute(
            select(SectionParagraph).where(
                SectionParagraph.section_id == section_id
            )
        )
        for old in result.scalars().all():
            await self.session.delete(old)

        await self.session.flush()
        await self._create_paragraphs(parsed, section_id)