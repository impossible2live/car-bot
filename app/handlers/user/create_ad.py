from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.states.advert_states import AdvertStates
from app.keyboards.builders import *
from app.keyboards.advert_content import AdvertContent
from .advert_help_fc import (
    clean_number,
    show_preview,
    STEP_HANDLERS,
    get_next_unfilled_step,
    process_resume,
    proceed_to_next_step, publish_ad, handle_autoteka_from_creating,
)
import re

from .search_help_fc import _format_filters_text
from .subscription import create_payment_flow
from app.db.crud_admin import get_settings
from app.db.crud_user import get_user, topup_user_balance, down_user_balance
from app.other import _format_price
from app.services.cars_data import parse_car_input, get_models_for_brand_cached,  \
    validate_car_name
from rapidfuzz import fuzz, process

from app.db.crud_advert import save_or_update_user_filter
from app.keyboards.builders import _filters_menu_kb
from app.states.search_ad_states import SearchAdStates

router = Router(name=__name__)


@router.callback_query(F.data == "resume_advert")
async def resume_advert(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    next_step = get_next_unfilled_step(data)
    await process_resume(callback, state, next_step)
    await callback.answer()


@router.callback_query(F.data == "restart_advert")
async def restart_advert(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await proceed_to_next_step(
        callback,
        state,
        'city',
        AdvertContent.TEXTS['city'],
        cancel_kb()
    )

@router.message(AdvertStates.waiting_city, F.text)
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await proceed_to_next_step(
        message,
        state,
        'name',
        AdvertContent.TEXTS['name'],
    )


@router.message(AdvertStates.waiting_name, F.text)
async def process_name(message: Message, state: FSMContext):
    input_text = message.text.strip()

    if len(input_text) < 2:
        await message.answer("❌ Слишком короткое название")
        return

    await message.answer("⌛ Пожалуйста подождите...")


    await state.update_data(original_name_input=input_text)

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
                reply_markup=get_suggestions_inline_kb()
            )
        else:
            await message.answer(response)
        return

    # Всё ок
    await state.update_data(name=result_msg)

    await proceed_to_next_step(
        message,
        state,
        'year',
        AdvertContent.TEXTS['year'],
    )


@router.callback_query(F.data == "keep_my_input")
async def handle_keep_my_input_global(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state == AdvertStates.waiting_name:
        data = await state.get_data()
        original_input = data.get('original_name_input')

        if original_input:
            await state.update_data(name=original_input)
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer("✅ Ваш вариант сохранен")

            await proceed_to_next_step(
                callback.message,
                state,
                'year',
                AdvertContent.TEXTS['year'],
            )

    elif current_state == SearchAdStates.waiting_filter_name:
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
        await callback.answer("❌ Действие недоступно", show_alert=True)

@router.message(F.text, AdvertStates.waiting_name)
async def handle_suggestion(message: Message, state: FSMContext):
    input_text = message.text.strip()

    is_valid, result_msg, _ = await validate_car_name(input_text)

    if is_valid:
        await state.update_data(name=result_msg)

        await proceed_to_next_step(
            message,
            state,
            'year',
            AdvertContent.TEXTS['year'],
        )
    else:
        await process_name(message, state)


@router.message(AdvertStates.waiting_year, F.text)
async def process_year(message: Message, state: FSMContext):
    cleaned_text = clean_number(message.text)
    if not cleaned_text.isdigit():
        await message.answer("❌ Введите год цифрами")
        return

    await state.update_data(year=int(cleaned_text))
    await proceed_to_next_step(
        message,
        state,
        'mileage',
        AdvertContent.TEXTS['mileage'],
    )

@router.message(AdvertStates.waiting_mileage, F.text)
async def process_mileage(message: Message, state: FSMContext):
    cleaned_text = clean_number(message.text)
    if not cleaned_text.isdigit():
        await message.answer("❌ Введите пробег цифрами")
        return

    await state.update_data(mileage=int(cleaned_text))
    await proceed_to_next_step(
        message,
        state,
        'condition',
        AdvertContent.TEXTS['condition'],
        condition_kb()
    )


@router.callback_query(AdvertStates.waiting_condition, F.data.startswith("step_condition_"))
async def process_condition(callback: CallbackQuery, state: FSMContext):
    condition_map = {
        "step_condition_perfect": "Отличное",
        "step_condition_good": "Хорошее",
        "step_condition_bad": "Требует ремонта"
    }

    condition = condition_map[callback.data]
    await state.update_data(condition=condition)
    await proceed_to_next_step(
        callback,
        state,
        'fuel_type',
        AdvertContent.TEXTS['fuel_type'],
        fuel_type_kb()
    )


@router.callback_query(AdvertStates.waiting_fuel_type, F.data.startswith("step_fuel_"))
async def process_fuel_type(callback: CallbackQuery, state: FSMContext):
    fuel_map = {
        "step_fuel_petrol": "Бензин",
        "step_fuel_diesel": "Дизель",
        "step_fuel_gas": "Газ"
    }

    fuel_type = fuel_map[callback.data]
    await state.update_data(fuel_type=fuel_type)
    await proceed_to_next_step(
        callback,
        state,
        'engine_volume',
        AdvertContent.TEXTS['engine_volume'],
    )


@router.message(AdvertStates.waiting_engine_volume, F.text)
async def process_engine_volume(message: Message, state: FSMContext):
    if not re.match(r'^\d+\.?\d*$', message.text):
        await message.answer("❌ Введите объем цифрами, например: 1.6")
        return

    await state.update_data(engine_volume=message.text)
    await proceed_to_next_step(
        message,
        state,
        'transmission',
        AdvertContent.TEXTS['transmission'],
        transmission_kb()
    )


@router.callback_query(AdvertStates.waiting_transmission, F.data.startswith("step_transmission_"))
async def process_transmission(callback: CallbackQuery, state: FSMContext):
    transmission_map = {
        "step_transmission_manual": "Механика",
        "step_transmission_auto": "Автомат",
        "step_transmission_robot": "Робот",
        "step_transmission_cvt": "Вариатор"
    }

    transmission = transmission_map[callback.data]
    await state.update_data(transmission=transmission)
    await proceed_to_next_step(
        callback,
        state,
        'body_type',
        AdvertContent.TEXTS['body_type'],
        body_type_kb()
    )


@router.callback_query(AdvertStates.waiting_body_type, F.data.startswith("step_body_"))
async def process_body_type(callback: CallbackQuery, state: FSMContext):
    body_map = {
        "step_body_sedan": "Седан",
        "step_body_hatchback": "Хэтчбек",
        "step_body_wagon": "Универсал",
        "step_body_suv": "Внедорожник",
        "step_body_coupe": "Купе",
        "step_body_minivan": "Минивэн",
        "step_body_pickup": "Пикап",
        "step_body_convertible": "Кабриолет"
    }

    body_type = body_map[callback.data]
    await state.update_data(body_type=body_type)
    await proceed_to_next_step(
        callback,
        state,
        'color',
        AdvertContent.TEXTS['color'],
        color_kb()
    )


@router.callback_query(AdvertStates.waiting_color, F.data.startswith("step_color_"))
async def process_color(callback: CallbackQuery, state: FSMContext):
    if callback.data == "step_color_custom":
        await callback.message.edit_text("Напишите свой цвет:")
        return

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
        "step_color_purple": "Фиолетовый"
    }

    color = color_map[callback.data]
    await state.update_data(color=color)
    await proceed_to_next_step(
        callback,
        state,
        'vin',
        AdvertContent.TEXTS['vin'],
    )


@router.message(AdvertStates.waiting_color, F.text)
async def process_custom_color(message: Message, state: FSMContext):
    await state.update_data(color=message.text)
    await proceed_to_next_step(
        message,
        state,
        'vin',
        AdvertContent.TEXTS['vin'],
    )


@router.message(AdvertStates.waiting_vin, F.text)
async def process_vin(message: Message, state: FSMContext):
    vin = message.text.upper().strip()
    if len(vin) != 17:
        await message.answer("❌ VIN должен содержать 17 символов")
        return

    await state.update_data(vin=vin)
    await proceed_to_next_step(
        message,
        state,
        'license_plate',
        AdvertContent.TEXTS['license_plate'],
    )

@router.message(AdvertStates.waiting_license_plate, F.text)
async def process_license_plate(message: Message, state: FSMContext):
    await state.update_data(license_plate=message.text.upper())
    await proceed_to_next_step(
        message,
        state,
        'autoteka',
        AdvertContent.TEXTS['autoteka'],
        autoteka_kb()
    )


@router.callback_query(AdvertStates.waiting_autoteka_decision, F.data.startswith("autoteka_"))
async def process_autoteka_decision(callback: CallbackQuery, state: FSMContext):
    settings = await get_settings()
    user = await get_user(callback.from_user.id)
    user_balance = user.balance
    if callback.data == "autoteka_yes":
        if user_balance >= settings.autoteka_price:
            await down_user_balance(callback.from_user.id, settings.autoteka_price)
            await handle_autoteka_from_creating(callback, state)
            return
        else:
            await state.update_data(autoteka_purchased=False)
            await create_payment_flow(callback, callback.from_user.id, "autoteka2")
            return

    elif callback.data == "autoteka_no":
        await state.update_data(autoteka_purchased=False)
        await proceed_to_next_step(
            callback,
            state,
            'photos',
            AdvertContent.TEXTS['photos'],
            skip_photos_kb(0)
        )

    elif callback.data == "autoteka_continue":
        await proceed_to_next_step(
            callback,
            state,
            'photos',
            AdvertContent.TEXTS['photos'],
            skip_photos_kb(0)
        )

    await callback.answer()


@router.message(AdvertStates.waiting_photos, F.photo)
async def process_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])

    if len(photos) >= 6:
        await message.answer("❌ Можно добавить не более 6 фото")
        return

    photo = message.photo[-1]
    photos.append(photo.file_id)
    await state.update_data(photos=photos)

    if len(photos) < 6:
        await message.answer(
            f"✅ Фото добавлено. Добавлено {len(photos)}/6. "
            f"Можете добавить еще фото или продолжить",
            reply_markup=skip_photos_kb(len(photos))
        )
    else:
        await message.answer(
            "✅ Добавлено максимальное количество фото. Нажмите 'Продолжить'",
            reply_markup=skip_photos_kb(len(photos))
        )


@router.callback_query(AdvertStates.waiting_photos, F.data.startswith("step_photos_skip"))
async def skip_photos(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get('photos'):
        await state.update_data(photos=[])
    await proceed_to_next_step(
        callback,
        state,
        'contacts',
        AdvertContent.TEXTS['contacts'],
    )


@router.callback_query(AdvertStates.waiting_photos, F.data.startswith("step_photos_process"))
async def continue_after_photos(callback: CallbackQuery, state: FSMContext):
    await proceed_to_next_step(
        callback,
        state,
        'contacts',
        AdvertContent.TEXTS['contacts'],
    )


@router.message(AdvertStates.waiting_contacts, F.text)
async def process_contacts(message: Message, state: FSMContext):
    await state.update_data(contacts=message.text)
    await proceed_to_next_step(
        message,
        state,
        'price',
        AdvertContent.TEXTS['price'],
    )



@router.message(AdvertStates.waiting_price, F.text)
async def process_price(message: Message, state: FSMContext):
    cleaned_text = clean_number(message.text)
    if not cleaned_text.isdigit():
        await message.answer("❌ Введите цену цифрами")
        return

    await state.update_data(price=int(cleaned_text))
    await proceed_to_next_step(
        message,
        state,
        'description',
        AdvertContent.TEXTS['description'],
    )




@router.message(AdvertStates.waiting_description, F.text)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await show_preview(message, state)
    await state.set_state(AdvertStates.waiting_confirmation)


@router.callback_query(F.data == "ad_payment")
async def ad_payment(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    settings = await get_settings()



    if user.balance >= settings.advert_publish_price:
        await callback.message.edit_text(
            f"С баланса будет списано {_format_price(settings.advert_publish_price)}₽",
            reply_markup=quick_inline([
                ("✅ Ок", "ad_publish_balance"),
                ("⬅️ Назад", "back_to_preview")
            ])
            )
        return
    await create_payment_flow(callback, callback.from_user.id, "advert")
    await callback.answer()


@router.callback_query(F.data == "back_to_preview")
async def process_back_preview(callback: CallbackQuery, state: FSMContext):
    await show_preview(callback, state)
    await state.set_state(AdvertStates.waiting_confirmation)



@router.callback_query(F.data == "ad_change")
async def ad_change(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Что хотите изменить?", reply_markup=ad_change_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("change_"))
async def process_change(callback: CallbackQuery, state: FSMContext):
    change_type = callback.data.replace("change_", "")

    if change_type == "back":
        await show_preview(callback.message, state)
        await callback.answer()
        return

    if change_type in STEP_HANDLERS:
        state_obj, text, keyboard = STEP_HANDLERS[change_type]
        await callback.message.edit_text(text, reply_markup=keyboard)
        await state.set_state(state_obj)

    await callback.answer()


@router.callback_query(F.data == "ad_publish")
async def ad_publish(callback: CallbackQuery, state: FSMContext):
    from app.db.crud_user import is_user_shadow_banned
    if is_user_shadow_banned(callback.from_user.id):
        await callback.edit_text(
            "✅ Объявление успешно опубликовано!"
        )
        return
    await publish_ad(callback, state)


@router.callback_query(F.data == "ad_publish_balance")
async def ad_publish(callback: CallbackQuery, state: FSMContext):
    from app.db.crud_user import down_user_balance, is_user_shadow_banned
    from app.db.crud_admin import get_settings

    if is_user_shadow_banned(callback.from_user.id):
        await callback.edit_text(
            "✅ Объявление успешно опубликовано!"
        )
        return

    settings = await get_settings()
    await down_user_balance(callback.from_user.id, settings.advert_publish_price)

    await publish_ad(callback, state)




@router.message(F.text == "❌ Отменить")
async def cancel_advert(message: Message, state: FSMContext):
    await message.answer("❌ Создание объявления отменено", reply_markup=main_menu_kb())
    await state.clear()