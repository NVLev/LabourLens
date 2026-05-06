import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
from app.parsing.finlex import ACTS_CONFIG, FinlexParser
from app.parsing.tyosuojelu import TYOSUOJELU_PAGES, TyosuojeluParser
from app.services.interpretation_service import InterpretationService
from app.services.law_service import LawService
from app.services.topic_service import TopicService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parse", tags=["parse"])


@router.post("/finlex", summary="Parse all acts from Finlex Open Data API")
async def parse_finlex(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Запускает парсинг всех законов из ACTS_CONFIG,
    сохраняет в БД через upsert.
    Безопасно запускать повторно.
    """
    parser = FinlexParser()
    service = LawService(session)
    results = []

    for act_key in ACTS_CONFIG:
        try:
            parsed = await parser.parse_act(act_key)
            act = await service.upsert_act(parsed)
            results.append(
                {
                    "act": act_key,
                    "status": "ok",
                    "chapters": len(parsed.chapters),
                    "sections": sum(len(ch.sections) for ch in parsed.chapters),
                }
            )
        except Exception as e:
            logger.error("Failed to parse %s: %s", act_key, e)
            results.append(
                {
                    "act": act_key,
                    "status": "error",
                    "detail": str(e),
                }
            )

    return {"parsed": results}


@router.post("/finlex/{act_key}", summary="Parse single act")
async def parse_finlex_act(
    act_key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Парсит один конкретный закон по ключу."""
    if act_key not in ACTS_CONFIG:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown act key: {act_key}. "
            f"Available: {list(ACTS_CONFIG.keys())}",
        )

    parser = FinlexParser()
    service = LawService(session)

    parsed = await parser.parse_act(act_key)
    act = await service.upsert_act(parsed)

    return {
        "act": act_key,
        "status": "ok",
        "chapters": len(parsed.chapters),
        "sections": sum(len(ch.sections) for ch in parsed.chapters),
        "version_date": str(act.version_date) if act.version_date else None,
    }


@router.post("/topics/seed", summary="Load topics from topic_map into DB")
async def seed_topics(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Загружает темы и их связи с параграфами из topic_map.py.
    Требует чтобы законы уже были распарсены.
    Безопасно запускать повторно.
    """
    service = TopicService(session)
    result = await service.seed_topics()
    return result


@router.post("/tyosuojelu", summary="Parse all Tyosuojelu pages")
async def parse_tyosuojelu(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Парсит все страницы tyosuojelu.fi из TYOSUOJELU_PAGES,
    сохраняет интерпретации в БД через upsert.
    Безопасно запускать повторно.
    """
    parser = TyosuojeluParser()
    service = InterpretationService(session)

    parsed = await parser.parse_all()
    stats = await service.upsert_all(parsed)

    return {
        "pages_fetched": len(parsed),
        **stats,
    }


@router.post("/tyosuojelu/{topic_key}", summary="Parse single Tyosuojelu page")
async def parse_tyosuojelu_topic(
    topic_key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Парсит одну страницу по topic_key."""
    if topic_key not in TYOSUOJELU_PAGES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown topic key: {topic_key}. "
            f"Available: {list(TYOSUOJELU_PAGES.keys())}",
        )
    parser = TyosuojeluParser()
    service = InterpretationService(session)

    parsed = await parser.parse_page(topic_key, TYOSUOJELU_PAGES[topic_key])
    stats = await service.upsert_all([parsed])

    return {
        "topic": topic_key,
        "title_fi": parsed.title_fi,
        "text_length": len(parsed.full_text_fi),
        "finlex_refs": len(parsed.finlex_refs),
        **stats,
    }
