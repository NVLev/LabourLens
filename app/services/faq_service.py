from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import FaqRule

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import FaqRule
from app.repositories.faq import FaqRepository


class FaqService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FaqRepository(session)

    async def match(self, topic_key: str, user_input: dict) -> FaqRule | None:
        """
        Находит наиболее подходящее правило FAQ по теме и условиям.
        Правила проверяются в порядке убывания priority.
        """
        rules = await self.repo.get_rules_by_topic(topic_key)
        for rule in rules:
            if self._match_conditions(rule.conditions, user_input):
                return rule
        return None

    def _match_conditions(self, conditions: dict, user_input: dict) -> bool:
        """
        Rule-based движок.
        Поддержка: equality, lt / lte / gt / gte.
        Пустой conditions ({}) — правило срабатывает всегда.
        """
        for key, expected in conditions.items():
            value = user_input.get(key)
            if isinstance(expected, dict):
                if "lt" in expected and not (value is not None and value < expected["lt"]):
                    return False
                if "lte" in expected and not (value is not None and value <= expected["lte"]):
                    return False
                if "gt" in expected and not (value is not None and value > expected["gt"]):
                    return False
                if "gte" in expected and not (value is not None and value >= expected["gte"]):
                    return False
            else:
                if value != expected:
                    return False
        return True