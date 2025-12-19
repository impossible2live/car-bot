from typing import Dict

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app.db.crud_admin import get_settings
from app.db.crud_autoteka import handle_autoteka_purchase
from app.db.crud_user import topup_user_balance, award_referral_bonus
from app.handlers.payment_handler import create_payment_flow
from app.handlers.user.advert_help_fc import publish_ad
from app.handlers.user.create_ad import handle_autoteka_from_creating
from app.keyboards.builders import (
    main_menu_kb,
    pay_button
)
from app.keyboards.helpers import quick_inline
from app.other import _format_price
from app.services.invoice import create_payment_async, check_payment_async
from app.db.crud_transaction import check_active_subscription, create_transaction, create_or_update_subscription

router = Router(name=__name__)


@router.message(F.text == "💳 Купить подписку")
async def month_sub(message: Message, state: FSMContext):
    payment_data = await create_payment_flow(message, message.from_user.id, "subscription")


@router.callback_query(F.data.startswith("done_"))
async def button_checker_payment(callback: CallbackQuery, state: FSMContext):
    payment_type = callback.data.split("_")[-2]
    payment_id = callback.data.split("_")[-1]

    settings = await get_settings()
    data = await state.get_data()
    price_map = {
        "subscription": settings.subscription_price,
        "advert": settings.advert_publish_price,
        "autoteka": settings.autoteka_price,
        "autoteka2": settings.autoteka_price,
        "topup": data.get("topup_amount")
    }
    amount_to_pay = price_map.get(payment_type)

    payment_data = await check_payment_async(payment_id)

    if not payment_data.get('success'):
        await callback.message.answer("❌ Оплата пока не прошла, нажмите снова на кнопку")
        return

    if payment_data.get('is_paid') == True:
        await callback.answer("✅ Оплата успешно прошла")

        transaction = await create_transaction(
            callback.from_user.id,
            payment_id=payment_data.get("payment_id"),
            amount=amount_to_pay,
            payment_url=payment_data.get("payment_url"),
            type=payment_type
        )
        if payment_type == "subscription":
            await create_or_update_subscription(user_id=callback.from_user.id)
            await award_referral_bonus(referred_user_id=callback.from_user.id, payment_amount=amount_to_pay)
            active_sub = await check_active_subscription(callback.from_user.id)
            expires_str = active_sub.expires_at.strftime('%d.%m.%Y %H:%M')
            await callback.message.edit_text("✅ Подписка оформлена"
                                             f"\n⏳ Действует до: {expires_str}")

        elif payment_type == "advert":
            await publish_ad(callback, state)
            await award_referral_bonus(referred_user_id=callback.from_user.id, payment_amount=amount_to_pay)

        elif payment_type == "autoteka":
            await topup_user_balance(callback.from_user.id, amount_to_pay)
            data = await state.get_data()
            advert_id = data.get("current_advert_id")
            await handle_autoteka_purchase(callback, advert_id)
            await award_referral_bonus(referred_user_id=callback.from_user.id, payment_amount=amount_to_pay)

        elif payment_type == "autoteka2":
            await topup_user_balance(callback.from_user.id, amount_to_pay)
            await handle_autoteka_from_creating(callback, state)
            await award_referral_bonus(referred_user_id=callback.from_user.id, payment_amount=amount_to_pay)

        elif payment_type == "topup":
            user = await topup_user_balance(callback.from_user.id, amount_to_pay)
            await callback.message.edit_text("✅ Ваш баланс успешно пополнен\n\n"
                                  f"Баланс: {_format_price(user.balance)}")
            await award_referral_bonus(referred_user_id=callback.from_user.id, payment_amount=amount_to_pay)

            await state.clear()
    else:
        await callback.message.answer("❌ Оплата не прошла")

    await callback.answer()


