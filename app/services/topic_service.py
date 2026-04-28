import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Act, Chapter, Section, Topic, TopicSection
from app.application.seeds.topic_map import TOPICS, TopicSeed

logger = logging.getLogger(__name__)


class TopicService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def seed_topics(self) -> dict:
        """
        Загружает темы из topic_map.py в БД.
        Безопасно запускать повторно — upsert по key.
        """
        created = 0
        updated = 0
        skipped_refs = 0

        for topic_data in TOPICS:
            topic = await self._upsert_topic(topic_data)
            await self.session.flush()

            for ref in topic_data["section_refs"]:
                ok = await self._upsert_topic_section(topic, ref)
                if not ok:
                    skipped_refs += 1
                    logger.warning(
                        "Section not found: %s chp%d §%d — skipping",
                        ref["act"], ref["chapter"], ref["section"],
                    )

        await self.session.commit()
        logger.info("Topics seeded: %d topics, %d refs skipped", len(TOPICS), skipped_refs)
        return {"topics": len(TOPICS), "skipped_refs": skipped_refs}

    async def _upsert_topic(self, data: TopicSeed) -> Topic:
        result = await self.session.execute(
            select(Topic).where(Topic.key == data["key"])
        )
        topic = result.scalar_one_or_none()

        if topic is None:
            topic = Topic(
                key=data["key"],
                name_en=data["name_en"],
                name_ru=data["name_ru"],
                description=data["description"],
            )
            self.session.add(topic)
        else:
            topic.name_en = data["name_en"]
            topic.name_ru = data["name_ru"]
            topic.description = data["description"]

        return topic

    async def _upsert_topic_section(
        self, topic: Topic, ref: dict
    ) -> bool:
        # Находим секцию по act/chapter/section
        result = await self.session.execute(
            select(Section)
            .join(Chapter)
            .join(Act)
            .where(
                Act.key == ref["act"],
                Chapter.number == ref["chapter"],
                Section.number == ref["section"],
            )
        )
        section = result.scalar_one_or_none()

        if section is None:
            return False

        # Upsert TopicSection
        result = await self.session.execute(
            select(TopicSection).where(
                TopicSection.topic_id == topic.id,
                TopicSection.section_id == section.id,
            )
        )
        link = result.scalar_one_or_none()

        if link is None:
            self.session.add(TopicSection(
                topic_id=topic.id,
                section_id=section.id,
                relevance=ref["relevance"],
            ))
        else:
            link.relevance = ref["relevance"]

        return True