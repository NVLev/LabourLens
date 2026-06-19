from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import FaqRule, FaqSectionRef, Topic


class FaqRepository:
    """
    Репозиторий для работы с FAQ-правилами.
    Покрывает FaqRule и FaqSectionRef.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_rules_by_topic(self, topic_key: str) -> list[FaqRule]:
        result = await self.session.execute(
            select(FaqRule)
            .join(FaqRule.topic)
            .where(Topic.key == topic_key)
            .order_by(FaqRule.priority.desc())
        )
        return list(result.scalars().all())

    async def get_by_topic_and_question(
        self, topic_id: int, question_en: str
    ) -> FaqRule | None:
        result = await self.session.execute(
            select(FaqRule)
            .where(FaqRule.topic_id == topic_id)
            .where(FaqRule.question_en == question_en)
        )
        return result.scalar_one_or_none()

    def add(self, rule: FaqRule) -> None:
        self.session.add(rule)

    async def delete_section_refs(self, faq_id: int) -> None:
        """Удаляет все ссылки на параграфы для данного правила."""
        await self.session.execute(
            delete(FaqSectionRef).where(FaqSectionRef.faq_id == faq_id)
        )

    def add_section_ref(self, ref: FaqSectionRef) -> None:
        self.session.add(ref)
