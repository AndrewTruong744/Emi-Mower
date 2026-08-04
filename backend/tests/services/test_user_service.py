from unittest.mock import AsyncMock, Mock

import pytest

from src.exceptions import (
    AuthenticationError,
    ForbiddenError,
    UserNotFoundError,
    ValidationError,
)
from src.services import user
from src.zenoh.generated import UserLoginRequest


async def test_create_user_service_validates_claims_and_delegates(monkeypatch):
    create = AsyncMock(return_value={"id": "user-1"})
    monkeypatch.setattr(user, "create_user", create)

    assert await user.create_user_service(
        {"uid": "user-1", "email": "one@example.test", "name": "One"}, object()
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
        {"uid": "user-1", "email": "one@example.test"}, object()
    )

    assert create.await_args.kwargs["name"] == "Generated"


async def test_user_login_service_rejects_empty_token():
    with pytest.raises(ValidationError):
        await user.user_login_service(UserLoginRequest(id_token=""), object())


async def test_user_login_service_rejects_identity_without_user_id(monkeypatch):
    monkeypatch.setattr(user, "verify_gcp_identity", AsyncMock(return_value={}))

    with pytest.raises(AuthenticationError):
        await user.user_login_service(UserLoginRequest(id_token="token"), object())


async def test_user_login_service_creates_missing_user(monkeypatch):
    monkeypatch.setattr(
        user,
        "verify_gcp_identity",
        AsyncMock(
            return_value={
                "uid": "user-1",
                "email": "one@example.test",
                "name": "One",
            }
        ),
    )
    monkeypatch.setattr(
        user, "get_user_data", AsyncMock(side_effect=UserNotFoundError("missing"))
    )
    monkeypatch.setattr(
        user,
        "create_user_service",
        AsyncMock(
            return_value={
                "id": "user-1",
                "email": "one@example.test",
                "name": "One",
                "created_at": None,
            }
        ),
    )
    monkeypatch.setattr(user, "get_mowers_of_user", AsyncMock(return_value=[]))
    monkeypatch.setattr(user, "generate_jwt_token", Mock(return_value="jwt"))
    admin = Mock()
    admin.configure_user_app = AsyncMock()
    monkeypatch.setattr(user, "ZenohAdminClient", Mock(return_value=admin))
    monkeypatch.setattr(user, "record_zenoh_credential_expiry", AsyncMock())

    result = await user.user_login_service(UserLoginRequest(id_token="token"), object())

    assert result.user_id == "user-1"


async def test_update_user_email_service_rejects_missing_email_claim(monkeypatch):
    monkeypatch.setattr(
        user, "verify_gcp_identity", AsyncMock(return_value={"uid": "user-1"})
    )

    with pytest.raises(ValidationError):
        await user.update_user_email_service("user-1", "token", object())


async def test_update_user_email_service_delegates_verified_email(monkeypatch):
    update = AsyncMock()
    monkeypatch.setattr(
        user,
        "verify_gcp_identity",
        AsyncMock(return_value={"uid": "user-1", "email": "new@example.test"}),
    )
    monkeypatch.setattr(user, "update_user_email", update)

    await user.update_user_email_service("user-1", "token", object())

    update.assert_awaited_once()


async def test_get_user_data_service_delegates(monkeypatch):
    get_data = AsyncMock(return_value={"id": "user-1"})
    monkeypatch.setattr(user, "get_user_data", get_data)

    assert await user.get_user_data_service("user-1", object()) == {"id": "user-1"}
    get_data.assert_awaited_once()


async def test_get_zenoh_jwt_service_configures_acl_and_records_expiry(monkeypatch):
    monkeypatch.setattr(user, "get_mowers_of_user", AsyncMock(return_value=["mower-1"]))
    monkeypatch.setattr(user, "generate_jwt_token", Mock(return_value="jwt"))
    monkeypatch.setattr(user, "record_zenoh_credential_expiry", AsyncMock())
    admin = Mock()
    admin.configure_user_app = AsyncMock()
    monkeypatch.setattr(user, "ZenohAdminClient", Mock(return_value=admin))

    assert await user.get_zenoh_jwt_service("user-1", object()) == "jwt"
    admin.configure_user_app.assert_awaited_once()


async def test_update_user_email_service_requires_matching_verified_identity(
    monkeypatch,
):
    monkeypatch.setattr(
        user,
        "verify_gcp_identity",
        AsyncMock(return_value={"uid": "other", "email": "other@example.test"}),
    )

    with pytest.raises(ForbiddenError):
        await user.update_user_email_service("user-1", "token", object())


async def test_update_user_name_service_validates_then_delegates(monkeypatch):
    update = AsyncMock()
    monkeypatch.setattr(user, "update_user_name", update)

    await user.update_user_name_service("user-1", "NewName", object())
    update.assert_awaited_once()
    with pytest.raises(ValidationError):
        await user.update_user_name_service("user-1", "not valid", object())


async def test_user_login_service_configures_zenoh_and_records_expiry(monkeypatch):
    monkeypatch.setattr(
        user,
        "verify_gcp_identity",
        AsyncMock(
            return_value={"uid": "user-1", "email": "one@example.test", "name": "One"}
        ),
    )
    monkeypatch.setattr(
        user,
        "get_user_data",
        AsyncMock(
            return_value={
                "id": "user-1",
                "email": "one@example.test",
                "name": "One",
                "created_at": None,
            }
        ),
    )
    monkeypatch.setattr(user, "get_mowers_of_user", AsyncMock(return_value=["mower-1"]))
    monkeypatch.setattr(user, "generate_jwt_token", Mock(return_value="jwt"))
    record = AsyncMock()
    monkeypatch.setattr(user, "record_zenoh_credential_expiry", record)
    admin = Mock()
    admin.configure_user_app = AsyncMock()
    monkeypatch.setattr(user, "ZenohAdminClient", Mock(return_value=admin))

    result = await user.user_login_service(
        UserLoginRequest(id_token="firebase-token"), object()
    )

    assert result.user_id == "user-1"
    assert result.token == "jwt"
    admin.configure_user_app.assert_awaited_once_with(
        user_id="user-1", mower_ids=["mower-1"], password="jwt"
    )
    record.assert_awaited_once()
