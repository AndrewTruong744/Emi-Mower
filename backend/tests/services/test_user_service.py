from unittest.mock import AsyncMock, Mock

import pytest

from src.exceptions import ForbiddenError, ValidationError
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
