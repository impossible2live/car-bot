from datetime import datetime


from .models import (
    User,
    UserSubscription,
    Transaction,
    Advert,
    AdvertPhoto,
    FavoriteAdvert,
    AutotekaReport, SearchFilter, UserCoupon, Coupon,
)


async def check_active_subscription(user_id: int):
    user = await User.get(id=user_id)
    active_sub = await UserSubscription.filter(
        user=user.id,
        is_active=True,
        expires_at__gt=datetime.now()
    ).first()

    if active_sub:
        return active_sub


async def create_transaction(user_id: int, payment_id: str, amount: float, payment_url: str, type: str):
    user = await User.get(id=user_id)
    transaction = await Transaction.create(
        user=user,
        payment_id=payment_id,
        amount=amount,
        type=type,
        payment_url=payment_url
    )
    return transaction


from datetime import datetime, timedelta, timezone


async def create_or_update_subscription(user_id: int, days: int = 30):
    user = await User.get(id=user_id)

    active_sub = await UserSubscription.filter(
        user=user,
        is_active=True
    ).first()

    # Получаем текущее время с учетом временной зоны (UTC)
    now_utc = datetime.now(timezone.utc)

    if active_sub:
        if active_sub.expires_at:
            if active_sub.expires_at.tzinfo is None:
                expires_at_utc = active_sub.expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at_utc = active_sub.expires_at.astimezone(timezone.utc)

            if expires_at_utc > now_utc:
                active_sub.expires_at = expires_at_utc + timedelta(days=days)
            else:
                active_sub.expires_at = now_utc + timedelta(days=days)
        else:
            active_sub.expires_at = now_utc + timedelta(days=days)

        await active_sub.save()
        return active_sub
    else:
        subscription = await UserSubscription.create(
            user=user,
            expires_at=now_utc + timedelta(days=days),
            is_active=True
        )
        return subscription


async def get_user_applied_coupon(user_id: int):
    return await UserCoupon.filter(
        user_id=user_id,
        is_applied=True,
        is_used=False
    ).prefetch_related('coupon').first()


async def apply_coupon_for_user(user_id: int, coupon_code: str):
    coupon = await Coupon.filter(code=coupon_code).first()
    if not coupon:
        return None

    user_coupon = await UserCoupon.filter(user_id=user_id, coupon_id=coupon.id).first()

    if user_coupon:
        if user_coupon.is_applied and not user_coupon.is_used:
            return None
        user_coupon.is_applied = True
        await user_coupon.save()
    else:
        user_coupon = await UserCoupon.create(
            user_id=user_id,
            coupon_id=coupon.id,
            is_applied=True
        )

    return user_coupon


async def mark_coupon_as_used(user_coupon_id: int):
    user_coupon = await UserCoupon.get(id=user_coupon_id)
    user_coupon.is_used = True
    await user_coupon.save()

    coupon = await Coupon.get(id=user_coupon.coupon_id)
    coupon.used_count += 1
    await coupon.save()

    return user_coupon