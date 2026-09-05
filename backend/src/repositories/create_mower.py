"""Create an unassigned mower during trusted device provisioning."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import RepositoryError, ValidationError
from src.models.mower import MowerModel


async def create_mower(
    mower_id: uuid.UUID,
    serial_number: str,
    nickname: str,
    db: AsyncSession,
) -> MowerModel:
    """Create one mower, or return its identical prior provisioning record.

    The deterministic retry behavior is intentional: provisioning can be
    resumed after an ACL or certificate-issuance failure without minting a
    second mower identity.
    """
    serial_number = serial_number.strip()
    nickname = nickname.strip()
    if not serial_number or not nickname:
        raise ValidationError("mower serial number and nickname must be non-empty")

    try:
        existing_by_id = await db.scalar(
            select(MowerModel).where(MowerModel.id == mower_id)
        )
        if existing_by_id is not None:
            if existing_by_id.serial_number != serial_number:
                raise ValidationError(
                    f"mower ID {mower_id} is already assigned to a different "
                    "serial number"
                )
            return existing_by_id

        existing_by_serial = await db.scalar(
            select(MowerModel).where(MowerModel.serial_number == serial_number)
        )
        if existing_by_serial is not None:
            raise ValidationError(
                f"serial number {serial_number!r} is already provisioned as "
                f"{existing_by_serial.id}"
            )

        mower = MowerModel(
            id=mower_id,
            serial_number=serial_number,
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
