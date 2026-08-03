import pytest
from sqlalchemy import select

from src.models.user import UserModel
from src.repositories.update_user_email import update_user_email
from src.schemas.valkey import user_data_key

pytestmark = pytest.mark.repository


async def test_update_user_email_updates_database_and_invalidates_cache(
    db_session, cache, seed_user
):
    await seed_user()
    key = user_data_key("user-1")
    await cache.set(key, "old-cache")

    await update_user_email("user-1", "new@example.test", db_session)

    assert (
        await db_session.execute(select(UserModel.email))
    ).scalar_one() == "new@example.test"
    assert await cache.get(key) is None
