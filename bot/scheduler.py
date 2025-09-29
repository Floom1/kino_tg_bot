from __future__ import annotations

from datetime import date
from typing import Dict, List

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from .config import settings
from .filters import filter_movie_titles
from .parsers.prada import fetch_prada_titles
from .parsers.afisha_karo import fetch_karo_titles
from .parsers.kino_format import fetch_kinoformat_titles
from .storage import SeenStorage


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    tz = pytz.timezone(settings.TZ)
    scheduler = AsyncIOScheduler(timezone=tz)

    async def daily_check() -> None:
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

    async def morning_digest() -> None:
        today = date.today()
        prada = filter_movie_titles(fetch_prada_titles(today))
        karo = await fetch_karo_titles(today)
        kino = await fetch_kinoformat_titles(today)
        if settings.OWNER_CHAT_ID:
            await bot.send_message(settings.OWNER_CHAT_ID, "<b>Prada 3D</b>\n" + ("\n".join(prada) or "— нет данных"))
            await bot.send_message(settings.OWNER_CHAT_ID, "<b>Karo 10 Реутов</b>\n" + ("\n".join(karo) or "— нет данных"))
            await bot.send_message(settings.OWNER_CHAT_ID, "<b>Киноцентр (Kino-Format)</b>\n" + ("\n".join(kino) or "— нет данных"))

    # New films check daily at 08:00
    scheduler.add_job(daily_check, CronTrigger(hour=8, minute=0))
    # Weekdays (Mon-Fri) 08:00 digest
    scheduler.add_job(morning_digest, CronTrigger(day_of_week="mon-fri", hour=8, minute=0))
    # Weekends (Sat-Sun) 12:00 digest
    scheduler.add_job(morning_digest, CronTrigger(day_of_week="sat,sun", hour=12, minute=0))

    return scheduler
