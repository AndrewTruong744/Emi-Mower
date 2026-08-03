import pytest
from sqlalchemy import select

from src.models.mower import MowerModel
from src.repositories.update_mower_name import update_mower_name
from src.schemas.valkey import mower_data_key

pytestmark = pytest.mark.repository


async def test_update_mower_name_updates_database_and_invalidates_cache(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()
    key = mower_data_key(str(mower.id))
    await cache.set(key, "stale")

    await update_mower_name(mower.id, "NewMower", db_session)

    assert (
        await db_session.execute(select(MowerModel.nickname))
    ).scalar_one() == "NewMower"
    assert await cache.get(key) is None
