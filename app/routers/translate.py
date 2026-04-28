import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
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
        deepl_api_key=settings.translation.deepl_api_key,
    )


# EN (Helsinki-NLP)

@router.post("/laws/en", summary="Translate all acts fi→en via Helsinki-NLP")
async def translate_all_en(
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_en()


@router.post("/laws/{act_key}/en", summary="Translate single act fi→en")
async def translate_act_en(
    act_key: str,
    service: TranslationService = Depends(get_translation_service),
):
    if act_key not in ACTS_CONFIG:
        raise HTTPException(404, f"Unknown act: {act_key}")
    return await service.translate_en(act_key)


# RU (DeepL)

@router.post("/laws/ru", summary="Translate all acts fi→ru via DeepL")
async def translate_all_ru(
    service: TranslationService = Depends(get_translation_service),
):
    return await service.translate_ru()


@router.post("/laws/{act_key}/ru", summary="Translate single act fi→ru")
async def translate_act_ru(
    act_key: str,
    service: TranslationService = Depends(get_translation_service),
):
    if act_key not in ACTS_CONFIG:
        raise HTTPException(404, f"Unknown act: {act_key}")
    return await service.translate_ru(act_key)


# Утилиты

@router.get("/usage", summary="Check DeepL quota usage")
async def get_deepl_usage(
    service: TranslationService = Depends(get_translation_service),
):
    if not service.deepl:
        raise HTTPException(400, "DeepL not configured")
    usage = await service.deepl.get_usage()
    if not usage:
        raise HTTPException(503, "Failed to fetch DeepL usage")
    return usage