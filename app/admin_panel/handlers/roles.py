from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.db.models import User
from app.services.autoteca_no_api import get_remaining_reports_async

router = Router(name=__name__)


class RoleChangeState(StatesGroup):
    waiting_for_user_input = State()


@router.callback_query(F.data == "admin_roles_menu")
async def manage_roles_menu(callback: CallbackQuery):
    admins = await User.filter(role__in=["admin", "owner", "moderator"]).order_by("-created_at").all()

    keyboard_buttons = []

    if admins:
        text = "👑 <b>Управление ролями</b>\n\n"
        text += "<b>Текущие администраторы и модераторы:</b>\n\n"

        for i, admin_user in enumerate(admins, 1):
            role_icon = {
                "owner": "👑",
                "admin": "⚡",
                "moderator": "🛡️"
            }.get(admin_user.role, "👤")

            text += f"{i}. {role_icon} {admin_user.fullname or 'Без имени'}\n"
            text += f"   🆔 ID: <code>{admin_user.id}</code>\n"
            text += f"   📊 Роль: {admin_user.role}\n"
            text += "─" * 25 + "\n"

            keyboard_buttons.append([InlineKeyboardButton(
                text=f"{role_icon} Изменить {admin_user.fullname or f'ID {admin_user.id}'}",
                callback_data=f"roles_change_user_{admin_user.id}"
            )])

    else:
        text = "👑 <b>Управление ролями</b>\n\n"
        text += "Нет администраторов и модераторов.\n"

    keyboard_buttons.extend([
        [InlineKeyboardButton(text="🔍 Найти пользователя по ID", callback_data="roles_find_user")],
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="roles_all_users_page_0")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "roles_find_user")
async def find_user_for_role(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_roles_menu")]
    ])

    await callback.message.edit_text(
        "🔍 Введите ID пользователя для изменения роли:\n"
        "Пример: <code>123456789</code>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(RoleChangeState.waiting_for_user_input)
    await callback.answer()


@router.message(StateFilter(RoleChangeState.waiting_for_user_input))
async def process_user_id_for_role(message: Message, state: FSMContext):
    user_input = message.text.strip()

    await state.clear()

    if not user_input.isdigit():
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="roles_find_user")]
        ])
        await message.answer("❌ Пожалуйста, введите корректный ID (только цифры)", reply_markup=keyboard)
        return

    target_id = int(user_input)
    target_user = await User.get_or_none(id=target_id)

    if not target_user:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="roles_find_user")]
        ])
        await message.answer("❌ Пользователь не найден. Попробуйте другой ID.", reply_markup=keyboard)
        return

    await show_role_selection(message, target_user)


async def show_role_selection(message: Message, target_user: User):
    text = f"👤 <b>Выбор роли для пользователя</b>\n\n"
    text += f"🆔 ID: <code>{target_user.id}</code>\n"
    text += f"👤 Имя: {target_user.fullname or 'Не указано'}\n"
    text += f"📊 Текущая роль: {target_user.role}\n"
    text += f"📅 Дата регистрации: {target_user.created_at.strftime('%d.%m.%Y')}\n\n"

    text += "<b>Выберите новую роль:</b>"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 Пользователь", callback_data=f"roles_set_user_{target_user.id}"),
            InlineKeyboardButton(text="🔒 Забанен", callback_data=f"roles_set_banned_{target_user.id}")
        ],
        [
            InlineKeyboardButton(text="👻 Теневой бан", callback_data=f"roles_set_shadow_{target_user.id}"),
            InlineKeyboardButton(text="🛡️ Модератор", callback_data=f"roles_set_moderator_{target_user.id}")
        ],
        [
            InlineKeyboardButton(text="⚡ Админ", callback_data=f"roles_set_admin_{target_user.id}"),
            InlineKeyboardButton(text="👑 Владелец", callback_data=f"roles_set_owner_{target_user.id}")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_roles_menu")]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("roles_change_user_"))
async def quick_change_role(callback: CallbackQuery):
    target_id = int(callback.data.replace("roles_change_user_", ""))
    target_user = await User.get(id=target_id)

    await callback.message.delete()
    await show_role_selection(callback.message, target_user)
    await callback.answer()


@router.callback_query(F.data.startswith("roles_set_"))
async def set_user_role(callback: CallbackQuery):
    data = callback.data.replace("roles_set_", "")
    role_parts = data.split("_")

    if len(role_parts) < 2:
        await callback.answer("❌ Ошибка данных")
        return

    role = role_parts[0]
    target_id = int(role_parts[1])

    role_mapping = {
        "user": "user",
        "banned": "user",
        "shadow": "user",
        "moderator": "moderator",
        "admin": "admin",
        "owner": "owner"
    }

    db_role = role_mapping.get(role, "user")

    target_user = await User.get(id=target_id)

    old_role = target_user.role
    old_status = target_user.status

    target_user.role = db_role

    if role == "banned":
        target_user.status = "banned"
    elif role == "shadow":
        target_user.status = "shadow_ban"
    else:
        target_user.status = "active"

    await target_user.save()

    role_names = {
        "user": "👤 Пользователь",
        "moderator": "🛡️ Модератор",
        "admin": "⚡ Админ",
        "owner": "👑 Владелец"
    }

    role_display = role_names.get(db_role, "👤 Пользователь")
    status_display = '🔒 Забанен' if role == 'banned' else '👻 Теневой бан' if role == 'shadow' else '✅ Активен'

    try:
        await callback.bot.send_message(
            target_id,
            f"👑 Ваша роль изменена!\n"
            f"📊 Новая роль: {role_display}\n"
            f"📋 Статус: {status_display}"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление пользователю {target_id}: {e}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад к управлению ролями", callback_data="admin_roles_menu")]
    ])

    await callback.message.edit_text(
        f"✅ <b>Роль успешно изменена!</b>\n\n"
        f"👤 Пользователь: {target_user.fullname or f'ID {target_user.id}'}\n"
        f"🆔 ID: <code>{target_user.id}</code>\n"
        f"📊 Старая роль: {old_role}\n"
        f"📊 Новая роль: {role_display}\n"
        f"📋 Статус: {status_display}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

    await callback.answer()


@router.callback_query(F.data.startswith("roles_all_users_page_"))
async def all_users_for_roles(callback: CallbackQuery):
    page = int(callback.data.replace("roles_all_users_page_", ""))

    users = await User.all().order_by("-created_at").all()

    if not users:
        await callback.message.edit_text(
            "👥 Нет пользователей в базе.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_roles_menu")]
            ])
        )
        await callback.answer()
        return

    page_size = 5
    total_pages = (len(users) + page_size - 1) // page_size
    current_page = max(0, min(page, total_pages - 1))

    start_idx = current_page * page_size
    end_idx = start_idx + page_size
    page_users = users[start_idx:end_idx]

    text = f"👥 <b>Все пользователи</b>\n\n"
    text += f"📄 Страница {current_page + 1}/{total_pages}\n"
    text += f"👤 Всего пользователей: {len(users)}\n\n"

    keyboard_buttons = []

    for user in page_users:
        role_icon = {
            "owner": "👑",
            "admin": "⚡",
            "moderator": "🛡️",
            "user": "👤"
        }.get(user.role, "👤")

        btn_text = f"{role_icon} {user.fullname or f'ID {user.id}'}"
        callback_data = f"roles_change_user_{user.id}"
        keyboard_buttons.append([InlineKeyboardButton(text=btn_text, callback_data=callback_data)])

        text += f"• {user.fullname or 'Без имени'} | 🆔 {user.id} | {role_icon} {user.role}\n"

    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"roles_all_users_page_{current_page - 1}"
        ))

    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {current_page + 1}/{total_pages}",
        callback_data="roles_noop"
    ))

    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="Вперед ➡️",
            callback_data=f"roles_all_users_page_{current_page + 1}"
        ))

    if nav_buttons:
        keyboard_buttons.append(nav_buttons)

    keyboard_buttons.append([InlineKeyboardButton(
        text="◀️ Назад",
        callback_data="admin_roles_menu"
    )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_check_autoteka")
async def autoteka_count(callback: CallbackQuery):
    from app.db.models import AutotekaBalance

    await callback.message.edit_text("⌛ Пожалуйста подождите...")
    remaining = await get_remaining_reports_async()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
    ])

    await callback.message.edit_text(
        f"🔍 <b>Остаток отчетов автотеки</b>\n\n"
        f"📊 <b>Доступно отчетов:</b> {remaining}\n\n",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "roles_noop")
async def roles_noop_handler(callback: CallbackQuery):
    await callback.answer()