import uuid
from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from config.database import Base


class MowerModel(Base):
    __tablename__ = "mowers"

    # Native PostgreSQL UUID, auto-generated on insert using Python's uuid4
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    serial_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)

    # Foreign key linking back to your String-based Firebase User ID table
    owner_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
