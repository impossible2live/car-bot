from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.db.crud_advert import get_user_favorites, get_advert_by_id ,remove_from_favorites

from app.keyboards.builders import liked_car_kb, main_menu_kb
from app.keyboards.helpers import quick_inline

router = Router(name=__name__)


async def show_favorite_advert(
        message: Message,
        state: FSMContext,
        user_id: int,
        advert_index: int = 0
):

    favorites = await get_user_favorites(user_id)

    if not favorites:
        await message.answer(
            "❤️ У вас пока нет понравившихся авто.\n\n"
            "Нажмите ❤️ на объявлении чтобы добавить его сюда.",
            reply_markup=main_menu_kb()
        )
        return

    if advert_index >= len(favorites):
        advert_index = 0

    favorite = favorites[advert_index]
    advert = await get_advert_by_id(favorite.advert_id)

    if not advert:
        await favorite.delete()
        await show_favorite_advert(message, state, user_id, advert_index)
        return

    await state.update_data(current_advert_id=advert.id)

    await _show_favorite_advert_detail(
        message,
        advert,
        advert_index,
        len(favorites)
    )


async def _show_favorite_advert_detail(
        message: Message,
        advert,
        current_index: int,
        total_count: int
):

    photos = await advert.photos.all().order_by("position")

    autoteka_text = "✅ Есть отчёт Автотеки" if advert.autoteka_purchased else "❌ Нет отчёта"

    text = (
        f"❤️ Понравившееся авто\n\n"
        f"🚗 {advert.name}\n"
        f"📍 Город: {advert.city}\n"
        f"📏 Пробег: {advert.mileage:,} км\n"
        f"⭐ Состояние: {advert.condition}\n"
        f"⛽ Топливо: {advert.fuel_type}\n"
        f"⚙️ Двигатель: {advert.engine_volume} л\n"
        f"🔧 КПП: {advert.transmission}\n"
        f"🚙 Кузов: {advert.body_type}\n"
        f"🎨 Цвет: {advert.color}\n"
        f"🔢 VIN: {advert.vin}\n"
        f"🚘 Гос номер: {advert.license_plate}\n"
        f"🔍 Автотека: {autoteka_text}\n"
        f"💰 Цена: {int(advert.price):,} ₽\n\n"
        f"📞 Контакты:\n {advert.contacts}\n\n"
        f"📝 Описание:\n{advert.description}"
    ).replace(",", " ")

    if photos:
        await message.answer_photo(
            photos[0].file_id,
            caption=text,
            reply_markup=liked_car_kb(advert.id, current_index, total_count),
        )
    else:
        await message.answer(
            text,
            reply_markup=liked_car_kb(advert.id, current_index, total_count),
        )



@router.callback_query(F.data.startswith("fav_prev_"))
async def fav_previous(callback: CallbackQuery, state: FSMContext):
    advert_id = int(callback.data.replace("fav_prev_", ""))

    favorites = await get_user_favorites(callback.from_user.id)
    current_index = await _get_current_fav_index(favorites, advert_id)

    if current_index > 0:
        await show_favorite_advert(callback.message, state, callback.from_user.id, current_index - 1)

    await callback.answer()


@router.callback_query(F.data.startswith("fav_next_"))
async def fav_next(callback: CallbackQuery, state: FSMContext):
    advert_id = int(callback.data.replace("fav_next_", ""))

    favorites = await get_user_favorites(callback.from_user.id)
    current_index = await _get_current_fav_index(favorites, advert_id)

    if current_index < len(favorites) - 1:
        await show_favorite_advert(callback.message, state,callback.from_user.id, current_index + 1)

    await callback.answer()


@router.callback_query(F.data.startswith("fav_contact_"))
async def fav_contact(callback: CallbackQuery):
    advert_id = int(callback.data.replace("fav_contact_", ""))
    advert = await get_advert_by_id(advert_id)

    if advert:
        await callback.message.answer(
            f"📞 Контакты продавца:\n\n{advert.contacts}",
            reply_markup=quick_inline([("⬅️ Назад", f"fav_back_{advert_id}")])
        )
    else:
        await callback.answer("❌ Объявление не найдено")

    await callback.answer()


@router.callback_query(F.data.startswith("fav_autoteka_"))
async def fav_autoteka(callback: CallbackQuery):
    advert_id = int(callback.data.replace("fav_autoteka_", ""))
    advert = await get_advert_by_id(advert_id)

    if not advert:
        await callback.answer("❌ Объявление не найдено")
        return

    from app.db.crud_autoteka import handle_autoteka_request
    await handle_autoteka_request(callback, advert_id)
    await callback.answer()


@router.callback_query(F.data.startswith("fav_delete_"))
async def fav_delete(callback: CallbackQuery, state: FSMContext):
    advert_id = int(callback.data.replace("fav_delete_", ""))

    success = await remove_from_favorites(callback.from_user.id, advert_id)

    if success:
        await callback.answer("❌ Удалено из избранного")
        favorites = await get_user_favorites(callback.from_user.id)
        if favorites:
            await show_favorite_advert(callback.message, state,callback.from_user.id, 0)
        else:
            await callback.message.answer(
                "❤️ У вас больше нет понравившихся авто.",
                reply_markup=main_menu_kb()
            )
    else:
        await callback.answer("❌ Ошибка при удалении")


@router.callback_query(F.data.startswith("fav_back_"))
async def fav_back(callback: CallbackQuery, state: FSMContext):
    advert_id = int(callback.data.replace("fav_back_", ""))

    favorites = await get_user_favorites(callback.from_user.id)
    current_index = await _get_current_fav_index(favorites, advert_id)

    await show_favorite_advert(callback.message, state, callback.from_user.id, current_index)
    await callback.answer()


@router.callback_query(F.data == "fav_back_menu")
async def fav_back_menu(callback: CallbackQuery):
    await callback.message.answer(
        "Главное меню:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()



async def _get_current_fav_index(favorites, advert_id: int) -> int:
    for i, fav in enumerate(favorites):
        if fav.advert_id == advert_id:
            return i
    return 0