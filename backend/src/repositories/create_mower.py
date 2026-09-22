"""Create an unassigned mower during trusted device provisioning."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import RepositoryError, ValidationError
from src.models.mower import MowerModel


async def create_mower(
    mower_id: uuid.UUID,
    nickname: str,
    db: AsyncSession,
) -> MowerModel:
    """Create one mower, or return its prior record for the same UUID.

    The deterministic retry behavior is intentional: provisioning can be
    resumed after an ACL or certificate-issuance failure without minting a
    second mower identity.
    """
    nickname = nickname.strip()
    if not nickname:
        raise ValidationError("mower nickname must be non-empty")

    try:
        existing_by_id = await db.scalar(
            select(MowerModel).where(MowerModel.id == mower_id)
        )
        if existing_by_id is not None:
            return existing_by_id

        mower = MowerModel(
            id=mower_id,
            nickname=nickname,
            owner_id=None,
        )
        db.add(mower)
        await db.commit()
        await db.refresh(mower)
        return mower
    except ValidationError:
        raise
    except Exception as error:
        await db.rollback()
        raise RepositoryError("failed to create mower provisioning record") from error
