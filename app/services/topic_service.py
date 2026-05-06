import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Act, Chapter, Section, Topic, TopicSection
from app.application.seeds.topic_map import TOPICS, TopicSeed
from app.repositories.topics import TopicRepository

logger = logging.getLogger(__name__)


class TopicService:
    """
        Инициализирует темы и их связи с параграфами законов в БД.

        Читает конфигурацию из topic_map.py и выполняет upsert тем (Topic)
        и связей тема-параграф (TopicSection). Требует чтобы законы
        уже были распарсены через FinlexParser.
        """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TopicRepository(session)

    async def seed_topics(self) -> dict:
        """
        Загружает темы из topic_map.py в БД.
        Безопасно запускать повторно — upsert по key.
        """
        skipped_refs = 0

        for topic_data in TOPICS:
            topic = await self._upsert_topic(topic_data)
            await self.session.flush()  # нужен topic.id

            for ref in topic_data["section_refs"]:
                ok = await self._upsert_topic_section(topic, ref)
                if not ok:
                    skipped_refs += 1
                    logger.warning(
                        "Section not found: %s chp%d §%d — skipping",
                        ref["act"], ref["chapter"], ref["section"],
                    )

        await self.session.commit()

        return {
            "topics": len(TOPICS),
            "skipped_refs": skipped_refs,
        }


    async def _upsert_topic(self, data: TopicSeed) -> Topic:
        topic = await self.repo.get_by_key(data["key"])

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
        section = await self.repo.find_section(
            act=ref["act"],
            chapter=ref["chapter"],
            section=ref["section"],
        )

        if section is None:
            return False

        link = await self.repo.get_topic_section_link(
            topic_id=topic.id,
            section_id=section.id,
        )

        if link is None:
            self.session.add(
                TopicSection(
                    topic_id=topic.id,
                    section_id=section.id,
                    relevance=ref["relevance"],
                )
            )
        else:
            link.relevance = ref["relevance"]

        return True