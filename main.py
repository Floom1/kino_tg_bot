import asyncio
import logging
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from bot.config import settings
from bot.handlers import register_handlers
from bot.scheduler import setup_scheduler
from bot.storage import events_db
from bot.utils.time_utils import get_current_moscow_time, check_time_difference


def register_handlers(dp: Dispatcher):
    from bot.handlers import router
    dp.include_router(router)


async def main() -> None:
    # Настройка логгирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Проверка времени при запуске
    moscow_time = get_current_moscow_time()
    utc_time = datetime.now(pytz.utc)

    logging.info(f"Текущее время в Москве: {moscow_time}")
    logging.info(f"Текущее время UTC: {utc_time}")

    # Проверка разницы во времени
    check_time_difference()

    # Инициализация бота
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Инициализация базы данных событий
    events_db.init_db()

    # Регистрация обработчиков
    register_handlers(dp)

    # Настройка планировщика
    scheduler = setup_scheduler(bot)
    scheduler.start()

    # Startup notification to owner
    try:
        owner_id = settings.OWNER_CHAT_ID or 700064662
        await bot.send_message(
            owner_id,
            "Бот запущен ✅\n"
            "Текущее время в Москве: " + get_current_moscow_time().strftime("%d.%m.%Y %H:%M")
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление о запуске: {e}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass