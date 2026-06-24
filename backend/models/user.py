from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from config.database import Base


class UserModel(Base):
    __tablename__ = "users"

    # Modern SQLAlchemy 2.0 Type-Safe Mapping Syntax
    id: Mapped[str] = mapped_column(String(128), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.now())
