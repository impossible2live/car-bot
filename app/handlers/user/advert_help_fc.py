import re
from decimal import Decimal

from aiogram.types import InputMediaPhoto, Message
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from app.db.crud_advert import create_advert_from_state
from app.db.crud_autoteka import save_autoteka_report
from app.db.crud_transaction import check_active_subscription
from app.other import _format_price
from app.services.autoteca_no_api import get_vehicle_report_async
from app.states.advert_states import AdvertStates
from app.keyboards.builders import *
from app.keyboards.advert_content import AdvertContent

from app.db.models import User, Advert, AdvertPhoto
import random


STEPS_ORDER = [
    'name', 'year','mileage', 'condition', 'fuel_type',
    'engine_volume', 'transmission', 'body_type', 'color',
    'vin', 'autoteka', 'license_plate', 'photos', 'contacts', 'city', 'price', 'description'
]

REQUIRED_FIELDS = [
    'name', 'year','mileage', 'condition', 'fuel_type',
    'engine_volume', 'transmission', 'body_type', 'color',
    'vin', 'license_plate', 'contacts', 'city', 'price', 'description'
]

STEP_HANDLERS = {
    'name': (AdvertStates.waiting_name, AdvertContent.TEXTS['name'], None),
    'year': (AdvertStates.waiting_year, AdvertContent.TEXTS['year'], None),
    'mileage': (AdvertStates.waiting_mileage, AdvertContent.TEXTS['mileage'], None),
    'condition': (AdvertStates.waiting_condition, AdvertContent.TEXTS['condition'], condition_kb()),
    'fuel_type': (AdvertStates.waiting_fuel_type, AdvertContent.TEXTS['fuel_type'], fuel_type_kb()),
    'engine_volume': (AdvertStates.waiting_engine_volume, AdvertContent.TEXTS['engine_volume'], None),
    'transmission': (AdvertStates.waiting_transmission, AdvertContent.TEXTS['transmission'], transmission_kb()),
    'body_type': (AdvertStates.waiting_body_type, AdvertContent.TEXTS['body_type'], body_type_kb()),
    'color': (AdvertStates.waiting_color, AdvertContent.TEXTS['color'], color_kb()),
    'vin': (AdvertStates.waiting_vin, AdvertContent.TEXTS['vin'], None),
    'autoteka': (AdvertStates.waiting_autoteka_decision, AdvertContent.TEXTS['autoteka'], autoteka_kb()),
    'license_plate': (AdvertStates.waiting_license_plate, AdvertContent.TEXTS['license_plate'], None),
    'photos': (AdvertStates.waiting_photos, AdvertContent.TEXTS['photos'], skip_photos_kb(0)),
    'contacts': (AdvertStates.waiting_contacts, AdvertContent.TEXTS['contacts'], None),
    'city': (AdvertStates.waiting_city, AdvertContent.TEXTS['city'], None),
    'price': (AdvertStates.waiting_price, AdvertContent.TEXTS['price'], None),
    'description': (AdvertStates.waiting_description, AdvertContent.TEXTS['description'], None),
}

def clean_number(text: str) -> str:
    return re.sub(r'[^\d]', '', text)


async def show_preview(message, state: FSMContext):
    active_sub = await check_active_subscription(message.from_user.id)
    is_active_sub = True if active_sub else False
    data = await state.get_data()
    if data.get('autoteka_purchased'):
        autoteka_info = "Включен отчет Автотеки"
    else:
        autoteka_info = "Нет"

    preview_text = f"""
🚗 {data.get('name', 'Не указано')}
🔢 Год выпуска: {data.get('year', 'Не указано')}
📏 Пробег: {data.get('mileage', 0):,} км
⭐ Состояние: {data.get('condition', 'Не указано')}
💰 Цена: {data.get('price', 0):,} руб
⛽ Топливо: {data.get('fuel_type', 'Не указано')}
⚙️ Двигатель: {data.get('engine_volume', 'Не указано')} л
🔧 КПП: {data.get('transmission', 'Не указано')}
🚙 Кузов: {data.get('body_type', 'Не указано')}
🎨 Цвет: {data.get('color', 'Не указано')}
🔢 VIN: {data.get('vin', 'Не указано')}
🔍 Отчёт автотеки: {autoteka_info}
🚘 Гос номер: {data.get('license_plate', 'Не указано')}
🌍 Город: {data.get('city', 'Не указано')}
📞 Контакты: {data.get('contacts', 'Не указано')}

📝 Описание:
{data.get('description', 'Не указано')}
"""

    photos = data.get('photos', [])

    if photos:
        media = []

        media.append(InputMediaPhoto(
            media=photos[0],
            caption=f"📋 Превью объявления:\n{preview_text}"
        ))

        for photo in photos[1:]:
            media.append(InputMediaPhoto(media=photo))

        if isinstance(message, CallbackQuery):
            await message.message.answer_media_group(media=media)
            await message.message.answer("✅ Все данные заполнены!", reply_markup=publish_kb(is_active_sub))
        else:
            await message.answer_media_group(media=media)
            await message.answer("✅ Все данные заполнены!", reply_markup=publish_kb(is_active_sub))
    else:
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(f"📋 Превью объявления:\n{preview_text}", reply_markup=publish_kb(is_active_sub))
        else:
            await message.answer(f"📋 Превью объявления:\n{preview_text}", reply_markup=publish_kb(is_active_sub))


def get_next_unfilled_step(data: dict) -> str:
    for step in STEPS_ORDER:
        if step not in data or not data[step]:
            return step
    return 'confirmation'


async def process_resume(message, state: FSMContext, step: str):
    if step in STEP_HANDLERS:
        state_obj, text, keyboard = STEP_HANDLERS[step]
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)
        await state.set_state(state_obj)


async def should_show_preview(state: FSMContext) -> bool:
    """Проверяет, все ли обязательные поля заполнены для показа превью"""
    data = await state.get_data()

    for field in REQUIRED_FIELDS:
        if not data.get(field):
            return False

    return True


async def proceed_to_next_step(chat_obj, state: FSMContext, next_step: str, text: str, keyboard=None):
    if await should_show_preview(state):
        await show_preview(chat_obj, state)
    else:
        if isinstance(chat_obj, CallbackQuery):
            await chat_obj.message.answer(text, reply_markup=keyboard)
        else:
            await chat_obj.answer(text, reply_markup=keyboard)

        if next_step in STEP_HANDLERS:
            next_state, _, _ = STEP_HANDLERS[next_step]
            await state.set_state(next_state)


async def publish_ad(obj: Message | CallbackQuery, state: FSMContext):
    if isinstance(obj, CallbackQuery):
        user_id = obj.from_user.id
        message = obj.message
    else:
        user_id = obj.from_user.id
        message = obj
    data = await state.get_data()
    advert = await create_advert_from_state(user_id, data)
    await save_autoteka_report(
        vin=data.get('vin'),
        license_plate=data.get('license_plate'),
        advert_id=advert.id,
        pdf_file_path=data.get('autoteka_pdf_path')
    )

    await message.edit_text(
        "✅ Объявление успешно опубликовано!"
    )
    await message.answer(
        "Оно будет проверено модератором в течение 24 часов.",
        reply_markup=main_menu_kb()
    )
    await notify_moderators_about_new_advert(message.bot, advert.id)
    await state.clear()


async def notify_moderators_about_new_advert(bot, advert_id: int):
    moderators = await User.filter(role__in=["moderator"]).all()

    if not moderators:
        return

    moderator = random.choice(moderators)

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
        ]
    ])

    try:
        if photo_ids:
            media = []
            media.append(InputMediaPhoto(
                media=photo_ids[0],
                caption=text,
                parse_mode="HTML"
            ))

            for photo_id in photo_ids[1:]:
                media.append(InputMediaPhoto(media=photo_id))

            await bot.send_media_group(chat_id=moderator.id, media=media)
            await bot.send_message(
                chat_id=moderator.id,
                text="📋 Просмотр объявления на модерации",
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=moderator.id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except:
        pass

async def handle_autoteka_from_creating(obj: Message | CallbackQuery, state: FSMContext):
    if isinstance(obj, CallbackQuery):
        message = obj.message
    else:
        message = obj
    data = await state.get_data()

    await message.edit_text(
        "⏳ Запрашиваем отчет Автотеки...\n"
        "Это может занять несколько минут."
    )

    vin = data.get('vin')
    license_plate = data.get('license_plate')
    report = None
    try:
        report = await get_vehicle_report_async(vin=vin, license_plate=license_plate)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await state.update_data(autoteka_purchased=False)

        await message.edit_text(
            "❌ Не удалось получить отчет Автотеки.\n"
            "Возможно, по этому VIN или гос номеру нет информации или произошла ошибка.",
            reply_markup=quick_inline([("➡️ Продолжить", "autoteka_continue")])
        )
    if report:
        await state.update_data(
            autoteka_pdf_path=report,
            autoteka_purchased=True,
        )
        try:
            with open(report, 'rb') as pdf_file:
                await message.answer_document(
                    document=pdf_file,
                    caption="📄 Отчет Автотеки"
                )

            await message.edit_text(
                "✅ Отчет Автотеки успешно получен!\n\n"
                "Отчет будет прикреплен к вашему объявлению.",
                reply_markup=quick_inline([("➡️ Продолжить", "autoteka_continue")])
            )

        except Exception as e:
            print(f"❌ Ошибка: {e}")

            await message.answer(
                "❌ Не удалось получить отчет Автотеки.\n"
                "Возможно, по этому VIN или гос номеру нет информации или произошла ошибка.",
                reply_markup=quick_inline([("➡️ Продолжить", "autoteka_continue")])
            )


    else:
        await message.edit_text(
            "❌ Не удалось получить отчет Автотеки.\n"
            "Возможно, по этому VIN или гос номеру нет информации или произошла ошибка.",
            reply_markup=quick_inline([("➡️ Продолжить", "autoteka_continue")])
        )


