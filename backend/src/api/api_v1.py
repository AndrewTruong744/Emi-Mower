from fastapi import APIRouter, Depends

from src.api.protected.protected import router as auth_router
from src.api.public.public import router as public_router
from src.services.auth import verify_gcp_identity

router = APIRouter()

router.include_router(
    auth_router,
    prefix="/protected",
    tags=["protected"],
    dependencies=[Depends(verify_gcp_identity)],
)
router.include_router(public_router, prefix="/public", tags=["public"])
