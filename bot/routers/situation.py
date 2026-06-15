import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.application.seeds.topic_map import TOPIC_LABELS
from app.services.analyze_service import AnalyzeService
from bot.keyboards import salary_type_keyboard, contract_type_keyboard, group_choosing_keyboard, parental_bool_keyboard, \
    sector_choosing_keyboard, choosing_topic_keyboard, tenure_keyboard, showing_result_keyboard, \
    shop_steward_bool_keyboard, main_menu
from bot.states import SituationStates
from app.database.db_helper import db_helper

logger = logging.getLogger(__name__)
router = Router()

PAGE_SIZE = 5

@router.message(F.text == "🧠 My situation")
async def situation_enter(message: Message, state: FSMContext) -> None:
    await state.set_state(SituationStates.choosing_group)
    await message.answer(
        "Please answer a few simple questions\n\n"
        "This will help me find the most relevant information for your situation 👇",
        reply_markup=group_choosing_keyboard(),
    )

@router.callback_query(SituationStates.choosing_group, F.data.startswith("group:"))
async def group_chosen (callback:CallbackQuery, state: FSMContext) -> None:
    group_key = callback.data.split(":")[1]
    logger.info("User %s chose group: %s", callback.from_user.id, group_key)
    await state.update_data(group=group_key)
    await state.set_state(SituationStates.choosing_sector)
    await callback.answer()
    await callback.message.edit_text(
        "Please choose your job sphere 👇",
        reply_markup=sector_choosing_keyboard(group_key)
    )

@router.callback_query(SituationStates.choosing_sector, F.data.startswith("sector:"))
async def sector_chosen (callback:CallbackQuery, state: FSMContext) -> None:
    sector_key = callback.data.split(":")[1]
    logger.info("User %s chose sector: %s", callback.from_user.id, sector_key)
    await state.update_data(sector=sector_key)
    await state.set_state(SituationStates.choosing_topic)
    await callback.answer()
    await callback.message.edit_text(
        "Now choose your topic 👇",
        reply_markup=choosing_topic_keyboard()
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
            "What type of salary do you have?",
            reply_markup=salary_type_keyboard()
        )
    elif topic_key == "dismissal_protection":
        await state.update_data(details_step="parental_leave")
        await callback.answer()
        await callback.message.edit_text(
            "Are you currently on parental leave?",
            reply_markup=parental_bool_keyboard()
        )
    else:
        await state.update_data(details_step="employment_type")
        await callback.answer()
        await callback.message.edit_text(
            "What type of contract do you have?",
            reply_markup=contract_type_keyboard()
        )

@router.callback_query(SituationStates.entering_details, F.data.startswith("employment:"))
async def employment_type_chosen(callback: CallbackQuery, state: FSMContext):
    employment_type = callback.data.split(":")[1]
    logger.info("User %s chose employment_type: %s", callback.from_user.id, employment_type)
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
            reply_markup=tenure_keyboard()
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
        reply_markup=tenure_keyboard()
    )

@router.callback_query(SituationStates.entering_details, F.data.startswith("parental_leave:"))
async def on_parental_leave_chosen(callback: CallbackQuery, state: FSMContext):
    parental_data =callback.data.split(":")[1]
    logger.info("User %s chose parental_data: %s", callback.from_user.id, parental_data)
    await state.update_data(parental_leave=parental_data)
    await state.set_state(SituationStates.showing_result)
    await callback.answer()
    await callback.message.edit_text(
        "Are you a union representative?",
        reply_markup=shop_steward_bool_keyboard()
    )


@router.callback_query(SituationStates.entering_details, F.data.startswith("shop_steward:"))
async def shop_steward_chosen(callback: CallbackQuery, state: FSMContext):
    shop_steward_data = callback.data.split(":")[1]
    logger.info("User %s chose shop_steward_data: %s", callback.from_user.id, shop_steward_data)
    await state.update_data(shop_steward=shop_steward_data)
    await state.set_state(SituationStates.showing_result)
    await callback.answer()
    await show_result(callback, state)


@router.callback_query(SituationStates.entering_details, F.data.startswith("skip:details"))
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

async def show_result(callback: CallbackQuery, state: FSMContext) -> None:
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
    logger.info("User %s requesting result for topic: %s", callback.from_user.id, topic_key)

    try:
        async with db_helper.session_factory() as session:
            service = AnalyzeService(session)
            result = await service.analyze(topic_key, user_input)

        if result is None:
            await callback.message.edit_text(
                "⚠️ Sorry, no information found on this topic yet.",
                reply_markup=showing_result_keyboard(),
            )
            return
    except Exception as e:
        logger.error("AnalyzeService failed for user %s, topic %s: %s",
                     callback.from_user.id, topic_key, e, exc_info=True)
        await callback.message.answer(
            "⚠️ Something went wrong. Please try again.",
            reply_markup=showing_result_keyboard(),
        )
        return

    await callback.message.edit_text(format_result(result, topic_key))

    if result["interpretations"]:
        interp_text = "📋 <b>Additional guidance:</b>\n\n"
        for i in result["interpretations"]:
            if i["text_en"]:
                interp_text += f"<b>{i['source']}:</b>\n{i['text_en']}\n\n"
        await callback.message.answer(interp_text)

    await callback.message.answer(
        "Was this helpful? 👇",
        reply_markup=showing_result_keyboard(),
    )
    await state.set_state(SituationStates.showing_result)

def format_result(result: dict, topic_key: str) -> str:
    header = TOPIC_LABELS[topic_key]
    if result["answer_en"]:
        body = result["answer_en"]
    elif result["law"]:
        paragraphs = result["law"][0]["paragraphs"]
        body = "\n".join(p["en"] for p in paragraphs if p["en"])
    else:
        body = "See additional guidance below ↓"
    lines = [
        f"⚖️ <b>{header}</b>",
        "",
        "<b>Legal answer:</b>",
        body,
    ]
    return "\n".join(lines)



