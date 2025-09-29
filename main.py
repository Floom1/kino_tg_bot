import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot.config import settings
from bot.handlers import register_handlers
from bot.scheduler import setup_scheduler


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    register_handlers(dp)

    scheduler = setup_scheduler(bot)
    scheduler.start()

    # Startup notification to owner
    try:
        owner_id = settings.OWNER_CHAT_ID or 700064662
        await bot.send_message(owner_id, "Бот запущен ✅")
    except Exception:
        pass

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
