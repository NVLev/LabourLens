from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db_helper import db_helper
from app.services.analyze_service import AnalyzeService

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/", summary="Analyze user situation")
async def analyze(
    payload: dict,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    """
    Выполняет ситуационный анализ.

    Вход:
    - topic
    - параметры пользователя (employment_type, tenure, union...)

    Выход:
    - релевантные параграфы закона
    - ответ (FAQ rule)
    """

    topic_key = payload.get("topic")
    if not topic_key:
        raise HTTPException(400, "Missing topic")

    service = AnalyzeService(session)
    result = await service.analyze(topic_key, payload)

    if not result:
        raise HTTPException(404, "Topic not found")

    return result
