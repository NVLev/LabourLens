import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
from app.database.models import Agreement
from app.parsing.tes.union_portal import _extract_sector_fi
from app.repositories.tes import TesRepository
from app.services.tes_service import TesService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tes", tags=["tes"])


@router.post("/tes/fix-sectors", summary="Recalculate and clean sector_fi")
async def fix_agreement_sectors(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    result = await session.execute(select(Agreement))
    agreements = result.scalars().all()

    updated = 0
    cleaned = 0

    GARBAGE_KEYS = {
        "teollisuus",
        "tyoehtosopimus",
        "rialaisia-koskevat-tyoehtosopimukset",
    }

    for agr in agreements:
        new_sector = _extract_sector_fi(agr.name_fi)

        # обновление сектора
        if new_sector != agr.sector_fi:
            logger.info(
                "Sector update: [%s] '%s' → '%s'",
                agr.key,
                agr.sector_fi,
                new_sector,
            )
            agr.sector_fi = new_sector
            updated += 1

        # очистка мусорных значений
        if agr.sector_fi and agr.sector_fi.lower() in GARBAGE_KEYS:
            logger.warning(
                "Cleaning garbage sector: [%s] '%s' → NULL",
                agr.key,
                agr.sector_fi,
            )
            agr.sector_fi = None
            cleaned += 1

    await session.commit()

    return {
        "updated": updated,
        "cleaned": cleaned,
        "total": len(agreements),
    }


@router.get("/unions", summary="List all current unions")
async def list_agreements(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Список порталов профсоюзов.
    """
    repo = TesRepository(session)
    unions = await repo.get_all_unions()
    return [
        {
            "key": u.key,
            "name_fi": u.name_fi,
            "website": u.website,
        }
        for u in unions
    ]


@router.get("/agreements", summary="List all current agreements")
async def list_agreements(
    union_key: str | None = None,
    sector_fi: str | None = None,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Список актуальных договоров.
    Фильтрация по профсоюзу и сектору для фронта и бота.
    """
    repo = TesRepository(session)
    agreements = await repo.get_all_agreements(
        current_only=True,
        union_key=union_key,
        sector_fi=sector_fi,
    )
    return [
        {
            "key": a.key,
            "name_fi": a.name_fi,
            "sector_fi": a.sector_fi,
            "sector_en": a.sector_en,
            "valid_from": str(a.valid_from) if a.valid_from else None,
            "valid_until": str(a.valid_until) if a.valid_until else None,
            "is_universally_binding": a.is_universally_binding,
        }
        for a in agreements
    ]


@router.get("/agreements/{key}", summary="Get agreement with clauses")
async def get_agreement(
    key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Договор со всеми клаузурами — полный текст TES."""
    repo = TesRepository(session)
    agreement = await repo.get_agreement_with_clauses_by_key(key)
    if not agreement:
        raise HTTPException(404, f"Agreement '{key}' not found")
    return {
        "key": agreement.key,
        "name_fi": agreement.name_fi,
        "sector_fi": agreement.sector_fi,
        "sector_en": agreement.sector_en,
        "valid_from": str(agreement.valid_from) if agreement.valid_from else None,
        "valid_until": str(agreement.valid_until) if agreement.valid_until else None,
        "is_universally_binding": agreement.is_universally_binding,
        "source_url": agreement.source_url,
        "clauses": [
            {
                "id": c.id,
                "section_ref": c.section_ref,
                "text_fi": c.text_fi,
                "text_en": c.text_en,
                "text_ru": c.text_ru,
                "topic_id": c.topic_id,
                "priority_over_law": c.priority_over_law,
            }
            for c in agreement.clauses
        ],
    }


@router.post("/relink-topics", summary="Reassign topic_id for all TES clauses")
async def relink_tes_topics(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Переназначает topic_id для всех клауз по актуальному SECTION_TOPIC_MAP.
    Запускать после обновления topic_map.py и пересева топиков.
    Idempotent.
    """
    service = TesService(session)
    return await service.relink_topics()


@router.get("/agreements/{key}/unlinked", summary="Get unlinked clauses")
async def get_unlinked_clauses(
    key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """Клаузуры без topic_id — для ручной линковки. Административный endpoint."""
    repo = TesRepository(session)
    agreement = await repo.get_agreement_by_key(key)
    if not agreement:
        raise HTTPException(404, f"Agreement '{key}' not found")
    clauses = await repo.get_unlinked_clauses(agreement.id)
    return [
        {
            "id": c.id,
            "section_ref": c.section_ref,
            "text_fi": c.text_fi[:300],
        }
        for c in clauses
    ]


@router.get("/topic/{topic_key}", summary="Get TES clauses by topic")
async def get_clauses_by_topic(
    topic_key: str,
    union_key: str | None = None,
    sector_fi: str | None = None,
    agreement_key: str | None = None,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Клаузуры по теме из всех договоров.
    Фильтрация по профсоюзу и сектору.
    Основной endpoint для AnalyzeService и бота.
    """
    repo = TesRepository(session)
    clauses = await repo.get_clauses_by_topic_key(
        topic_key=topic_key,
        union_key=union_key,
        sector_fi=sector_fi,
        agreement_key=agreement_key,
    )
    if not clauses:
        raise HTTPException(404, f"No TES clauses found for topic '{topic_key}'")
    return [
        {
            "id": c.id,
            "agreement_key": c.agreement.key,
            "sector_fi": c.agreement.sector_fi,
            "section_ref": c.section_ref,
            "text_fi": c.text_fi,
            "text_en": c.text_en,
            "priority_over_law": c.priority_over_law,
        }
        for c in clauses
    ]
