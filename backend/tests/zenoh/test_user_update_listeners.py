from importlib import import_module
from unittest.mock import AsyncMock, Mock

import pytest

from src.exceptions import ValidationError
from src.services import user as user_service
from src.zenoh.generated import (
    AddMowerToUserRequest,
    AddMowerToUserResponse,
    UpdateMowerNameRequest,
    UpdateMowerNameResponse,
    UpdateUserEmailRequest,
    UpdateUserEmailResponse,
    UpdateUserNameRequest,
    UpdateUserNameResponse,
)


async def test_add_mower_to_user_listener_verifies_token_and_assigns_to_user(
    monkeypatch,
):
    listener = import_module("src.zenoh.listeners.add_mower_to_user")
    verify = AsyncMock(return_value={"uid": "user-1"})
    service = AsyncMock()
    monkeypatch.setattr("src.services.auth._verify_google_id_token", verify)
    monkeypatch.setattr(listener, "update_mower_ownership_service", service)

    db = Mock()
    result = await listener.add_mower_to_user(
        AddMowerToUserRequest(id_token="google-token", mower_id="mower-1"),
        db,
    )

    verify.assert_awaited_once()
    service.assert_awaited_once_with(
        current_owner_id=None,
        new_owner_id="user-1",
        mower_id="mower-1",
        db=db,
    )
    assert isinstance(result, AddMowerToUserResponse)
    assert result.user_id == "user-1"
    assert result.mower_id == "mower-1"


async def test_update_user_name_listener_verifies_token_and_returns_reply(monkeypatch):
    listener = import_module("src.zenoh.listeners.update_user_name")
    verify = AsyncMock(return_value={"user_id": "user-1"})
    service = AsyncMock()
    monkeypatch.setattr("src.services.auth._verify_google_id_token", verify)
    monkeypatch.setattr(listener, "update_user_name_service", service)
    db = Mock()

    result = await listener.update_user_name(
        UpdateUserNameRequest(id_token="google-token", new_user_name="NewName"),
        db,
    )

    verify.assert_awaited_once()
    service.assert_awaited_once_with("user-1", "NewName", db=db)
    assert isinstance(result, UpdateUserNameResponse)
    assert result.new_user_name == "NewName"


async def test_update_mower_name_listener_verifies_token_and_returns_reply(monkeypatch):
    listener = import_module("src.zenoh.listeners.update_mower_name")
    verify = AsyncMock(return_value={"uid": "user-1"})
    service = AsyncMock()
    monkeypatch.setattr("src.services.auth._verify_google_id_token", verify)
    monkeypatch.setattr(listener, "update_mower_name_service", service)
    db = Mock()

    result = await listener.update_mower_name(
        UpdateMowerNameRequest(id_token="google-token", new_name="NewMower"),
        db,
        "mower/mower-1/update_name",
    )

    verify.assert_awaited_once()
    service.assert_awaited_once_with(
        user_id="user-1",
        mower_id="mower-1",
        new_name="NewMower",
        db=db,
    )
    assert isinstance(result, UpdateMowerNameResponse)
    assert result.new_name == "NewMower"


async def test_update_mower_name_listener_rejects_a_mismatched_query_path(monkeypatch):
    listener = import_module("src.zenoh.listeners.update_mower_name")
    monkeypatch.setattr(
        "src.services.auth._verify_google_id_token",
        AsyncMock(return_value={"uid": "user-1"}),
    )
    service = AsyncMock()
    monkeypatch.setattr(listener, "update_mower_name_service", service)

    with pytest.raises(ValidationError):
        await listener.update_mower_name(
            UpdateMowerNameRequest(id_token="google-token", new_name="NewMower"),
            Mock(),
            "mower/mower-1/update_email",
        )

    service.assert_not_awaited()


async def test_update_user_email_listener_verifies_token_and_returns_new_email(
    monkeypatch,
):
    listener = import_module("src.zenoh.listeners.update_user_email")
    verify = AsyncMock(
        side_effect=[
            {"uid": "user-1", "email": "old@example.test"},
            {"uid": "new-firebase-user", "email": "new@example.test"},
        ]
    )
    monkeypatch.setattr("src.services.auth._verify_google_id_token", verify)
    update = AsyncMock()
    monkeypatch.setattr(
        user_service, "find_user_by_email", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(user_service, "update_user_email", update)
    db = Mock()

    result = await listener.update_user_email(
        UpdateUserEmailRequest(
            id_token="original-google-token", new_id_token="new-google-token"
        ),
        db,
    )

    assert verify.await_count == 2
    assert verify.await_args_list[0].args == ("original-google-token",)
    assert verify.await_args_list[1].args == ("new-google-token",)
    update.assert_awaited_once_with("user-1", "new@example.test", db=db)
    assert isinstance(result, UpdateUserEmailResponse)
    assert result.new_email == "new@example.test"
