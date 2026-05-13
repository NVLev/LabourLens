import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.database.db_helper import db_helper
from app.routers import analyze, laws, parse, topics, translate, tes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/app.log", encoding="utf-8"),
        ],
    )
    logger.info("🚀 Приложение запущено. Подключение к БД готово.")
    logger.info("Loading translation models...")
    from app.translation.nllb import _load_model

    _load_model()
    logger.info("Models ready")

    try:
        yield
    finally:
        await db_helper.dispose()
        logger.info("🔌 Соединение с БД закрыто.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LabourLens API",
        description="Finnish labour law aggregator",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(parse.router)
    app.include_router(laws.router)
    app.include_router(translate.router)
    app.include_router(topics.router)
    app.include_router(analyze.router)
    app.include_router(tes.router)
    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("app_main:app", host="0.0.0.0", port=8000)
