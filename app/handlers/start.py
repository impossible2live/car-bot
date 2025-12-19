from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.keyboards.builders import main_menu_kb
from app.db.crud_user import get_or_create_user, get_user, add_referral

router = Router(name=__name__)


@router.message(Command("start"))
async def start(message: Message, bot: Bot, state: FSMContext) -> None:
    await state.set_state(None)
    await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        fullname=message.from_user.full_name,
    )

    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    await handle_start_with_referral(message.from_user.id, args)

    info = await bot.get_me()
    await message.answer(
         f"""<b>🚘 @{info.username}</b>
<code>━━━━━━━━━━━━━━━━━━━</code>

🤖 <b>Ключевые возможности бота:</b>

🛒 <b>Сделки с автомобилями</b>
• Продажа авто: Разместите ваше объявление за несколько минут.
• Покупка авто: Большая база проверенных предложений.

📊 <b>Детальные отчёты Автотеки</b>
• Полная история автомобиля (ДТП, залоги, пробег).

🔍 <b>Инструменты поиска</b>
• Гибкие фильтры: Точная настройка под ваши критерии.
• Удобный поиск: Быстрый и интуитивно понятный интерфейс для подбора.

<code>━━━━━━━━━━━━━━━━━━━</code>
<b>Выберите раздел:</b>""",
        reply_markup=main_menu_kb()
    )


async def handle_start_with_referral(user_id: int, args: list):
    if args and args[0].startswith("r_"):
        try:
            referrer_id = int(args[0].split("_")[1])

            if referrer_id == user_id:
                return

            await add_referral(user_id=user_id, referrer_id=referrer_id)
        except Exception as e:
            print(f"Ошибка реферала: {e}")
