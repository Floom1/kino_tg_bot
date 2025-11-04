from datetime import date, datetime
from typing import Literal
import asyncio

import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from bot.config import settings

from bot.storage import events_db
from bot.utils.time_utils import is_date_in_future
from bot.config import settings
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
        "/schedule <кинотеатр> <дата> — например: /schedule prada 2025-09-28\n"
        "Кинотеатры: prada, karo, kinoformat\n\n"
        "Для напоминаний о событиях:\n"
        "/add_event <дата> <название> — добавить событие\n"
        "/setgroup — установить группу для напоминаний\n"
        "/list_events — посмотреть все события\n"
        "/delete_event <id> — удалить событие\n\n"
        "Для отсчёта до Нового года:\n"
        "/newyear — показать стикер с отсчетом до Нового года\n"
        "/sticker — отправить стикер из пака\n\n"
        "Вы также можете использовать кнопки меню:"
    )
    # Отправляем без HTML-разметки
    await message.answer(text, parse_mode=None, reply_markup=main_menu_kb())


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


# Команда для установки группы
@router.message(Command("setgroup"))
async def set_group_handler(message: Message):
    # Проверяем, что сообщение пришло из группы
    if message.chat.type not in ["group", "supergroup"]:
        await message.answer("❌ Эту команду нужно отправить в группе, куда добавлен бот")
        return

    # Сохраняем ID группы как дефолтную
    events_db.set_default_group(message.chat.id)

    # Отправляем подтверждение
    await message.answer(f"✅ Группа установлена! ID: {message.chat.id}")

# Команда добавления события
@router.message(Command("add_event"))
async def add_event_handler(message: Message):
    # Получаем аргументы команды
    text = message.text
    parts = text.split(maxsplit=2)  # Разбиваем на 3 части: команда, дата, название

    if len(parts) < 3:
        await message.answer("❌ Используйте формат: /add_event <дата> <название>\nПример: /add_event 2025-12-20 День рождения Вани", parse_mode=None)
        return

    date_str = parts[1]
    event_name = parts[2]

    # Проверяем корректность даты
    try:
        # Проверяем формат даты
        datetime.strptime(date_str, "%Y-%m-%d")
        # Проверяем, что дата не в прошлом
        if not is_date_in_future(date_str):
            await message.answer("❌ Дата не может быть в прошлом", parse_mode=None)
            return
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте YYYY-MM-DD", parse_mode=None)
        return

    # Добавляем событие в базу данных
    try:
        # Получаем дефолтную группу
        default_group = events_db.get_default_group()
        if default_group == 0:
            await message.answer("❌ Сначала установите группу через /setgroup")
            return

        events_db.add_event(event_name, date_str, default_group)
        await message.answer(f"✅ Событие '{event_name}' добавлено на {date_str}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении события: {str(e)}")

# Команда списка событий
@router.message(Command("list_events"))
async def list_events_handler(message: Message):
    events = events_db.get_all_events()
    if not events:
        await message.answer("📝 Нет добавленных событий")
        return

    text = "📝 Список событий:\n"
    for event in events:
        event_id, name, event_date, group_chat_id = event
        text += f"• {event_id}: {name} ({event_date})\n"

    await message.answer(text)

# Команда удаления события
@router.message(Command("delete_event"))
async def delete_event_handler(message: Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Используйте формат: /delete_event <id>", parse_mode=None)
        return

    try:
        event_id = int(parts[1])
        events_db.delete_event(event_id)
        await message.answer(f"✅ Событие #{event_id} удалено")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении события: {str(e)}")

# Команда отправки стикера
@router.message(Command("sticker"))
async def send_sticker_handler(message: Message):
    if not settings.STICKER_IDS:
        await message.answer("❌ Стикеры не настроены. Добавьте STICKER_ID в .env")
        return

    await message.answer_sticker(settings.STICKER_IDS)

@router.message(F.sticker)
async def get_sticker_id(message: Message):
    # Получаем file_id стикера
    sticker_id = message.sticker.file_id

    # Отправляем его пользователю (чтобы можно было скопировать)
    await message.answer(f"📋 Файл ID этого стикера:\n`{sticker_id}`", parse_mode="Markdown")

    # Записываем в лог для надежности
    logging.info(f"Получен стикер с file_id: {sticker_id}")

@router.message(Command("newyear"))
async def send_newyear_sticker(message: Message):
    new_year = date(2026, 1, 1)
    today = date.today()
    days_remaining = (new_year - today).days

    if days_remaining > 100:
        days_remaining = 100
    elif days_remaining < -1:
        days_remaining = -1

    # Используем settings.STICKER_IDS
    sticker_id = settings.STICKER_IDS.get(days_remaining)

    if sticker_id:
        await message.answer_sticker(sticker_id)
    else:
        await message.answer("❌ Стикера для этого количества дней не найдено")


@router.message(F.text == "События")
async def events_menu(message: Message):
    text = (
        "Меню событий:\n"
        "/add_event <дата> <название> — добавить событие\n"
        "/list_events — посмотреть все события\n"
        "/delete_event <id> — удалить событие\n"
        "/setgroup — установить группу для напоминаний"
    )
    await message.answer(text, parse_mode=None)