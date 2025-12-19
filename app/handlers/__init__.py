from .start import router as start_router
from .user.menu import router as menu_router
from .user.profile import router as profile_router
from .user.create_ad import router as create_ad_router
from .user.search_ad import router as search_ad_router
from .user.subscription import router as subscription_router
from .user.liked_auto import router as liked_router
from .payment_handler import router as payment_router

routers = [
    start_router,
    menu_router,
    profile_router,
    create_ad_router,
    search_ad_router,
    subscription_router,
    liked_router,
    payment_router
]