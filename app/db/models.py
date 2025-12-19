from tortoise import Model, fields


class User(Model):
    id = fields.BigIntField(pk=True)
    username = fields.CharField(max_length=64, null=True)
    fullname = fields.CharField(max_length=255, null=True)

    balance = fields.DecimalField(max_digits=18, decimal_places=2, default=0)
    ref_percent = fields.DecimalField(max_digits=5, decimal_places=2, default=10)

    role = fields.CharField(
        max_length=16,
        default="user",  # user / moderator / admin / owner
    )
    status = fields.CharField(
        max_length=16,
        default="active",  # active / banned / shadow_ban
    )

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"


class UserCoupon(Model):
    user = fields.ForeignKeyField("models.User", related_name="user_coupons")
    coupon = fields.ForeignKeyField("models.Coupon", related_name="user_coupons")
    is_applied = fields.BooleanField(default=False)
    is_used = fields.BooleanField(default=False)

    class Meta:
        table = "user_coupons"
        unique_together = (("user", "coupon"),)

class Referral(Model):
    id = fields.IntField(pk=True)
    referrer = fields.ForeignKeyField(
        "models.User",
        related_name="referrals_made",
        null=True,
        on_delete=fields.SET_NULL,
    )
    referred = fields.OneToOneField(
        "models.User",
        related_name="referred_by",
        on_delete=fields.CASCADE,
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "referrals"


class Advert(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField(
        "models.User",
        related_name="adverts",
        on_delete=fields.CASCADE,
    )

    name = fields.CharField(max_length=255)  # марка + модель
    year = fields.IntField()
    mileage = fields.IntField()  # км
    condition = fields.CharField(max_length=32)  # Отличное / Хорошее / Требует ремонта
    fuel_type = fields.CharField(max_length=16)  # Бензин / Дизель / Газ
    engine_volume = fields.CharField(max_length=16)  # "1.6", "2.0"
    transmission = fields.CharField(max_length=16)  # Механика / Автомат / ...
    body_type = fields.CharField(max_length=32)  # Седан / SUV / ...
    color = fields.CharField(max_length=32)

    vin = fields.CharField(max_length=17)
    license_plate = fields.CharField(max_length=32)

    contacts = fields.CharField(max_length=255)
    city = fields.CharField(max_length=128)

    description = fields.TextField()
    price = fields.DecimalField(max_digits=18, decimal_places=2)

    status = fields.CharField(
        max_length=16,
        default="pending",  # waiting_to_pay / pending / active / rejected
    )

    autoteka_purchased = fields.BooleanField(default=False)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "adverts"


class AdvertPhoto(Model):
    id = fields.IntField(pk=True)
    advert = fields.ForeignKeyField(
        "models.Advert",
        related_name="photos",
        on_delete=fields.CASCADE,
    )
    file_id = fields.CharField(max_length=255)  # Telegram file_id
    position = fields.IntField(default=0)  # порядок показа

    class Meta:
        table = "advert_photos"


class FavoriteAdvert(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="favorites",
        on_delete=fields.CASCADE,
    )
    advert = fields.ForeignKeyField(
        "models.Advert",
        related_name="liked_by",
        on_delete=fields.CASCADE,
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "favorite_adverts"
        unique_together = ("user", "advert")


class SearchFilter(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="search_filters",
        on_delete=fields.CASCADE,
    )

    city = fields.CharField(max_length=128, null=True)
    name = fields.CharField(max_length=255, null=True)
    year = fields.IntField(null=True)
    condition = fields.CharField(max_length=32, null=True)
    fuel_type = fields.CharField(max_length=16, null=True)

    mileage_from = fields.IntField(null=True)
    mileage_to = fields.IntField(null=True)

    price_from = fields.DecimalField(
        max_digits=18, decimal_places=2, null=True
    )
    price_to = fields.DecimalField(
        max_digits=18, decimal_places=2, null=True
    )

    engine_volume_max = fields.CharField(max_length=16, null=True)
    transmission = fields.CharField(max_length=16, null=True)
    body_type = fields.CharField(max_length=32, null=True)
    color = fields.CharField(max_length=32, null=True)

    is_default = fields.BooleanField(default=False)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "search_filters"


class AutotekaReport(Model):
    id = fields.IntField(pk=True)
    advert = fields.OneToOneField(
        "models.Advert",
        related_name="autoteka_report",
        on_delete=fields.CASCADE,
    )
    vin = fields.CharField(max_length=17)
    license_plate = fields.CharField(max_length=15, null=True)
    pdf_file_path = fields.CharField(max_length=512, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "autoteka_reports"


class UserSubscription(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="subscriptions",
        on_delete=fields.CASCADE,
    )

    started_at = fields.DatetimeField(auto_now_add=True)
    expires_at = fields.DatetimeField(null=True)

    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "user_subscriptions"


class Coupon(Model):
    id = fields.IntField(pk=True)
    code = fields.CharField(max_length=64, unique=True)
    description = fields.TextField(null=True)

    discount_percent = fields.DecimalField(max_digits=5, decimal_places=2)
    max_uses = fields.IntField(null=True)
    used_count = fields.IntField(default=0)

    is_active = fields.BooleanField(default=True)
    valid_from = fields.DatetimeField(null=True)
    valid_to = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "coupons"


class Transaction(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="transactions",
        on_delete=fields.CASCADE,
    )

    payment_id = fields.CharField(max_length=255)
    amount = fields.DecimalField(max_digits=18, decimal_places=2)

    type = fields.CharField(
        max_length=32,
        default="other",  # autoteka / autoteka2 / topup / advert_publish / subscription / referral_bonus
    )
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "transactions"


class Broadcast(Model):
    id = fields.IntField(pk=True)
    created_by = fields.ForeignKeyField(
        "models.User",
        related_name="broadcasts_created",
        null=True,
        on_delete=fields.SET_NULL,
    )

    text = fields.TextField(null=True)
    media_type = fields.CharField(
        max_length=16,
        null=True,
    )  # photo / document / None
    media_file_id = fields.CharField(max_length=255, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "broadcasts"


class AutotekaBalance(Model):
    id = fields.IntField(pk=True)
    remaining_reports = fields.IntField(default=0)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "autoteka_balance"


class Settings(Model):
    id = fields.IntField(pk=True)
    autoteka_price = fields.DecimalField(max_digits=18, decimal_places=2, default=150)
    advert_publish_price = fields.DecimalField(max_digits=18, decimal_places=2, default=50)
    subscription_price = fields.DecimalField(max_digits=18, decimal_places=2, default=250)

    class Meta:
        table = "settings"