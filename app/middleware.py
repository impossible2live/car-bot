from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Dict, Any, Callable, Awaitable


class StatusCheckMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable,
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        user_id = None

        if event.message:
            user_id = event.message.from_user.id
        elif event.callback_query:
            user_id = event.callback_query.from_user.id
        elif event.edited_message:
            user_id = event.edited_message.from_user.id
        elif event.inline_query:
            user_id = event.inline_query.from_user.id

        if not user_id:
            return await handler(event, data)

        from app.db.models import User
        user = await User.get_or_none(id=user_id)

        if not user:
            return await handler(event, data)

        if user.status == "banned":
            if event.message:
                await event.message.answer("🚫 Ваш аккаунт заблокирован")
            elif event.callback_query:
                await event.callback_query.answer("🚫 Ваш аккаунт заблокирован", show_alert=True)
            return

        return await handler(event, data)