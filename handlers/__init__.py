"""Handlers router registration and exports."""

from aiogram import Router
from handlers.start import router as start_router
from handlers.giveaways import router as giveaways_router
from handlers.referrals import router as referrals_router
from handlers.profile import router as profile_router
from handlers.winners import router as winners_router
from handlers.claims import router as claims_router
from handlers.admin import router as admin_router
from handlers.ai_assistant import router as ai_router
from handlers.leaderboard import router as leaderboard_router
from handlers.redeem import router as redeem_router
from handlers.groups import router as groups_router


def setup_routers() -> Router:
    """Combine and order all feature routers."""
    main_router = Router(name="main_router")
    main_router.include_router(admin_router)
    main_router.include_router(groups_router)
    main_router.include_router(start_router)
    main_router.include_router(giveaways_router)
    main_router.include_router(referrals_router)
    main_router.include_router(profile_router)
    main_router.include_router(winners_router)
    main_router.include_router(claims_router)
    main_router.include_router(ai_router)
    main_router.include_router(leaderboard_router)
    main_router.include_router(redeem_router)
    return main_router
