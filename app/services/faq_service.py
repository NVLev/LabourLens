from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import FaqRule


class FaqService:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def match(self, topic_key: str, user_input: dict) -> FaqRule | None:
        """
        Находит наиболее подходящее правило FAQ по теме и условиям.
        """

        result = await self.session.execute(
            select(FaqRule)
            .join(FaqRule.topic)
            .where(FaqRule.topic.has(key=topic_key))
            .order_by(FaqRule.priority.desc())
        )
        rules = result.scalars().all()

        for rule in rules:
            if self._match_conditions(rule.conditions, user_input):
                return rule

        return None

    # ── conditions matcher ─────────────────────────────

    def _match_conditions(self, conditions: dict, user_input: dict) -> bool:
        """
        rule-based движок.
        Поддержка:
        - equality
        - lt / lte / gt / gte
        """
        for key, expected in conditions.items():
            value = user_input.get(key)

            if isinstance(expected, dict):
                if "lt" in expected and not (value < expected["lt"]):
                    return False
                if "lte" in expected and not (value <= expected["lte"]):
                    return False
                if "gt" in expected and not (value > expected["gt"]):
                    return False
                if "gte" in expected and not (value >= expected["gte"]):
                    return False
            else:
                if value != expected:
                    return False

        return True
