from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.keyboards.builders import (
    search_filters_kb,
    now_liked_car_kb,
    _filters_menu_kb
)
from app.db.crud_advert import (
    get_random_advert_with_filters,
    get_advert_by_id,
    get_user_filter,
)
from app.other import _format_price

router = Router(name=__name__)


async def _get_filters_from_db(user_id: int) -> dict:
    filter_data = await get_user_filter(user_id)
    if not filter_data:
        return {}

    return filter_data


async def _show_random_advert(chat_obj, state: FSMContext, user_id: int):

    filters = await _get_filters_from_db(user_id)

    advert = await get_random_advert_with_filters(filters, exclude_ids=[])
    if not advert:
        text = "По текущим фильтрам объявлений не найдено.\n\nГлавное меню - /start"
        if hasattr(chat_obj, "message"):  # CallbackQuery
            await chat_obj.message.answer(text, reply_markup=_filters_menu_kb())
        else:
            await chat_obj.answer(text, reply_markup=_filters_menu_kb())
        return

    await state.update_data(current_advert_id=advert.id)

    photos = await advert.photos.all()
    caption = (
        f"🚗 {advert.name}\n"
        f"📍 Город: {advert.city}\n"
        f"📏 Пробег: {advert.mileage:,} км\n"
        f"💰 Цена: {int(advert.price):,} ₽".replace(",", " ")
    )

    if hasattr(chat_obj, "message"):  # CallbackQuery
        send_obj = chat_obj.message
    else:  # Message
        send_obj = chat_obj

    if photos:
        await send_obj.answer_photo(
            photos[0].file_id,
            caption=caption,
            reply_markup=search_filters_kb(),
        )
    else:
        await send_obj.answer(
            caption,
            reply_markup=search_filters_kb(),
        )


async def _show_full_advert(message: Message, advert_id: int):
    advert = await get_advert_by_id(advert_id)
    if not advert:
        await message.answer("Это объявление больше недоступно.")
        return

    photos = await advert.photos.all()

    autoteka_text = "Есть отчёт" if advert.autoteka_purchased else "Нет"

    text = (
        f"🚗 {advert.name}\n"
        f"📍 Город: {advert.city}\n"
        f"🔢 Год выпуска: {advert.year}\n"
        f"📏 Пробег: {advert.mileage:,} км\n"
        f"⭐ Состояние: {advert.condition}\n"
        f"⛽ Топливо: {advert.fuel_type}\n"
        f"⚙️ Двигатель: {advert.engine_volume} л\n"
        f"🪛 КПП: {advert.transmission}\n"
        f"🚙 Кузов: {advert.body_type}\n"
        f"🎨 Цвет: {advert.color}\n"
        f"🔢 VIN: {advert.vin}\n"
        f"🚘 Гос номер: {advert.license_plate}\n"
        f"🔍 Отчёт Автотеки: {autoteka_text}\n"
        f"💰 Цена: {int(advert.price):,} ₽\n"
        f"📞 Контакты:\n {advert.contacts}\n\n"
        f"📝 Описание:\n{advert.description}"
    ).replace(",", " ")

    if photos:
        await message.answer_photo(
            photos[0].file_id,
            caption=text,
            reply_markup=now_liked_car_kb(),
        )
    else:
        await message.answer(
            text,
            reply_markup=now_liked_car_kb(),
        )


async def _format_filters_text(user_id: int) -> str:

    filter_data = await get_user_filter(user_id)

    if not filter_data:
        return (
            "⚙️ Текущие фильтры:\n\n"
            f"🏙 Город: Любой\n"
            f"🔢 Год выпуска: Любой\n"
            f"🚗 Марка/модель: Любое\n"
            f"⭐ Состояние: Любое\n"
            f"⛽ Топливо: Любое\n"
            f"📏 Пробег: Любой\n"
            f"💰 Цена: Любой\n"
            f"⚙️ Объём двигателя: Любой\n"
            f"🪛 КПП: Любая\n"
            f"🚙 Кузов: Любой\n"
            f"🎨 Цвет: Любой\n\n"
            "Выберите, что изменить:"
        )

    def _val(v, default):
        if v is None:
            return default
        if isinstance(v, str) and v.strip() == "":
            return default
        return v

    def _engine_val(v):
        if v is None:
            return "Любой"
        if isinstance(v, str) and v.strip() == "":
            return "Любой"
        try:
            return f"{float(v):.1f} л"
        except (TypeError, ValueError):
            return str(v)

    city = _val(filter_data.get("city"), "Любой")
    year = _val(filter_data.get("year"), "Любой")
    name = _val(filter_data.get("name"), "Любое")
    condition = _val(filter_data.get("condition"), "Любое")
    fuel = _val(filter_data.get("fuel_type"), "Любое")
    engine_volume = _engine_val(filter_data.get("engine_volume_max"))
    transmission = _val(filter_data.get("transmission"), "Любая")
    body_type = _val(filter_data.get("body_type"), "Любой")
    color = _val(filter_data.get("color"), "Любой")

    mileage_from = filter_data.get("mileage_from")
    mileage_to = filter_data.get("mileage_to")
    price_from = filter_data.get("price_from")
    price_to = filter_data.get("price_to")

    def _range_text(v_from, v_to, unit=""):
        if v_from is None and v_to is None:
            return "Любой"
        if v_from is not None and v_to is not None:
            return f"{v_from}–{v_to}{unit}"
        if v_from is not None:
            return f"от {v_from}{unit}"
        if v_to is not None:
            return f"до {v_to}{unit}"
        return "Любой"

    price_from = _format_price(filter_data.get("price_from"))
    price_to = _format_price(filter_data.get("price_to"))

    mileage_txt = _range_text(mileage_from, mileage_to, " км")
    price_txt = _range_text(price_from, price_to, " ₽")

    return (
        "⚙️ Текущие фильтры:\n\n"
        f"🏙 Город: {city}\n"
        f"🔢 Год выпуска: {year}\n"
        f"🚗 Марка/модель: {name}\n"
        f"⭐ Состояние: {condition}\n"
        f"⛽ Топливо: {fuel}\n"
        f"📏 Пробег: {mileage_txt}\n"
        f"💰 Цена: {price_txt}\n"
        f"⚙️ Объём двигателя: {engine_volume}\n"
        f"🪛 КПП: {transmission}\n"
        f"🚙 Кузов: {body_type}\n"
        f"🎨 Цвет: {color}\n\n"
        "Выберите, что изменить:"
    )
