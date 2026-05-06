from app.repositories.laws import LawRepository
from app.repositories.topics import TopicRepository
from app.services.faq_service import FaqService


class AnalyzeService:
    """
        Собирает ответ на запрос пользователя по заданной теме трудового права.

        Для заданного topic_key возвращает:
        - релевантные параграфы законов (отсортированные по relevance из TopicSection)
        - FAQ-ответ если user_input совпадает с условиями одного из FaqRule
        - None если тема не найдена в БД

        Используется как основной слой логики для API и Telegram-бота.
        """

    def __init__(self, session):
        self.session = session
        self.topic_repo = TopicRepository(session)
        self.law_repo = LawRepository(session)
        self.faq_service = FaqService(session)

    async def analyze(self, topic_key: str, user_input: dict):
        """
                Возвращает данные по теме для заданного пользовательского контекста.

                :param topic_key: ключ темы, например 'dismissal' или 'overtime'
                :param user_input: словарь с параметрами пользователя,
                                   например {"employment_type": "fixed", "tenure_months": 3}
                :return: dict с полями topic, law, answer_en, answer_ru, matched_rule_id
                         или None если тема не найдена
                """
        # 1. Получаем тему с секциями
        topic = await self.topic_repo.get_with_sections(topic_key)
        if not topic:
            return None

        # 2. Закон
        sections = sorted(
            topic.section_links,
            key=lambda x: x.relevance,
            reverse=True,
        )

        law_data = [
            {
                "section_id": link.section.id,
                "title": link.section.title_fi,
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

        # 3. FAQ match
        rule = await self.faq_service.match(topic_key, user_input)

        return {
            "topic": topic.key,
            "law": law_data,
            "answer_en": rule.answer_en if rule else None,
            "answer_ru": rule.answer_ru if rule else None,
            "matched_rule_id": rule.id if rule else None,
        }