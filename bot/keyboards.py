from __future__ import annotations

from datetime import date, timedelta
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Все на сегодня")],
            [KeyboardButton(text="По кинотеатрам"), KeyboardButton(text="По дате")],
            [KeyboardButton(text="События")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        selective=False,
    )


def cinema_picker_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Prada 3D", callback_data="pick:cinema:prada")],
            [InlineKeyboardButton(text="Karo 10 Реутов", callback_data="pick:cinema:karo")],
            [InlineKeyboardButton(text="Киноцентр (Kino-Format)", callback_data="pick:cinema:kinoformat")],
        ]
    )


def date_picker_kb(prefix: str = "pick:date:", days: int = 7) -> InlineKeyboardMarkup:
    today = date.today()
    rows = []
    for i in range(days):
        d = today + timedelta(days=i)
        label = "Сегодня" if i == 0 else ("Завтра" if i == 1 else d.strftime("%d.%m.%Y"))
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}{d.isoformat()}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cinema_date_picker_kb(cinema: str, days: int = 7) -> InlineKeyboardMarkup:
    today = date.today()
    rows = []
    for i in range(days):
        d = today + timedelta(days=i)
        label = "Сегодня" if i == 0 else ("Завтра" if i == 1 else d.strftime("%d.%m.%Y"))
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"pick:cinemadate:{cinema}:{d.isoformat()}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
