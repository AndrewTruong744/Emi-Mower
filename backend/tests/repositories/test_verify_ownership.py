import pytest

from src.repositories.verify_ownership import verify_ownership
from src.schemas.valkey import UserMowersCache, user_mowers_key

pytestmark = pytest.mark.repository


async def test_verify_ownership_populates_cache_on_miss(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()

    assert await verify_ownership("user-1", str(mower.id), db_session)
    assert UserMowersCache.model_validate_json(
        await cache.get(user_mowers_key("user-1"))
    ).root == [str(mower.id)]


async def test_verify_ownership_uses_cached_membership(db_session, cache, seed_user):
    await seed_user()
    mower_id = "00000000-0000-0000-0000-000000000001"
    await cache.set(
        user_mowers_key("user-1"), UserMowersCache([mower_id]).model_dump_json()
    )

    assert await verify_ownership("user-1", mower_id.upper(), db_session)


async def test_verify_ownership_returns_false_for_unknown_user(db_session):
    mower_id = "00000000-0000-0000-0000-000000000001"

    assert not await verify_ownership("missing-user", mower_id, db_session)


async def test_verify_ownership_ignores_malformed_cached_payload(
    db_session, cache, seed_mower, seed_user
):
    await seed_user()
    mower = await seed_mower()
    await cache.set(user_mowers_key("user-1"), "not-json")

    assert await verify_ownership("user-1", str(mower.id), db_session)
