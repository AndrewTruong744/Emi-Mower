import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

if TYPE_CHECKING:
    from src.models.user import UserModel


class MowerModel(Base):
    __tablename__ = "mowers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    serial_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    owner: Mapped["UserModel | None"] = relationship(
        "UserModel", back_populates="mowers"
    )
    telemetry_records: Mapped[list["MowerTelemetryModel"]] = relationship(
        "MowerTelemetryModel",
        back_populates="mower",
        cascade="all, delete-orphan",
    )


class MowerTelemetryModel(Base):
    __tablename__ = "mower_telemetry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mowers.id", ondelete="CASCADE"),
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Location Indicators
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    battery_percentage: Mapped[int] = mapped_column(Integer, nullable=False)

    # Actuator & Motor Metrics
    # (Speed as Float, Direction as Integer: 1=Forward, -1=Reverse, 0=Stopped)
    left_motor_speed: Mapped[float] = mapped_column(Float, default=0.0)
    left_motor_direction: Mapped[int] = mapped_column(Integer, default=0)
    right_motor_speed: Mapped[float] = mapped_column(Float, default=0.0)
    right_motor_direction: Mapped[int] = mapped_column(Integer, default=0)
    cutting_motor_speed: Mapped[float] = mapped_column(Float, default=0.0)

    # Safety Anomalies
    slippage_detected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Relationship Link to the IMU breakdown table
    # uselist=False makes this a strict 1-to-1 relationship mapping
    imu_data: Mapped["MowerImuModel"] = relationship(
        "MowerImuModel",
        back_populates="telemetry",
        uselist=False,
        cascade="all, delete-orphan",
    )
    mower: Mapped["MowerModel"] = relationship(
        "MowerModel", back_populates="telemetry_records"
    )


class MowerImuModel(Base):
    __tablename__ = "mower_imu_data"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 1-to-1 Foreign Key linking back to the parent Telemetry node
    telemetry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mower_telemetry.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Accelerometer (m/s^2) - Measures linear impact/gravity forces
    accel_x: Mapped[float] = mapped_column(Float, nullable=False)
    accel_y: Mapped[float] = mapped_column(Float, nullable=False)
    accel_z: Mapped[float] = mapped_column(Float, nullable=False)

    # Gyroscope (rad/s) - Measures rotational orientation (pitch, roll, yaw)
    gyro_x: Mapped[float] = mapped_column(Float, nullable=False)
    gyro_y: Mapped[float] = mapped_column(Float, nullable=False)
    gyro_z: Mapped[float] = mapped_column(Float, nullable=False)

    # Magnetometer (uT) - Compass heading relative to Earth's field
    mag_x: Mapped[float] = mapped_column(Float, nullable=False)
    mag_y: Mapped[float] = mapped_column(Float, nullable=False)
    mag_z: Mapped[float] = mapped_column(Float, nullable=False)

    # Bidirectional structural connection back to parent mapping
    telemetry: Mapped["MowerTelemetryModel"] = relationship(
        "MowerTelemetryModel", back_populates="imu_data"
    )
