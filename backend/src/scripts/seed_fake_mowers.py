"""Create repeatable fake mowers for the development Firebase user."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from src.config.database import AsyncSessionLocal, engine
from src.config.valkey_client import close_valkey_pool, get_valkey_client
from src.models.mower import MowerImuModel, MowerModel, MowerTelemetryModel
from src.models.user import UserModel
from src.schemas.valkey import (
    mower_data_key,
    mower_owner_key,
    mower_status_key,
    user_mowers_key,
)

SEED_USER_EMAIL = "andrewtruong40024@gmail.com"

FAKE_MOWERS = (
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000001"),
        "serial_number": "EMI-DEV-0001",
        "nickname": "Front Yard Mower",
        "latitude": 30.2672,
        "longitude": -97.7431,
        "battery_percentage": 92,
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000002"),
        "serial_number": "EMI-DEV-0002",
        "nickname": "Back Yard Mower",
        "latitude": 30.2678,
        "longitude": -97.7425,
        "battery_percentage": 76,
    },
    {
        "id": uuid.UUID("00000000-0000-4000-8000-000000000003"),
        "serial_number": "EMI-DEV-0003",
        "nickname": "Side Yard Mower",
        "latitude": 30.2667,
        "longitude": -97.7438,
        "battery_percentage": 61,
    },
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scripts.seed_fake_mowers")


async def seed_fake_mowers() -> None:
    """Upsert three fake mowers and one telemetry sample for each mower."""

    async with AsyncSessionLocal() as db:
        try:
            user = await db.scalar(
                select(UserModel).where(UserModel.email == SEED_USER_EMAIL)
            )
            if user is None:
                raise RuntimeError(
                    f"No PostgreSQL user found for {SEED_USER_EMAIL!r}. "
                    "Sign in once before running this script."
                )

            mower_ids = [mower["id"] for mower in FAKE_MOWERS]
            existing_mowers = (
                await db.scalars(select(MowerModel).where(MowerModel.id.in_(mower_ids)))
            ).all()
            existing_by_id = {mower.id: mower for mower in existing_mowers}

            for fake_mower in FAKE_MOWERS:
                mower = existing_by_id.get(fake_mower["id"])
                if mower is None:
                    mower = MowerModel(id=fake_mower["id"])
                    db.add(mower)

                mower.serial_number = fake_mower["serial_number"]
                mower.nickname = fake_mower["nickname"]
                mower.owner_id = user.id

            await db.flush()
            await db.execute(
                delete(MowerTelemetryModel).where(
                    MowerTelemetryModel.mower_id.in_(mower_ids)
                )
            )

            now = datetime.now(timezone.utc)
            for index, fake_mower in enumerate(FAKE_MOWERS):
                telemetry = MowerTelemetryModel(
                    mower_id=fake_mower["id"],
                    timestamp=now - timedelta(minutes=index * 5),
                    latitude=fake_mower["latitude"],
                    longitude=fake_mower["longitude"],
                    battery_percentage=fake_mower["battery_percentage"],
                    left_motor_speed=0.35 + index * 0.1,
                    left_motor_direction=1,
                    right_motor_speed=0.4 + index * 0.1,
                    right_motor_direction=1,
                    cutting_motor_speed=2_800.0,
                    slippage_detected=False,
                    imu_data=MowerImuModel(
                        accel_x=0.01 * index,
                        accel_y=0.02 * index,
                        accel_z=9.81,
                        gyro_x=0.0,
                        gyro_y=0.01 * index,
                        gyro_z=0.02 * index,
                        mag_x=22.0,
                        mag_y=-4.0,
                        mag_z=41.0,
                    ),
                )
                db.add(telemetry)

            await db.commit()
            logger.info(
                "Seeded %d fake mower(s) for PostgreSQL user %s (%s)",
                len(FAKE_MOWERS),
                user.id,
                user.email,
            )

        except Exception:
            await db.rollback()
            raise

    mower_id_strings = [str(mower["id"]) for mower in FAKE_MOWERS]
    cache_keys = [
        key
        for mower_id in mower_id_strings
        for key in (
            mower_data_key(mower_id),
            mower_owner_key(mower_id),
            mower_status_key(mower_id),
        )
    ]
    async with get_valkey_client() as client:
        await client.delete(user_mowers_key(user_id=user.id), *cache_keys)

    logger.info("Invalidated cached mower data for %s", user.email)


async def main() -> None:
    try:
        await seed_fake_mowers()
    finally:
        await close_valkey_pool()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
