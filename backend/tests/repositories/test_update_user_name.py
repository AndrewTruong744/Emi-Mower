import pytest
from sqlalchemy import select

from src.models.user import UserModel
from src.repositories.update_user_name import update_user_name
from src.schemas.valkey import user_data_key

pytestmark = pytest.mark.repository


async def test_update_user_name_updates_database_and_invalidates_cache(
    db_session, cache, seed_user
):
    await seed_user()
    key = user_data_key("user-1")
    await cache.set(key, "old-cache")

    await update_user_name("user-1", "NewName", db_session)

    assert (await db_session.execute(select(UserModel.name))).scalar_one() == "NewName"
    assert await cache.get(key) is None
