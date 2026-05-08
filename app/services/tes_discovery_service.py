import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Agreement, UnionPortal
from app.parsing.tes.pam_portal import PamPortalParser
from app.parsing.tes.pam import TesPdfParser
from app.repositories.tes import TesRepository
from app.services.tes_service import TesService

logger = logging.getLogger(__name__)


class TesDiscoveryService:
    """
    Обнаруживает и парсит TES с порталов профсоюзов.

    Workflow:
    1. discover_pam()  — сканирует каталог pam.fi, сохраняет Agreement
                         с pdf_url но без клаузул (is_parsed=False)
    2. parse_all()     — парсит PDF для всех Agreement где is_parsed=False
    3. parse_one(key)  — парсит один Agreement по key
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TesRepository(session)
        self.tes_service = TesService(session)

    # ── Discovery ─────────────────────────────────────────────────────────────

    async def discover_pam(self) -> dict:
        """
        Шаг 1: сканирует каталог pam.fi, сохраняет найденные TES в БД.
        Не парсит PDF — только регистрирует договоры с ключами.
        """
        portal = await self._get_portal("pam")
        if not portal:
            return {"error": "PAM portal not found. Run POST /parse/unions/seed first."}

        parser = PamPortalParser()
        discovered = await parser.discover()
        logger.info("PAM: discovered %d TES", len(discovered))

        created = skipped = 0
        for tes in discovered:
            existing = await self.repo.get_agreement_by_url(tes.pdf_url)
            if existing is not None:
                skipped += 1
                continue

            key = tes.tes_page_url.rstrip("/").split("/")[-1]
            agreement = Agreement(
                union_id=portal.union_id,
                key=key,
                name_fi=tes.name_fi,
                sector_fi=tes.sector_fi,
                source_url=tes.pdf_url,
                source_type="pdf",
                is_current=True,
                is_universally_binding=True,
                is_parsed=False,
            )
            self.repo.add_agreement(agreement)
            created += 1

        # Обновляем время последнего сканирования
        portal.last_scanned_at = datetime.now(timezone.utc)
        await self.session.commit()

        return {
            "discovered": len(discovered),
            "created": created,
            "skipped": skipped,
        }

    # ── Parsing ───────────────────────────────────────────────────────────────

    async def parse_all(self) -> dict:
        """
        Шаг 2: парсит PDF для всех Agreement где is_parsed=False.
        """
        result = await self.session.execute(
            select(Agreement).where(Agreement.is_parsed == False)
        )
        agreements = list(result.scalars().all())
        logger.info("Parsing %d unparsed TES", len(agreements))

        success = errors = 0
        for agreement in agreements:
            try:
                await self._parse_agreement(agreement)
                success += 1
            except Exception as e:
                logger.error("Failed to parse '%s': %s", agreement.name_fi, e)
                errors += 1

        await self.session.commit()
        return {"total": len(agreements), "success": success, "errors": errors}

    async def parse_one(self, key: str) -> dict:
        """
        Парсит один TES по ключу.
        """
        result = await self.session.execute(
            select(Agreement).where(Agreement.key == key)
        )
        agreement = result.scalar_one_or_none()
        if not agreement:
            return {"error": f"Agreement with key '{key}' not found."}

        try:
            await self._parse_agreement(agreement)
            await self.session.commit()
            return {"key": key, "status": "ok", "name_fi": agreement.name_fi}
        except Exception as e:
            logger.error("Failed to parse '%s': %s", key, e)
            return {"key": key, "status": "error", "detail": str(e)}

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _parse_agreement(self, agreement: Agreement) -> None:
        """Скачивает и парсит PDF, сохраняет клаузулы."""
        parser = TesPdfParser()
        from app.parsing.tes.pam import ParsedAgreement

        parsed = await parser.parse_from_url(
            url=agreement.source_url,
            union_key="pam",
            is_universally_binding=agreement.is_universally_binding,
        )
        parsed.name_fi = agreement.name_fi

        await self.tes_service.upsert_clauses_for_agreement(
            agreement=agreement,
            clauses=parsed.clauses,
        )
        agreement.is_parsed = True
        agreement.parsed_at = datetime.now(timezone.utc)

    async def _get_portal(self, union_key: str) -> UnionPortal | None:
        result = await self.session.execute(
            select(UnionPortal)
            .join(UnionPortal.union)
            .where(UnionPortal.union.has(key=union_key))
            .where(UnionPortal.is_active == True)
        )
        return result.scalar_one_or_none()