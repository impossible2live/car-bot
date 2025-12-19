from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from decimal import Decimal
from app.db.crud_admin import get_settings
from app.admin_panel.keyboards.admin_kbs import admin_prices_kb, back_to_admin_kb
from app.other import _format_price

router = Router()

class PriceState(StatesGroup):
    waiting_subscription = State()
    waiting_advert = State()
    waiting_autoteka = State()

@router.callback_query(F.data == "admin_prices")
async def admin_prices(callback: CallbackQuery):
    settings = await get_settings()
    text = f"💰 Текущие цены:\n\n"
    text += f"• Подписка: {_format_price(settings.subscription_price)} руб\n"
    text += f"• Объявление: {_format_price(settings.advert_publish_price)} руб\n"
    text += f"• Автотека: {_format_price(settings.autoteka_price)} руб\n\n"
    text += "Выберите что изменить:"
    await callback.message.edit_text(text, reply_markup=admin_prices_kb())

@router.callback_query(F.data == "admin_change_subscription")
async def admin_change_subscription(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новую цену подписки (руб):", reply_markup=back_to_admin_kb())
    await state.set_state(PriceState.waiting_subscription)

@router.callback_query(F.data == "admin_change_advert")
async def admin_change_advert(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новую цену размещения объявления (руб):", reply_markup=back_to_admin_kb())
    await state.set_state(PriceState.waiting_advert)

@router.callback_query(F.data == "admin_change_autoteka")
async def admin_change_autoteka(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите новую цену отчёта автотеки (руб):",  reply_markup=back_to_admin_kb())
    await state.set_state(PriceState.waiting_autoteka)

@router.message(PriceState.waiting_subscription)
async def process_subscription_price(message: Message, state: FSMContext):
    try:
        price = Decimal(message.text.strip().replace(',', '.'))
        if price < 0:
            await message.answer("Цена не может быть отрицательной. Введите корректное значение:")
            return
        settings = await get_settings()
        settings.subscription_price = price
        await settings.save()
        await message.answer(f"✅ Цена подписки изменена на {_format_price(price)} руб", reply_markup=back_to_admin_kb())
        await state.clear()

    except Exception as e:
        await message.answer("❌ Ошибка! Введите корректное число (например: 199, 299.99, 1500):")

@router.message(PriceState.waiting_advert)
async def process_advert_price(message: Message, state: FSMContext):
    try:
        price = Decimal(message.text.strip().replace(',', '.'))
        if price < 0:
            await message.answer("Цена не может быть отрицательной. Введите корректное значение:")
            return
        settings = await get_settings()
        settings.advert_publish_price = price
        await settings.save()
        await message.answer(f"✅ Цена размещения объявления изменена на {_format_price(price)} руб", reply_markup=back_to_admin_kb())
        await state.clear()

    except Exception as e:
        await message.answer("❌ Ошибка! Введите корректное число (например: 199, 299.99, 1500):")

@router.message(PriceState.waiting_autoteka)
async def process_autoteka_price(message: Message, state: FSMContext):
    try:
        price = Decimal(message.text.strip().replace(',', '.'))
        if price < 0:
            await message.answer("Цена не может быть отрицательной. Введите корректное значение:")
            return
        settings = await get_settings()
        settings.autoteka_price = price
        await settings.save()
        await message.answer(f"✅ Цена отчёта автотеки изменена на {_format_price(price)} руб", reply_markup=back_to_admin_kb())
        await state.clear()

    except Exception as e:
        await message.answer("❌ Ошибка! Введите корректное число (например: 199, 299.99, 1500):")

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔙 Возврат в админ-панель", reply_markup=back_to_admin_kb())