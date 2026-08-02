from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def protected_status() -> dict[str, str]:
    """Authenticated status endpoint preserving the protected API namespace."""
    return {"status": "protected"}
