
from .models import (
    User,
    Advert,
    Settings,
    AdvertPhoto,
    FavoriteAdvert,
    AutotekaReport, SearchFilter,
)


async def get_settings():
    settings, _ = await Settings.get_or_create(id=1)
    return settings