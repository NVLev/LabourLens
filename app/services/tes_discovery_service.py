import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Agreement, Union, UnionPortal
from app.parsing.tes.kt import KtParser
from app.parsing.tes.pam import TesPdfParser
from app.parsing.tes.union_portal import UnionPortalParser
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

    async def discover(self, union_key: str) -> dict:
        """
        Шаг 1: сканирует каталоги, сохраняет найденные TES в БД.
        Не парсит PDF — только регистрирует договоры с ключами.
        """
        portal = await self._get_portal(union_key)
        if not portal:
            return {
                "error": f"Portal for '{union_key}' not found. Run POST /parse/unions/seed first."
            }
        if union_key == "kt":
            from app.parsing.tes.kt import KtParser

            parser = KtParser()
            discovered = await parser.discover()
            created = skipped = 0
            for tes in discovered:
                existing = await self.repo.get_agreement_by_url(tes.full_url)
                if existing is not None:
                    if existing.valid_from is None and tes.valid_from:
                        existing.valid_from = date.fromisoformat(tes.valid_from)
                    if existing.valid_until is None and tes.valid_until:
                        existing.valid_until = date.fromisoformat(tes.valid_until)
                    skipped += 1
                    continue
                agreement = Agreement(
                    union_id=portal.union_id,
                    key=f"kt-{tes.slug}-{tes.period}",
                    name_fi=tes.name_fi,
                    sector_fi=tes.sector_fi,
                    source_url=tes.full_url,
                    source_type="html",
                    is_current=True,
                    is_universally_binding=True,
                    is_parsed=False,
                    valid_from=(
                        date.fromisoformat(tes.valid_from) if tes.valid_from else None
                    ),
                    valid_until=(
                        date.fromisoformat(tes.valid_until) if tes.valid_until else None
                    ),
                )
                self.repo.add_agreement(agreement)
                created += 1
            portal.last_scanned_at = datetime.now(timezone.utc)
            await self.session.commit()
            return {
                "union": union_key,
                "discovered": len(discovered),
                "created": created,
                "skipped": skipped,
            }

        parser = UnionPortalParser(union_key)
        discovered = await parser.discover()
        logger.info("%s: discovered %d TES", union_key, len(discovered))

        created = skipped = 0
        for tes in discovered:
            existing = await self.repo.get_agreement_by_url(tes.pdf_url)
            if existing is not None:
                skipped += 1
                continue

            key_source = tes.key_source or tes.tes_page_url
            key = key_source.rstrip("/").split("/")[-1]
            if key.endswith(".pdf"):
                key = key[:-4]
            catalog_slug = portal.catalog_url.rstrip("/").split("/")[-1]
            if not key or key == catalog_slug:
                logger.warning(
                    "Skipping TES with invalid key from URL: %s", tes.tes_page_url
                )
                skipped += 1
                continue
            GENERIC_NAMES = {"tyoehtosopimus", "teollisuus"}
            if tes.name_fi.lower().replace(" ", "").replace("-", "") in GENERIC_NAMES:
                logger.warning(
                    "Skipping generic TES name '%s' (key=%s)", tes.name_fi, key
                )
                skipped += 1
                continue
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

        portal.last_scanned_at = datetime.now(timezone.utc)
        await self.session.commit()

        return {
            "union": union_key,
            "discovered": len(discovered),
            "created": created,
            "skipped": skipped,
        }

    # ── Parsing ───────────────────────────────────────────────────────────────

    async def parse_all(self, union_key: str | None = None) -> dict:
        """
        Шаг 2: парсит PDF для всех Agreement где is_parsed=False.
        """
        query = (
            select(Agreement)
            .options(selectinload(Agreement.union))
            .where(Agreement.is_parsed == False)
        )
        if union_key:
            query = query.join(Agreement.union).where(Union.key == union_key)

        result = await self.session.execute(query)
        agreements = list(result.scalars().all())
        logger.info(
            "Parsing %d unparsed TES%s",
            len(agreements),
            f" for {union_key}" if union_key else "",
        )

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
        if agreement.union.key == "kt":
            from app.parsing.tes.kt import KtParser

            parser = KtParser()
            clauses = await parser.fetch_and_parse(agreement.source_url)
            agreement.is_parsed = True
            agreement.parsed_at = datetime.now(timezone.utc)
            await self.tes_service.upsert_clauses_for_agreement(
                agreement=agreement,
                clauses=clauses,
            )
            return
        parser = TesPdfParser()
        union_key = agreement.union.key
        parsed = await parser.parse_from_url(
            url=agreement.source_url,
            union_key=union_key,
            is_universally_binding=agreement.is_universally_binding,
        )

        # Обновляем name_fi из PDF только если оно содержит "työehtosopimus"
        # и лучше того что в БД (slug-based без Finnish chars)
        pdf_name = parsed.name_fi or ""
        if pdf_name and "ehtosopimus" in pdf_name.lower():
            agreement.name_fi = pdf_name
            # Пересчитываем sector_fi из нового имени
            from app.parsing.tes.union_portal import _extract_sector_fi

            agreement.sector_fi = _extract_sector_fi(pdf_name)

        if parsed.valid_from:
            agreement.valid_from = self.tes_service._parse_date(parsed.valid_from)
        if parsed.valid_until:
            agreement.valid_until = self.tes_service._parse_date(parsed.valid_until)

        agreement.is_parsed = True
        agreement.parsed_at = datetime.now(timezone.utc)

        await self.tes_service.upsert_clauses_for_agreement(
            agreement=agreement,
            clauses=parsed.clauses,
        )

    async def _get_portal(self, union_key: str) -> UnionPortal | None:
        result = await self.session.execute(
            select(UnionPortal)
            .join(UnionPortal.union)
            .where(UnionPortal.union.has(key=union_key))
            .where(UnionPortal.is_active == True)
        )
        return result.scalar_one_or_none()
