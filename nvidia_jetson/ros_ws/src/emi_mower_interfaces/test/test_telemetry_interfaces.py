from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]


def test_telemetry_batch_is_typed_without_media_url_fields() -> None:
    record = (PACKAGE_ROOT / "msg" / "TelemetryRecord.msg").read_text()
    batch = (PACKAGE_ROOT / "msg" / "TelemetryBatch.msg").read_text()
    assert "std_msgs/Header header" in record
    assert "float64 latitude" in record
    assert "float64 longitude" in record
    assert "uint8 battery_percentage" in record
    assert "int8 left_motor_direction" in record
    assert "bool has_imu_data" in record
    assert "rgb_image_url" not in record
    assert "lidar_image_url" not in record
    assert "emi_mower_interfaces/TelemetryRecord[] records" in batch
