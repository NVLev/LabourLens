from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧠 My situation")],
            [KeyboardButton(text="❓ FAQ"), KeyboardButton(text="📚 Laws")],
            [KeyboardButton(text="🧮 TES Calculator")],
            [KeyboardButton(text="⚙️ Settings")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an option...",
    )
