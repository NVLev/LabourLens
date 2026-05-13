import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
from app.database.models import TesClause
from app.parsing.finlex import ACTS_CONFIG
from app.services.translation_service import TranslationService
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/translate", tags=["translate"])


def get_translation_service(
    session: AsyncSession = Depends(db_helper.session_getter),
) -> TranslationService:
    return TranslationService(
        session=session,
    )


@router.get("/laws/status", summary="Translation status for all acts")
async def get_translation_status(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    from sqlalchemy import func

    from app.database.models import Act, Chapter, Section, SectionParagraph

    result = await session.execute(
        select(
            Act.key,
            Act.name_fi,
            func.count(SectionParagraph.id).label("total"),
            func.count(SectionParagraph.text_en).label("translated_en"),
            func.count(SectionParagraph.text_ru).label("translated_ru"),
            func.max(SectionParagraph.translated_at).label("last_translated_en"),
            func.max(SectionParagraph.translated_ru_at).label("last_translated_ru"),
        )
        .join(Section, SectionParagraph.section_id == Section.id)
        .join(Chapter, Section.chapter_id == Chapter.id)
        .join(Act, Chapter.act_id == Act.id)
        .group_by(Act.key, Act.name_fi)
        .order_by(Act.key)
    )
    rows = result.all()

    return [
        {
            "act": row.key,
            "name_fi": row.name_fi,
            "total_paragraphs": row.total,
            "translated_en": row.translated_en,
            "translated_ru": row.translated_ru,
            "pending_en": row.total - row.translated_en,
            "pending_ru": row.total - row.translated_ru,
            "last_translated_en": row.last_translated_en,
            "last_translated_ru": row.last_translated_ru,
        }
        for row in rows
    ]


@router.post("/laws/en", summary="Translate all acts fi→en via NLLB-600M")
async def translate_all_en(
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_en()


@router.post("/laws/ru", summary="Translate all acts fi→ru via NLLB-600M")
async def translate_all_ru(
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_ru()


@router.get("/laws/{act_key}/status", summary="Translation status for single act")
async def get_act_translation_status(
    act_key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    from sqlalchemy import func

    from app.database.models import Act, Chapter, Section, SectionParagraph

    if act_key not in ACTS_CONFIG:
        raise HTTPException(404, f"Unknown act: {act_key}")

    result = await session.execute(
        select(
            func.count(SectionParagraph.id).label("total"),
            func.count(SectionParagraph.text_en).label("translated_en"),
            func.count(SectionParagraph.text_ru).label("translated_ru"),
            func.max(SectionParagraph.translated_at).label("last_translated_en"),
            func.max(SectionParagraph.translated_ru_at).label("last_translated_ru"),
        )
        .join(Section, SectionParagraph.section_id == Section.id)
        .join(Chapter, Section.chapter_id == Chapter.id)
        .join(Act, Chapter.act_id == Act.id)
        .where(Act.key == act_key)
    )
    row = result.one()

    return {
        "act": act_key,
        "total_paragraphs": row.total,
        "translated_en": row.translated_en,
        "translated_ru": row.translated_ru,
        "pending_en": row.total - row.translated_en,
        "pending_ru": row.total - row.translated_ru,
        "percent_en": round(row.translated_en / row.total * 100, 1) if row.total else 0,
        "percent_ru": round(row.translated_ru / row.total * 100, 1) if row.total else 0,
        "last_translated_en": row.last_translated_en,
        "last_translated_ru": row.last_translated_ru,
    }


@router.post("/laws/{act_key}/en", summary="Translate single act fi→en")
async def translate_act_en(
    act_key: str,
    service: TranslationService = Depends(get_translation_service),
):
    if act_key not in ACTS_CONFIG:
        raise HTTPException(404, f"Unknown act: {act_key}")

    start = time.perf_counter()
    result = await service.translate_en(act_key)
    result["elapsed_seconds"] = round(time.perf_counter() - start, 2)
    return result


@router.post("/laws/{act_key}/ru", summary="Translate single act fi→ru")
async def translate_act_ru(
    act_key: str,
    service: TranslationService = Depends(get_translation_service),
):
    if act_key not in ACTS_CONFIG:
        raise HTTPException(404, f"Unknown act: {act_key}")

    start = time.perf_counter()
    result = await service.translate_ru(act_key)
    result["elapsed_seconds"] = round(time.perf_counter() - start, 2)
    return result


@router.get("/interpretations/status", summary="Translation status for interpretations")
async def get_interpretations_translation_status(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    from sqlalchemy import func

    from app.database.models import Interpretation, Topic

    result = await session.execute(
        select(
            Topic.key,
            Topic.name_en,
            func.count(Interpretation.id).label("total"),
            func.count(Interpretation.text_en).label("translated_en"),
            func.count(Interpretation.text_ru).label("translated_ru"),
        )
        .join(Interpretation, Interpretation.topic_id == Topic.id)
        .group_by(Topic.key, Topic.name_en)
        .order_by(Topic.key)
    )
    rows = result.all()
    return [
        {
            "topic": row.key,
            "name_en": row.name_en,
            "total": row.total,
            "translated_en": row.translated_en,
            "translated_ru": row.translated_ru,
            "pending_en": row.total - row.translated_en,
            "pending_ru": row.total - row.translated_ru,
        }
        for row in rows
    ]


@router.post("/interpretations/en", summary="Translate all interpretations fi→en")
async def translate_interpretations_en(
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_interpretations_en()


@router.post("/interpretations/ru", summary="Translate all interpretations fi→ru")
async def translate_interpretations_ru(
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_interpretations_ru()

@router.post("/tes/en", summary="Translate all TES clauses fi→en")
async def translate_tes_en(
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_tes_en()


@router.post("/tes/ru", summary="Translate all TES clauses fi→ru")
async def translate_tes_ru(
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_tes_ru()

@router.post("/tes/{key}/en", summary="Translate single TES fi→en")
async def translate_tes_by_key_en(
    key: str,
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_tes_en_by_key(key)

@router.post("/tes/{key}/ru", summary="Translate single TES fi→ru")
async def translate_tes_by_key_ru(
    key: str,
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_tes_ru_by_key(key)
