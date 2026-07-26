import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


class YardModel(Base):
    __tablename__ = "yards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mowers.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Image Asset Storage
    high_fidelity_img_url: Mapped[str] = mapped_column(String(512), nullable=False)
    panoramic_img_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Scale Calibration: Distance a single pixel covers (meters/pixel, e.g. 0.025)
    meters_per_pixel: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Prisma-Style Bundle relationship tracking for the perimeter coordinates
    # Ordered by sequence index to ensure the yard polygon renders accurately
    perimeter_coordinates: Mapped[list["YardCoordinateModel"]] = relationship(
        "YardCoordinateModel",
        back_populates="yard",
        cascade="all, delete-orphan",
        order_by="YardCoordinateModel.sequence_index",
    )

    # Add homography matrix & calibration data if needed for advanced mapping.


class YardCoordinateModel(Base):
    __tablename__ = "yard_coordinates"

    id: Mapped[int] = mapped_column(primary_key=True)
    yard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("yards.id", ondelete="CASCADE"),
        index=True,
    )

    # The Order Sequence: Crucial for drawing lines sequentially
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # Geographic Position Details
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Local Pixel Coordinates (Maps GPS point onto High-Fidelity Image)
    pixel_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pixel_y: Mapped[int | None] = mapped_column(Integer, nullable=True)

    yard: Mapped["YardModel"] = relationship(
        "YardModel", back_populates="perimeter_coordinates"
    )
