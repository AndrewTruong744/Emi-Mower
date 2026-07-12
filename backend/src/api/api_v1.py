from backend.src.api.protected.protected_route import router as auth_router
from backend.src.api.public.public_route import router as public_router
from backend.src.services.auth import verify_gcp_identity
from fastapi import APIRouter, Depends

router = APIRouter()

router.include_router(
    auth_router,
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(verify_gcp_identity)],  # ◄── FORCES SECURITY ON ALL CHILDS
)
router.include_router(public_router, prefix="/public", tags=["public"])
