from datetime import datetime
from decimal import Decimal
from typing import Iterable, Optional, Dict, Any, List
from uuid import uuid4

from .models import (
    User,
    Referral, Transaction
)


async def get_or_create_user(
    user_id: int,
    username: Optional[str],
    fullname: Optional[str],
) -> (User, bool):
    user, created = await User.get_or_create(
        id=user_id,
        defaults={
            "username": username,
            "fullname": fullname,
        },
    )
    is_new = False
    changed = False
    if username and user.username != username:
        user.username = username
        changed = True
    if fullname and user.fullname != fullname:
        user.fullname = fullname
        changed = True

    if changed:
        await user.save()
    if created:
        is_new = True

    return user, is_new


async def get_user(user_id: int):
    return await User.get_or_none(id=user_id)


async def topup_user_balance(user_id: int, amount: float):
    user = await User.get(id=user_id)
    amount_decimal = Decimal(str(amount))

    user.balance += amount_decimal
    await user.save()

    return user


async def down_user_balance(user_id: int, amount: float):
    user = await User.get(id=user_id)
    amount_decimal = Decimal(str(amount))

    user.balance -= amount_decimal
    await user.save()

    return user


async def add_referral(user_id, referrer_id):
    referrer = await User.get_or_none(id=referrer_id)
    user = await User.get_or_none(id=user_id)

    if not referrer or not user:
        return False

    existing_ref = await Referral.get_or_none(referred=user)
    if existing_ref:
        return False

    await Referral.create(
        referrer=referrer,
        referred=user
    )
    return True


async def get_referral_stats(user_id: int, bot_username: str):
    user = await User.get(id=user_id)

    referrals = await Referral.filter(referrer=user).prefetch_related('referred')
    referral_transactions = await Transaction.filter(type="referral_bonus").all()

    total_earned = sum([t.amount for t in referral_transactions]) if referral_transactions else 0

    active_referrals = []
    for ref in referrals:
        referred_user = ref.referred
        if referred_user.subscription_ends and referred_user.subscription_ends > datetime.now():
            active_referrals.append(referred_user)

    return {
        "referral_count": len(referrals),
        "active_referrals_count": len(active_referrals),
        "referral_percent": user.ref_percent,
        "total_earned": total_earned,
        "referral_link": f"https://t.me/{bot_username}?start=r_{user_id}",
        "referrals": referrals,
        "active_referrals": active_referrals
    }



async def award_referral_bonus(referred_user_id: int, payment_amount: float):
    try:
        referral = await Referral.get_or_none(referred_id=referred_user_id)
        if not referral or not referral.referrer:
            return None

        referrer = await referral.referrer
        bonus_amount = payment_amount * float(referrer.ref_percent) / 100


        referrer.balance += Decimal(str(bonus_amount))
        await referrer.save()

        await Transaction.create(
            user=referrer,
            payment_id=uuid4(),
            amount=bonus_amount,
            payment_type="referral_bonus"
        )

        return {
            "referrer_id": referrer.id,
            "bonus_amount": bonus_amount,
            "ref_percent": referrer.ref_percent
        }

    except Exception as e:
        print(f"Ошибка начисления реферального бонуса: {e}")
        return None


async def is_user_active(user_id: int) -> bool:
    user = await User.get(id=user_id)
    return user.status == "active"


async def is_user_banned(user_id: int) -> bool:
    user = await User.get(id=user_id)
    return user.status == "banned"


async def is_user_shadow_banned(user_id: int) -> bool:
    user = await User.get(id=user_id)
    return user.status == "shadow_ban"


async def get_user_status(user_id: int) -> str:
    user = await User.get(id=user_id)
    return user.status