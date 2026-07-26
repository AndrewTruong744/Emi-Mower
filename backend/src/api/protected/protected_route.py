from fastapi import APIRouter

from src.api.protected.mower_route import router as mower_router
from src.api.protected.user_route import router as user_router
from src.api.protected.yard_route import router as yard_router

router = APIRouter()

router.include_router(user_router, prefix="/user", tags=["user"])
router.include_router(mower_router, prefix="/mower", tags=["mower"])
router.include_router(yard_router, prefix="/yard", tags=["yard"])
