from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
from decimal import Decimal
from app.db.models import User, Advert, Transaction, Referral, AutotekaReport, Settings, AdvertPhoto
from app.other import _format_price

router = Router()

class ChangeBalance(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()

class UserSearch(StatesGroup):
    waiting_for_user_input = State()


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


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_user_search")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats_menu")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text("👥 Управление пользователями", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_stats_menu")
async def admin_stats_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Опубликованные объявления", callback_data="stats_adverts")],
        [InlineKeyboardButton(text="👤 Пользователи в боте", callback_data="stats_users")],
        [InlineKeyboardButton(text="💰 Купленные отчёты автотеки", callback_data="stats_autoteka_spent")],
        [InlineKeyboardButton(text="💵 Заработок", callback_data="stats_income")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")]
    ])

    await callback.message.edit_text("📊 Выберите раздел статистики:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_user_search")
async def admin_user_search_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔍 Введите ID пользователя или часть имени:\n"
        "Примеры:\n"
        "• 123456789\n"
        "• username",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_users")]
        ])
    )
    await state.set_state(UserSearch.waiting_for_user_input)
    await callback.answer()


@router.message(StateFilter(UserSearch.waiting_for_user_input))
async def process_user_search(message: Message, state: FSMContext):
    search_term = message.text.strip()

    if search_term.isdigit():
        user = await User.filter(id=int(search_term)).first()
        if user:
            await show_user_detail(message, user.id)
            return

    users = await User.filter(
        username__contains=search_term
    ).limit(5)

    if not users:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_user_search")]
        ])
        await message.answer("❌ Пользователь не найден. Попробуйте снова:", reply_markup=keyboard)
        return

    if len(users) == 1:
        await show_user_detail(message, users[0].id)
    else:
        keyboard_buttons = []
        for u in users:
            btn_text = f"👤 {u.id} - {u.fullname or 'Без имени'}"
            keyboard_buttons.append([InlineKeyboardButton(
                text=btn_text,
                callback_data=f"admin_user_{u.id}"
            )])

        keyboard_buttons.append([InlineKeyboardButton(
            text="◀️ Отмена",
            callback_data="admin_users"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await message.answer("Найдено несколько пользователей. Выберите:", reply_markup=keyboard)
        await state.clear()


async def show_user_detail(message: Message, user_id: int):
    user = await User.get(id=user_id)

    adverts = await Advert.filter(owner=user)
    transactions = await Transaction.filter(user=user)
    referrals = await Referral.filter(referrer=user)

    text = f"👤 <b>Информация о пользователе</b>\n\n"
    text += f"🆔 ID: <code>{user.id}</code>\n"
    text += f"👤 Имя: {user.fullname or 'Не указано'}\n"
    text += f" Юз: @{user.username or 'Не указано'}\n"
    text += f"💰 Баланс: <b>{_format_price(user.balance)}₽</b>\n"
    text += f"👑 Роль: {user.role}\n"
    text += f"📊 Статус: {user.status}\n"
    text += f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"

    text += f"<b>📊 Статистика:</b>\n"
    text += f"📢 Объявлений: {len(adverts)} шт\n"
    text += f"💰 Транзакций: {len(transactions)} шт\n"
    text += f"👥 Рефералов: {len(referrals)} шт\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Объявления", callback_data=f"user_adverts_{user.id}_page_0"),
            InlineKeyboardButton(text="💰 Транзакции", callback_data=f"user_transactions_{user.id}_page_0")
        ],
        [InlineKeyboardButton(text="💰 Изменить баланс", callback_data=f"user_change_balance_{user.id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")]
    ])

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("user_change_balance_"))
async def change_balance_start(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.replace("user_change_balance_", ""))
    user = await User.get(id=user_id)

    await state.update_data(user_id=user_id, current_balance=user.balance)

    await callback.message.edit_text(
        f"💰 <b>Изменение баланса пользователя</b>\n\n"
        f"👤 Пользователь: {user.fullname or user.id}\n"
        f"💰 Текущий баланс: <b>{_format_price(user.balance)}₽</b>\n\n"
        f"<b>Введите сумму для изменения:</b>\n"
        f"• Для пополнения: <b>+1000</b>\n"
        f"• Для списания: <b>-500</b>\n"
        f"• Чтобы установить точную сумму: <b>=2000</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"admin_user_{user_id}")]
        ])
    )
    await state.set_state(ChangeBalance.waiting_for_amount)
    await callback.answer()


@router.message(StateFilter(ChangeBalance.waiting_for_amount))
async def process_balance_amount(message: Message, state: FSMContext):
    amount_text = message.text.strip()
    data = await state.get_data()
    user_id = data['user_id']
    current_balance = data['current_balance']

    try:
        if amount_text.startswith('='):
            # Установка точной суммы
            new_balance = Decimal(amount_text[1:].strip())
            change_amount = new_balance - current_balance
            operation = "set"
        elif amount_text.startswith('+') or amount_text.startswith('-'):
            # Изменение на указанную сумму
            change_amount = Decimal(amount_text)
            new_balance = current_balance + change_amount
            operation = "change"
        else:
            # Просто число - считается как изменение
            change_amount = Decimal(amount_text)
            new_balance = current_balance + change_amount
            operation = "change"

        await state.update_data(
            change_amount=float(change_amount),
            new_balance=float(new_balance),
            operation=operation
        )

        change_amount = Decimal(str(change_amount))
        new_balance = Decimal(str(new_balance))
        user = await User.get(id=user_id)

        user.balance = new_balance
        await user.save()

        await message.answer(
            f"✅ <b>Баланс успешно обновлен!</b>\n\n"
            f"👤 Пользователь: {user.fullname or user.id}\n"
            f"📊 Изменение: {_format_price(change_amount)}₽\n"
            f"💰 Новый баланс: <b>{_format_price(new_balance)}₽</b>\n",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 К пользователю", callback_data=f"admin_user_{user_id}")]
            ])
        )

        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ <b>Ошибка!</b>\n"
            f"Неверный формат суммы. Пожалуйста, введите сумму в правильном формате.\n\n"
            f"Примеры:\n"
            f"• <b>+1000</b> - пополнить на 1000₽\n"
            f"• <b>-500</b> - списать 500₽\n"
            f"• <b>=2000</b> - установить баланс 2000₽\n\n"
            f"Ошибка: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"admin_user_{user_id}")]
            ])
        )


@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_detail(callback: CallbackQuery):
    user_id = int(callback.data.replace("admin_user_", ""))
    await callback.message.delete()
    await show_user_detail(callback.message, user_id)
    await callback.answer()


@router.callback_query(F.data.startswith("user_adverts_"))
async def show_user_adverts(callback: CallbackQuery):
    try:
        data_parts = callback.data.split("_")
        user_id = int(data_parts[2])
        page = int(data_parts[4])

        user = await User.get(id=user_id)
        adverts = await Advert.filter(owner=user).order_by("-created_at").all()

        if not adverts:
            text = f"📢 <b>Объявления пользователя {user.fullname or user.id}</b>\n\n"
            text += "Нет объявлений."

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_{user_id}")]
            ])

            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return

        pagination = Pagination(adverts, page_size=5)
        page_adverts = pagination.get_page(page)

        text = f"📢 <b>Объявления пользователя {user.fullname or user.id}</b>\n\n"
        text += f"{pagination.get_page_info()}\n\n"

        keyboard_buttons = []

        for advert in page_adverts:
            advert_date = advert.created_at.strftime("%d.%m.%Y")
            advert_status = "✅ Активно" if advert.status == "active" else "⏳ На модерации" if advert.status == "pending" else "❌ Отклонено"

            btn_text = f"🚗 {advert.name[:15]}... | {_format_price(advert.price)} | {advert_date}"
            callback_data = f"view_advert_{advert.id}"
            keyboard_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=callback_data)])

        nav_buttons = []
        if pagination.current_page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"user_adverts_{user_id}_page_{pagination.current_page - 1}"
            ))

        nav_buttons.append(InlineKeyboardButton(
            text=f"📄 {pagination.current_page + 1}/{pagination.total_pages}",
            callback_data="noop"
        ))

        if pagination.current_page < pagination.total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"user_adverts_{user_id}_page_{pagination.current_page + 1}"
            ))

        if nav_buttons:
            keyboard_buttons.append(nav_buttons)

        keyboard_buttons.append([InlineKeyboardButton(
            text="◀️ Назад к пользователю",
            callback_data=f"admin_user_{user_id}"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        print(f"Error in show_user_adverts: {e}")
        await callback.answer("❌ Ошибка при загрузке объявлений")


@router.callback_query(F.data.startswith("user_transactions_"))
async def show_user_transactions(callback: CallbackQuery):
    try:
        data_parts = callback.data.split("_")
        user_id = int(data_parts[2])
        page = int(data_parts[4])

        user = await User.get(id=user_id)
        transactions = await Transaction.filter(user=user).order_by("-created_at").all()

        if not transactions:
            text = f"💰 <b>Транзакции пользователя {user.fullname or user.id}</b>\n\n"
            text += "Нет транзакций."

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_user_{user_id}")]
            ])

            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
            return

        pagination = Pagination(transactions, page_size=5)
        page_transactions = pagination.get_page(page)

        text = f"💰 <b>Транзакции пользователя {user.fullname or user.id}</b>\n\n"
        text += f"{pagination.get_page_info()}\n\n"

        for i, trans in enumerate(page_transactions, 1):
            trans_date = trans.created_at.strftime("%d.%m.%Y %H:%M")
            trans_type = {
                "subscription": "🔔 Подписка",
                "advert": "📢 Публикация",
                "autoteka": "🔍 Автотека",
                "autotela2": "🔍 Автотека",
                "topup": "💰 Пополнение",
                "referral_bonus": "👥 Реферал",
                "other": "📊 Другое"
            }.get(trans.type, trans.type)

            amount_color = "🟢 +" if trans.amount > 0 else "🔴 "
            text += f"{i}. {trans_type}\n"
            text += f"   {amount_color}{_format_price(trans.amount)}\n"
            text += f"   📅 {trans_date}\n"
            text += "─" * 25 + "\n"

        keyboard_buttons = []

        nav_buttons = []
        if pagination.current_page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"user_transactions_{user_id}_page_{pagination.current_page - 1}"
            ))

        nav_buttons.append(InlineKeyboardButton(
            text=f"📄 {pagination.current_page + 1}/{pagination.total_pages}",
            callback_data="noop"
        ))

        if pagination.current_page < pagination.total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"user_transactions_{user_id}_page_{pagination.current_page + 1}"
            ))

        if nav_buttons:
            keyboard_buttons.append(nav_buttons)

        keyboard_buttons.append([InlineKeyboardButton(
            text="◀️ Назад к пользователю",
            callback_data=f"admin_user_{user_id}"
        )])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    except Exception as e:
        print(f"Error in show_user_transactions: {e}")
        await callback.answer("❌ Ошибка при загрузке транзакций")


@router.callback_query(F.data.startswith("view_advert_"))
async def view_advert_detail(callback: CallbackQuery):
    try:
        advert_id = int(callback.data.replace("view_advert_", ""))
        advert = await Advert.get(id=advert_id)

        photos = await AdvertPhoto.filter(advert=advert).order_by("position").all()
        photo_ids = [photo.file_id for photo in photos]

        owner = await User.get(id=advert.owner_id)

        autoteka_report = await AutotekaReport.filter(advert=advert).first()
        autoteka_info = "✅ Куплен" if autoteka_report else "❌ Нет"

        preview_text = f"""
🚗 {advert.name or 'Не указано'}
🔢 Год выпуска: {advert.year or 'Не указано'}
📏 Пробег: {advert.mileage:,} км
⭐ Состояние: {advert.condition or 'Не указано'}
💰 Цена: {_format_price(advert.price)}
⛽ Топливо: {advert.fuel_type or 'Не указано'}
⚙️ Двигатель: {advert.engine_volume or 'Не указано'} л
🔧 КПП: {advert.transmission or 'Не указано'}
🚙 Кузов: {advert.body_type or 'Не указано'}
🎨 Цвет: {advert.color or 'Не указано'}
🔢 VIN: {advert.vin or 'Не указано'}
🔍 Отчёт автотеки: {autoteka_info}
🚘 Гос номер: {advert.license_plate or 'Не указано'}
🌍 Город: {advert.city or 'Не указано'}
📞 Контакты: {advert.contacts or 'Не указано'}

👤 Владелец: {owner.fullname or 'Не указано'} (ID: {owner.id})
📊 Статус: {advert.status}
📅 Дата создания: {advert.created_at.strftime('%d.%m.%Y %H:%M')}

📝 Описание:
{advert.description or 'Не указано'}
"""
        if photo_ids:
            media = []
            media.append(InputMediaPhoto(
                media=photo_ids[0],
                caption=preview_text
            ))

            for photo_id in photo_ids[1:]:
                media.append(InputMediaPhoto(media=photo_id))

            await callback.message.answer_media_group(media=media)

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
            ])
            await callback.message.answer("📋 Просмотр объявления", reply_markup=keyboard)
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
            ])
            await callback.message.answer(f"📋 Просмотр объявления:\n{preview_text}", reply_markup=keyboard)

        await callback.answer()

    except Exception as e:
        print(f"Error in view_advert_detail: {e}")
        await callback.answer("❌ Ошибка при загрузке объявления")



@router.callback_query(F.data == "stats_adverts")
async def stats_adverts(callback: CallbackQuery):
    await show_adverts_page(callback, page=0)
    await callback.answer()


async def show_adverts_page(callback: CallbackQuery, page: int):
    adverts = await Advert.filter(status="active").order_by("-created_at").all()

    if not adverts:
        text = "📢 <b>Опубликованные объявления</b>\n\nНет активных объявлений."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        return

    pagination = Pagination(adverts, page_size=5)
    page_adverts = pagination.get_page(page)

    text = "📢 <b>Опубликованные объявления</b>\n\n"
    text += f"{pagination.get_page_info()}\n"
    text += f"Всего активных: {len(adverts)}\n\n"

    keyboard_buttons = []

    for advert in page_adverts:
        try:
            owner = await User.get(id=advert.owner_id)
            owner_info = f"{owner.fullname or 'Без имени'}" if owner else "Не найден"
        except:
            owner_info = "Не найден"

        date_str = advert.created_at.strftime("%d.%m.%Y")

        btn_text = f"🚗 {advert.name[:20]}... | {_format_price(advert.price)}"
        callback_data = f"view_advert_{advert.id}"
        keyboard_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=callback_data)])

        text += f"• {owner_info} | {date_str}\n"

    nav_buttons = []
    if pagination.current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"adverts_page_{pagination.current_page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {pagination.current_page + 1}/{pagination.total_pages}",
        callback_data="noop"
    ))

    if pagination.current_page < pagination.total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"adverts_page_{pagination.current_page + 1}"
        ))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="admin_stats_menu"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("adverts_page_"))
async def handle_adverts_page(callback: CallbackQuery):
    page = int(callback.data.replace("adverts_page_", ""))
    await show_adverts_page(callback, page)
    await callback.answer()


@router.callback_query(F.data == "stats_users")
async def stats_users(callback: CallbackQuery):
    await show_users_page(callback, page=0)
    await callback.answer()


async def show_users_page(callback: CallbackQuery, page: int):
    users = await User.all().order_by("-created_at").all()

    if not users:
        text = "👤 <b>Пользователи в боте</b>\n\nНет пользователей."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats_menu")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        return

    pagination = Pagination(users, page_size=5)
    page_users = pagination.get_page(page)

    total_users = len(users)
    owners = await User.filter(role="owner").count()
    admins = await User.filter(role="admin").count()
    moderators = await User.filter(role="moderator").count()
    users_count = await User.filter(role="user").count()

    text = "👤 <b>Пользователи в боте</b>\n\n"
    text += f"<b>Общая статистика:</b>\n"
    text += f"👑 Владельцев: {owners}\n"
    text += f"⚡ Админов: {admins}\n"
    text += f"👮 Модераторов: {moderators}\n"
    text += f"👤 Пользователей: {users_count}\n"
    text += f"📈 Всего: {total_users}\n\n"

    text += f"{pagination.get_page_info()}\n\n"

    keyboard_buttons = []

    for user in page_users:
        date_str = user.created_at.strftime("%d.%m.%Y")

        btn_text = f"👤 {user.fullname or f'ID: {user.id}'}"
        callback_data = f"admin_user_{user.id}"
        keyboard_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=callback_data)])

        text += f"• {user.fullname or 'Без имени'} | 🆔 {user.id} | 👑 {user.role} | 📅 {date_str}\n"

    nav_buttons = []
    if pagination.current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"users_page_{pagination.current_page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {pagination.current_page + 1}/{pagination.total_pages}",
        callback_data="noop"
    ))

    if pagination.current_page < pagination.total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"users_page_{pagination.current_page + 1}"
        ))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="admin_stats_menu"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("users_page_"))
async def handle_users_page(callback: CallbackQuery):
    page = int(callback.data.replace("users_page_", ""))
    await show_users_page(callback, page)
    await callback.answer()


@router.callback_query(F.data == "stats_autoteka_spent")
async def stats_autoteka_spent(callback: CallbackQuery):
    await show_autoteka_spent_page(callback, page=0)
    await callback.answer()


async def show_autoteka_spent_page(callback: CallbackQuery, page: int):
    settings = await Settings.first()
    if not settings:
        await callback.answer("❌ Настройки не найдены")
        return

    autoteka_price_user = settings.autoteka_price

    autoteka_transactions = await Transaction.filter(type__in=["autoteka", "autoteka2"]).all()

    user_reports = {}

    for transaction in autoteka_transactions:
        user_id = transaction.user_id

        if user_id not in user_reports:
            user_reports[user_id] = {
                'reports_count': 0,
                'user': None
            }

        amount_spent = abs(transaction.amount)
        if autoteka_price_user > 0:
            reports_from_transaction = int(amount_spent / autoteka_price_user)
        else:
            reports_from_transaction = 1

        user_reports[user_id]['reports_count'] += reports_from_transaction

    for user_id in user_reports.keys():
        user = await User.get_or_none(id=user_id)
        user_reports[user_id]['user'] = user

    users_list = []
    for user_id, data in user_reports.items():
        users_list.append({
            'user_id': user_id,
            'reports_count': data['reports_count'],
            'user': data['user']
        })

    users_list.sort(key=lambda x: x['reports_count'], reverse=True)

    if not users_list:
        text = "💰 <b>Купленные отчёты автотеки</b>\n\n"
        text += "Нет данных о покупках автотек."

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats_menu")]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        return

    pagination = Pagination(users_list, page_size=10)
    page_users = pagination.get_page(page)

    text = "💰 <b>Купленные отчёты автотеки</b>\n\n"

    text += f"<b>Общая статистика:</b>\n"
    text += f"🔍 Цена отчета: <b>{_format_price(autoteka_price_user)}</b>\n"
    text += f"📊 Всего отчетов куплено: <b>{sum(u['reports_count'] for u in users_list)} шт</b>\n"
    text += f"👤 Пользователей купили: <b>{len(users_list)}</b>\n\n"

    text += f"{pagination.get_page_info()}\n\n"

    for i, user_data in enumerate(page_users, 1):
        user = user_data['user']
        user_id = user_data['user_id']

        username = f"@{user.username}" if user and user.username else f"ID: {user_id}"
        user_name = user.fullname if user and user.fullname else username

        text += f"{i}. <b>{user_name}</b>\n"
        text += f"   📊 Отчетов куплено: <b>{user_data['reports_count']} шт</b>\n"
        text += f"   🆔 ID: <code>{user_id}</code>\n"
        text += "─" * 25 + "\n"

    keyboard_buttons = []

    nav_buttons = []
    if pagination.current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"autoteka_spent_page_{pagination.current_page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {pagination.current_page + 1}/{pagination.total_pages}",
        callback_data="noop"
    ))

    if pagination.current_page < pagination.total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"autoteka_spent_page_{pagination.current_page + 1}"
        ))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="admin_stats_menu"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("autoteka_spent_page_"))
async def handle_autoteka_spent_page(callback: CallbackQuery):
    page = int(callback.data.replace("autoteka_spent_page_", ""))
    await show_autoteka_spent_page(callback, page)
    await callback.answer()


@router.callback_query(F.data == "stats_income")
async def stats_income(callback: CallbackQuery):
    settings = await Settings.first()
    if not settings:
        await callback.answer("❌ Настройки не найдены")
        return

    autoteka_price_user = settings.autoteka_price
    AUTOTEKA_COST = Decimal('99')

    income_transactions = await Transaction.filter(
        type__in=["subscription", "advert", "autoteka", "autoteka2"]
    ).all()

    topup_transactions = await Transaction.filter(type="topup").all()

    income_by_type_all_time = {
        "subscription": Decimal('0'),
        "advert": Decimal('0'),
        "autoteka": Decimal('0'),
        "autoteka2": Decimal('0'),
        "total": Decimal('0')
    }

    income_by_type_month = {
        "subscription": Decimal('0'),
        "advert": Decimal('0'),
        "autoteka": Decimal('0'),
        "autoteka2": Decimal('0'),
        "total": Decimal('0')
    }

    current_month = datetime.now().month
    current_year = datetime.now().year

    total_topup_all_time = Decimal('0')
    total_topup_month = Decimal('0')

    for transaction in topup_transactions:
        if transaction.amount > 0:
            total_topup_all_time += transaction.amount

            if (transaction.created_at.month == current_month and
                    transaction.created_at.year == current_year):
                total_topup_month += transaction.amount

    for transaction in income_transactions:
        if transaction.amount > 0:
            income_by_type_all_time[transaction.type] += transaction.amount
            income_by_type_all_time["total"] += transaction.amount

            if (transaction.created_at.month == current_month and
                    transaction.created_at.year == current_year):
                income_by_type_month[transaction.type] += transaction.amount
                income_by_type_month["total"] += transaction.amount

    autoteka_transactions_all_time = await Transaction.filter(type__in=["autoteka", "autoteka2"]).all()
    total_autoteka_reports_all_time = 0
    total_autoteka_income = Decimal('0')

    for transaction in autoteka_transactions_all_time:
        if transaction.amount < 0:
            amount_spent = abs(transaction.amount)
            total_autoteka_income += amount_spent

            if autoteka_price_user > 0:
                total_autoteka_reports_all_time += int(amount_spent / autoteka_price_user)

    total_autoteka_expenses = Decimal('0')
    if total_autoteka_reports_all_time > 0:
        total_autoteka_expenses = total_autoteka_reports_all_time * AUTOTEKA_COST

    net_autoteka_profit = total_autoteka_income - total_autoteka_expenses

    text = "💵 <b>Статистика заработка</b>\n\n"

    text += f"<b>💰 Цены:</b>\n"
    text += f"🔍 Автотека в боте: <b>{_format_price(autoteka_price_user)}</b>\n"
    text += f"💰 Себестоимость отчета: <b>{_format_price(AUTOTEKA_COST)}</b>\n\n"

    text += "<b>📅 <u>За ВСЁ время:</u></b>\n"
    text += f"🔔 Подписки: <b>{_format_price(income_by_type_all_time['subscription'])}</b>\n"
    text += f"📢 Публикации: <b>{_format_price(income_by_type_all_time['advert'])}</b>\n"
    text += f"🔍 Автотека (доход): <b>{_format_price(total_autoteka_income)}</b>\n"
    text += f"🔍 Автотека (расходы): <b>{_format_price(total_autoteka_expenses)}</b>\n"
    text += f"🔍 Автотека (чистая): <b>{_format_price(net_autoteka_profit)}</b>\n"
    text += f"📊 Отчетов автотеки: <b>{total_autoteka_reports_all_time} шт</b>\n"
    text += f"💰 Пополнения баланса: <b>{_format_price(total_topup_all_time)}</b>\n"

    total_income_all_time = (income_by_type_all_time['subscription'] +
                             income_by_type_all_time['advert'] +
                             total_autoteka_income)

    total_expenses_all_time = total_autoteka_expenses

    text += f"📈 Общий доход: <b>{_format_price(total_income_all_time)}</b>\n"
    text += f"💸 Общие расходы: <b>{_format_price(total_expenses_all_time)}</b>\n"
    text += f"✅ Чистая прибыль: <b>{_format_price(total_income_all_time - total_expenses_all_time)}</b>\n\n"

    current_month_name = datetime.now().strftime("%B %Y")
    text += f"<b>📅 <u>За {current_month_name}:</u></b>\n"
    text += f"🔔 Подписки: <b>{_format_price(income_by_type_month['subscription'])}</b>\n"
    text += f"📢 Публикации: <b>{_format_price(income_by_type_month['advert'])}</b>\n"

    autoteka_income_month = Decimal('0')
    autoteka_reports_month = 0

    for transaction in autoteka_transactions_all_time:
        if (transaction.amount < 0 and
                transaction.created_at.month == current_month and
                transaction.created_at.year == current_year):

            amount_spent = abs(transaction.amount)
            autoteka_income_month += amount_spent

            if autoteka_price_user > 0:
                autoteka_reports_month += int(amount_spent / autoteka_price_user)

    autoteka_expenses_month = autoteka_reports_month * AUTOTEKA_COST
    net_autoteka_profit_month = autoteka_income_month - autoteka_expenses_month

    text += f"🔍 Автотека (доход): <b>{_format_price(autoteka_income_month)}</b>\n"
    text += f"🔍 Автотека (чистая): <b>{_format_price(net_autoteka_profit_month)}</b>\n"
    text += f"📊 Отчетов автотеки: <b>{autoteka_reports_month} шт</b>\n"
    text += f"💰 Пополнения баланса: <b>{_format_price(total_topup_month)}</b>\n"

    total_income_month = (income_by_type_month['subscription'] +
                          income_by_type_month['advert'] +
                          autoteka_income_month)

    text += f"📈 Итого за месяц: <b>{_format_price(total_income_month)}</b>\n"
    text += f"✅ Чистая прибыль: <b>{_format_price(total_income_month - autoteka_expenses_month)}</b>\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_stats_menu")]
    ])

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery):
    await callback.answer()