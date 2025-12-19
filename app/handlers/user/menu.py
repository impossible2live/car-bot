from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.keyboards.builders import (
    main_menu_kb, profile_kb, back_kb, subscription_kb, search_filters_kb, cancel_kb, rules_text
)
from app.states.advert_states import AdvertStates
from app.states.search_ad_states import SearchAdStates
from app.keyboards.helpers import quick_inline
from app.keyboards.advert_content import AdvertContent
from .search_ad import _show_random_advert
from .liked_auto import show_favorite_advert
from .search_help_fc import get_user_filter
from app.db.crud_user import get_user
from app.other import _format_price
from app.db.crud_transaction import check_active_subscription

router = Router(name=__name__)


@router.message(F.text == "📤 Подать объявление")
async def start_advert(message: Message, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()
    city = data.get('city')

    if current_state and str(current_state).startswith("AdvertStates") and city:
        await message.answer(
            "📝 У вас есть незавершенное объявление!\n"
            "Хотите продолжить заполнение?",
            reply_markup=quick_inline([
                ("✅ Продолжить", "resume_advert"),
                ("🗑️ Начать заново", "restart_advert")
            ])
        )
    else:
        await message.answer(AdvertContent.TEXTS['city'], reply_markup=cancel_kb())
        await state.set_state(AdvertStates.waiting_city)


@router.message(F.text == "🔍 Посмотреть объявления")
async def menu_search_ads(message: Message, state: FSMContext):

    filter = await get_user_filter(message.from_user.id)

    if filter:
        await _show_random_advert(message, state, message.from_user.id)
    else:
        await message.answer(
            AdvertContent.TEXTS['city'],
            reply_markup=quick_inline(
                [("⏩ Пропустить", "all_cities")]
            )
        )
        await state.set_state(SearchAdStates.waiting_filter_city)


@router.message(F.text == "💳 Подписка")
async def menu_subscription(message: Message, state: FSMContext):
    from app.db.crud_admin import get_settings
    settings = await get_settings()
    price = settings.subscription_price

    text = ""
    active_sub = await check_active_subscription(message.from_user.id)
    if active_sub:
        expires_str = active_sub.expires_at.strftime('%d.%m.%Y %H:%M')
        text = ("✅ У вас есть активная подписка\n"
                f"⏳ Действует до: {expires_str}\n\n")
    await message.answer(
        f"""<b>💳 Раздел: Подписка</b>
<code>━━━━━━━━━━━━━━━━━━━</code>

🎯 <b>Подписка даёт возможность выкладывать неограниченное количество объявлений</b>

💰 <b>Стоимость:</b> {_format_price(price)}₽ / месяц
    
<code>━━━━━━━━━━━━━━━━━━━</code>
{text}<b>Выберите действие:</b>""",
        reply_markup=subscription_kb()
    )
    await state.set_state(None)


@router.message(F.text == "👤 Профиль")
async def menu_profile(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    balance = _format_price(user.balance)

    reg_date = ""
    if hasattr(user, 'created_at') and user.created_at:
        reg_date = user.created_at.strftime('%d.%m.%Y')

    await message.answer(
        f"""<b>👤 Ваш профиль</b>
<code>━━━━━━━━━━━━━━━━━━━</code>

🆔 <b>ID:</b> <code>{message.from_user.id}</code>
💰 <b>Баланс:</b> {balance}
📅 <b>Дата регистрации:</b> {reg_date if reg_date else "Не указана"}

<code>━━━━━━━━━━━━━━━━━━━</code>
<b>Выберите действие:</b>""",
        reply_markup=profile_kb(),
    )
    await state.set_state(None)


@router.message(F.text == "📑 Правила")
async def menu_rules(message: Message, state: FSMContext):
    await message.answer(
        "📑 Правила платформы:\n\n"
        f"{rules_text()}",
    )
    await state.set_state(None)



@router.message(F.text == "❤️ Лайки")
async def menu_favorites(message: Message, state: FSMContext):
    await state.set_state(None)
    await show_favorite_advert(message, state ,message.from_user.id)


@router.message(F.text == "🛠️ Тех поддержка")
async def menu_support(message: Message, state: FSMContext):
    await message.answer(
        "🛠️ Техническая поддержка\n\n"
        "По всем вопросам обращайтесь: @car_sup\n",
    )
    await state.set_state(None)



@router.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message, state: FSMContext):
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_kb()
    )
    await state.set_state(None)



@router.message(F.text == "❌ Отменить")
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Действие отменено",
        reply_markup=main_menu_kb()
    )
