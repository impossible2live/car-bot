from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.states.search_ad_states import SearchAdStates
from app.keyboards.builders import (
    search_filters_kb,
    condition_kb,
    fuel_type_kb,
    transmission_kb,
    body_type_kb,
    color_kb,
    _filters_menu_kb,
    main_menu_kb,
    back_from_filter_kb, get_filter_suggestions_inline_kb
)
from app.keyboards.helpers import quick_reply
from app.db.crud_advert import (
    add_favorite_advert,
    save_or_update_user_filter, delete_user_filter
)
from .search_help_fc import _format_filters_text, _show_random_advert, _show_full_advert
from app.services.cars_data import validate_car_name

router = Router(name=__name__)




@router.message(F.text == "⚙️ Фильтры")
async def filters_menu(message: Message, state: FSMContext):
    text = await _format_filters_text(message.from_user.id)
    await message.answer(text, reply_markup=_filters_menu_kb())


@router.message(F.text == "⬅️ Отмена")
async def filters_menu(message: Message, state: FSMContext):
    await state.set_state(None)
    text = await _format_filters_text(message.from_user.id)
    await message.answer(text, reply_markup=_filters_menu_kb())


@router.callback_query(F.data == "all_cities", SearchAdStates.waiting_filter_city)
async def handle_filter_city_all(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Выбраны все города\n\n", reply_markup=search_filters_kb())
    await _show_random_advert(callback, state, callback.from_user.id)
    await state.set_state(None)


@router.message(F.text == "🏙 Город")
async def filters_city_start(message: Message, state: FSMContext):
    await message.answer("Введите город для фильтра:", reply_markup=back_from_filter_kb())
    await state.set_state(SearchAdStates.waiting_filter_city)


@router.message(SearchAdStates.waiting_filter_city, F.text != "⬅️ Назад к поиску")
async def filters_city_set(message: Message, state: FSMContext):
    city = message.text
    await save_or_update_user_filter(
        user_id=message.from_user.id,
        update_fields={"city": city}
    )

    await message.answer("Город обновлён.\n\n", reply_markup=search_filters_kb())
    await _show_random_advert(message, state, message.from_user.id)
    await state.set_state(None)


@router.message(F.text == "🚗 Марка и модель")
async def filters_name_start(message: Message, state: FSMContext):
    await message.answer("Введите марку/модель для фильтра:", reply_markup=back_from_filter_kb())
    await state.set_state(SearchAdStates.waiting_filter_name)


@router.message(SearchAdStates.waiting_filter_name, F.text)
async def filters_name_set(message: Message, state: FSMContext):
    input_text = message.text.strip()

    if len(input_text) < 2:
        await message.answer("❌ Слишком короткое название")
        return

    await message.answer("⌛ Пожалуйста подождите...")


    await state.update_data(filter_original_name_input=input_text)

    is_valid, result_msg, suggestions = await validate_car_name(input_text)

    if not is_valid:
        response = f"❌ {result_msg}"

        if suggestions:
            response += "\n\nВозможно вы имели в виду:\n"
            for suggestion in suggestions:
                response += f"• <code>{suggestion}</code>\n"
            response += "\nСкопируйте и отправьте нужный вариант или используйте кнопку ниже"

            await message.answer(
                response,
                reply_markup=get_filter_suggestions_inline_kb()
            )
            return
        else:
            await message.answer(response)
            return

    await save_or_update_user_filter(
        message.from_user.id,
        update_fields={"name": result_msg}
    )

    formatted = await _format_filters_text(message.from_user.id)
    await message.answer("Название обновлено.\n\n" + formatted, reply_markup=_filters_menu_kb())
    await state.set_state(None)


@router.callback_query(F.data == "filter_keep_my_input", SearchAdStates.waiting_filter_name)
async def handle_filter_keep_my_input(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    original_input = data.get('filter_original_name_input')

    if original_input:
        await save_or_update_user_filter(
            callback.from_user.id,
            update_fields={"name": original_input}
        )

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer("✅ Ваш вариант сохранен")

        formatted = await _format_filters_text(callback.from_user.id)
        await callback.message.answer(
            "Название обновлено.\n\n" + formatted,
            reply_markup=_filters_menu_kb()
        )
        await state.set_state(None)
    else:
        await callback.answer("❌ Ошибка: не найден оригинальный ввод", show_alert=True)


@router.message(SearchAdStates.waiting_filter_name, F.text)
async def handle_filter_suggestion(message: Message, state: FSMContext):
    input_text = message.text.strip()

    is_valid, result_msg, _ = await validate_car_name(input_text)

    if is_valid:
        await save_or_update_user_filter(
            message.from_user.id,
            update_fields={"name": result_msg}
        )

        formatted = await _format_filters_text(message.from_user.id)
        await message.answer("Название обновлено.\n\n" + formatted, reply_markup=_filters_menu_kb())
        await state.set_state(None)
    else:
        await filters_name_set(message, state)





@router.message(F.text == "🔢 Год")
async def filters_mileage_start(message: Message, state: FSMContext):
    await message.answer("Введите год выпуска авто\n\n"
                         "❗<b>Система "
        "автоматически расширит поиск на всё поколение этого авто.</b>\n"
        "• Например, если введете 2008 для Toyota Camry, будут показаны все авто с 2006 по 2011 "
        "(это одно поколение)\n"
        "• Так вы увидите больше вариантов с похожими характеристиками\n\n",
                         reply_markup=back_from_filter_kb())
    await state.set_state(SearchAdStates.waiting_filter_year)


@router.message(SearchAdStates.waiting_filter_year, F.text != "⬅️ Назад к поиску")
async def filters_mileage_set(message: Message, state: FSMContext):

    year = message.text
    if year is not None and year and not year.isdigit():
        await message.answer("❌ Введите год цифрами (пример: 2025).")
        return

    await save_or_update_user_filter(
        user_id=message.from_user.id,
        update_fields={"year": year}
    )

    text = await _format_filters_text(message.from_user.id)
    await message.answer("Год выпуска обновлён.\n\n" + text, reply_markup=_filters_menu_kb())
    await state.set_state(None)

@router.message(F.text == "📏 Пробег")
async def filters_mileage_start(message: Message, state: FSMContext):
    await message.answer("Введите пробег ОТ и ДО (км) через пробел, только цифры", reply_markup=back_from_filter_kb())
    await state.set_state(SearchAdStates.waiting_filter_mileage)


@router.message(SearchAdStates.waiting_filter_mileage, F.text != "⬅️ Назад к поиску")
async def filters_mileage_set(message: Message, state: FSMContext):
    parts = message.text.replace(",", " ").split()

    if len(parts) == 1:
        from_txt = parts[0]
        to_txt = None
    else:
        from_txt, to_txt = parts[0], parts[1]

    def _parse(v):
        v = v.strip()
        if not v or v == "0":
            return None
        if not v.isdigit():
            return None
        return int(v)

    mileage_from = _parse(from_txt)
    mileage_to = _parse(to_txt) if to_txt is not None else None

    if from_txt and not from_txt.isdigit():
        await message.answer("❌ Введите пробег цифрами (пример: 0 150000).")
        return
    if to_txt is not None and to_txt and not to_txt.isdigit():
        await message.answer("❌ Введите пробег цифрами (пример: 0 150000).")
        return

    await save_or_update_user_filter(
        user_id=message.from_user.id,
        update_fields={"mileage_from": mileage_from, "mileage_to": mileage_to}
    )

    text = await _format_filters_text(message.from_user.id)
    await message.answer("Пробег обновлён.\n\n" + text, reply_markup=_filters_menu_kb())
    await state.set_state(None)


@router.message(F.text == "💰 Цена")
async def filters_price_start(message: Message, state: FSMContext):
    await message.answer("Введите цену ОТ и ДО в рублях через пробел (пример: 300000 1500000).", reply_markup=back_from_filter_kb())
    await state.set_state(SearchAdStates.waiting_filter_price)


@router.message(SearchAdStates.waiting_filter_price, F.text != "⬅️ Назад к поиску")
async def filters_price_set(message: Message, state: FSMContext):
    parts = message.text.replace(",", " ").split()

    if len(parts) == 1:
        from_txt = parts[0]
        to_txt = None
    else:
        from_txt, to_txt = parts[0], parts[1]

    def _parse(v):
        v = v.strip()
        if not v or v == "0":
            return None
        if not v.isdigit():
            return None
        return int(v)

    price_from = _parse(from_txt)
    price_to = _parse(to_txt) if to_txt is not None else None

    if from_txt and not from_txt.isdigit():
        await message.answer("❌ Введите цену цифрами (пример: 300000 1500000).")
        return
    if to_txt is not None and to_txt and not to_txt.isdigit():
        await message.answer("❌ Введите цену цифрами (пример: 300000 1500000).")
        return

    await save_or_update_user_filter(
        user_id=message.from_user.id,
        update_fields={"price_from": price_from, "price_to": price_to}
    )

    text = await _format_filters_text(message.from_user.id)
    await message.answer("Цена обновлена.\n\n" + text, reply_markup=_filters_menu_kb())
    await state.set_state(None)


@router.message(F.text == "⭐ Состояние")
async def filters_condition_start(message: Message, state: FSMContext):
    await message.answer("Выберите состояние автомобиля:", reply_markup=condition_kb())
    await state.set_state(SearchAdStates.waiting_filter_condition)


@router.callback_query(SearchAdStates.waiting_filter_condition, F.data.startswith("step_condition_"))
async def filters_condition_set(callback: CallbackQuery, state: FSMContext):
    condition_map = {
        "step_condition_perfect": "Отличное",
        "step_condition_good": "Хорошее",
        "step_condition_bad": "Требует ремонта",
    }
    condition = condition_map.get(callback.data)
    if not condition:
        await callback.answer()
        return

    await save_or_update_user_filter(
        user_id=callback.from_user.id,
        update_fields={"condition": condition}
    )

    text = await _format_filters_text(callback.from_user.id)
    await callback.message.answer("Состояние обновлено.\n\n" + text, reply_markup=_filters_menu_kb())
    await state.set_state(None)
    await callback.answer()


@router.message(F.text == "⛽ Топливо")
async def filters_fuel_start(message: Message, state: FSMContext):
    await message.answer("Выберите тип топлива:", reply_markup=fuel_type_kb())
    await state.set_state(SearchAdStates.waiting_filter_fuel_type)


@router.callback_query(SearchAdStates.waiting_filter_fuel_type, F.data.startswith("step_fuel_"))
async def filters_fuel_set(callback: CallbackQuery, state: FSMContext):
    fuel_map = {
        "step_fuel_petrol": "Бензин",
        "step_fuel_diesel": "Дизель",
        "step_fuel_gas": "Газ",
    }
    fuel = fuel_map.get(callback.data)
    if not fuel:
        await callback.answer()
        return

    await save_or_update_user_filter(
        user_id=callback.from_user.id,
        update_fields={"fuel_type": fuel}
    )

    text = await _format_filters_text(callback.from_user.id)
    await callback.message.answer("Топливо обновлено.\n\n" + text, reply_markup=_filters_menu_kb())
    await state.set_state(None)
    await callback.answer()


@router.message(F.text == "⚙️ Объём двигателя")
async def filters_engine_start(message: Message, state: FSMContext):
    await message.answer("Введите объём двигателя в литрах (пример: 2.0).", reply_markup=back_from_filter_kb())
    await state.set_state(SearchAdStates.waiting_filter_engine_volume)


@router.message(SearchAdStates.waiting_filter_engine_volume, F.text != "⬅️ Назад к поиску")
async def filters_engine_set(message: Message, state: FSMContext):
    text = message.text.replace(",", ".").strip()
    if text in ("", "0"):
        value = None
    else:
        try:
            value = float(text)
        except ValueError:
            await message.answer("❌ Введите объём числом, например: 1.6 или 2.0")
            return

    await save_or_update_user_filter(
        user_id=message.from_user.id,
        update_fields={"engine_volume_max": value}
    )

    formatted = await _format_filters_text(message.from_user.id)
    await message.answer("Объём двигателя обновлён.\n\n" + formatted, reply_markup=_filters_menu_kb())
    await state.set_state(None)


@router.message(F.text == "🪛 КПП")
async def filters_transmission_start(message: Message, state: FSMContext):
    await message.answer("Выберите тип коробки передач:", reply_markup=transmission_kb())
    await state.set_state(SearchAdStates.waiting_filter_transmission)


@router.callback_query(SearchAdStates.waiting_filter_transmission, F.data.startswith("step_transmission_"))
async def filters_transmission_set(callback: CallbackQuery, state: FSMContext):
    transmission_map = {
        "step_transmission_manual": "Механика",
        "step_transmission_auto": "Автомат",
        "step_transmission_robot": "Робот",
        "step_transmission_cvt": "Вариатор",
    }
    tr = transmission_map.get(callback.data)
    if not tr:
        await callback.answer()
        return

    await save_or_update_user_filter(
        user_id=callback.from_user.id,
        update_fields={"transmission": tr}
    )

    text = await _format_filters_text(callback.from_user.id)
    await callback.message.answer("КПП обновлена.\n\n" + text, reply_markup=_filters_menu_kb())
    await state.set_state(None)
    await callback.answer()


@router.message(F.text == "🚙 Кузов")
async def filters_body_start(message: Message, state: FSMContext):
    await message.answer("Выберите тип кузова:", reply_markup=body_type_kb())
    await state.set_state(SearchAdStates.waiting_filter_body_type)


@router.callback_query(SearchAdStates.waiting_filter_body_type, F.data.startswith("step_body_"))
async def filters_body_set(callback: CallbackQuery, state: FSMContext):
    body_map = {
        "step_body_sedan": "Седан",
        "step_body_hatchback": "Хэтчбек",
        "step_body_wagon": "Универсал",
        "step_body_suv": "Внедорожник",
        "step_body_coupe": "Купе",
        "step_body_minivan": "Минивэн",
        "step_body_pickup": "Пикап",
        "step_body_convertible": "Кабриолет",
    }
    body = body_map.get(callback.data)
    if not body:
        await callback.answer()
        return

    await save_or_update_user_filter(
        user_id=callback.from_user.id,
        update_fields={"body_type": body}
    )

    text = await _format_filters_text(callback.from_user.id)
    await callback.message.answer("Кузов обновлён.\n\n" + text, reply_markup=_filters_menu_kb())
    await state.set_state(None)
    await callback.answer()


@router.message(F.text == "🎨 Цвет")
async def filters_color_start(message: Message, state: FSMContext):
    await message.answer("Выберите цвет:", reply_markup=color_kb())
    await state.set_state(SearchAdStates.waiting_filter_color)


@router.callback_query(SearchAdStates.waiting_filter_color, F.data.startswith("step_color_"))
async def filters_color_set(callback: CallbackQuery, state: FSMContext):
    color_map = {
        "step_color_white": "Белый",
        "step_color_black": "Черный",
        "step_color_gray": "Серый",
        "step_color_silver": "Серебристый",
        "step_color_red": "Красный",
        "step_color_blue": "Синий",
        "step_color_green": "Зеленый",
        "step_color_brown": "Коричневый",
        "step_color_yellow": "Желтый",
        "step_color_orange": "Оранжевый",
        "step_color_purple": "Фиолетовый",
    }
    clr = color_map.get(callback.data)
    if not clr:
        await callback.answer()
        return

    await save_or_update_user_filter(
        user_id=callback.from_user.id,
        update_fields={"color": clr}
    )

    text = await _format_filters_text(callback.from_user.id)
    await callback.message.answer("Цвет обновлён.\n\n" + text, reply_markup=_filters_menu_kb())
    await state.set_state(None)
    await callback.answer()



@router.message(F.text == "♻️ Сбросить фильтры")
async def filters_reset(message: Message, state: FSMContext):
    deleted = await delete_user_filter(message.from_user.id)
    await state.clear()

    if deleted:
        text = await _format_filters_text(message.from_user.id)
        await message.answer("Фильтры сброшены.\n\n" + text, reply_markup=_filters_menu_kb())
    else:
        text = await _format_filters_text(message.from_user.id)
        await message.answer("Фильтров и так не было.\n\n" + text, reply_markup=_filters_menu_kb())


@router.message(F.text == "⬅️ Назад к поиску")
async def filters_back_to_search(message: Message, state: FSMContext):
    await state.set_state(None)
    await _show_random_advert(message, state, message.from_user.id)


@router.message(F.text == "❤️")
async def like(message: Message, state: FSMContext):
    data = await state.get_data()
    advert_id = data.get("current_advert_id")
    if not advert_id:
        await message.answer("Нет выбранного объявления для лайка.")
        return

    await add_favorite_advert(message.from_user.id, advert_id)
    await _show_full_advert(message, advert_id)


@router.message(F.text == "👎")
async def dislike(message: Message, state: FSMContext):
    await _show_random_advert(message, state,message.from_user.id)

@router.message(F.text == "🏠 Главное меню")
async def back_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=main_menu_kb())

@router.message(F.text == "⏩ Продолжить")
async def process_next(message: Message, state: FSMContext):
    await _show_random_advert(message, state ,message.from_user.id)


@router.message(F.text == "🔍 Отчёт автотеки")
async def autoteka_see(message: Message, state: FSMContext):
    data = await state.get_data()
    advert_id = data.get("current_advert_id")
    if not advert_id:
        await message.answer("Нет выбранного объявления")
        return

    from app.db.crud_autoteka import handle_autoteka_request
    await handle_autoteka_request(message, advert_id)


@router.callback_query(F.data == "buy_autoteka")
async def buy_autoteka(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    advert_id = data.get("current_advert_id")
    if not advert_id:
        await callback.answer("Нет выбранного объявления")
        return

    from app.db.crud_autoteka import handle_autoteka_purchase
    await handle_autoteka_purchase(callback, advert_id)


