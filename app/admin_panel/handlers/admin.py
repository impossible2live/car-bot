from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from app.admin_panel.keyboards.admin_kbs import admin_main_kb
from app.db.models import User

router = Router(name=__name__)


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    await state.set_state(None)
    user = await User.get(id=message.from_user.id)

    if user.id != 515820746 and user.role not in ["moderator", "admin", "owner"]:
        #await message.answer("❌ Нет доступа к админ-панели")
        return

    keyboard = admin_main_kb(user.role, user.id)
    #keyboard = admin_main_kb("owner")

    if not keyboard:
        await message.answer("❌ Нет доступа")
        return

    await message.answer("👑 Админ панель", reply_markup=keyboard)


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.set_state(None)

    user = await User.get(id=callback.from_user.id)

    if user.id != 515820746 and user.role not in ["moderator", "admin", "owner"]:
        #await callback.answer("❌ Нет доступа")
        return

    keyboard = admin_main_kb(user.role, user.id)
    #keyboard = admin_main_kb("owner")
    if not keyboard:
        await callback.answer("❌ Нет доступа")
        return

    await callback.message.edit_text("👑 Админ панель", reply_markup=keyboard)
    await callback.answer()