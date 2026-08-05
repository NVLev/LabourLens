import logging
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.seeds.topic_map import (
    SECTOR_KEYS,
    SECTOR_KEYS_REVERSE,
    TOPIC_LABELS,
)
from app.database.db_helper import db_helper
from app.repositories.tes import TesRepository
from app.services.analyze_service import AnalyzeService
from bot.keyboards import (
    choosing_topic_keyboard,
    contract_type_keyboard,
    group_choosing_keyboard,
    main_menu,
    parental_bool_keyboard,
    salary_type_keyboard,
    sector_choosing_keyboard,
    shop_steward_bool_keyboard,
    showing_result_fi_keyboard,
    showing_result_keyboard,
    showing_result_ru_keyboard,
    tenure_keyboard,
    showing_tes_en_keyboard,
    showing_tes_fi_keyboard,
    showing_tes_ru_keyboard,
)
from bot.states import SituationStates

logger = logging.getLogger(__name__)
router = Router()

PAGE_SIZE = 5

TOPICS_NO_DETAILS = {
    "min_wage",
    "wages",
    "expense_reimbursement",
    "working_hours",
    "working_hours_reduction",
    "overtime",
    "night_and_sunday_work",
    "parental_leave",
    "discrimination",
    "workplace_safety",
    "warning",
    "work_certificate",
    "contract_types",
    "employer_obligations",
    "employee_obligations",
    "shop_steward",
    "safety_representative",
    "local_agreement",
}


@router.message(F.text == "🧠 My situation")
async def situation_enter(message: Message, state: FSMContext) -> None:
    await state.set_state(SituationStates.choosing_group)
    await message.answer(
        "Please answer a few simple questions\n\n"
        "This will help me find the most relevant information for your situation 👇",
        reply_markup=group_choosing_keyboard(),
    )


@router.callback_query(SituationStates.choosing_group, F.data.startswith("group:"))
async def group_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    group_key = callback.data.split(":")[1]
    logger.info("User %s chose group: %s", callback.from_user.id, group_key)
    await state.update_data(group=group_key)
    await state.set_state(SituationStates.choosing_sector)
    await callback.answer()
    await callback.message.edit_text(
        "Please choose your job sphere 👇",
        reply_markup=sector_choosing_keyboard(group_key),
    )


@router.callback_query(SituationStates.choosing_sector, F.data.startswith("sector:"))
async def sector_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    sector_key = callback.data.split(":")[1]
    sector_fi = SECTOR_KEYS[sector_key]
    await state.update_data(sector=sector_fi)
    logger.info("User %s chose sector: %s", callback.from_user.id, sector_key)
    await state.set_state(SituationStates.choosing_topic)
    await callback.answer()
    await callback.message.edit_text(
        "Now choose your topic 👇", reply_markup=choosing_topic_keyboard()
    )


@router.callback_query(SituationStates.choosing_topic, F.data.startswith("topic:"))
async def topic_chosen(callback: CallbackQuery, state: FSMContext):
    topic_key = callback.data.split(":")[1]
    logger.info("User %s chose topic: %s", callback.from_user.id, topic_key)
    await state.update_data(topic_key=topic_key)
    await state.set_state(SituationStates.entering_details)

    if topic_key == "holiday_pay":
        await state.update_data(details_step="salary_type")
        await callback.answer()
        await callback.message.edit_text(
            "What type of salary do you have?", reply_markup=salary_type_keyboard()
        )
    elif topic_key == "dismissal_protection":
        await state.update_data(details_step="parental_leave")
        await callback.answer()
        await callback.message.edit_text(
            "Are you currently on parental leave?",
            reply_markup=parental_bool_keyboard(),
        )
    elif topic_key in TOPICS_NO_DETAILS:
        await state.set_state(SituationStates.showing_result)
        await callback.answer()
        await show_result(callback, state)
        return
    else:
        await state.update_data(details_step="employment_type")
        await callback.answer()
        await callback.message.edit_text(
            "What type of contract do you have?", reply_markup=contract_type_keyboard()
        )


@router.callback_query(
    SituationStates.entering_details, F.data.startswith("employment:")
)
async def employment_type_chosen(callback: CallbackQuery, state: FSMContext):
    employment_type = callback.data.split(":")[1]
    logger.info(
        "User %s chose employment_type: %s", callback.from_user.id, employment_type
    )
    await state.update_data(employment_type=employment_type)
    data = await state.get_data()
    topic_key = data.get("topic_key")

    if topic_key in ("layoff", "dismissal_grounds"):
        await state.set_state(SituationStates.showing_result)
        await callback.answer()
        await show_result(callback, state)
    else:
        await state.update_data(details_step="tenure")
        await callback.answer()
        await callback.message.edit_text(
            "How long have you been working at your current job? 👇",
            reply_markup=tenure_keyboard(),
        )


@router.callback_query(SituationStates.entering_details, F.data.startswith("tenure:"))
async def tenure_chosen(callback: CallbackQuery, state: FSMContext):
    tenure_data = callback.data.split(":")[1]
    logger.info("User %s chose tenure_data: %s", callback.from_user.id, tenure_data)
    tenure_months = int(tenure_data)
    await state.update_data(tenure_months=tenure_months)
    await state.set_state(SituationStates.showing_result)
    await callback.answer()
    await show_result(callback, state)


@router.callback_query(SituationStates.entering_details, F.data.startswith("salary:"))
async def salary_type_chosen(callback: CallbackQuery, state: FSMContext):
    salary_type = callback.data.split(":")[1]
    logger.info("User %s chose salary_type: %s", callback.from_user.id, salary_type)
    await state.update_data(salary_type=salary_type)
    await callback.answer()
    await callback.message.edit_text(
        "How long have you been working at your current job? 👇",
        reply_markup=tenure_keyboard(),
    )


@router.callback_query(
    SituationStates.entering_details, F.data.startswith("parental_leave:")
)
async def on_parental_leave_chosen(callback: CallbackQuery, state: FSMContext):
    parental_data = callback.data.split(":")[1]
    logger.info("User %s chose parental_data: %s", callback.from_user.id, parental_data)
    await state.update_data(parental_leave=parental_data)
    await callback.answer()
    await callback.message.edit_text(
        "Are you a union representative?", reply_markup=shop_steward_bool_keyboard()
    )


@router.callback_query(
    SituationStates.entering_details, F.data.startswith("shop_steward:")
)
async def shop_steward_chosen(callback: CallbackQuery, state: FSMContext):
    shop_steward_data = callback.data.split(":")[1]
    logger.info(
        "User %s chose shop_steward_data: %s", callback.from_user.id, shop_steward_data
    )
    await state.update_data(shop_steward=shop_steward_data)
    await state.set_state(SituationStates.showing_result)
    await callback.answer()
    await show_result(callback, state)


@router.callback_query(
    SituationStates.entering_details, F.data.startswith("skip:details")
)
async def skip_details(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SituationStates.showing_result)
    await callback.answer()
    await show_result(callback, state)


@router.callback_query(F.data == "back:main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        "Choose an option below 👇",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()


async def show_result(
    callback: CallbackQuery,
    state: FSMContext,
    offset: int = 0,
) -> None:
    data = await state.get_data()
    user_input = {
        "sector_group": data.get("group"),
        "sector_fi": data.get("sector"),
        "employment_type": data.get("employment_type"),
        "tenure_months": data.get("tenure_months"),
        "salary_type": data.get("salary"),
        "on_parental_leave": data.get("parental_leave"),
        "is_shop_steward": data.get("shop_steward"),
    }
    topic_key = data.get("topic_key")
    await state.update_data(lang="en", result_type="non_tes")
    logger.info(
        "User %s requesting result for topic: %s", callback.from_user.id, topic_key
    )

    try:
        async with db_helper.session_factory() as session:
            service = AnalyzeService(session)
            result = await service.analyze(topic_key, user_input)

        if result is None:
            await callback.message.edit_text(
                "⚠️ Sorry, no information found on this topic yet.",
            )
            return
    except Exception as e:
        logger.error(
            "AnalyzeService failed for user %s, topic %s: %s",
            callback.from_user.id,
            topic_key,
            e,
            exc_info=True,
        )
        await callback.message.answer(
            "⚠️ Something went wrong. Please try again.",
        ),
        return

    base_text = format_result(result, topic_key)
    law_text = ""

    for section in result["law"]:
        title = section.get("title_en")
        if title:
            law_text += f"<b>{title}</b>\n"

        for p in section["paragraphs"]:
            if p["en"]:
                law_text += escape(p["en"]) + "\n\n"

    interp_text = ""
    for i in result["interpretations"]:
        if i["text_en"]:
            interp_text += f"<b>{escape(i['source'])}:</b>\n{escape(i['text_en'])}\n\n"
    combined_text = base_text

    if law_text:
        combined_text += "\n\n📜 <b>Law:</b>\n\n" + law_text

    if interp_text:
        combined_text += "\n\n📋 <b>Additional guidance:</b>\n\n" + interp_text

    pages = split_text(combined_text)
    total = len(pages)
    offset = max(0, min(offset, total - 1))
    page_text = pages[offset]
    await callback.message.edit_text(
        page_text + f"\n\n<i>Page {offset + 1}/{total}</i>",
        reply_markup=showing_result_keyboard(offset=offset, total=total),
    )
    await state.set_state(SituationStates.showing_result)


async def show_result_ru(
    callback: CallbackQuery,
    state: FSMContext,
    offset: int = 0,
):
    data = await state.get_data()
    user_input = {
        "sector_group": data.get("group"),
        "sector_fi": data.get("sector"),
        "employment_type": data.get("employment_type"),
        "tenure_months": data.get("tenure_months"),
        "salary_type": data.get("salary"),
        "on_parental_leave": data.get("parental_leave"),
        "is_shop_steward": data.get("shop_steward"),
    }
    topic_key = data.get("topic_key")
    await state.update_data(lang="ru", result_type="non_tes")
    logger.info(
        "User %s requesting result in Russian for topic: %s",
        callback.from_user.id,
        topic_key,
    )

    try:
        async with db_helper.session_factory() as session:
            service = AnalyzeService(session)
            result = await service.analyze(topic_key, user_input)

        if result is None:
            await callback.message.edit_text(
                "⚠️ Извините, по этой теме нет результатов на русском языке",
            )
            return
    except Exception as e:
        logger.error(
            "AnalyzeService failed for user %s, topic %s: %s",
            callback.from_user.id,
            topic_key,
            e,
            exc_info=True,
        )
        await callback.message.answer(
            "Что-то пошло не так, попробуйте снова",
        )
        return
    base_text = format_result_ru(result, topic_key)
    law_text = ""

    for section in result["law"]:
        title = section.get("title_ru")
        if title:
            law_text += f"<b>{title}</b>\n"

        for p in section["paragraphs"]:
            if p["ru"]:
                law_text += escape(p["ru"]) + "\n\n"

    interp_text = ""
    for i in result["interpretations"]:
        if i["text_ru"]:
            interp_text += f"<b>{escape(i['source'])}:</b>\n{escape(i['text_ru'])}\n\n"
    combined_text = base_text

    if law_text:
        combined_text += "\n\n📜 <b>Закон:</b>\n\n" + law_text

    if interp_text:
        combined_text += "\n\n📋 <b>Дополнительная информация:</b>\n\n" + interp_text

    pages = split_text(combined_text)
    total = len(pages)
    offset = max(0, min(offset, total - 1))
    page_text = pages[offset]
    await callback.message.edit_text(
        page_text + f"\n\n<i>Стр {offset + 1}/{total}</i>",
        reply_markup=showing_result_ru_keyboard(offset=offset, total=total),
    )
    await state.set_state(SituationStates.showing_result)


@router.callback_query(F.data == "show:en")
async def show_in_english(callback: CallbackQuery, state: FSMContext):
    await state.update_data(lang="en")
    await callback.answer()
    await show_result(callback, state)


@router.callback_query(F.data == "show:ru")
async def show_in_russian(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_result_ru(callback, state)


@router.callback_query(F.data == "show:fi")
async def show_in_finnish(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_result_fi(callback, state)


async def show_result_fi(
    callback: CallbackQuery,
    state: FSMContext,
    offset: int = 0,
):
    data = await state.get_data()
    user_input = {
        "sector_group": data.get("group"),
        "sector_fi": data.get("sector"),
        "employment_type": data.get("employment_type"),
        "tenure_months": data.get("tenure_months"),
        "salary_type": data.get("salary"),
        "on_parental_leave": data.get("parental_leave"),
        "is_shop_steward": data.get("shop_steward"),
    }
    topic_key = data.get("topic_key")
    await state.update_data(lang="fi", result_type="non_tes")
    logger.info(
        "User %s requesting result in Finnish for topic: %s",
        callback.from_user.id,
        topic_key,
    )

    try:
        async with db_helper.session_factory() as session:
            service = AnalyzeService(session)
            result = await service.analyze(topic_key, user_input)

        if result is None:
            await callback.message.edit_text(
                "Valitettavasti aiheesta ei löytynyt vielä tietoja.",
            )
            return
    except Exception as e:
        logger.error(
            "AnalyzeService failed for user %s, topic %s: %s",
            callback.from_user.id,
            topic_key,
            e,
            exc_info=True,
        )
        await callback.message.answer(
            "Jotain meni pieleen. Yritä uudelleen.",
        )
        return
    base_text = format_result_fi(result, topic_key)
    law_text = ""

    for section in result["law"]:
        title = section.get("title_fi")
        if title:
            law_text += f"<b>{title}</b>\n"

        for p in section["paragraphs"]:
            if p["fi"]:
                law_text += escape(p["fi"]) + "\n\n"

    interp_text = ""
    for i in result["interpretations"]:
        if i["text_fi"]:
            interp_text += f"<b>{escape(i['source'])}:</b>\n{escape(i['text_fi'])}\n\n"
    combined_text = base_text

    if law_text:
        combined_text += "\n\n📜 <b>Laki:</b>\n\n" + law_text

    if interp_text:
        combined_text += "\n\n📋 <b>Lisäohjeet:</b>\n\n" + interp_text

    pages = split_text(combined_text)
    total = len(pages)
    offset = max(0, min(offset, total - 1))
    page_text = pages[offset]
    await callback.message.edit_text(
        page_text + f"\n\n<i>Page {offset + 1}/{total}</i>",
        reply_markup=showing_result_fi_keyboard(offset=offset, total=total),
    )
    await state.set_state(SituationStates.showing_result)


@router.callback_query(F.data == "show:tes")
async def show_tes(
    callback: CallbackQuery,
    state: FSMContext,
    offset: int = 0,
) -> None:
    data = await state.get_data()
    topic_key = data.get("topic_key")
    sector_fi = data.get("sector")
    await state.update_data(lang="en", result_type="tes")
    logger.info(
        "User %s requesting TES for topic: %s", callback.from_user.id, topic_key
    )
    try:
        async with db_helper.session_factory() as session:
            repo = TesRepository(session)
            clauses = await repo.get_clauses_by_topic_key(
                topic_key=topic_key,
                sector_fi=sector_fi,
            )

            parts = []
            for c in clauses:
                title = c.section_ref or ""
                text = (c.text_en or "")[:3500]
                clause_text = f"<b>{title}</b>\n{text}"
                parts.append(clause_text)

        tes_text = "\n".join(parts)
        if len(tes_text) == 0:
            await callback.message.edit_text(
                "Sorry, there is no English text yet, try Finnish o Russian instead.",
                reply_markup=showing_tes_en_keyboard(offset=offset, total=0),
            )
            return
        logger.info("TES text length: %d", len(tes_text))
        pages = split_text(tes_text)
        total = len(pages)
        offset = max(0, min(offset, total - 1))
        page_text = pages[offset]
        await callback.message.edit_text(
            page_text + f"\n\n<i>Page {offset + 1}/{total}</i>",
            reply_markup=showing_tes_en_keyboard(offset=offset, total=total),
        )
        await state.set_state(SituationStates.showing_result)

    except Exception as e:
        logger.error(
            "Getting Tes failed for user %s, topic %s: %s",
            callback.from_user.id,
            topic_key,
            e,
            exc_info=True,
        )
        await callback.message.answer(
            "⚠️ Something went wrong. Please try again.",
        ),
        return


async def show_tes_ru(
    callback: CallbackQuery,
    state: FSMContext,
    offset: int = 0,
) -> None:
    data = await state.get_data()
    topic_key = data.get("topic_key")
    sector_fi = data.get("sector")
    await state.update_data(lang="ru", result_type="tes")
    logger.info(
        "User %s requesting TES in Russian for topic: %s",
        callback.from_user.id,
        topic_key,
    )
    try:
        async with db_helper.session_factory() as session:
            repo = TesRepository(session)
            clauses = await repo.get_clauses_by_topic_key(
                topic_key=topic_key,
                sector_fi=sector_fi,
            )
            parts = []
            for c in clauses:
                title = c.section_ref or ""
                text = (c.text_ru or "")[:3500]
                clause_text = f"<b>{title}</b>\n{text}"
                parts.append(clause_text)

        tes_text = "\n".join(parts)
        logger.info("TES text length: %d", len(tes_text))
        if len(tes_text) == 0:
            await callback.message.edit_text(
                "Sorry, there is no Russian text yet, try Finnish or English instead.",
                reply_markup=showing_tes_en_keyboard(offset=offset, total=0),
            )
            return

        pages = split_text(tes_text)
        total = len(pages)
        offset = max(0, min(offset, total - 1))
        page_text = pages[offset]
        await callback.message.edit_text(
            page_text + f"\n\n<i>Page {offset + 1}/{total}</i>",
            reply_markup=showing_tes_ru_keyboard(offset=offset, total=total),
        )
        await state.set_state(SituationStates.showing_result)

    except Exception as e:
        logger.error(
            "Getting Tes failed for user %s, topic %s: %s",
            callback.from_user.id,
            topic_key,
            e,
            exc_info=True,
        )
        await callback.message.answer(
            "⚠️ Что-то пошло не так, повторите попытку",
        ),
        return


@router.callback_query(F.data == "show:tes_ru")
async def show_tes_russian(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_tes_ru(callback, state)


async def show_tes_fi(
    callback: CallbackQuery,
    state: FSMContext,
    offset: int = 0,
) -> None:
    data = await state.get_data()
    topic_key = data.get("topic_key")
    sector_fi = data.get("sector")
    await state.update_data(
        lang="fi",
        result_type="tes",
    )
    logger.info(
        "User %s requesting TES for topic: %s", callback.from_user.id, topic_key
    )
    try:
        async with db_helper.session_factory() as session:
            repo = TesRepository(session)
            clauses = await repo.get_clauses_by_topic_key(
                topic_key=topic_key,
                sector_fi=sector_fi,
            )
            parts = []
            for c in clauses:
                title = c.section_ref or ""
                text = (c.text_fi or "")[:3500]
                clause_text = f"<b>{title}</b>\n{text}"
                parts.append(clause_text)

        tes_text = "\n".join(parts)
        logger.info("TES text length: %d", len(tes_text))
        if len(tes_text) == 0:
            await callback.message.edit_text(
                "Sorry, there is no any clause yet",
                reply_markup=showing_tes_fi_keyboard(offset=offset, total=0),
            )
            return
        logger.info("TES text length: %d", len(tes_text))
        pages = split_text(tes_text)
        total = len(pages)
        offset = max(0, min(offset, total - 1))
        page_text = pages[offset]
        await callback.message.edit_text(
            page_text + f"\n\n<i>Page {offset + 1}/{total}</i>",
            reply_markup=showing_tes_fi_keyboard(offset=offset, total=total),
        )
        await state.set_state(SituationStates.showing_result)

    except Exception as e:
        logger.error(
            "Getting Tes failed for user %s, topic %s: %s",
            callback.from_user.id,
            topic_key,
            e,
            exc_info=True,
        )
        await callback.message.answer(
            "⚠️ Something went wrong. Please try again.",
        ),
        return


@router.callback_query(F.data == "show:tes_fi")
async def show_tes_finnish(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_tes_fi(callback, state)


@router.callback_query(
    F.data.startswith("results:prev:") | F.data.startswith("results:next:")
)
async def paginate_results(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    direction = parts[1]
    offset = int(parts[2])

    if direction == "next":
        new_offset = offset + 1
    else:
        new_offset = offset - 1

    new_offset = max(0, new_offset)

    data = await state.get_data()
    result_type = data.get("result_type")
    lang = data.get("lang", "en")
    if result_type == "non_tes":
        if lang == "ru":
            await callback.answer()
            await show_result_ru(
                callback,
                state,
                offset=new_offset,
            )
        elif lang == "fi":
            await callback.answer()
            await show_result_fi(
                callback,
                state,
                offset=new_offset,
            )
        else:
            await callback.answer()
            await show_result(
                callback,
                state,
                offset=new_offset,
            )
    else:
        if lang == "ru":
            await callback.answer()
            await show_tes_ru(
                callback,
                state,
                offset=new_offset,
            )
        elif lang == "fi":
            await callback.answer()
            await show_tes_fi(
                callback,
                state,
                offset=new_offset,
            )
        else:
            await callback.answer()
            await show_tes(
                callback,
                state,
                offset=new_offset,
            )


def split_text(text: str, limit: int = 900) -> list[str]:
    if "\n\n" in text:
        blocks = text.split("\n\n")
    else:
        blocks = text.split(". ")

    pages = []
    current = ""

    for block in blocks:
        block = block.strip() + "\n\n"

        if len(current) + len(block) > limit:
            if current:
                pages.append(current)
            current = block
        else:
            current += block

    if current:
        pages.append(current)

    return [p for p in pages if p.strip()]


def format_result(result: dict, topic_key: str) -> str:
    header = TOPIC_LABELS[topic_key]
    lines = [
        f"⚖️ <b>{header}</b>",
        "",
    ]
    if result["answer_en"]:
        lines += [
            "<b>Legal answer:</b>",
            result["answer_en"],
        ]

    else:
        lines += [
            "<b>Legal answer:</b>",
            "No direct legal answer found. See details below ↓",
        ]

    return "\n".join(lines)


def format_result_ru(result: dict, topic_key: str) -> str:
    header = TOPIC_LABELS[topic_key]
    lines = [
        f"⚖️ <b>{header}</b>",
        "",
    ]
    if result["answer_ru"]:
        lines += [
            "<b>Юридическая консультация:</b>",
            result["answer_ru"],
        ]

    else:
        lines += [
            "<b>Ответ:</b>",
            "Прямого юридического обоснования не найдено. См. детали ниже ↓",
        ]

    return "\n".join(lines)


def format_result_fi(result: dict, topic_key: str) -> str:
    header = TOPIC_LABELS[topic_key]
    lines = [
        f"⚖️ <b>{header}</b>",
        "",
    ]
    if result["answer_fi"]:
        lines += [
            "<b>Oikeudellinen ohje:</b>",
            result["answer_fi"],
        ]
    else:
        lines += [
            "<b>Vastaus:</b>",
            "Suoraa lain mukaista vastausta ei löytynyt. Katso lisätiedot alta ↓",
        ]
    return "\n".join(lines)
