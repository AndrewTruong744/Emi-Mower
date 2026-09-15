"""Compatibility name for the shared mower ownership lookup."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.check_mower_ownership import check_mower_ownership


async def find_user_by_mower(mower_id: str | uuid.UUID, db: AsyncSession) -> str | None:
    """Return the owner using the canonical ``mower:{id}:data`` cache entry."""
    return await check_mower_ownership(str(mower_id), db)
