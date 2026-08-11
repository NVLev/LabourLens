import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
from app.repositories.tes_rate import TesRateRepository
from app.calculator.service import TesRateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calculator", tags=["calculator"])


@router.post("/extract/kt-min-wage", summary="Extracts min-wage from KT agreements")
async def run_kt_min_wage_extraction(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    service = TesRateService(session)
    return await service.extract_rates_for_kt()

@router.post("/extract/kt-overtime", summary="Extracts additional rates from KT overtime topics clauses")
async def run_kt_overtime_extraction(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    service = TesRateService(session)
    return await service.extract_overtime_rates()

@router.post(
    "/extract/kt-night-sunday",
    summary="Extracts additional rates from KT night_sunday_work topics clauses"
)
async def run_kt_night_sunday_extraction(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    service = TesRateService(session)
    return await service.extract_night_sunday_rates()

@router.get("/extract/{topic_key}", summary="Get TES Rates by topic and (optionally) by union")
async def get_rates_by_topic(
    topic_key: str,
    union_key: str | None = None,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    TesRates по теме из всех договоров.
    Фильтрация по профсоюзу
    """
    repo = TesRateRepository(session)
    rates = await repo.get_rate_by_topic(
        topic_key=topic_key,
        union_key=union_key,
    )
    if not rates:
        raise HTTPException(404, f"No TES clauses found for topic '{topic_key}'")
    return [
        {
            "id": r.id,
            "rate_type": r.rate_type,
            "rate_type_context": r.rate_type_context,
            "value": r.value,
            "unit": r.unit,
            "source_text": r.source_text,
        }
        for r in rates
    ]
