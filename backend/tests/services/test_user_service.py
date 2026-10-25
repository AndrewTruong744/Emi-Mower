from unittest.mock import AsyncMock, Mock

import pytest

from src.exceptions import (
    AuthenticationError,
    UserNotFoundError,
    ValidationError,
)
from src.services import user
from src.zenoh.generated import UserLoginRequest


async def test_create_user_service_validates_claims_and_delegates(monkeypatch):
    create = AsyncMock(return_value={"id": "user-1"})
    monkeypatch.setattr(user, "create_user", create)

    assert await user.create_user_service(
        {"user_id": "user-1", "email": "one@example.test", "name": "One"},
        object(),
    ) == {"id": "user-1"}
    create.assert_awaited_once()
    with pytest.raises(ValidationError):
        await user.create_user_service({"email": "one@example.test"}, object())


async def test_create_user_service_generates_name_when_claim_is_missing(monkeypatch):
    create = AsyncMock(return_value={"id": "user-1"})
    monkeypatch.setattr(user, "create_user", create)
    monkeypatch.setattr(
        user.random, "choices", lambda *_args, **_kwargs: list("Generated")
    )

    await user.create_user_service(
        {"user_id": "user-1", "email": "one@example.test"}, object()
    )

    assert create.await_args.kwargs["name"] == "Generated"


async def test_user_login_service_rejects_empty_token():
    with pytest.raises(ValidationError):
        await user.user_login_service(UserLoginRequest(id_token=""), object())


async def test_user_login_service_rejects_identity_without_user_id(monkeypatch):
    monkeypatch.setattr(user, "verify_firebase_id_token", AsyncMock(return_value={}))

    with pytest.raises(AuthenticationError):
        await user.user_login_service(UserLoginRequest(id_token="token"), object())


def google_identity(user_id="new-user", email="new@example.test"):
    return {
        "user_id": user_id,
        "email": email,
        "email_verified": True,
        "firebase": {"sign_in_provider": "google.com"},
    }


async def test_login_reads_locked_snapshot_and_commits_after_grant(monkeypatch):
    db = AsyncMock()
    monkeypatch.setattr(
        user,
        "verify_firebase_id_token",
        AsyncMock(return_value=google_identity("user-1")),
    )
    monkeypatch.setattr(
        user,
        "user_authorization_snapshot",
        AsyncMock(
            side_effect=[UserNotFoundError("missing"), ({"id": "user-1"}, ["mower-1"])]
        ),
    )
    create = AsyncMock()
    monkeypatch.setattr(user, "create_user_service", create)
    admin = Mock(configure_user_app=AsyncMock(), authorize_connection=AsyncMock())
    monkeypatch.setattr(user, "ZenohAdminClient", lambda: admin)

    async def grant(*args):
        db.commit.assert_not_awaited()

    admin.authorize_connection.side_effect = grant
    result = await user.user_login_service(
        UserLoginRequest(id_token="token"), db, {"id": "a" * 32, "nonce": "b" * 32}
    )
    assert result["authorized"] and result["user_data"]["mowers"] == ["mower-1"]
    create.assert_awaited_once()
    admin.configure_user_app.assert_awaited_once_with("user-1", ["mower-1"])
    db.commit.assert_awaited_once()


async def test_login_rejects_missing_context_and_router_failure(monkeypatch):
    monkeypatch.setattr(
        user,
        "verify_firebase_id_token",
        AsyncMock(return_value=google_identity("user-1")),
    )
    monkeypatch.setattr(
        user,
        "user_authorization_snapshot",
        AsyncMock(return_value=({"id": "user-1"}, [])),
    )
    admin = Mock(
        configure_user_app=AsyncMock(),
        authorize_connection=AsyncMock(side_effect=RuntimeError("router unavailable")),
    )
    monkeypatch.setattr(user, "ZenohAdminClient", lambda: admin)
    db = AsyncMock()
    with pytest.raises(AuthenticationError, match="captured"):
        await user.user_login_service(UserLoginRequest(id_token="token"), db)
    with pytest.raises(RuntimeError):
        await user.user_login_service(
            UserLoginRequest(id_token="token"), db, {"id": "a" * 32, "nonce": "b" * 32}
        )
    db.commit.assert_not_awaited()


@pytest.mark.parametrize(
    "identity",
    [
        {"user_id": "x"},
        {"email": "x@example.test"},
        {"user_id": "x", "email": "x@example.test"},
    ],
)
async def test_switch_requires_verified_google_identity(monkeypatch, identity):
    from src.exceptions import ForbiddenError

    monkeypatch.setattr(
        user, "verify_firebase_id_token", AsyncMock(return_value=identity)
    )
    stage = AsyncMock()
    monkeypatch.setattr(user, "stage_account_switch", stage)
    with pytest.raises((ValidationError, ForbiddenError)):
        await user.update_user_email_service("old", "token", AsyncMock())
    stage.assert_not_awaited()


async def test_same_identity_sync_is_idempotent_and_rejects_foreign_collision(
    monkeypatch,
):
    monkeypatch.setattr(
        user,
        "verify_firebase_id_token",
        AsyncMock(return_value=google_identity("user-1")),
    )
    lookup = AsyncMock(return_value="user-1")
    update = AsyncMock()
    monkeypatch.setattr(user, "find_user_by_email", lookup)
    monkeypatch.setattr(user, "update_user_email", update)
    assert await user.update_user_email_service("user-1", "token", AsyncMock()) == {
        "user_id": "user-1",
        "new_email": "new@example.test",
    }
    update.assert_awaited_once()
    lookup.return_value = "another-user"
    with pytest.raises(ValidationError, match="already in use"):
        await user.update_user_email_service("user-1", "token", AsyncMock())


async def test_switch_revokes_and_scrubs_before_commit_and_rolls_back_failures(
    monkeypatch,
):
    events = []

    async def stage(*args):
        events.append("stage")
        return ["mower-1"]

    async def retire(*args):
        events.append("retire")

    async def scrub(*args):
        events.append("scrub")

    async def commit():
        events.append("commit")

    monkeypatch.setattr(
        user, "verify_firebase_id_token", AsyncMock(return_value=google_identity())
    )
    monkeypatch.setattr(user, "stage_account_switch", stage)
    monkeypatch.setattr(user, "invalidate_account_switch_cache", scrub)
    admin = Mock(retire_user=AsyncMock(side_effect=retire))
    monkeypatch.setattr(user, "ZenohAdminClient", lambda: admin)
    db = AsyncMock()
    db.commit.side_effect = commit
    assert await user.update_user_email_service("old", "proof", db) == {
        "user_id": "new-user",
        "new_email": "new@example.test",
    }
    assert events == ["stage", "retire", "scrub", "commit"]
    admin.retire_user.side_effect = RuntimeError("ACL failed")
    with pytest.raises(RuntimeError):
        await user.update_user_email_service("old", "proof", db)
    db.rollback.assert_awaited_once()
    assert events.count("commit") == 1


@pytest.mark.parametrize("name", ["New Name", "Mária O'Neil-Smith", "New_Name1"])
async def test_update_name_supports_real_display_names(monkeypatch, name):
    update = AsyncMock()
    monkeypatch.setattr(user, "update_user_name", update)
    await user.update_user_name_service("user-1", "  " + name + "  ", object())
    assert update.await_args.args[:2] == ("user-1", name)


@pytest.mark.parametrize("name", ["", "   ", "a" * 65, "bad\nname", "bad\x00name"])
async def test_update_name_rejects_invalid_names(name):
    with pytest.raises(ValidationError):
        await user.update_user_name_service("user-1", name, object())


async def test_get_user_data_service_delegates(monkeypatch):
    get_data = AsyncMock(return_value={"id": "user-1"})
    monkeypatch.setattr(user, "get_user_data", get_data)
    assert await user.get_user_data_service("user-1", object()) == {"id": "user-1"}
