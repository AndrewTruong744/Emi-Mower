import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

if TYPE_CHECKING:
    from src.models.mower import MowerModel
    from src.models.user import UserModel


class CutoutModel(Base):
    """A GCS-backed boundary cutout and its upload-verification state."""

    __tablename__ = "cutouts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    assignments: Mapped[list["CutoutMowerAssignmentModel"]] = relationship(
        back_populates="cutout", cascade="all, delete-orphan"
    )


class CutoutMowerAssignmentModel(Base):
    """Associates a verified user cutout with each intended mower."""

    __tablename__ = "cutout_mower_assignments"

    cutout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cutouts.id", ondelete="CASCADE"), primary_key=True
    )
    mower_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mowers.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    cutout: Mapped["CutoutModel"] = relationship(back_populates="assignments")
    mower: Mapped["MowerModel"] = relationship()
