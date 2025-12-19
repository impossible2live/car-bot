import logging
import traceback
from aiogram import Dispatcher, Bot
from aiogram.types import ErrorEvent

ADMIN_ID = 808416712
error_count = 0


async def error_handler(event: ErrorEvent, bot: Bot):
    global error_count
    error_count += 1

    exception = event.exception
    update = event.update

    logging.error(f"Ошибка #{error_count}: {exception}", exc_info=True)

    try:
        user_message = (
            "❌ <b>Произошла ошибка</b>\n\n"
            "Мы уже работаем над исправлением.\n"
            "Попробуйте перезапустить бота командой /start"
        )

        if update.message:
            await update.message.answer(user_message)
        elif update.callback_query:
            await update.callback_query.message.answer(user_message)
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение пользователю: {e}")

    user_id = None
    username = None
    if update.message:
        user_id = update.message.from_user.id
        username = update.message.from_user.username
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        username = update.callback_query.from_user.username


    await send_error_to_admin(bot, exception, user_id, username, error_count)


async def send_error_to_admin(bot: Bot, exception: Exception, user_id: int, username: str | None, error_num: int):
    try:
        tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
        full_traceback = "".join(tb)
        full_traceback = full_traceback[-2000:]

        lines = full_traceback.strip().split('\n')
        short_error = "\n".join(lines[-2:]) if len(lines) > 2 else full_traceback

        message = (
            f"🚨 Ошибка #{error_num}\n"
            f"👤 User: {user_id} | @{username}\n"
            f"{short_error}\n\n"
            f"<blockquote expandable>📄 Полная ошибка:\n"
            f"{full_traceback}</blockquote>"
        )

        await bot.send_message(ADMIN_ID, message)

    except Exception as e:
        logging.error(f"Не удалось отправить ошибку админу: {e}")


def register_error_handlers(dp: Dispatcher):
    dp.errors.register(error_handler)