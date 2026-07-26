from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

if TYPE_CHECKING:
    from src.models.mower import MowerModel


class UserModel(Base):
    __tablename__ = "users"

    # Modern SQLAlchemy 2.0 Type-Safe Mapping Syntax
    id: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())

    mowers: Mapped[list["MowerModel"]] = relationship(
        "MowerModel", back_populates="owner"
    )
