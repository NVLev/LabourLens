import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.interpretations import InterpretationRepository
from app.repositories.laws import LawRepository
from app.repositories.topics import TopicRepository
from app.services.faq_service import FaqService

logger = logging.getLogger(__name__)


class AnalyzeService:
    """
    Собирает ответ на запрос пользователя по заданной теме трудового права.

    Для заданного topic_key возвращает:
    - релевантные параграфы законов (отсортированные по relevance из TopicSection)
    - интерпретации с tyosuojelu.fi и профсоюзов (TES)
    - FAQ-ответ если user_input совпадает с условиями одного из FaqRule
    - None если тема не найдена в БД

    Используется как основной слой логики для API и Telegram-бота.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.topic_repo = TopicRepository(session)
        self.law_repo = LawRepository(session)
        self.interpretation_repo = InterpretationRepository(session)
        self.faq_service = FaqService(session)

    async def analyze(self, topic_key: str, user_input: dict) -> dict | None:
        """
        Возвращает данные по теме для заданного пользовательского контекста.

        :param topic_key: ключ темы, например 'dismissal_grounds' или 'overtime'
        :param user_input: словарь с параметрами пользователя,
                           например {"employment_type": "fixed", "tenure_months": 3}
        :return: dict с полями topic, law, interpretations, answer_en, answer_ru,
                 matched_rule_id — или None если тема не найдена
        """
        topic = await self.topic_repo.get_with_sections(topic_key)
        if not topic:
            return None

        # 1. Параграфы законов — отсортированы по relevance
        sections = sorted(
            topic.section_links,
            key=lambda x: x.relevance,
            reverse=True,
        )
        law_data = [
            {
                "section_id": link.section.id,
                "title_fi": link.section.title_fi,
                "title_en": link.section.title_en,
                "relevance": link.relevance,
                "paragraphs": [
                    {
                        "fi": p.text_fi,
                        "en": p.text_en,
                        "ru": p.text_ru,
                    }
                    for p in link.section.paragraphs
                ],
            }
            for link in sections
        ]

        # 2. Интерпретации (tyosuojelu + профсоюзы)
        interpretations = await self.interpretation_repo.get_by_topic_key(topic_key)
        interpretation_data = [
            {
                "source": i.source,
                "title_fi": i.title_fi,
                "text_fi": i.text_fi,
                "text_en": i.text_en,
                "text_ru": i.text_ru,
            }
            for i in interpretations
        ]

        # 3. FAQ match
        rule = await self.faq_service.match(topic_key, user_input)

        return {
            "topic": topic.key,
            "law": law_data,
            "interpretations": interpretation_data,
            "answer_en": rule.answer_en if rule else None,
            "answer_ru": rule.answer_ru if rule else None,
            "matched_rule_id": rule.id if rule else None,
        }