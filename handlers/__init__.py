"""Handlers router registration and exports."""

from aiogram import Router
from handlers.start import router as start_router
from handlers.giveaways import router as giveaways_router
from handlers.referrals import router as referrals_router
from handlers.profile import router as profile_router
from handlers.winners import router as winners_router
from handlers.claims import router as claims_router
from handlers.admin import router as admin_router


def setup_routers() -> Router:
    """Combine and order all feature routers."""
    main_router = Router(name="main_router")
    main_router.include_router(admin_router)
    main_router.include_router(start_router)
    main_router.include_router(giveaways_router)
    main_router.include_router(referrals_router)
    main_router.include_router(profile_router)
    main_router.include_router(winners_router)
    main_router.include_router(claims_router)
    return main_router
