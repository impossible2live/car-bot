from decimal import Decimal
from aiogram import Router
from aiogram.types import Message, CallbackQuery

from app.keyboards.builders import pay_button
from app.services.invoice import create_payment_async
from app.other import _format_price

router = Router(name=__name__)


async def create_payment_flow(
        obj: Message | CallbackQuery,
        user_id: int,
        payment_type: str,
        topup_sum: float = None
):
    from app.db.crud_admin import get_settings
    from app.db.crud_transaction import get_user_applied_coupon

    settings = await get_settings()

    if isinstance(obj, CallbackQuery):
        message = obj.message
    else:
        message = obj

    price_map = {
        "subscription": settings.subscription_price,
        "advert": settings.advert_publish_price,
        "autoteka": settings.autoteka_price,
        "autoteka2": settings.autoteka_price,
        "topup": topup_sum
    }

    description_map = {
        "subscription": "Подписка на месяц",
        "advert": "Размещение объявления",
        "autoteka": "Отчёт автотеки",
        "autoteka2": "Отчёт автотеки",
        "topup": "Пополнение баланса"
    }

    base_amount = price_map.get(payment_type)

    if base_amount is not None:
        if not isinstance(base_amount, Decimal):
            base_amount = Decimal(str(base_amount))
    else:
        base_amount = Decimal('0')

    amount_to_pay = base_amount
    coupon_applied = False
    coupon_info = None

    if payment_type in ["subscription", "advert", "autoteka", "autoteka2"]:
        user_coupon = await get_user_applied_coupon(user_id)
        if user_coupon:
            coupon = user_coupon.coupon
            discount_percent = Decimal(str(coupon.discount_percent))
            discount_amount = base_amount * (discount_percent / Decimal('100'))
            amount_to_pay = base_amount - discount_amount
            coupon_applied = True
            coupon_info = {
                'code': coupon.code,
                'discount': coupon.discount_percent,
                'discount_amount': discount_amount,
                'original_price': base_amount
            }

    payment_desc = description_map.get(payment_type, "Оплата")

    payment_data = await create_payment_async(
        amount=float(amount_to_pay),
        user_id=user_id,
        description=payment_desc
    )

    payment_data['payment_type'] = payment_type
    payment_data['user_id'] = user_id

    if not payment_data.get("success"):
        await message.answer("❌ Произошла ошибка при создании платежа, попробуйте снова")
    else:
        payment_text = "💰 *Оплата*\n\n"

        if coupon_applied:
            payment_text += f"🎫 Применен промокод: `{coupon_info['code']}`\n"
            payment_text += f"💎 Скидка: {coupon_info['discount']}%\n"
            payment_text += f"💸 Изначальная сумма: {_format_price(coupon_info['original_price'])}₽\n"
            payment_text += f"💵 Сумма со скидкой: {_format_price(amount_to_pay)}₽\n"
        else:
            payment_text += f"💳 Сумма к оплате: {_format_price(amount_to_pay)}₽\n\n"

        payment_text += "⬇️ Оплата по кнопке ниже\n"
        payment_text += "После оплаты нажмите \"✅ Готово\""

        await message.answer(
            payment_text,
            reply_markup=pay_button(payment_data)
        )