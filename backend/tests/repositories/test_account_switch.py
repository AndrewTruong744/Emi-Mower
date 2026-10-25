"""Ownership, rollback and old-email reuse against disposable Postgres/Valkey."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import func, select

from src.config.database import AsyncSessionLocal
from src.models.mower import MowerModel, MowerTelemetryModel
from src.models.user import UserModel
from src.repositories.account_switch import (
    stage_account_switch,
    user_authorization_snapshot,
)
from src.repositories.find_user_by_email import find_user_by_email
from src.schemas.valkey import (
    ZENOH_TOKEN_EXPIRY_KEY,
    mower_data_key,
    user_data_key,
    user_mowers_key,
)
from src.services import user
from src.zenoh.generated import UserLoginRequest

pytestmark = pytest.mark.repository


def google(uid, email):
    return {
        "user_id": uid,
        "email": email,
        "email_verified": True,
        "name": "Fresh signup",
        "firebase": {"sign_in_provider": "google.com"},
    }


@pytest.mark.parametrize("target_exists", [False, True])
async def test_switch_moves_all_mowers_scrubs_source_and_allows_fresh_old_signup(
    monkeypatch, db_session, cache, seed_user, seed_mower, target_exists
):
    await seed_user(email="old@example.test", name="Original Display Name")
    if target_exists:
        await seed_user(
            user_id="new-user", email="new@example.test", name="Existing Target"
        )
    await seed_user(user_id="unrelated", email="unrelated@example.test")
    first = await seed_mower(owner_id="user-1")
    second = await seed_mower(owner_id="user-1")
    other = await seed_mower(owner_id="unrelated")
    db_session.add(
        MowerTelemetryModel(
            mower_id=first.id, latitude=1, longitude=2, battery_percentage=90
        )
    )
    await db_session.commit()
    await cache.set(user_data_key("user-1"), json.dumps({"email": "old@example.test"}))
    await cache.set(
        user_mowers_key("user-1"), json.dumps([str(first.id), str(second.id)])
    )
    await cache.set(mower_data_key(str(first.id)), json.dumps({"owner_id": "user-1"}))
    await cache.hset(ZENOH_TOKEN_EXPIRY_KEY, "user-1", "retired")
    admin = Mock(
        retire_user=AsyncMock(),
        configure_user_app=AsyncMock(),
        authorize_connection=AsyncMock(),
    )
    monkeypatch.setattr(user, "ZenohAdminClient", lambda: admin)
    identity = AsyncMock(return_value=google("new-user", "new@example.test"))
    monkeypatch.setattr(user, "verify_firebase_id_token", identity)
    result = await user.update_user_email_service("user-1", "new-proof", db_session)
    assert result == {"user_id": "new-user", "new_email": "new@example.test"}
    owners = dict(
        (await db_session.execute(select(MowerModel.id, MowerModel.owner_id))).all()
    )
    assert owners[first.id] == owners[second.id] == "new-user"
    assert owners[other.id] == "unrelated"
    assert (
        await db_session.execute(select(func.count()).select_from(MowerTelemetryModel))
    ).scalar_one() == 1
    assert await find_user_by_email("old@example.test", db_session) is None
    assert (
        await db_session.execute(select(UserModel.id).where(UserModel.id == "user-1"))
    ).scalar_one_or_none() is None
    for key in [
        user_data_key("user-1"),
        user_mowers_key("user-1"),
        mower_data_key(str(first.id)),
    ]:
        assert await cache.get(key) is None
    assert await cache.hget(ZENOH_TOKEN_EXPIRY_KEY, "user-1") is None
    admin.retire_user.assert_awaited_once_with("user-1")
    await cache.set(user_mowers_key("user-1"), json.dumps([str(first.id)]))
    identity.return_value = google("user-1", "old@example.test")
    fresh = await user.user_login_service(
        UserLoginRequest(id_token="old-google"),
        db_session,
        {"id": "a" * 32, "nonce": "b" * 32},
    )
    assert fresh["user_data"]["mowers"] == []
    assert fresh["user_data"]["name"] == "Fresh signup"
    admin.configure_user_app.assert_awaited_with("user-1", [])


@pytest.mark.parametrize("failure", ["acl", "cache"])
async def test_failure_rolls_back_without_losing_mowers(
    monkeypatch, db_session, seed_user, seed_mower, failure
):
    await seed_user()
    await seed_mower(owner_id="user-1")
    monkeypatch.setattr(
        user,
        "verify_firebase_id_token",
        AsyncMock(return_value=google("new", "new@example.test")),
    )
    admin = Mock(retire_user=AsyncMock(), configure_user_app=AsyncMock())
    monkeypatch.setattr(user, "ZenohAdminClient", lambda: admin)
    if failure == "acl":
        admin.retire_user.side_effect = RuntimeError("offline")
    else:
        monkeypatch.setattr(
            user,
            "invalidate_account_switch_cache",
            AsyncMock(side_effect=RuntimeError("offline")),
        )
    with pytest.raises(RuntimeError, match="offline"):
        await user.update_user_email_service("user-1", "proof", db_session)
    assert (await db_session.execute(select(UserModel.id))).scalar_one() == "user-1"
    assert (
        await db_session.execute(select(MowerModel.owner_id))
    ).scalar_one() == "user-1"


async def test_login_cannot_republish_ownership_during_switch(
    db_session, seed_user, seed_mower
):
    from src.exceptions import UserNotFoundError

    await seed_user()
    await seed_mower(owner_id="user-1")
    await stage_account_switch("user-1", "new", "new@example.test", db_session)
    async with AsyncSessionLocal() as other:
        login = asyncio.create_task(user_authorization_snapshot("user-1", other))
        await asyncio.sleep(0.05)
        assert not login.done()
        await db_session.commit()
        with pytest.raises(UserNotFoundError):
            await asyncio.wait_for(login, 3)
