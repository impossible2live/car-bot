from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.db.models import Advert, User, AdvertPhoto, AutotekaReport
from app.admin_panel.keyboards.admin_kbs import admin_adverts_kb, back_to_admin_kb
from app.other import _format_price
from decimal import Decimal

router = Router()


class ModerationState(StatesGroup):
    waiting_reason = State()


class Pagination:
    def __init__(self, items, page_size=5):
        self.items = items
        self.page_size = page_size
        self.total_pages = (len(items) + page_size - 1) // page_size
        self.current_page = 0

    def get_page(self, page):
        self.current_page = max(0, min(page, self.total_pages - 1))
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.items[start:end]

    def get_page_info(self):
        return f"Страница {self.current_page + 1}/{self.total_pages}"


@router.callback_query(F.data == "admin_adverts")
async def admin_adverts(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Все объявления", callback_data="admin_adverts_all_page_0")],
        [InlineKeyboardButton(text="✅ Активные", callback_data="admin_adverts_active_page_0")],
        [InlineKeyboardButton(text="⏳ На модерации", callback_data="admin_adverts_pending_page_0")],
        [InlineKeyboardButton(text="❌ Отклоненные", callback_data="admin_adverts_rejected_page_0")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text("📢 Управление объявлениями", reply_markup=keyboard)


async def show_adverts_page(callback: CallbackQuery, status_filter: str = None, page: int = 0):
    if status_filter:
        adverts = await Advert.filter(status=status_filter).order_by("-created_at").prefetch_related('owner').all()
        status_name = {
            "active": "✅ Активные",
            "pending": "⏳ На модерации",
            "rejected": "❌ Отклоненные",
            "archived": "📁 Архивные"
        }.get(status_filter, "Все")
    else:
        adverts = await Advert.all().order_by("-created_at").prefetch_related('owner').all()
        status_name = "📋 Все"

    if not adverts:
        text = f"{status_name} объявления\n\nНет объявлений."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_adverts")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        return

    pagination = Pagination(adverts, page_size=5)
    page_adverts = pagination.get_page(page)

    text = f"{status_name} объявления\n\n"
    text += f"{pagination.get_page_info()}\n"
    text += f"Всего: {len(adverts)}\n\n"

    keyboard_buttons = []

    for advert in page_adverts:
        owner_name = advert.owner.fullname or f"ID: {advert.owner.id}"
        date_str = advert.created_at.strftime("%d.%m.%Y")

        advert_name = advert.name
        if len(advert_name) > 25:
            advert_name = advert_name[:22] + "..."

        btn_text = f"🚗 {advert_name} | {_format_price(advert.price)}"
        callback_data = f"view_admin_advert_{advert.id}"
        keyboard_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=callback_data)])

        status_icon = {
            "active": "✅",
            "pending": "⏳",
            "rejected": "❌",
            "archived": "📁"
        }.get(advert.status, "📄")

        text += f"{status_icon} {owner_name} | {date_str}\n"

    nav_buttons = []
    if pagination.current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"admin_adverts_{status_filter or 'all'}_page_{pagination.current_page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {pagination.current_page + 1}/{pagination.total_pages}",
        callback_data="noop"
    ))

    if pagination.current_page < pagination.total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"admin_adverts_{status_filter or 'all'}_page_{pagination.current_page + 1}"
        ))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="admin_adverts"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data == "admin_adverts_all_page_0")
@router.callback_query(F.data.startswith("admin_adverts_all_page_"))
async def admin_adverts_all(callback: CallbackQuery):
    if callback.data == "admin_adverts_all_page_0":
        page = 0
    else:
        page = int(callback.data.replace("admin_adverts_all_page_", ""))
    await show_adverts_page(callback, None, page)


@router.callback_query(F.data == "admin_adverts_active_page_0")
@router.callback_query(F.data.startswith("admin_adverts_active_page_"))
async def admin_adverts_active(callback: CallbackQuery):
    if callback.data == "admin_adverts_active_page_0":
        page = 0
    else:
        page = int(callback.data.replace("admin_adverts_active_page_", ""))
    await show_adverts_page(callback, "active", page)


@router.callback_query(F.data == "admin_adverts_pending_page_0")
@router.callback_query(F.data.startswith("admin_adverts_pending_page_"))
async def admin_adverts_pending(callback: CallbackQuery):
    if callback.data == "admin_adverts_pending_page_0":
        page = 0
    else:
        page = int(callback.data.replace("admin_adverts_pending_page_", ""))
    await show_adverts_page(callback, "pending", page)


@router.callback_query(F.data == "admin_adverts_rejected_page_0")
@router.callback_query(F.data.startswith("admin_adverts_rejected_page_"))
async def admin_adverts_rejected(callback: CallbackQuery):
    if callback.data == "admin_adverts_rejected_page_0":
        page = 0
    else:
        page = int(callback.data.replace("admin_adverts_rejected_page_", ""))
    await show_adverts_page(callback, "rejected", page)


@router.callback_query(F.data.startswith("view_admin_advert_"))
async def admin_advert_detail(callback: CallbackQuery):
    advert_id = int(callback.data.replace("view_admin_advert_", ""))
    advert = await Advert.get(id=advert_id).prefetch_related('owner')

    photos = await AdvertPhoto.filter(advert=advert).order_by("position").all()
    photo_ids = [photo.file_id for photo in photos]

    autoteka_report = await AutotekaReport.filter(advert=advert).first()
    autoteka_info = "✅ Куплен" if autoteka_report else "❌ Нет"

    text = f"📢 <b>Объявление #{advert.id}</b>\n\n"
    text += f"🚗 <b>{advert.name}</b>\n"
    text += f"🔢 Год выпуска: {advert.year}\n"
    text += f"📏 Пробег: {advert.mileage:,} км\n"
    text += f"⭐ Состояние: {advert.condition}\n"
    text += f"💰 Цена: {_format_price(advert.price)}\n"
    text += f"⛽ Топливо: {advert.fuel_type}\n"
    text += f"⚙️ Двигатель: {advert.engine_volume} л\n"
    text += f"🔧 КПП: {advert.transmission}\n"
    text += f"🚙 Кузов: {advert.body_type}\n"
    text += f"🎨 Цвет: {advert.color}\n"
    text += f"🔢 VIN: {advert.vin}\n"
    text += f"🔍 Отчёт автотеки: {autoteka_info}\n"
    text += f"🚘 Гос номер: {advert.license_plate}\n"
    text += f"🌍 Город: {advert.city}\n"
    text += f"📞 Контакты: {advert.contacts}\n"
    text += f"👤 Владелец: {advert.owner.fullname or 'Не указано'} (ID: {advert.owner.id})\n"

    status_text = {
        "active": "✅ Активно",
        "pending": "⏳ На модерации",
        "rejected": "❌ Отклонено",
        "archived": "📁 В архиве",
        "waiting_to_pay": "💰 Ожидает оплаты"
    }.get(advert.status, advert.status)

    text += f"📊 Статус: {status_text}\n"
    text += f"📅 Дата создания: {advert.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    text += f"📝 <b>Описание:</b>\n{advert.description}\n"

    keyboard_buttons = []

    if advert.status == "active":
        keyboard_buttons.append([InlineKeyboardButton(
            text="❌ Снять с публикации",
            callback_data=f"hide_admin_advert_{advert.id}"
        )])
    elif advert.status == "pending":
        keyboard_buttons.append([
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_admin_advert_{advert.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_admin_advert_{advert.id}")
        ])
    elif advert.status == "archived":
        keyboard_buttons.append([InlineKeyboardButton(
            text="🔄 Восстановить",
            callback_data=f"restore_admin_advert_{advert.id}"
        )])

    keyboard_buttons.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="admin_adverts_all_page_0"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    if photo_ids:
        try:
            media = []
            media.append(InputMediaPhoto(
                media=photo_ids[0],
                caption=text,
                parse_mode="HTML"
            ))

            for photo_id in photo_ids[1:]:
                media.append(InputMediaPhoto(media=photo_id))

            await callback.message.answer_media_group(media=media)
            await callback.message.answer("📋 Просмотр объявления", reply_markup=keyboard)
        except Exception as e:
            print(f"Error sending photos: {e}")
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("hide_admin_advert_"))
async def hide_advert(callback: CallbackQuery, state: FSMContext):
    advert_id = int(callback.data.replace("hide_admin_advert_", ""))
    await state.update_data(advert_id=advert_id)
    await state.set_state(ModerationState.waiting_reason)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"view_admin_advert_{advert_id}")]
    ])

    await callback.message.edit_text("✏️ Введите причину снятия с публикации:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("restore_admin_advert_"))
async def restore_advert(callback: CallbackQuery):
    advert_id = int(callback.data.replace("restore_admin_advert_", ""))

    advert = await Advert.get(id=advert_id)
    advert.status = "active"
    await advert.save()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"view_admin_advert_{advert_id}")]
    ])

    await callback.message.edit_text("✅ Объявление восстановлено и опубликовано", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("approve_admin_advert_"))
async def approve_advert(callback: CallbackQuery):
    advert_id = int(callback.data.replace("approve_admin_advert_", ""))

    advert = await Advert.get(id=advert_id)
    advert.status = "active"
    await advert.save()

    try:
        await callback.bot.send_message(
            chat_id=advert.owner_id,
            text=f"✅ Ваше объявление #{advert.id} одобрено и опубликовано!"
        )
    except:
        pass

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_adverts_pending_page_0")]
    ])

    await callback.message.edit_text("✅ Объявление одобрено и опубликовано", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("reject_admin_advert_"))
async def reject_advert(callback: CallbackQuery, state: FSMContext):
    advert_id = int(callback.data.replace("reject_admin_advert_", ""))
    await state.update_data(advert_id=advert_id)
    await state.set_state(ModerationState.waiting_reason)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"view_admin_advert_{advert_id}")]
    ])

    await callback.message.edit_text("✏️ Введите причину отклонения:", reply_markup=keyboard)


@router.message(ModerationState.waiting_reason)
async def process_hide_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    advert_id = data["advert_id"]
    reason = message.text

    advert = await Advert.get(id=advert_id)

    if advert.status == "active":
        advert.status = "archived"
        action_text = "снято с публикации"
        notify_text = f"❌ Ваше объявление #{advert.id} снято с публикации\nПричина: {reason}"
    else:  # pending
        advert.status = "rejected"
        action_text = "отклонено"
        notify_text = f"❌ Ваше объявление #{advert.id} отклонено\nПричина: {reason}"

    await advert.save()

    try:
        await message.bot.send_message(
            chat_id=advert.owner_id,
            text=notify_text
        )
    except:
        pass

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_adverts")]
    ])

    await message.answer(f"✅ Объявление #{advert.id} {action_text}", reply_markup=keyboard)
    await state.clear()


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()