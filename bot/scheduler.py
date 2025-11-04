from __future__ import annotations

from datetime import date, datetime
import pytz

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.config import settings
from bot.storage import events_db
from bot.utils.time_utils import get_current_moscow_date
from .filters import filter_movie_titles
from .parsers.prada import fetch_prada_titles
from .parsers.afisha_karo import fetch_karo_titles
from .parsers.kino_format import fetch_kinoformat_titles
from .storage.storage import SeenStorage

async def daily_check(bot: Bot) -> None:
    """Проверяет новые фильмы и отправляет уведомления владельцу"""
    today = date.today()
    storage = SeenStorage()

    prada_titles = filter_movie_titles(fetch_prada_titles(today))
    karo_titles = await fetch_karo_titles(today)
    kino_titles = await fetch_kinoformat_titles(today)

    filtered: Dict[str, List[str]] = {
        "prada": prada_titles,
        "karo": karo_titles,
        "kinoformat": kino_titles,
    }

    new_titles: Dict[str, List[str]] = {}
    for key, titles in filtered.items():
        newly = storage.add_and_get_new(key, titles)
        if newly:
            new_titles[key] = newly

    if new_titles and settings.OWNER_CHAT_ID:
        lines: List[str] = ["Обнаружены новые фильмы:"]
        for key, titles in new_titles.items():
            lines.append(f"\n<b>{key}</b>:\n" + "\n".join(titles))
        await bot.send_message(chat_id=settings.OWNER_CHAT_ID, text="\n".join(lines))

async def morning_digest(bot: Bot) -> None:
    """Отправляет дайджест киноафиш владельцу"""
    today = date.today()
    prada = filter_movie_titles(fetch_prada_titles(today))
    karo = await fetch_karo_titles(today)
    kino = await fetch_kinoformat_titles(today)

    if settings.OWNER_CHAT_ID:
        await bot.send_message(settings.OWNER_CHAT_ID, "<b>Prada 3D</b>\n" + ("\n".join(prada) or "— нет данных"))
        await bot.send_message(settings.OWNER_CHAT_ID, "<b>Karo 10 Реутов</b>\n" + ("\n".join(karo) or "— нет данных"))
        await bot.send_message(settings.OWNER_CHAT_ID, "<b>Киноцентр (Kino-Format)</b>\n" + ("\n".join(kino) or "— нет данных"))

async def send_event_reminders(bot: Bot) -> None:
    """Отправляет напоминания о событиях в группы"""
    today = get_current_moscow_date()

    # Получаем все события из базы данных
    events = events_db.get_all_events()

    for event in events:
        event_id, name, event_date_str, group_chat_id = event
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()

        # Рассчитываем разницу в днях
        days_remaining = (event_date - today).days

        # Пропускаем прошедшие события
        if days_remaining < 0:
            continue

        # Формируем сообщение
        if days_remaining == 0:
            message = f"🎉 СЕГОДНЯ {name}!"
        elif days_remaining == 1:
            message = f"⏳ До {name} остался 1 день!"
        else:
            message = f"⏳ До {name} осталось {days_remaining} дней!"

        # Отправляем в группу
        if group_chat_id > 0:
            await bot.send_message(chat_id=group_chat_id, text=message)
        else:
            # Используем дефолтную группу
            default_group = events_db.get_default_group()
            if default_group > 0:
                await bot.send_message(chat_id=default_group, text=message)

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Настройка планировщика задач"""
    tz = pytz.timezone(settings.TZ)
    scheduler = AsyncIOScheduler(timezone=tz)

    # Запускать проверку новых фильмов каждый день в 8:00 по Москве
    scheduler.add_job(daily_check, 'cron', hour=8, minute=0, args=[bot])

    # Запускать дайджест киноафиш по будням в 8:00 и по выходным в 12:00
    scheduler.add_job(morning_digest, 'cron', day_of_week="mon-fri", hour=8, minute=0, args=[bot])
    scheduler.add_job(morning_digest, 'cron', day_of_week="sat,sun", hour=12, minute=0, args=[bot])
    scheduler.add_job(send_newyear_sticker_daily, 'cron', hour=9, minute=0, args=[bot])


    # Запускать напоминания о событиях каждый день в 9:00 по Москве
    scheduler.add_job(send_event_reminders, 'cron', hour=9, minute=0, args=[bot])

    return scheduler


async def send_newyear_sticker_daily(bot: Bot) -> None:
    new_year = date(2026, 1, 1)
    today = get_current_moscow_date()
    days_remaining = (new_year - today).days

    # Ограничиваем значения
    if days_remaining > 100:
        days_remaining = 100
    elif days_remaining < -1:
        days_remaining = -1

    # Получаем file_id для соответствующего стикера
    sticker_id = settings.STICKER_IDS.get(days_remaining)

    if sticker_id and settings.OWNER_CHAT_ID:
        await bot.send_sticker(chat_id=settings.OWNER_CHAT_ID, sticker=sticker_id)