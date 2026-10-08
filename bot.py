"""Main application entry point for the Telegram Giveaway Bot.
Handles lifecycle events, background tasks, middlewares, startup polling, and anti-crash keepalive watchdog.
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


async def start_render_keepalive_watchdog(port: int) -> None:
    """Anti-sleep background task for Render Free tier.
    Pings the internal /health endpoint every 8 minutes to prevent Render from idling the container.
    """
    import aiohttp

    await asyncio.sleep(20)  # Wait for web server to be up
    logger.info("Render anti-sleep keepalive watchdog started (pings every 8m)")

    while True:
        try:
            external_url = os.getenv("RENDER_EXTERNAL_URL")
            target = f"{external_url}/health" if external_url else f"http://127.0.0.1:{port}/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(target, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.debug("Keepalive ping to %s -> HTTP %s", target, resp.status)
        except Exception as e:
            logger.debug("Keepalive ping error (ignorable): %s", e)
        await asyncio.sleep(480)  # 8 minutes


async def main() -> None:
    """Initialize resources, attach middlewares, and launch the bot with self-healing keepalive."""
    logger.info("Initializing Telegram Giveaway Platform (John's Giveaway Bot)...")

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
                    "service": "johns_giveaway_bot",
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

            # Start anti-sleep watchdog
            asyncio.create_task(start_render_keepalive_watchdog(port))
        except Exception as e:
            logger.warning("Could not start HTTP health server on port %s: %s", port_env, e)

    # 2. Initialize Database with automatic retry logic
    try:
        await init_db()
    except Exception as e:
        logger.exception("Failed to initialize database: %s", e)
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

    # 7. Resilient Long Polling Loop: NEVER DIE WATCHDOG
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning("Webhook cleanup on boot encountered: %s", e)

    retry_delay = 2
    try:
        while True:
            try:
                logger.info("Starting resilient Telegram long polling...")
                await dp.start_polling(
                    bot,
                    allowed_updates=dp.resolve_used_update_types(),
                    handle_signals=False,
                )
            except asyncio.CancelledError:
                logger.info("Polling loop cancelled, breaking...")
                break
            except Exception as e:
                logger.error("Polling error caught: %s. Auto-reconnecting in %d seconds...", e, retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # Exponential backoff up to 30s max
            else:
                logger.warning("Polling exited without exception. Auto-resuming in 2 seconds...")
                await asyncio.sleep(2)
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
