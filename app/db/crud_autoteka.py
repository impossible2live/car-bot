from typing import Iterable, Optional, Dict, Any, List
from tortoise.exceptions import DoesNotExist
from pathlib import Path
import os
from aiogram.types import Message, CallbackQuery

from .crud_admin import get_settings
from .crud_user import get_user, topup_user_balance, down_user_balance
from .models import (
    User,
    Advert,
    AutotekaReport,
)
from app.keyboards.advert_content import AdvertContent
from app.keyboards.builders import autoteka_buy_kb


async def handle_autoteka_request(obj: Message | CallbackQuery, advert_id: int):
    if isinstance(obj, CallbackQuery):
        message = obj.message
    else:
        message = obj

    try:
        advert = await Advert.get(id=advert_id)
    except DoesNotExist:
        await message.answer("❌ Объявление не найдено")
        return
    try:
        report = await AutotekaReport.get(advert_id=advert_id)

        if report.pdf_file_path and os.path.exists(report.pdf_file_path):
            with open(report.pdf_file_path, 'rb') as pdf_file:
                await message.answer_document(
                    pdf_file,
                    caption=f"📄 Отчет Autoteka для {advert.name}"
                )
            return
        else:
            await report.delete()
            await message.answer(
                AdvertContent.TEXTS['autoteka'],
                reply_markup=autoteka_buy_kb()
            )


    except DoesNotExist:
        if advert.autoteka_purchased:
            await message.answer(
                "⏳ Отчет Autoteka уже куплен и обрабатывается...\n"
                "Пожалуйста, подождите немного.",
            )
            return

        await message.answer(
            AdvertContent.TEXTS['autoteka'],
            reply_markup=autoteka_buy_kb()
        )


async def handle_autoteka_purchase(obj: Message | CallbackQuery, advert_id: int = None):
    settings = await get_settings()
    price = settings.autoteka_price
    user_id = obj.from_user.id

    if isinstance(obj, CallbackQuery):
        message = obj.message
    else:
        message = obj
    user = await get_user(user_id)
    user_balance = user.balance


    try:
        advert = await Advert.get(id=advert_id)
    except DoesNotExist:
        await message.answer("❌ Объявление не найдено")
        return

    try:
        existing_report = await AutotekaReport.get(advert_id=advert_id)
        if existing_report.pdf_file_path and os.path.exists(existing_report.pdf_file_path):
            with open(existing_report.pdf_file_path, 'rb') as pdf_file:
                await message.answer_document(
                    pdf_file,
                    caption=f"📄 Отчет Autoteka"
                )
            return

    except DoesNotExist:
        pass

    if advert.autoteka_purchased:
        await message.answer(
            "⏳ Отчет Autoteka уже куплен и обрабатывается...\n"
            "Пожалуйста, подождите немного.",
        )
        return

    if user_balance >= price:
        await down_user_balance(user_id, settings.autoteka_price)

    else:
        from app.handlers.payment_handler import create_payment_flow
        await create_payment_flow(obj, user_id, "autoteka")
        return
    await message.edit_text(
        "⏳ Запрашиваем отчет Автотеки...\n"
        "Это может занять несколько минут."
    )

    try:
        from app.services.autoteca_no_api import get_vehicle_report_async
        pdf_file_path = await get_vehicle_report_async(
            vin=advert.vin,
            license_plate=advert.license_plate,
        )

        report = await save_autoteka_report(
            vin=advert.vin,
            license_plate=advert.license_plate,
            advert_id=advert.id,
            pdf_file_path=pdf_file_path
        )

        advert.autoteka_purchased = True
        await advert.save()

        with open(pdf_file_path, 'rb') as pdf_file:
            await message.answer_document(
                pdf_file,
                caption="📄 Отчет Автотеки"
            )


    except Exception as e:
        print(f"❌ Ошибка получения отчета: {e}")
        await message.edit_text(
            "❌ Не удалось получить отчет Автотеки.\n"
            "Возможно, по этому VIN или гос номеру нет информации или произошла ошибка.",
        )


async def save_autoteka_report(
        vin: str,
        license_plate: str,
        advert_id: int,
        pdf_file_path: Optional[str] = None,
) -> AutotekaReport:

    if pdf_file_path:
        pdf_file_path = f"/reports/{Path(pdf_file_path).name}"

    report = await AutotekaReport.create(
        advert_id=advert_id,
        vin=vin,
        license_plate=license_plate,
        pdf_file_path=pdf_file_path,
    )
    return report
