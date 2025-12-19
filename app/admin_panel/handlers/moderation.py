from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.db.models import Advert, User, AdvertPhoto, AutotekaReport
from app.admin_panel.keyboards.admin_kbs import admin_moderation_kb, back_to_admin_kb
from app.db.crud_advert import reject_advert_and_refund
from app.other import _format_price

router = Router()


class ModerationState(StatesGroup):
    waiting_reject_reason = State()


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


@router.callback_query(F.data == "admin_moderation")
async def admin_moderation(callback: CallbackQuery):
    await show_moderation_page(callback, page=0)


async def show_moderation_page(callback: CallbackQuery, page: int):
    adverts = await Advert.filter(status="pending").order_by("-created_at").prefetch_related('owner').all()

    if not adverts:
        text = "📝 <b>Объявления на модерации</b>\n\n"
        text += "✅ Нет объявлений, ожидающих проверки."

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_moderation")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ])

        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            pass
        await callback.answer()
        return

    pagination = Pagination(adverts, page_size=5)
    page_adverts = pagination.get_page(page)

    text = "📝 <b>Объявления на модерации</b>\n\n"
    text += f"{pagination.get_page_info()}\n"
    text += f"Всего на проверке: {len(adverts)}\n\n"

    keyboard_buttons = []

    for advert in page_adverts:
        owner_name = advert.owner.fullname or f"ID: {advert.owner.id}"
        date_str = advert.created_at.strftime("%d.%m.%Y")

        advert_name = advert.name
        if len(advert_name) > 25:
            advert_name = advert_name[:22] + "..."

        btn_text = f"🚗 {advert_name} | {_format_price(advert.price)}"
        callback_data = f"moderate_advert_detail_{advert.id}"
        keyboard_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=callback_data)])

        text += f"⏳ {owner_name} | 📅 {date_str}\n"

    nav_buttons = []
    if pagination.current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"moderation_page_{pagination.current_page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {pagination.current_page + 1}/{pagination.total_pages}",
        callback_data="noop"
    ))

    if pagination.current_page < pagination.total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"moderation_page_{pagination.current_page + 1}"
        ))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_moderation"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("moderation_page_"))
async def handle_moderation_page(callback: CallbackQuery):
    page = int(callback.data.replace("moderation_page_", ""))
    await show_moderation_page(callback, page)


@router.callback_query(F.data.regexp(r'^moderate_advert_detail_\d+$'))
async def moderate_advert_detail(callback: CallbackQuery):
    advert_id = int(callback.data.replace("moderate_advert_detail_", ""))
    advert = await Advert.get(id=advert_id).prefetch_related('owner')

    photos = await AdvertPhoto.filter(advert=advert).order_by("position").all()
    photo_ids = [photo.file_id for photo in photos]

    text = f"📝 <b>Модерация объявления #{advert.id}</b>\n\n"
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
    text += f"🚘 Гос номер: {advert.license_plate}\n"
    text += f"🌍 Город: {advert.city}\n"
    text += f"📞 Контакты: {advert.contacts}\n"
    text += f"👤 Владелец: {advert.owner.fullname or 'Не указано'} (ID: {advert.owner.id})\n"
    text += f"📅 Дата подачи: {advert.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    text += f"📝 <b>Описание:</b>\n{advert.description}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_advert_{advert.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_advert_{advert.id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_moderation")]
    ])

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
            await callback.message.answer("📋 Просмотр объявления на модерации", reply_markup=keyboard)
        except Exception as e:
            print(f"Error sending photos: {e}")
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.regexp(r'^approve_advert_\d+$'))
async def approve_advert(callback: CallbackQuery):
    advert_id = int(callback.data.replace("approve_advert_", ""))
    advert = await Advert.get(id=advert_id)

    advert.status = "active"
    await advert.save()

    try:
        await callback.bot.send_message(
            chat_id=advert.owner_id,
            text=f"✅ Ваше объявление одобрено и опубликовано!\n\n"
                 f"🚗 {advert.name}\n"
                 f"💰 Цена: {_format_price(advert.price)}\n"
                 f"📅 Дата публикации: {advert.created_at.strftime('%d.%m.%Y %H:%M')}"
        )
    except:
        pass

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к модерации", callback_data="admin_moderation")]
    ])

    await callback.message.edit_text(
        f"✅ Объявление одобрено!\n\n"
        f"🚗 {advert.name}\n"
        f"💰 Цена: {_format_price(advert.price)}\n"
        f"👤 Владелец: ID {advert.owner_id}\n"
        f"📅 Одобрено: {advert.created_at.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=keyboard
    )

    await callback.answer()


@router.callback_query(F.data.regexp(r'^reject_advert_\d+$'))
async def reject_advert_start(callback: CallbackQuery, state: FSMContext):
    advert_id = int(callback.data.replace("reject_advert_", ""))

    await state.update_data(advert_id=advert_id)
    await state.set_state(ModerationState.waiting_reject_reason)

    advert = await Advert.get(id=advert_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"moderate_advert_detail_{advert_id}")]
    ])

    await callback.message.edit_text(
        f"✏️ Введите причину отклонения объявления:\n\n"
        f"🚗 {advert.name}\n"
        f"💰 Цена: {_format_price(advert.price)}",
        reply_markup=keyboard
    )

    await callback.answer()


@router.message(ModerationState.waiting_reject_reason)
async def process_reject_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    advert_id = data["advert_id"]
    reason = message.text

    await state.clear()

    await reject_advert_and_refund(advert_id, reason, message.bot)

    advert = await Advert.get(id=advert_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к модерации", callback_data="admin_moderation")]
    ])

    await message.answer(
        f"❌ Объявление отклонено!\n\n"
        f"🚗 {advert.name}\n"
        f"💰 Цена: {_format_price(advert.price)}\n"
        f"👤 Владелец: ID {advert.owner_id}\n"
        f"📋 Причина: {reason}",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()