import io
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.keyboards import salary_type_keyboard, contract_type_keyboard, group_choosing_keyboard, parental_bool_keyboard, \
    sector_choosing_keyboard, choosing_topic_keyboard, tenure_keyboard, showing_result_keyboard
from bot.states import SituationStates

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
    await state.update_data(group=group_key)
    await state.set_state(SituationStates.choosing_sector)
    await callback.answer()
    await callback.message.edit_text(
        "Please choose your job sphere 👇",
        reply_markup=sector_choosing_keyboard(group_key)
    )

@router.callback_query(SituationStates.choosing_sector. F.data.startswith("sector:"))
async def sector_chosen (callback:CallbackQuery, state: FSMContext) -> None:
    sector_key = callback.data.split(":")[1]
    await state.update_data(sector=sector_key)
    await state.set_state(SituationStates.choosing_topic)
    await callback.answer()
    await callback.message.edit_text(
        "Now choose the particular job sector",
        reply_markup=choosing_topic_keyboard()
    )


@router.callback_query(SituationStates.choosing_topic, F.data.startswith("topic:"))
async def topic_chosen(callback: CallbackQuery, state: FSMContext):
    topic_key = callback.data.split(":")[1]
    await state.update_data(topic_key=topic_key)
    await state.set_state(SituationStates.entering_details)

    if topic_key == "holiday_pay":
        await state.update_data(details_step="salary_type")
        await callback.message.edit_text(
            "What type of salary do you have?",
            reply_markup=salary_type_keyboard()
        )
    elif topic_key == "dismissal_protection":
        await state.update_data(details_step="parental_leave")
        await callback.message.edit_text(
            "Are you currently on parental leave?",
            reply_markup=parental_bool_keyboard()
        )
    else:
        await state.update_data(details_step="employment_type")
        await callback.message.edit_text(
            "What type of contract do you have?",
            reply_markup=contract_type_keyboard()
        )

@router.callback_query(SituationStates.entering_details, F.data.startswith("employment:"))
async def employment_type_chosen(callback: CallbackQuery, state: FSMContext):
    employment_type = callback.data.split(":")[1]
    await state.update_data(employment_type=employment_type)
    data = await state.get_data()
    topic_key = data.get("topic_key")

    if topic_key in ("layoff", "dismissal_grounds"):
        await state.set_state(SituationStates.showing_result)
        await callback.answer()
        await callback.message.edit_text("Showing results...", reply_markup=showing_result_keyboard())
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
    tenure_months = int(tenure_data)
    await state.update_data(tenure_months=tenure_months)
    await state.set_state(SituationStates.showing_result)
    await callback.answer()
    await callback.message.edit_text("Showing results...", reply_markup=showing_result_keyboard())

