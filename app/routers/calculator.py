import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
from app.database.models import Agreement
from app.parsing.tes.union_portal import _extract_sector_fi
from app.repositories.tes import TesRepository
from app.calculator.service import TesRateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calculator", tags=["calculator"])


@router.post("/extract/kt-min-wage", summary="Extracts min-wage from KT agreements")
async def run_kt_min_wage_extraction(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    service = TesRateService(session)
    return await service.extract_rates_for_kt()
