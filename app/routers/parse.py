import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
from app.parsing.finlex import ACTS_CONFIG, FinlexParser
from app.parsing.tyosuojelu import TYOSUOJELU_PAGES, TyosuojeluParser
from app.repositories.tes import TesRepository
from app.services.interpretation_service import InterpretationService
from app.services.law_service import LawService

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

@router.post("/unions/seed", summary="Seed union portals")
async def seed_union_portals(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Создаёт записи UnionPortal для всех поддерживаемых профсоюзов."""
    from app.services.union_seed_service import seed_unions_and_portals
    return await seed_unions_and_portals(session)

from app.services.tes_service import TesService
from app.services.tes_discovery_service import TesDiscoveryService


@router.post("/tes/discover/{union_key}", summary="Discover TES catalog for a union")
async def discover_tes(
    union_key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Сканирует каталог профсоюза, находит все TES,
    сохраняет в БД с ключами. Не парсит PDF.
    Безопасно запускать повторно.
    Доступные ключи: pam, rakennusliitto.
    """
    service = TesDiscoveryService(session)
    return await service.discover(union_key)

@router.get("/tes/agreements", summary="List discovered TES agreements with parse status")
async def list_tes_agreements(
    union_key: str | None = None,
    is_parsed: bool | None = None,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Список договоров с ключами и статусом парсинга.
    Используется для выбора что парсить через POST /parse/tes/{key}.
    is_parsed=false — показать ещё не распарсенные.
    """
    repo = TesRepository(session)
    agreements = await repo.get_all_agreements(
        current_only=True,
        union_key=union_key,
        is_parsed=is_parsed,
    )
    return [
        {
            "key": a.key,
            "name_fi": a.name_fi,
            "sector_fi": a.sector_fi,
            "is_parsed": a.is_parsed,
            "parsed_at": str(a.parsed_at) if a.parsed_at else None,
            "source_url": a.source_url,
        }
        for a in agreements
    ]

@router.post("/tes", summary="Parse all discovered TES")
async def parse_tes_all(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Парсит PDF для всех найденных TES.
    Сначала запустите /parse/tes/discover/pam.
    """
    service = TesDiscoveryService(session)
    return await service.parse_all()


@router.post("/tes/{key}", summary="Parse single TES by key")
async def parse_tes_one(
    key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Парсит один TES по ключу из БД.
    Ключи доступны через GET /tes/agreements.
    """
    service = TesDiscoveryService(session)
    return await service.parse_one(key)