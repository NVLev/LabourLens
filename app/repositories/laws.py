from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Act, Chapter, Section


class LawRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Act

    async def get_all_acts(self) -> list[Act]:
        result = await self.session.execute(select(Act))
        return list(result.scalars().all())

    async def get_act_by_key(self, key: str) -> Act | None:
        result = await self.session.execute(
            select(Act)
            .options(selectinload(Act.chapters).selectinload(Chapter.sections))
            .where(Act.key == key)
        )
        return result.scalar_one_or_none()

    async def get_act_by_key_plain(self, key: str) -> Act | None:
        """Без eager loading — для сервиса upsert."""
        result = await self.session.execute(select(Act).where(Act.key == key))
        return result.scalar_one_or_none()

    # Chapter

    async def get_chapter(self, act_key: str, chapter_number: int) -> Chapter | None:
        result = await self.session.execute(
            select(Chapter)
            .join(Act)
            .options(selectinload(Chapter.sections))
            .where(
                Act.key == act_key,
                Chapter.number == chapter_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_chapter_plain(
        self, act_id: int, chapter_number: int
    ) -> Chapter | None:
        """Без eager loading — для сервиса upsert."""
        result = await self.session.execute(
            select(Chapter).where(
                Chapter.act_id == act_id,
                Chapter.number == chapter_number,
            )
        )
        return result.scalar_one_or_none()

    # Section

    async def get_section(
        self,
        act_key: str,
        chapter_number: int,
        section_number: int,
    ) -> Section | None:
        result = await self.session.execute(
            select(Section)
            .join(Chapter)
            .join(Act)
            .options(selectinload(Section.paragraphs))
            .where(
                Act.key == act_key,
                Chapter.number == chapter_number,
                Section.number == section_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_section_plain(
        self, act_id: int, chapter_id: int, section_number: int
    ) -> Section | None:
        """Без eager loading — для сервиса upsert."""
        result = await self.session.execute(
            select(Section).where(
                Section.act_id == act_id,
                Section.chapter_id == chapter_id,
                Section.number == section_number,
            )
        )
        return result.scalar_one_or_none()

    async def find_section(
            self,
            act_key: str,
            chapter_number: int,
            section_number: int,
    ) -> Section | None:
        """
        Находит параграф по ключу закона, номеру главы и номеру параграфа.
        Без eager loading — используется в seed-сервисах для получения section.id.
        """
        result = await self.session.execute(
            select(Section)
            .join(Chapter)
            .join(Act)
            .where(
                Act.key == act_key,
                Chapter.number == chapter_number,
                Section.number == section_number,
            )
        )
        return result.scalar_one_or_none()

    async def get_sections_by_topic(self, topic_key: str) -> list[Section]:
        """Все параграфы привязанные к теме — понадобится для situation_resolver."""
        from app.database.models import Topic, TopicSection

        result = await self.session.execute(
            select(Section)
            .join(TopicSection)
            .join(Topic)
            .options(selectinload(Section.paragraphs))
            .where(Topic.key == topic_key)
            .order_by(TopicSection.relevance.desc())
        )
        return list(result.scalars().all())
