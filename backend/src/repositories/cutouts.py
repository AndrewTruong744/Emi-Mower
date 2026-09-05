import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cutout import CutoutModel, CutoutMowerAssignmentModel


async def create_cutout(
    *,
    owner_id: str,
    object_key: str,
    content_type: str,
    mower_ids: list[str],
    db: AsyncSession,
) -> CutoutModel:
    cutout = CutoutModel(
        owner_id=owner_id,
        object_key=object_key,
        content_type=content_type,
        assignments=[
            CutoutMowerAssignmentModel(mower_id=uuid.UUID(mower_id))
            for mower_id in mower_ids
        ],
    )
    db.add(cutout)
    await db.flush()
    return cutout


async def get_cutout_for_owner(
    *, cutout_id: str, owner_id: str, db: AsyncSession
) -> CutoutModel | None:
    try:
        identifier = uuid.UUID(cutout_id)
    except ValueError:
        return None
    result = await db.execute(
        select(CutoutModel).where(
            CutoutModel.id == identifier, CutoutModel.owner_id == owner_id
        )
    )
    return result.scalar_one_or_none()


async def get_latest_ready_cutout_for_mower(
    *, mower_id: str, db: AsyncSession
) -> CutoutModel | None:
    try:
        identifier = uuid.UUID(mower_id)
    except ValueError:
        return None
    result = await db.execute(
        select(CutoutModel)
        .join(CutoutMowerAssignmentModel)
        .where(
            CutoutMowerAssignmentModel.mower_id == identifier,
            CutoutModel.status == "ready",
        )
        .order_by(CutoutModel.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
