"""Main application entry point for the Telegram Giveaway Bot.
Handles lifecycle events, background tasks, middlewares, and startup polling.
"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.database import init_db, close_db
from handlers import setup_routers
from middlewares import BanMiddleware, ThrottlingMiddleware
from utils.scheduler import run_giveaway_scheduler

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("giveaway_bot")


async def main() -> None:
    """Initialize resources, attach middlewares, and launch the bot."""
    logger.info("Initializing Telegram Giveaway Platform...")

    # 1. Render Web Service compatibility: Start health check web server IMMEDIATELY if PORT is set
    port_env = os.getenv("PORT")
    web_runner = None
    if port_env:
        try:
            port = int(port_env)
            from aiohttp import web

            async def health_handler(request: web.Request) -> web.Response:
                return web.json_response({
                    "status": "healthy",
                    "service": "telegram_giveaway_bot",
                    "admin_ids": settings.admin_id_list,
                })

            app = web.Application()
            app.router.add_get("/", health_handler)
            app.router.add_get("/health", health_handler)

            web_runner = web.AppRunner(app)
            await web_runner.setup()
            site = web.TCPSite(web_runner, "0.0.0.0", port)
            await site.start()
            logger.info("Health check HTTP server active on 0.0.0.0:%d (Render compatibility)", port)
        except Exception as e:
            logger.warning("Could not start optional HTTP server on port %s: %s", port_env, e)

    # 2. Initialize Database with automatic retry logic
    try:
        await init_db()
    except Exception as e:
        logger.exception("Failed to initialize database after retries: %s", e)
        if web_runner:
            await web_runner.cleanup()
        sys.exit(1)

    # 3. Initialize Bot and Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 4. Register Middlewares
    dp.update.outer_middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.update.outer_middleware(BanMiddleware())

    # 5. Include Master Router
    dp.include_router(setup_routers())

    # 6. Start Background Scheduler
    scheduler_task = asyncio.create_task(run_giveaway_scheduler(bot=bot, interval_seconds=30))

    logger.info("Bot configured. Admin IDs: %s", settings.admin_id_list)
    logger.info("Starting long polling...")

    try:
        # Drop pending updates to avoid backlog on cold starts
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error("Polling terminated with error: %s", e)
    finally:
        logger.info("Shutting down bot gracefully...")
        scheduler_task.cancel()
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()
        await close_db()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
