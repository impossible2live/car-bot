from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_kb(user_role: str, user_id: int):
    if user_id == 515820746:
        user_role = "owner"
    if user_role == "moderator":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Объявления на модерации", callback_data="admin_moderation")],
        ])

    elif user_role == "admin":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Все объявления", callback_data="admin_adverts")],
            [InlineKeyboardButton(text="🔔 Рассылка", callback_data="admin_broadcast"),
             InlineKeyboardButton(text="🎫 Купоны", callback_data="admin_coupons")],
            [InlineKeyboardButton(text="💰 Цены", callback_data="admin_prices"),
             InlineKeyboardButton(text="🔍 Остаток автотек", callback_data="admin_check_autoteka")],
            [InlineKeyboardButton(text="📝 Модерация", callback_data="admin_moderation")],
        ])

    elif user_role == "owner":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пользователи и статистика", callback_data="admin_users")],
            [InlineKeyboardButton(text="📢 Все объявления", callback_data="admin_adverts")],
            [InlineKeyboardButton(text="🔔 Рассылка", callback_data="admin_broadcast"),
             InlineKeyboardButton(text="🎫 Купоны", callback_data="admin_coupons")],
            [InlineKeyboardButton(text="💰 Цены", callback_data="admin_prices"),
             InlineKeyboardButton(text="🔍 Остаток автотек", callback_data="admin_check_autoteka")],
            [InlineKeyboardButton(text="📝 Модерация", callback_data="admin_moderation"),
             InlineKeyboardButton(text="👑 Роли", callback_data="admin_roles_menu")],
        ])

    return None
def admin_users_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Общая статистика", callback_data="admin_stats_all")],
        [InlineKeyboardButton(text="👤 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

def admin_adverts_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Все объявления", callback_data="admin_adverts_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

def admin_broadcast_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

def admin_coupons_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Создать купон", callback_data="admin_create_coupon")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

def admin_prices_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Подписка", callback_data="admin_change_subscription")],
        [InlineKeyboardButton(text="📢 Объявление", callback_data="admin_change_advert")],
        [InlineKeyboardButton(text="🔍 Автотека", callback_data="admin_change_autoteka")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

def admin_moderation_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

def admin_roles_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])

def back_to_admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])