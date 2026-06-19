from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.application.sector_mapping import GROUP_LABELS, SECTOR_GROUPS, SECTOR_LABELS_EN
from app.application.seeds.topic_map import (
    SECTOR_KEYS_REVERSE,
    TOPIC_CATEGORIES,
    TOPIC_LABELS,
)


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


def group_choosing_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in GROUP_LABELS.items():
        builder.button(text=label, callback_data=f"group:{key}")
    builder.button(text="🔍 Other / Not sure", callback_data="group:ANY")
    builder.adjust(2)
    return builder.as_markup()


def sector_choosing_keyboard(group_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sector_fi in SECTOR_GROUPS.get(group_key, []):
        label = SECTOR_LABELS_EN.get(sector_fi, sector_fi)
        builder.button(
            text=label, callback_data=f"sector:{SECTOR_KEYS_REVERSE[sector_fi]}"
        )
    builder.button(text="🔍 Other / Not sure", callback_data="group:ANY")
    builder.button(text="⬅️ Back", callback_data="back:group")
    builder.adjust(2)
    return builder.as_markup()


def choosing_topic_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category_label, topic_keys in TOPIC_CATEGORIES:
        builder.row(InlineKeyboardButton(text=category_label, callback_data="noop"))
        # темы внутри категории — по 2 в ряд
        buttons = [
            InlineKeyboardButton(text=TOPIC_LABELS[key], callback_data=f"topic:{key}")
            for key in topic_keys
        ]
        # добавляем по 2 кнопки в ряд
        for i in range(0, len(buttons), 2):
            builder.row(*buttons[i : i + 2])
        builder.row(InlineKeyboardButton(text="⬅️ Back", callback_data="back:sector"))
    return builder.as_markup()


def contract_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    types = [
        ("📋 Permanent", "permanent"),
        ("📋 Fixed-term", "fixed"),
    ]
    for label, data in types:
        builder.button(text=label, callback_data=f"employment:{data}")
    builder.button(text="⏭️ Skip", callback_data="back:sector")
    builder.adjust(2)
    return builder.as_markup()


def tenure_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    periods = [
        ("< 1 month", "0"),
        ("1–11 months", "1"),
        ("1–4 years", "12"),
        ("4–8 years", "48"),
        ("8–12 years", "96"),
        ("12+ years", "144"),
    ]
    for label, data in periods:
        builder.button(text=label, callback_data=f"tenure:{data}")
    builder.button(text="⏭️ Skip", callback_data="skip:details")
    builder.adjust(2)
    return builder.as_markup()


def salary_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    salaries = [("Monthly", "monthly"), ("Hourly", "hourly")]
    for label, data in salaries:
        builder.button(text=label, callback_data=f"salary:{data}")
    builder.button(text="⏭️ Skip", callback_data="skip:details")
    builder.adjust(2)
    return builder.as_markup()


def parental_bool_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ yes", callback_data="parental_leave:true")
    builder.button(text="No", callback_data="parental_leave:false")
    builder.button(text="⏭️ Skip", callback_data="skip:details")
    builder.adjust(2)
    return builder.as_markup()


def shop_steward_bool_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ yes", callback_data="shop_steward:true")
    builder.button(text="No", callback_data="shop_steward:false")
    builder.button(text="⏭️ Skip", callback_data="skip:details")
    builder.adjust(2)
    return builder.as_markup()


def showing_result_keyboard(offset: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if offset > 0:
        builder.button(
            text="⬅️ Prev",
            callback_data=f"results:prev:{offset}",
        )

    if offset < total - 1:
        builder.button(
            text="➡️ Next",
            callback_data=f"results:next:{offset}",
        )

    builder.button(text="🇷🇺 RU", callback_data="show:ru")
    builder.button(text="🇫🇮 FI", callback_data="show:fi")
    builder.button(text="🔄 New search", callback_data="back:main_menu")

    builder.adjust(2, 2, 1)
    return builder.as_markup()


def showing_result_ru_keyboard(offset: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if offset > 0:
        builder.button(
            text="⬅️ Prev",
            callback_data=f"results:prev:{offset}",
        )

    if offset < total - 1:
        builder.button(
            text="➡️ Next",
            callback_data=f"results:next:{offset}",
        )
    builder.button(text="🇫🇮 Show in Finnish", callback_data="show:fi")
    builder.button(text="🇬🇧 Show in English", callback_data="show:en")
    builder.button(text="🔄 New search", callback_data="back:main_menu")
    builder.adjust(2)
    return builder.as_markup()


def showing_result_fi_keyboard(offset: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if offset > 0:
        builder.button(
            text="⬅️ Prev",
            callback_data=f"results:prev:{offset}",
        )

    if offset < total - 1:
        builder.button(
            text="➡️ Next",
            callback_data=f"results:next:{offset}",
        )
    builder.button(text="🇷🇺 Show in Russian", callback_data="show:ru")
    builder.button(text="🇬🇧 Show in English", callback_data="show:en")
    builder.button(text="🔄 New search", callback_data="back:main_menu")
    builder.adjust(2)
    return builder.as_markup()
