import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from app.db import init_db
from handlers import routers
from admin_panel.handlers import admin_routers
from handlers.error import register_error_handlers
from middleware import StatusCheckMiddleware

from config import BOT_TOKEN

logging.basicConfig(
    level=logging.ERROR,
    format='[%(asctime)s] - %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
dispatcher_logger = logging.getLogger('aiogram.dispatcher')
dispatcher_logger.setLevel(logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

dp.update.middleware(StatusCheckMiddleware())

for router in routers:
    dp.include_router(router)

for router in admin_routers:
    dp.include_router(router)

register_error_handlers(dp)

async def main():
    await init_db()
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())