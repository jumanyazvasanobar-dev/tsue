```python
import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from . import config, db
from .bot_instance import get_bot
from .group_watcher import watch_groups_loop
from .handlers import routers
from .middlewares import UserTrackingMiddleware
from .scheduler import run_scheduler
from .screenshot import start_browser, stop_browser


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    if not config.BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN muhit o'zgaruvchisi berilmagan. "
            ".env fayliga yoki Railway Variables bo'limiga "
            "BOT_TOKEN=... qo'shing."
        )

    # Bazani ishga tushirish
    await db.init_db()
    logger.info("Baza tayyor.")

    # Bot
    bot = get_bot()

    # Dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    dp.message.outer_middleware(UserTrackingMiddleware())
    dp.callback_query.outer_middleware(UserTrackingMiddleware())

    # Routerlarni ulash
    for router in routers:
        dp.include_router(router)

    # Playwright brauzerini ishga tushirish
    await start_browser()
    logger.info("Playwright brauzeri ishga tushdi.")

    # Asosiy scheduler
    scheduler_task = asyncio.create_task(run_scheduler())

    # ==========================================================
    # AVTOMATIK SKANERLAR O'CHIRILDI
    # ==========================================================

    # Xonalarni avtomatik skanerlash O'CHIRILDI
    room_scan_task = None

    # O'qituvchilarni avtomatik skanerlash O'CHIRILDI
    teacher_scan_task = None

    # ==========================================================

    # Guruhlarni kuzatish ishlaydi
    group_watch_task = asyncio.create_task(watch_groups_loop())

    try:
        # Webhookni o'chirish
        await bot.delete_webhook(drop_pending_updates=False)

        logger.info("Bot polling rejimida ishga tushmoqda...")

        # Botni ishga tushirish
        await dp.start_polling(bot)

    finally:
        # Scheduler
        scheduler_task.cancel()

        # Room scan o'chirilgan, lekin xavfsiz tarzda tekshiramiz
        if room_scan_task:
            room_scan_task.cancel()

        # Teacher scan o'chirilgan, lekin xavfsiz tarzda tekshiramiz
        if teacher_scan_task:
            teacher_scan_task.cancel()

        # Guruh kuzatuvchisi
        group_watch_task.cancel()

        # Brauzerni yopish
        await stop_browser()

        # Bot session
        await bot.session.close()

        # Database
        await db.close_db()


if __name__ == "__main__":
    asyncio.run(main())
```
