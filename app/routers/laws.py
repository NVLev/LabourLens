import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.db_helper import db_helper
from app.database.models import Act, Section, Chapter
from app.parsing.finlex import FinlexParser, ACTS_CONFIG
from app.services.law_service import LawService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/laws", tags=["laws"])


@router.get("/acts", summary="List all acts")
async def get_acts(
    session: AsyncSession = Depends(db_helper.session_getter),
):
    result = await session.execute(select(Act))
    acts = result.scalars().all()

    return [
        {
            "key": act.key,
            "name_fi": act.name_fi,
            "code": act.code,
            "version_date": str(act.version_date) if act.version_date else None,
        }
        for act in acts
    ]


# ──────────────────────────────────────────────
# GET ACT WITH CHAPTERS
# ──────────────────────────────────────────────

@router.get("/acts/{act_key}", summary="Get act with chapters")
async def get_act(
    act_key: str,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    result = await session.execute(
        select(Act)
        .options(
            selectinload(Act.chapters)
            .selectinload(Chapter.sections)
        )
        .where(Act.key == act_key)
    )
    act = result.scalar_one_or_none()

    if not act:
        raise HTTPException(404, "Act not found")

    return {
        "key": act.key,
        "name_fi": act.name_fi,
        "chapters": [
            {
                "number": ch.number,
                "title_fi": ch.title_fi,
                "sections_count": len(ch.sections),
            }
            for ch in act.chapters
        ],
    }


# ──────────────────────────────────────────────
# GET CHAPTER WITH SECTIONS
# ──────────────────────────────────────────────

@router.get("/acts/{act_key}/{chapter_number}", summary="Get chapter with sections")
async def get_chapter(
    act_key: str,
    chapter_number: int,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    result = await session.execute(
        select(Chapter)
        .join(Act)
        .options(selectinload(Chapter.sections))
        .where(
            Act.key == act_key,
            Chapter.number == chapter_number,
        )
    )
    chapter = result.scalar_one_or_none()

    if not chapter:
        raise HTTPException(404, "Chapter not found")

    return {
        "act": act_key,
        "chapter": chapter.number,
        "title_fi": chapter.title_fi,
        "sections": [
            {
                "number": sec.number,
                "title_fi": sec.title_fi,
            }
            for sec in chapter.sections
        ],
    }


# ──────────────────────────────────────────────
# GET SECTION WITH FULL TEXT
# ──────────────────────────────────────────────

@router.get(
    "/acts/{act_key}/{chapter_number}/{section_number}",
    summary="Get section with paragraphs",
)
async def get_section(
    act_key: str,
    chapter_number: int,
    section_number: int,
    session: AsyncSession = Depends(db_helper.session_getter),
):
    result = await session.execute(
        select(Section)
        .join(Chapter)
        .join(Act)
        .options(selectinload(Section.paragraphs))
        .where(
            Act.key == act_key,
            Chapter.number == chapter_number,
            Section.number == section_number,
        )
    )
    section = result.scalar_one_or_none()

    if not section:
        raise HTTPException(404, "Section not found")

    return {
        "act": act_key,
        "chapter": chapter_number,
        "section": section.number,
        "title_fi": section.title_fi,
        "paragraphs": [
            {
                "order": p.order_index,
                "text_fi": p.text_fi,
            }
            for p in section.paragraphs
        ],
    }