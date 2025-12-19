from .admin import router as main_router
from .users import router as users_router
from .adverts import router as adverts_router
from .broadcast import router as broadcast_router
from .coupons import router as coupons_router
from .prices import router as prices_router
from .moderation import router as moderation_router
from .roles import router as roles_router

admin_routers = [
    main_router,
    users_router,
    adverts_router,
    broadcast_router,
    coupons_router,
    prices_router,
    moderation_router,
    roles_router,
]