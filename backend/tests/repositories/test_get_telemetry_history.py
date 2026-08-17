from datetime import datetime, timedelta, timezone

import pytest

from src.exceptions import ValidationError
from src.models.mower import MowerTelemetryModel
from src.repositories.get_telemetry_history import (
    TELEMETRY_PAGE_SIZE,
    decode_telemetry_cursor,
    get_telemetry_history,
)

pytestmark = pytest.mark.repository


async def test_telemetry_history_cursor_returns_non_overlapping_pages(
    db_session, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            MowerTelemetryModel(
                mower_id=mower.id,
                timestamp=now - timedelta(seconds=index),
                latitude=1,
                longitude=2,
                battery_percentage=index,
            )
            for index in range(TELEMETRY_PAGE_SIZE * 2 + 1)
        ]
    )
    await db_session.commit()

    total, first_page, cursor = await get_telemetry_history(
        str(mower.id), "battery_percentage", None, db_session
    )
    _, second_page, second_cursor = await get_telemetry_history(
        str(mower.id), "battery_percentage", cursor, db_session
    )

    assert total == 121
    assert len(first_page) == len(second_page) == TELEMETRY_PAGE_SIZE
    first_ids = {point.id for point in first_page}
    second_ids = {point.id for point in second_page}
    assert first_ids.isdisjoint(second_ids)
    assert cursor is not None
    assert decode_telemetry_cursor(cursor)[1] == first_page[-1].id
    assert second_cursor is not None


async def test_telemetry_history_rejects_an_invalid_cursor(db_session):
    with pytest.raises(ValidationError, match="cursor"):
        await get_telemetry_history(
            "00000000-0000-4000-8000-000000000001",
            "battery_percentage",
            "not-a-cursor",
            db_session,
        )
