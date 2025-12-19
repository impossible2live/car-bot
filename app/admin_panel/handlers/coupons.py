from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from decimal import Decimal
from app.db.models import Coupon

router = Router()


class CouponState(StatesGroup):
    waiting_code = State()
    waiting_percent = State()
    waiting_uses = State()
    waiting_days = State()


@router.callback_query(F.data == "admin_coupons")
async def admin_coupons(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать купон", callback_data="admin_create_coupon")],
        [InlineKeyboardButton(text="📋 Список купонов", callback_data="admin_coupons_list_page_0")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text("🎫 Управление купонами", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_coupons_list_page_"))
async def admin_coupons_list(callback: CallbackQuery):
    page = int(callback.data.replace("admin_coupons_list_page_", ""))

    coupons = await Coupon.all().order_by("-created_at").all()

    if not coupons:
        text = "🎫 <b>Список купонов</b>\n\n"
        text += "Нет созданных купонов.\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать купон", callback_data="admin_create_coupon")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_coupons")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    page_size = 5
    total_pages = (len(coupons) + page_size - 1) // page_size
    current_page = max(0, min(page, total_pages - 1))

    start_idx = current_page * page_size
    end_idx = start_idx + page_size
    page_coupons = coupons[start_idx:end_idx]

    text = "🎫 <b>Список купонов</b>\n\n"
    text += f"📄 Страница {current_page + 1}/{total_pages}\n"
    text += f"🎫 Всего купонов: {len(coupons)}\n\n"

    keyboard_buttons = []

    for coupon in page_coupons:
        is_active = coupon.is_active
        status = "✅ Активен" if is_active else "❌ Неактивен"

        validity = ""
        if coupon.valid_to:
            valid_to_naive = coupon.valid_to.replace(tzinfo=None)
            current_time_naive = datetime.now()

            if valid_to_naive < current_time_naive:
                status = "⏰ Истек"
                validity = f"до {coupon.valid_to.strftime('%d.%m.%Y')}"
            else:
                validity = f"до {coupon.valid_to.strftime('%d.%m.%Y')}"

        uses_info = ""
        if coupon.max_uses:
            uses_left = coupon.max_uses - coupon.used_count
            uses_info = f"({coupon.used_count}/{coupon.max_uses})"
        else:
            uses_left = "∞"
            uses_info = f"({coupon.used_count} использовано)"

        text += f"<b>🎫 {coupon.code}</b>\n"
        text += f"📊 Скидка: {coupon.discount_percent}%\n"
        text += f"📈 Использований: {uses_info}\n"
        if validity:
            text += f"📅 {validity}\n"
        text += f"📊 Статус: {status}\n"

        if coupon.description:
            text += f"📝 Описание: {coupon.description[:30]}...\n"

        text += "─" * 25 + "\n"

        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"🎫 {coupon.code} | {coupon.discount_percent}%",
                callback_data=f"coupon_detail_{coupon.id}"
            )
        ])

    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"admin_coupons_list_page_{current_page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {current_page + 1}/{total_pages}",
        callback_data="admin_noop"
    ))

    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"admin_coupons_list_page_{current_page + 1}"
        ))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([
        InlineKeyboardButton(text="➕ Создать купон", callback_data="admin_create_coupon"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_coupons")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("coupon_detail_"))
async def coupon_detail(callback: CallbackQuery):
    coupon_id = int(callback.data.replace("coupon_detail_", ""))
    coupon = await Coupon.get(id=coupon_id)

    text = f"🎫 <b>Детальная информация о купоне</b>\n\n"
    text += f"<b>Код:</b> <code>{coupon.code}</code>\n"
    text += f"<b>Скидка:</b> {coupon.discount_percent}%\n"
    text += f"<b>Использовано:</b> {coupon.used_count} раз\n"

    if coupon.max_uses:
        text += f"<b>Макс. использований:</b> {coupon.max_uses}\n"
        text += f"<b>Осталось:</b> {coupon.max_uses - coupon.used_count}\n"
    else:
        text += f"<b>Макс. использований:</b> безлимит\n"

    if coupon.valid_from:
        text += f"<b>Действует с:</b> {coupon.valid_from.strftime('%d.%m.%Y %H:%M')}\n"

    if coupon.valid_to:
        valid_to_naive = coupon.valid_to.replace(tzinfo=None)
        current_time_naive = datetime.now()

        if valid_to_naive < current_time_naive:
            text += f"<b>Срок действия:</b> ⏰ Истек {coupon.valid_to.strftime('%d.%m.%Y %H:%M')}\n"
        else:
            text += f"<b>Срок действия до:</b> {coupon.valid_to.strftime('%d.%m.%Y %H:%M')}\n"
    else:
        text += f"<b>Срок действия:</b> 🕰️ Бессрочно\n"

    text += f"<b>Статус:</b> {'✅ Активен' if coupon.is_active else '❌ Неактивен'}\n"

    if coupon.description:
        text += f"\n<b>Описание:</b>\n{coupon.description}\n"

    text += f"\n<b>Дата создания:</b> {coupon.created_at.strftime('%d.%m.%Y %H:%M')}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Удалить купон",
                callback_data=f"coupon_delete_confirm_{coupon.id}"
            ),
            InlineKeyboardButton(
                text="🔄 Статус",
                callback_data=f"coupon_toggle_status_{coupon.id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="✏️ Изменить описание",
                callback_data=f"coupon_edit_desc_{coupon.id}"
            )
        ],
        [InlineKeyboardButton(text="📋 Назад к списку", callback_data="admin_coupons_list_page_0")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("coupon_delete_confirm_"))
async def coupon_delete_confirm(callback: CallbackQuery):
    coupon_id = int(callback.data.replace("coupon_delete_confirm_", ""))
    coupon = await Coupon.get(id=coupon_id)

    text = f"⚠️ <b>Подтверждение удаления</b>\n\n"
    text += f"Вы уверены, что хотите удалить купон?\n\n"
    text += f"🎫 <code>{coupon.code}</code>\n"
    text += f"📊 Скидка: {coupon.discount_percent}%\n"
    text += f"📈 Использований: {coupon.used_count}\n\n"
    text += f"<i>Это действие нельзя отменить!</i>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"coupon_delete_{coupon.id}"),
            InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"coupon_detail_{coupon.id}")
        ]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("coupon_delete_"))
async def coupon_delete(callback: CallbackQuery):
    coupon_id = int(callback.data.replace("coupon_delete_", ""))
    coupon = await Coupon.get(id=coupon_id)

    coupon_code = coupon.code
    await coupon.delete()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Назад к списку", callback_data="admin_coupons_list_page_0")]
    ])

    await callback.message.edit_text(
        f"✅ <b>Купон удален</b>\n\n"
        f"🎫 Код: <code>{coupon_code}</code>\n"
        f"📊 Скидка: {coupon.discount_percent}%\n"
        f"📈 Использований: {coupon.used_count}\n"
        f"🗑️ Удален: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("coupon_toggle_status_"))
async def coupon_toggle_status(callback: CallbackQuery):
    coupon_id = int(callback.data.replace("coupon_toggle_status_", ""))
    coupon = await Coupon.get(id=coupon_id)

    coupon.is_active = not coupon.is_active
    await coupon.save()

    status_text = "активирован" if coupon.is_active else "деактивирован"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"coupon_detail_{coupon.id}")]
    ])

    await callback.message.edit_text(
        f"🔄 <b>Статус купона изменен</b>\n\n"
        f"🎫 Код: <code>{coupon.code}</code>\n"
        f"📊 Скидка: {coupon.discount_percent}%\n"
        f"📈 Новый статус: {'✅ Активен' if coupon.is_active else '❌ Неактивен'}\n"
        f"📅 Изменен: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_create_coupon")
async def admin_create_coupon(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Введите код купона (только латинские буквы и цифры):")
    await state.set_state(CouponState.waiting_code)
    await callback.answer()


@router.message(CouponState.waiting_code)
async def process_coupon_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()

    if not code.isalnum() or not code.isascii():
        await message.answer("❌ Код купона должен содержать только латинские буквы и цифры. Попробуйте снова:")
        return

    existing_coupon = await Coupon.filter(code=code).first()
    if existing_coupon:
        await message.answer(f"❌ Купон с кодом {code} уже существует. Введите другой код:")
        return

    await state.update_data(code=code)
    await state.set_state(CouponState.waiting_percent)
    await message.answer(f"✏️ Введите процент скидки (например: 10, 15, 20):")


@router.message(CouponState.waiting_percent)
async def process_coupon_percent(message: Message, state: FSMContext):
    try:
        percent = float(message.text.strip())
        if percent <= 0 or percent > 100:
            await message.answer("❌ Процент скидки должен быть от 1 до 100. Попробуйте снова:")
            return

        await state.update_data(percent=Decimal(str(percent)))
        await state.set_state(CouponState.waiting_uses)
        await message.answer("✏️ Введите количество использований (0 = безлимит):")
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте снова:")


@router.message(CouponState.waiting_uses)
async def process_coupon_uses(message: Message, state: FSMContext):
    try:
        uses_text = message.text.strip()
        if uses_text == "0":
            max_uses = None
        else:
            max_uses = int(uses_text)
            if max_uses < 1:
                await message.answer("❌ Количество использований должно быть больше 0. Попробуйте снова:")
                return

        await state.update_data(max_uses=max_uses)
        await state.set_state(CouponState.waiting_days)
        await message.answer("✏️ Введите срок действия в днях (0 = бессрочно):")
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте снова:")


@router.message(CouponState.waiting_days)
async def process_coupon_days(message: Message, state: FSMContext):
    try:
        days_text = message.text.strip()
        data = await state.get_data()

        if days_text == "0":
            valid_to = None
            valid_from = datetime.now()
        else:
            valid_days = int(days_text)
            if valid_days < 1:
                await message.answer("❌ Срок действия должен быть больше 0 дней. Попробуйте снова:")
                return
            valid_from = datetime.now()
            valid_to = valid_from + timedelta(days=valid_days)


        await Coupon.create(
            code=data['code'],
            discount_percent=data['percent'],
            max_uses=data['max_uses'],
            valid_from=valid_from,
            valid_to=valid_to,
            is_active=True,
            description=f"Купон создан {datetime.now().strftime('%d.%m.%Y')}"
        )

        success_text = f"✅ <b>Купон успешно создан!</b>\n\n"
        success_text += f"🎫 <b>Код:</b> <code>{data['code']}</code>\n"
        success_text += f"📊 <b>Скидка:</b> {data['percent']}%\n"

        if data['max_uses']:
            success_text += f"📈 <b>Лимит использований:</b> {data['max_uses']}\n"
        else:
            success_text += f"📈 <b>Лимит использований:</b> безлимит\n"

        if valid_to:
            success_text += f"📅 <b>Действует до:</b> {valid_to.strftime('%d.%m.%Y %H:%M')}\n"
        else:
            success_text += f"📅 <b>Срок действия:</b> бессрочно\n"

        success_text += f"📊 <b>Статус:</b> ✅ Активен\n"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 К списку купонов", callback_data="admin_coupons_list_page_0")],
            [InlineKeyboardButton(text="➕ Ещё купон", callback_data="admin_create_coupon")],
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="admin_coupons")]
        ])

        await message.answer(success_text, reply_markup=keyboard, parse_mode="HTML")
        await state.clear()

    except Exception as e:
        await message.answer(f"❌ Ошибка при создании купона: {str(e)}")
        await state.clear()


@router.callback_query(F.data == "admin_noop")
async def admin_noop_handler(callback: CallbackQuery):
    await callback.answer()