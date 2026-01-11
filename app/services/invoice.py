import uuid
from yookassa import Configuration, Payment
from app.config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY


class YookassaService:
    def __init__(self):
        self.idempotence_key = str(uuid.uuid4())

    async def create_payment(self, amount: float, user_id: int, description: str = "Пополнение баланса"):
        try:
            payment_data = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/fast_buy_car_bot"
                },
                "capture": True,
                "description": f"{description} (ID: {user_id})",
                "metadata": {
                    "user_id": str(user_id)
                },
                "receipt": {
                    "customer": {
                        "email": f"{user_id}@tg.ru"
                    },
                    "items": [
                        {
                            "description": description[:128],
                            "quantity": "1.00",
                            "amount": {
                                "value": f"{amount:.2f}",
                                "currency": "RUB"
                            },
                            "vat_code": 1,
                            "payment_mode": "full_payment",
                            "payment_subject": "service"
                        }
                    ]
                }
            }

            payment = Payment.create(payment_data, self.idempotence_key)

            self.idempotence_key = str(uuid.uuid4())

            return {
                'success': True,
                'payment_id': payment.id,
                'payment_url': payment.confirmation.confirmation_url,
                'amount': float(payment.amount.value),
                'status': payment.status
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def get_payment_status(self, payment_id: str):
        try:
            payment = Payment.find_one(payment_id)

            is_paid = payment.status == 'succeeded'

            return {
                'success': True,
                'payment_id': payment.id,
                'status': payment.status,
                'is_paid': is_paid,
                'amount': float(payment.amount.value) if payment.amount else 0,
                'metadata': payment.metadata
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


_yookassa_service = None


async def get_yookassa_service():
    global _yookassa_service
    if _yookassa_service is None:
        _yookassa_service = YookassaService()
    return _yookassa_service


async def create_payment_async(amount: float, user_id: int, description: str = "Пополнение баланса"):
    service = await get_yookassa_service()
    return await service.create_payment(amount, user_id, description)


async def check_payment_async(payment_id: str):
    service = await get_yookassa_service()
    return await service.get_payment_status(payment_id)


async def close_yookassa_service():
    global _yookassa_service
    _yookassa_service = None


import asyncio
async def test_yookassa():
    print("🔄 Тестирование ЮKassa...")

    user_id = 123456789
    amount = 100.50
    description = "Тестовая оплата"

    print(f"💰 Создаем платеж: {amount} руб для пользователя {user_id}")

    payment_result = await create_payment_async(amount, user_id, description)

    if payment_result['success']:
        print(f"✅ Платеж создан успешно!")
        print(f"🆔 ID платежа: {payment_result['payment_id']}")
        print(f"🔗 Ссылка для оплаты: {payment_result['payment_url']}")
        print(f"💵 Сумма: {payment_result['amount']} руб")
        print(f"📊 Статус: {payment_result['status']}")

        payment_id = payment_result['payment_id']

        print("\n🔄 Проверяем статус платежа...")

        status_result = await check_payment_async(payment_id)

        if status_result['success']:
            print(f"✅ Статус получен: {status_result['status']}")
            print(f"💰 Оплачено: {'Да' if status_result['is_paid'] else 'Нет'}")
            print(f"📦 Метаданные: {status_result['metadata']}")
        else:
            print(f"❌ Ошибка получения статуса: {status_result['error']}")

    else:
        print(f"❌ Ошибка создания платежа: {payment_result['error']}")

    await close_yookassa_service()
    print("\n✅ Тест завершен")


if __name__ == "__main__":
    asyncio.run(test_yookassa())
