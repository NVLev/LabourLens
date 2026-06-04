import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.seeds.faq_rules import FAQ_RULES
from app.database.models import FaqRule, FaqSectionRef
from app.repositories.faq import FaqRepository
from app.repositories.topics import TopicRepository
from app.repositories.laws import LawRepository

logger = logging.getLogger(__name__)


class FaqSeedService:
    """
    Загружает FAQ-правила из faq_rules.py в БД.

    Стратегия upsert: по паре (topic_id, question_en).
    - Если правило с таким вопросом уже существует — обновляем условия,
      ответы и приоритет на месте (id остаётся стабильным).
    - FaqSectionRef пересоздаются при каждом запуске
      (внешних FK на них нет).
    - Если тема или параграф не найдены в БД — правило пропускается
      с предупреждением.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = FaqRepository(session)
        self.topic_repo = TopicRepository(session)
        self.law_repo = LawRepository(session)

    async def seed_faq_rules(self) -> dict:
        """
        Выполняет upsert всех правил из FAQ_RULES.
        Безопасно запускать повторно.
        """
        created = updated = skipped = 0
        skipped_details: list[str] = []

        for rule_data in FAQ_RULES:
            topic = await self.topic_repo.get_by_key(rule_data["topic_key"])
            if topic is None:
                msg = f"Topic not found: {rule_data['topic_key']}"
                logger.warning(msg)
                skipped_details.append(msg)
                skipped += 1
                continue

            existing = await self.repo.get_by_topic_and_question(
                topic_id=topic.id,
                question_en=rule_data["question_en"],
            )

            if existing is None:
                rule = FaqRule(
                    topic_id=topic.id,
                    question_en=rule_data["question_en"],
                    question_ru=rule_data.get("question_ru"),
                    conditions=rule_data["conditions"],
                    answer_en=rule_data["answer_en"],
                    answer_ru=rule_data.get("answer_ru"),
                    priority=rule_data.get("priority", 0),
                )
                self.repo.add(rule)
                await self.session.flush()  # нужен rule.id для section refs
                created += 1
            else:
                existing.conditions = rule_data["conditions"]
                existing.answer_en = rule_data["answer_en"]
                existing.answer_ru = rule_data.get("answer_ru")
                existing.question_ru = rule_data.get("question_ru")
                existing.priority = rule_data.get("priority", 0)
                rule = existing
                await self.session.flush()
                updated += 1

            # Пересоздаём FaqSectionRef
            await self.repo.delete_section_refs(rule.id)
            refs_ok = refs_skipped = 0

            for ref_data in rule_data.get("section_refs", []):
                section = await self.law_repo.find_section(
                    act_key=ref_data["act"],
                    chapter_number=ref_data["chapter"],
                    section_number=ref_data["section"],
                )
                if section is None:
                    logger.warning(
                        "Section not found for rule '%s': %s chp%d §%d",
                        rule_data["question_en"][:50],
                        ref_data["act"],
                        ref_data["chapter"],
                        ref_data["section"],
                    )
                    refs_skipped += 1
                    continue

                self.repo.add_section_ref(
                    FaqSectionRef(faq_id=rule.id, section_id=section.id)
                )
                refs_ok += 1

            if refs_skipped:
                skipped_details.append(
                    f"Rule '{rule_data['question_en'][:50]}': "
                    f"{refs_skipped} section ref(s) not found"
                )

        await self.session.commit()

        logger.info(
            "FAQ seed done: %d created, %d updated, %d skipped",
            created, updated, skipped,
        )
        return {
            "total": len(FAQ_RULES),
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "skipped_details": skipped_details,
        }
