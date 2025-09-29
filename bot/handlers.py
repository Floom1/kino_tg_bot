from datetime import date, datetime
from typing import Literal
import asyncio

from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery

from .parsers.prada import fetch_prada_titles
from .parsers.afisha_karo import fetch_karo_titles, fetch_karo_titles_quick
from .parsers.kino_format import fetch_kinoformat_titles
from .filters import filter_movie_titles
from .keyboards import main_menu_kb, cinema_picker_kb, date_picker_kb, cinema_date_picker_kb

router = Router()

CinemaKey = Literal["prada", "karo", "kinoformat"]


def register_handlers(dp):
    dp.include_router(router)


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    text = (
        "Привет! Я помогу отслеживать новые фильмы в кинотеатрах Балашихи/Реутова.\n\n"
        "Доступные команды:\n"
        "/today — список фильмов на сегодня по всем кинотеатрам\n"
        "/schedule &lt;кинотеатр&gt; &lt;YYYY-MM-DD|DD.MM.YYYY&gt; — например: /schedule prada 2025-09-28\n\n"
        "Кинотеатры: prada, karo, kinoformat"
    )
    await message.answer(text, reply_markup=main_menu_kb())


def _parse_date_any(fmt: str) -> date | None:
    try:
        return date.fromisoformat(fmt)
    except ValueError:
        pass
    try:
        return datetime.strptime(fmt, "%d.%m.%Y").date()
    except ValueError:
        return None


async def get_titles_for(cinema: CinemaKey, day: date, fast: bool = False) -> list[str]:
    if cinema == "prada":
        return filter_movie_titles(fetch_prada_titles(day))
    if cinema == "karo":
        if fast:
            return await fetch_karo_titles_quick(day)
        return await fetch_karo_titles(day)
    if cinema == "kinoformat":
        return await fetch_kinoformat_titles(day)
    return []


async def _send_chunked(message: Message, header: str, items: list[str], chunk_size: int = 50) -> None:
    if not items:
        await message.answer(f"{header}\n— нет данных")
        return
    lines: list[str] = items
    for i in range(0, len(lines), chunk_size):
        part = lines[i:i + chunk_size]
        text = f"{header}\n" + "\n".join(part)
        await message.answer(text)
        header = "(продолжение)"


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    d = date.today()

    async def with_timeout(coro, timeout=8.0, fallback=None):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except Exception:
            return fallback or []

    prada_task = with_timeout(get_titles_for("prada", d, fast=True))
    karo_task = with_timeout(get_titles_for("karo", d, fast=True))
    kino_task = with_timeout(get_titles_for("kinoformat", d, fast=True))

    prada, karo, kinof = await asyncio.gather(prada_task, karo_task, kino_task)

    await _send_chunked(message, "<b>Prada 3D</b>", prada)
    await _send_chunked(message, "<b>Karo 10 Реутов</b>", karo)
    await _send_chunked(message, "<b>Киноцентр (Kino-Format)</b>", kinof)


@router.message(Command("schedule"))
async def cmd_schedule(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Использование: /schedule &lt;кинотеатр&gt; &lt;YYYY-MM-DD|DD.MM.YYYY&gt;")
        return
    parts = command.args.split()
    if len(parts) != 2:
        await message.answer("Использование: /schedule &lt;кинотеатр&gt; &lt;YYYY-MM-DD|DD.MM.YYYY&gt;")
        return

    cinema_key, date_str = parts[0].lower(), parts[1]
    d = _parse_date_any(date_str)
    if not d:
        await message.answer("Некорректная дата. Формат: YYYY-MM-DD или DD.MM.YYYY")
        return

    if cinema_key not in {"prada", "karo", "kinoformat"}:
        await message.answer("Неизвестный кинотеатр. Доступно: prada, karo, kinoformat")
        return

    fast = True
    titles = await get_titles_for(cinema_key, d, fast=fast)
    await _send_chunked(message, f"<b>{cinema_key}</b>", titles)


# Menu: text buttons
@router.message(F.text == "Все на сегодня")
async def menu_all_today(message: Message) -> None:
    await cmd_today(message)


@router.message(F.text == "По дате")
async def menu_by_date(message: Message) -> None:
    await message.answer("Выберите дату:", reply_markup=date_picker_kb(prefix="pick:date:"))


@router.message(F.text == "По кинотеатрам")
async def menu_by_cinema(message: Message) -> None:
    await message.answer("Выберите кинотеатр:", reply_markup=cinema_picker_kb())


# Callbacks
@router.callback_query(F.data.startswith("pick:date:"))
async def cb_pick_date(q: CallbackQuery) -> None:
    iso = q.data.split(":")[-1]
    d = _parse_date_any(iso)
    if not d:
        await q.answer("Некорректная дата")
        return
    # Fetch all for date
    async def with_timeout(coro, timeout=8.0, fallback=None):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except Exception:
            return fallback or []
    prada_task = with_timeout(get_titles_for("prada", d, fast=True))
    karo_task = with_timeout(get_titles_for("karo", d, fast=True))
    kino_task = with_timeout(get_titles_for("kinoformat", d, fast=True))
    prada, karo, kinof = await asyncio.gather(prada_task, karo_task, kino_task)
    await _send_chunked(q.message, f"<b>Prada 3D — {d}</b>", prada)
    await _send_chunked(q.message, f"<b>Karo 10 Реутов — {d}</b>", karo)
    await _send_chunked(q.message, f"<b>Киноцентр (Kino-Format) — {d}</b>", kinof)
    await q.answer()


@router.callback_query(F.data.startswith("pick:cinema:"))
async def cb_pick_cinema(q: CallbackQuery) -> None:
    cinema = q.data.split(":")[-1]
    await q.message.answer("Выберите дату:", reply_markup=cinema_date_picker_kb(cinema))
    await q.answer()


@router.callback_query(F.data.startswith("pick:cinemadate:"))
async def cb_pick_cinema_date(q: CallbackQuery) -> None:
    _, _, cinema, iso = q.data.split(":", 3)
    d = _parse_date_any(iso)
    if not d:
        await q.answer("Некорректная дата")
        return
    titles = await get_titles_for(cinema, d, fast=True)  # type: ignore[arg-type]
    await _send_chunked(q.message, f"<b>{cinema} — {iso}</b>", titles)
    await q.answer()
