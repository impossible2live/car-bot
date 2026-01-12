from decimal import Decimal
from typing import Iterable, Optional, Dict, Any, List
from tortoise.exceptions import DoesNotExist
from pathlib import Path

from .models import (
    User,
    Advert,
    AdvertPhoto,
    FavoriteAdvert,
    AutotekaReport, SearchFilter, Transaction,
)
from app.services.car_generation import apply_generation_filter, BRAND_TRANSLATIONS
from ..other import _format_price


async def create_advert_from_state(user_id: int, data: Dict[str, Any]) -> Advert:
    advert = await Advert.create(
        owner_id=user_id,
        name=data.get("name", ""),
        year=data.get("year", 2015),
        mileage=int(data.get("mileage") or 0),
        condition=data.get("condition", ""),
        fuel_type=data.get("fuel_type", ""),
        engine_volume=str(data.get("engine_volume", "")),
        transmission=data.get("transmission", ""),
        body_type=data.get("body_type", ""),
        color=data.get("color", ""),
        vin=data.get("vin", ""),
        license_plate=data.get("license_plate", ""),
        contacts=data.get("contacts", ""),
        city=data.get("city", ""),
        description=data.get("description", ""),
        price=data.get("price") or 0,
        autoteka_purchased=bool(data.get("autoteka_purchased")),
        status="pending",
    )

    photos = data.get("photos") or []
    for idx, file_id in enumerate(photos):
        await AdvertPhoto.create(
            advert=advert,
            file_id=file_id,
            position=idx,
        )

    report = data.get("autoteka_report")
    if report:
        await AutotekaReport.create(
            advert=advert,
            vin=advert.vin,
            web_link=report.get("webLink") or None,
            pdf_link=report.get("pdfLink") or None,
            raw_data=report,
        )

    return advert


async def get_advert_by_id(advert_id: int) -> Optional[Advert]:
    try:
        advert = await Advert.get(id=advert_id).prefetch_related("photos")
    except Advert.DoesNotExist:
        return None
    return advert


async def add_favorite_advert(user_id: int, advert_id: int) -> FavoriteAdvert:
    fav, _ = await FavoriteAdvert.get_or_create(
        user_id=user_id,
        advert_id=advert_id,
    )
    return fav


async def get_random_advert_with_filters(
        filters: Dict[str, Any],
        exclude_ids: Optional[Iterable[int]] = None,
) -> Optional[Advert]:
    name = filters.get("name")
    brand = None
    model = None

    if name:
        name = name.strip()
        for possible_brand in BRAND_TRANSLATIONS:
            if name.lower().startswith(possible_brand.lower()):
                brand = possible_brand
                model = name[len(brand):].strip()
                break

        if not brand:
            parts = name.split()
            if len(parts) >= 2:
                brand = parts[0]
                model = ' '.join(parts[1:])

    if brand and model and 'year' in filters and filters['year']:
        filters_copy = filters.copy()
        filters_copy = apply_generation_filter(filters_copy, brand, model)

        if 'year_from' in filters_copy and 'year_to' in filters_copy:
            filters = filters_copy

    qs = Advert.filter(status="pending")

    city = filters.get("city")
    if city:
        qs = qs.filter(city__iexact=city)

    if name:
        qs = qs.filter(name__icontains=name)

    if 'year' in filters:
        year = filters.get("year")
        if year:
            try:
                year_int = int(str(year).strip())
                qs = qs.filter(year=year_int)
            except (ValueError, TypeError):
                pass

    elif 'year_from' in filters or 'year_to' in filters:
        year_from = filters.get("year_from")
        year_to = filters.get("year_to")

        if year_from is not None:
            try:
                year_from_int = int(str(year_from).strip())
                qs = qs.filter(year__gte=year_from_int)
            except (ValueError, TypeError):
                pass

        if year_to is not None:
            try:
                year_to_int = int(str(year_to).strip())
                qs = qs.filter(year__lte=year_to_int)
            except (ValueError, TypeError):
                pass

    condition = filters.get("condition")
    if condition:
        qs = qs.filter(condition=condition)

    fuel_type = filters.get("fuel_type")
    if fuel_type:
        qs = qs.filter(fuel_type=fuel_type)

    mileage_from = filters.get("mileage_from")
    mileage_to = filters.get("mileage_to")
    if mileage_from is not None:
        try:
            qs = qs.filter(mileage__gte=int(mileage_from))
        except (ValueError, TypeError):
            pass
    if mileage_to is not None:
        try:
            qs = qs.filter(mileage__lte=int(mileage_to))
        except (ValueError, TypeError):
            pass

    price_from = filters.get("price_from")
    price_to = filters.get("price_to")
    if price_from is not None:
        try:
            qs = qs.filter(price__gte=float(price_from))
        except (ValueError, TypeError):
            pass
    if price_to is not None:
        try:
            qs = qs.filter(price__lte=float(price_to))
        except (ValueError, TypeError):
            pass

    engine_volume_max = filters.get("engine_volume_max")
    if engine_volume_max:
        qs = qs.filter(engine_volume__icontains=str(engine_volume_max))

    transmission = filters.get("transmission")
    if transmission:
        qs = qs.filter(transmission=transmission)

    body_type = filters.get("body_type")
    if body_type:
        qs = qs.filter(body_type=body_type)

    color = filters.get("color")
    if color:
        qs = qs.filter(color=color)

    if exclude_ids:
        try:
            exclude_list = list(exclude_ids)
            if exclude_list:
                qs = qs.exclude(id__in=exclude_list)
        except Exception:
            pass

    count = await qs.count()
    if count == 0:
        return None

    import random
    random_offset = random.randint(0, max(0, count - 1))

    advert = await qs.offset(random_offset).prefetch_related("photos").first()
    return advert

async def get_user_favorites(user_id: int) -> List[FavoriteAdvert]:
    return await FavoriteAdvert.filter(
        user_id=user_id
    ).prefetch_related(
        "advert",
        "advert__photos"
    ).order_by("-created_at")

async def remove_from_favorites(user_id: int, advert_id: int) -> bool:
    deleted_count = await FavoriteAdvert.filter(
        user_id=user_id,
        advert_id=advert_id
    ).delete()
    return deleted_count > 0



async def save_or_update_user_filter(
        user_id: int,
        update_fields: Dict[str, Any]
) -> SearchFilter:

    try:
        filter_obj = await SearchFilter.get(user_id=user_id)

        for field, value in update_fields.items():
            if hasattr(filter_obj, field):
                setattr(filter_obj, field, value)

        await filter_obj.save()
        return filter_obj

    except DoesNotExist:
        filter_obj = await SearchFilter.create(
            user_id=user_id,
            **update_fields
        )
        return filter_obj


async def get_user_filter(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        filter_obj = await SearchFilter.get(user_id=user_id)

        filter_data = {}
        fields = [
            'city', 'name', 'year', 'condition', 'fuel_type',
            'mileage_from', 'mileage_to', 'price_from', 'price_to',
            'engine_volume_max', 'transmission', 'body_type', 'color'
        ]

        for field in fields:
            value = getattr(filter_obj, field)
            if value is not None:
                filter_data[field] = value

        return filter_data if filter_data else None

    except DoesNotExist:
        return None

async def delete_user_filter(user_id: int) -> bool:
    try:
        filter_obj = await SearchFilter.get(user_id=user_id)
        await filter_obj.delete()
        return True
    except DoesNotExist:
        return False



async def reject_advert_and_refund(advert_id: int, reason: str, bot):
    advert = await Advert.get(id=advert_id)
    owner = await User.get(id=advert.owner_id)

    transaction = await Transaction.filter(
        user=owner,
        type="advert",
    ).order_by("-created_at").first()

    advert.status = "rejected"
    await advert.save()

    refund_amount = Decimal('0')

    if transaction:
        refund_amount = Decimal(str(abs(transaction.amount)))

        owner.balance += refund_amount
        await owner.save()

    try:
        refund_text = ""
        if refund_amount > 0:
            refund_text = f"\n💰 Вам возвращено: {_format_price(refund_amount)}₽"

        await bot.send_message(
            chat_id=owner.id,
            text=f"❌ Ваше объявление отклонено\n\n"
                 f"🚗 {advert.name}\n"
                 f"💰 Цена: {_format_price(advert.price)}\n"
                 f"📋 Причина: {reason}{refund_text}\n\n"
                 f"Если вы не согласны с решением, обратитесь в поддержку."
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления пользователю: {e}")

    return refund_amount
