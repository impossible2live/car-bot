from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.db.models import User
from app.admin_panel.keyboards.admin_kbs import back_to_admin_kb

router = Router()


class BroadcastState(StatesGroup):
    waiting_text = State()
    waiting_media = State()
    confirm = State()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📢 Создание рассылки\n\nОтправьте текст рассылки:",
                                     reply_markup=back_to_admin_kb())
    await state.set_state(BroadcastState.waiting_text)


@router.message(BroadcastState.waiting_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(BroadcastState.waiting_media)
    await message.answer("Текст сохранен. Отправьте фото/документ или 'нет':")


@router.message(BroadcastState.waiting_media)
async def process_broadcast_media(message: Message, state: FSMContext):
    if message.photo:
        media_type = "photo"
        media_file_id = message.photo[-1].file_id
    elif message.document:
        media_type = "document"
        media_file_id = message.document.file_id
    elif message.text and message.text.lower() == "нет":
        media_type = None
        media_file_id = None
    else:
        await message.answer("Отправьте фото, документ или 'нет'")
        return

    await state.update_data(media_type=media_type, media_file_id=media_file_id)
    await state.set_state(BroadcastState.confirm)

    data = await state.get_data()
    preview = f"📢 Предпросмотр:\n\n{data['text']}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить всем", callback_data="confirm_broadcast")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_broadcast")]
    ])

    await message.answer(preview, reply_markup=keyboard)


@router.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = await User.all()

    await callback.message.edit_text(f"📤 Рассылка начата... 0/{len(users)}")

    sent = 0
    for user in users:
        try:
            if data.get('media_type') == "photo":
                await callback.bot.send_photo(user.id, data['media_file_id'], caption=data['text'])
            elif data.get('media_type') == "document":
                await callback.bot.send_document(user.id, data['media_file_id'], caption=data['text'])
            else:
                await callback.bot.send_message(user.id, data['text'])
            sent += 1
        except:
            pass

        if sent % 10 == 0:
            await callback.message.edit_text(f"📤 Рассылка... {sent}/{len(users)}")

    await callback.message.edit_text(f"✅ Рассылка завершена\nУспешно: {sent}/{len(users)}")
    await state.clear()


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена", reply_markup=back_to_admin_kb())