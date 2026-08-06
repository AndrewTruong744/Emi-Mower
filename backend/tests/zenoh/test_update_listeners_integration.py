"""Container-backed behavior tests for the authenticated Zenoh listeners."""

from importlib import import_module
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from src.exceptions import ValidationError
from src.models.mower import MowerModel
from src.models.user import UserModel
from src.services import user as user_service
from src.zenoh.generated import (
    AddMowerToUserRequest,
    UpdateMowerNameRequest,
    UpdateUserEmailRequest,
    UpdateUserNameRequest,
)

pytestmark = pytest.mark.repository


async def test_add_mower_to_user_listener_updates_real_database(
    monkeypatch, db_session, seed_user, seed_mower
):
    await seed_user()
    mower = await seed_mower(owner_id=None)
    listener = import_module("src.zenoh.listeners.add_mower_to_user")
    monkeypatch.setattr(
        "src.services.auth._verify_google_id_token",
        AsyncMock(return_value={"uid": "user-1"}),
    )

    await listener.add_mower_to_user(
        AddMowerToUserRequest(id_token="google-token", mower_id=str(mower.id)),
        db_session,
    )

    assert (
        await db_session.execute(select(MowerModel.owner_id))
    ).scalar_one() == "user-1"


async def test_update_user_name_listener_updates_real_database(
    monkeypatch, db_session, seed_user
):
    await seed_user()
    listener = import_module("src.zenoh.listeners.update_user_name")
    monkeypatch.setattr(
        "src.services.auth._verify_google_id_token",
        AsyncMock(return_value={"uid": "user-1"}),
    )

    await listener.update_user_name(
        UpdateUserNameRequest(id_token="google-token", new_user_name="NewName"),
        db_session,
    )

    assert (
        await db_session.execute(select(UserModel.name))
    ).scalar_one() == "NewName"


async def test_update_mower_name_listener_extracts_path_id_and_updates_real_database(
    monkeypatch, db_session, seed_user, seed_mower
):
    await seed_user()
    mower = await seed_mower(owner_id="user-1")
    listener = import_module("src.zenoh.listeners.update_mower_name")
    monkeypatch.setattr(
        "src.services.auth._verify_google_id_token",
        AsyncMock(return_value={"uid": "user-1"}),
    )

    await listener.update_mower_name(
        UpdateMowerNameRequest(id_token="google-token", new_name="NewMower"),
        db_session,
        f"mower/{mower.id}/update_name",
    )

    assert (
        await db_session.execute(select(MowerModel.nickname))
    ).scalar_one() == "NewMower"


async def test_update_user_email_listener_updates_real_database(
    monkeypatch, db_session, seed_user
):
    await seed_user()
    identity = {"uid": "user-1", "email": "new@example.test"}
    listener = import_module("src.zenoh.listeners.update_user_email")
    monkeypatch.setattr(
        "src.services.auth._verify_google_id_token",
        AsyncMock(return_value=identity),
    )
    monkeypatch.setattr(
        user_service,
        "verify_zenoh_google_id_token",
        AsyncMock(return_value=identity),
    )

    await listener.update_user_email(
        UpdateUserEmailRequest(
            id_token="original-google-token", new_id_token="new-google-token"
        ),
        db_session,
    )

    assert (
        await db_session.execute(select(UserModel.email))
    ).scalar_one() == "new@example.test"


async def test_update_user_email_rejects_a_duplicate_email_in_real_database(
    monkeypatch, db_session, seed_user
):
    await seed_user()
    await seed_user(
        user_id="user-2", email="taken@example.test", name="OtherUser"
    )
    identity = {"uid": "user-1", "email": "taken@example.test"}
    monkeypatch.setattr(
        user_service,
        "verify_zenoh_google_id_token",
        AsyncMock(return_value=identity),
    )

    with pytest.raises(ValidationError, match="already in use"):
        await user_service.update_user_email_service(
            "user-1", "google-token", db_session
        )

    assert (
        await db_session.execute(
            select(UserModel.email).where(UserModel.id == "user-1")
        )
    ).scalar_one() == "user-1@example.test"
