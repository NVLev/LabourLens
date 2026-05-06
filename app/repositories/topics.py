from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Act, Chapter, Section, Topic, TopicSection


class TopicRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Получить список тем
    async def get_all(self) -> list[Topic]:

        result = await self.session.execute(select(Topic))
        return list(result.scalars().all())

    # Получить тему с секциями
    async def get_with_sections(self, key: str) -> Topic | None:
        result = await self.session.execute(
            select(Topic)
            .options(
                selectinload(Topic.section_links)
                .selectinload(TopicSection.section)
                .selectinload(Section.paragraphs)
            )
            .where(Topic.key == key)
        )
        return result.scalar_one_or_none()

    # Получить секцию по ref.
    async def find_section(
        self, act: str, chapter: int, section: int
    ) -> Section | None:
        result = await self.session.execute(
            select(Section)
            .join(Chapter)
            .join(Act)
            .where(
                Act.key == act,
                Chapter.number == chapter,
                Section.number == section,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> Topic | None:
        result = await self.session.execute(select(Topic).where(Topic.key == key))
        return result.scalar_one_or_none()

    async def get_topic_section_link(
        self, topic_id: int, section_id: int
    ) -> TopicSection | None:
        result = await self.session.execute(
            select(TopicSection).where(
                TopicSection.topic_id == topic_id,
                TopicSection.section_id == section_id,
            )
        )
        return result.scalar_one_or_none()
