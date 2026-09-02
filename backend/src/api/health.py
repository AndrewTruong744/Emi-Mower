import valkey.asyncio as valkey
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_db, get_valkey

router = APIRouter(tags=["health"])


async def _dependency_status(
    db: AsyncSession, valkey_client: valkey.Valkey
) -> dict[str, str]:
    postgres_status = "unhealthy"
    valkey_status = "unhealthy"

    try:
        await db.execute(text("SELECT 1"))
        postgres_status = "healthy"
    except Exception:
        pass

    try:
        await valkey_client.ping()
        valkey_status = "healthy"
    except Exception:
        pass

    return {"postgres": postgres_status, "valkey": valkey_status}


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    valkey_client: valkey.Valkey = Depends(get_valkey),
) -> dict[str, str]:
    dependency_status = await _dependency_status(db, valkey_client)
    if "unhealthy" in dependency_status.values():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", **dependency_status},
        )
    return {"status": "healthy", **dependency_status}
