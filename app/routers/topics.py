from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
from app.repositories.interpretations import InterpretationRepository
from app.repositories.topics import TopicRepository
from app.services.topic_service import TopicService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/seed", summary="Seed topics and link them to law sections")
async def seed_topics(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Загружает темы из topic_map.py в базу данных.

    Что делает:
    - создаёт или обновляет Topic по key
    - связывает Topic с Section через TopicSection
    - пропускает ссылки на несуществующие параграфы

    Можно запускать повторно (idempotent).
    """
    service = TopicService(session)
    return await service.seed_topics()


@router.get("/", summary="List all topics")
async def list_topics(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Возвращает список всех тем.

    Используется для:
    - UI (меню тем)
    - Telegram-бота (кнопки)
    """
    repo = TopicRepository(session)
    topics = await repo.get_all()

    return [
        {
            "id": t.id,
            "key": t.key,
            "name_en": t.name_en,
            "name_ru": t.name_ru,
        }
        for t in topics
    ]


@router.get("/{key}", summary="Get topic with related law sections and interpretations")
async def get_topic(
    key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    topic_repo = TopicRepository(session)
    interp_repo = InterpretationRepository(session)

    topic = await topic_repo.get_with_sections(key)
    if not topic:
        raise HTTPException(404, "Topic not found")

    links = sorted(
        topic.section_links,
        key=lambda x: x.relevance,
        reverse=True,
    )

    interpretations = await interp_repo.get_by_topic_key(key)

    return {
        "topic": {
            "key": topic.key,
            "name_en": topic.name_en,
            "name_ru": topic.name_ru,
            "description": topic.description,
        },
        "law_sections": [
            {
                "section_id": link.section.id,
                "relevance": link.relevance,
                "title_fi": link.section.title_fi,
                "paragraphs": [
                    {
                        "fi": p.text_fi,
                        "en": p.text_en,
                        "ru": p.text_ru,
                    }
                    for p in link.section.paragraphs
                ],
            }
            for link in links
        ],
        "interpretations": [
            {
                "source": i.source,
                "title_fi": i.title_fi,
                "text_fi": i.text_fi,
                "text_en": i.text_en,
                "text_ru": i.text_ru,
            }
            for i in interpretations
        ],
    }
