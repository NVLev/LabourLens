from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"👋 Hi, <b>{message.from_user.first_name}</b>!\n\n"
        "Welcome to the Finnish Labour Law & TES Assistant! 🇫🇮⚖️\n\n"
        "You can:\n"
        "🧠 Describe your situation and get a legal explanation\n"
        "❓ Browse common questions\n"
        "📚 Read laws and paragraphs\n"
        "🧮 Calculate overtime and bonuses (TES)\n\n"
        "Choose an option below 👇",
        reply_markup=main_menu(),
    )
