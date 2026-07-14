import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TesRate, TesClause
from app.repositories.tes import TesRepository
from app.repositories.tes_rate import TesRateRepository
from app.calculator.extractors.kt_min_wage import extract_kt_min_wage


logger = logging.getLogger(__name__)



class TesRateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rate_repo = TesRateRepository(session)
        self.tes_repo = TesRepository(session)

    async def _upsert_rate(
            self,
            clause: TesClause,
            rate: dict[str, Any]
    ) -> str:

        existing = await self.rate_repo.get_by_unique_key(
            agreement_id=clause.agreement_id,
            rate_type=rate["rate_type"],
            wage_group=rate["wage_group"],
            effective_from=rate["effective_from"],
        )
        if existing is not None:
            if (
                    existing.value == rate["value"]
                    and existing.source_text == rate["source_text"]
            ):
                return "skipped"

            existing.clause_id = clause.id
            existing.value = rate["value"]
            existing.source_text = rate["source_text"]
            logger.debug("Updated tes_rate for clause id '%s'", existing.clause_id)
            return "updated"

        self.rate_repo.add(TesRate(
            rate_type=rate["rate_type"],
            agreement_id=clause.agreement_id,
            clause_id=clause.id,
            **rate))
        logger.debug(
            "Created rate %s %s %s",
            rate["rate_type"],
            rate["effective_from"],
            rate["value"],
        )
        return "created"

    # TODO: populate extraction metadata

    async def extract_rates_for_kt(self):
        clauses = await self.tes_repo.get_clauses_by_topic_key(topic_key="min_wage", union_key="kt")
        created = updated = skipped = 0
        for clause in clauses:
            rates = extract_kt_min_wage(clause.text_fi)
            for rate in rates:
                status = await self._upsert_rate(clause, rate)

                if status == "created":
                    created += 1
                elif status == "updated":
                    updated += 1
                else:
                    skipped += 1
        await self.session.commit()
        logger.info(
            "KT rates: %s created, %s updated, %s skipped",
            created,
            updated,
            skipped,
        )

