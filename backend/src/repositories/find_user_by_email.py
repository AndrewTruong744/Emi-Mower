"""Repository helper for checking whether an email is already registered."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import RepositoryError
from src.models.user import UserModel

logger = logging.getLogger("repositories.find_user_by_email")


async def find_user_by_email(email: str, db: AsyncSession) -> str | None:
    """Return the user ID registered for ``email``, if one exists."""
    try:
        result = await db.execute(
            select(UserModel.id).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()
    except Exception as db_err:
        logger.error("Failed to look up user email %s", email, exc_info=True)
        raise RepositoryError("Failed to check whether the email is in use") from db_err
