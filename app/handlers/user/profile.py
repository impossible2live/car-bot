from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from decimal import Decimal

from app.db.crud_user import get_referral_stats, get_user
from app.db.models import Coupon
from app.handlers.user.advert_help_fc import clean_number
from app.handlers.user.subscription import create_payment_flow
from app.keyboards.builders import (
    main_menu_kb, back_kb, profile_kb
)
from app.states.other_states import InputBalance
from app.other import _format_price

router = Router(name=__name__)


class CouponState(StatesGroup):
    waiting_coupon = State()


@router.message(F.text == "💸 Пополнить баланс")
async def profile_topup(message: Message, state: FSMContext):
    await message.answer(
        "💸 Пополнение баланса\n\n"
        "Введите сумму на которую хотите пополнить баланс:",
        reply_markup=back_kb(back_to_profile=True)
    )
    await state.set_state(InputBalance.waiting_balance)


@router.message(F.text == "👥 Реферальная программа")
async def profile_referral(message: Message, bot: Bot, state: FSMContext):
    await state.set_state(None)

    user_id = message.from_user.id
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    stats = await get_referral_stats(user_id, bot_username)

    text = f"👥 Реферальная программа\n\n"
    text += f"📊 Статистика:\n"
    text += f"• Всего приглашено: {stats['referral_count']}\n"
    text += f"• Активных рефералов: {stats['active_referrals_count']}\n"
    text += f"• Ваш процент: {_format_price(stats['referral_percent'])}%\n"
    text += f"• Заработано всего: {_format_price(stats['total_earned'])} руб\n\n"
    text += f"🔗 Ваша реферальная ссылка:\n"
    text += f"https://t.me/{bot_username}?start=r_{user_id}\n\n"
    text += f"💰 Как это работает:\n"
    text += f"• За каждого приглашенного друга вы получаете {_format_price(stats['referral_percent'])}% от его платежей\n"
    text += f"• Деньги поступают на ваш баланс сразу после оплаты\n"

    if stats['referrals']:
        text += f"📋 Ваши рефералы:\n"
        for i, ref in enumerate(stats['referrals'][:10], 1):
            referred_user = ref.referred
            username = referred_user.fullname or referred_user.username or f"ID: {referred_user.id}"
            text += f"{i}. {username}\n"

        if len(stats['referrals']) > 10:
            text += f"\n... и еще {len(stats['referrals']) - 10}"

    await message.answer(text, reply_markup=back_kb(back_to_profile=True))


@router.message(F.text == "🎫 Ввести промокод")
async def profile_coupon(message: Message, state: FSMContext):
    await message.answer(
        "🎫 Ввод промокода\n\n"
        "Введите код промокода для получения скидки на услуги:\n"
        "• 📢 Публикация объявлений\n"
        "• 🔔 Покупка подписки\n"
        "• 🔍 Покупке автотеки\n\n"
        "<i>⚠️ Промокоды не применяются к пополнению баланса</i>",
        reply_markup=back_kb(back_to_profile=True)
    )
    await state.set_state(CouponState.waiting_coupon)


@router.message(CouponState.waiting_coupon, F.text != "⬅️ Назад в профиль")
async def process_coupon_code(message: Message, state: FSMContext):
    from app.handlers.user.menu import menu_profile
    coupon_code = message.text.strip().upper()

    from app.db.crud_transaction import apply_coupon_for_user

    coupon = await Coupon.filter(code=coupon_code).first()

    if not coupon:
        await message.answer(
            f"❌ Промокод <code>{coupon_code}</code> не найден.",
            reply_markup=back_kb(back_to_profile=True)
        )
        return

    if not coupon.is_active:
        await message.answer(
            f"❌ Промокод <code>{coupon_code}</code> неактивен.",
            reply_markup=back_kb(back_to_profile=True)
        )
        return

    if coupon.valid_to:
        valid_to_naive = coupon.valid_to.replace(tzinfo=None)
        if valid_to_naive < datetime.now():
            await message.answer(
                f"❌ Срок действия промокода <code>{coupon_code}</code> истек.",
                reply_markup=back_kb(back_to_profile=True)
            )
            return

    if coupon.max_uses and coupon.used_count >= coupon.max_uses:
        await message.answer(
            f"❌ Промокод <code>{coupon_code}</code> уже использован максимальное количество раз.",
            reply_markup=back_kb(back_to_profile=True)
        )
        return

    if coupon.valid_from:
        valid_from_naive = coupon.valid_from.replace(tzinfo=None)
        if valid_from_naive > datetime.now():
            await message.answer(
                f"❌ Промокод <code>{coupon_code}</code> еще не начал действовать.\n"
                f"Начнет действовать с: {coupon.valid_from.strftime('%d.%m.%Y %H:%M')}",
                reply_markup=back_kb(back_to_profile=True)
            )
            return

    user_coupon = await apply_coupon_for_user(message.from_user.id, coupon_code)
    if not user_coupon:
        await message.answer(
            f"❌ Промокод <code>{coupon_code}</code> уже использован вами.",
            reply_markup=back_kb(back_to_profile=True)
        )
        return

    success_text = f"✅ <b>Промокод применен успешно!</b>\n\n"
    success_text += f"🎫 Код: <code>{coupon.code}</code>\n"
    success_text += f"📊 Скидка: {coupon.discount_percent}%\n"

    if coupon.max_uses:
        uses_left = coupon.max_uses - coupon.used_count
        success_text += f"📈 Осталось использований: {uses_left}\n"

    success_text += f"\n<b>Скидка будет применена к:</b>\n"
    success_text += f"• 📢 Публикации объявления\n"
    success_text += f"• 🔔 Покупке подписки\n"
    success_text += f"• 🔍 Покупке автотеки\n\n"
    success_text += f"<i>⚠️ Промокод НЕ применяется к пополнению баланса</i>"

    await state.clear()
    await menu_profile(message)


@router.message(InputBalance.waiting_balance, F.text, F.text != "⬅️ Назад в профиль")
async def topup_balance_process(message: Message, state: FSMContext):
    cleaned_text = clean_number(message.text)
    if not cleaned_text.isdigit():
        await message.answer("❌ Введите число", reply_markup=back_kb(back_to_profile=True))
        return

    amount = float(cleaned_text)

    await state.update_data(topup_amount=amount)
    await create_payment_flow(message, message.from_user.id, "topup", topup_sum=float(amount))


@router.message(F.text == "⬅️ Назад в профиль")
async def back_to_profile_handler(message: Message, state: FSMContext):
    await state.set_state(None)
    from app.handlers.user.menu import menu_profile

    await state.clear()
    await menu_profile(message, state)

