from datetime import datetime, timezone

from src.scripts.seed_fake_mowers import (
    FAKE_MOWERS,
    TELEMETRY_SAMPLES_PER_MOWER,
    _fake_telemetry,
)


def test_fake_mower_seed_builds_180_ordered_samples_with_imu_data():
    records = _fake_telemetry(
        FAKE_MOWERS[0], 0, datetime(2026, 1, 1, tzinfo=timezone.utc)
    )

    assert len(records) == TELEMETRY_SAMPLES_PER_MOWER == 180
    assert records[0].timestamp < records[-1].timestamp
    assert len({record.timestamp for record in records}) == 180
    assert all(record.mower_id == FAKE_MOWERS[0]["id"] for record in records)
    assert all(record.imu_data is not None for record in records)
