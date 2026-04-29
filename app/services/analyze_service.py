from app.repositories.laws import LawRepository
from app.repositories.topics import TopicRepository
from app.services.faq_service import FaqService


class AnalyzeService:

    def __init__(self, session):
        self.session = session
        self.topic_repo = TopicRepository(session)
        self.law_repo = LawRepository(session)
        self.faq_service = FaqService(session)

    async def analyze(self, topic_key: str, user_input: dict):
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