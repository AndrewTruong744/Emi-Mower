from unittest.mock import AsyncMock, Mock

import pytest

from src.exceptions import ValidationError
from src.services import cutouts
from src.zenoh.generated import CutoutUploadNotification, CutoutUploadUrlRequest

MOWER_IDS = [
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
]


@pytest.mark.asyncio
async def test_request_cutout_upload_requires_an_owned_mower_and_returns_signed_url(
    monkeypatch,
):
    monkeypatch.setattr(
        cutouts,
        "verify_firebase_id_token",
        AsyncMock(return_value={"user_id": "user-1"}),
    )
    get_mowers = AsyncMock(return_value=[MOWER_IDS[0]])
    monkeypatch.setattr(cutouts, "get_mowers_of_user", get_mowers)
    monkeypatch.setattr(
        cutouts, "_signed_url", AsyncMock(return_value="https://signed.test/upload")
    )
    db = Mock()

    result = await cutouts.request_cutout_upload_service(
        CutoutUploadUrlRequest(id_token="token", content_type="image/png"),
        db,
    )

    assert result.object_key.startswith("users/user-1/cutouts/")
    assert result.object_key.endswith(".png")
    get_mowers.assert_awaited_once_with("user-1", db=db)


@pytest.mark.asyncio
async def test_request_cutout_upload_rejects_a_user_without_mowers(monkeypatch):
    monkeypatch.setattr(
        cutouts,
        "verify_firebase_id_token",
        AsyncMock(return_value={"user_id": "user-1"}),
    )
    monkeypatch.setattr(cutouts, "get_mowers_of_user", AsyncMock(return_value=[]))

    with pytest.raises(ValidationError, match="owned mower"):
        await cutouts.request_cutout_upload_service(
            CutoutUploadUrlRequest(id_token="token", content_type="image/png"),
            Mock(),
        )


@pytest.mark.asyncio
async def test_successful_upload_is_verified_then_delivered_to_each_mower(monkeypatch):
    cutout_id = "752d6676-1e6a-4f6a-baf3-f5262d06e342"
    object_key = f"users/user-1/cutouts/{cutout_id}.png"
    monkeypatch.setattr(
        cutouts,
        "verify_firebase_id_token",
        AsyncMock(return_value={"user_id": "user-1"}),
    )
    get_mowers = AsyncMock(return_value=MOWER_IDS)
    monkeypatch.setattr(cutouts, "get_mowers_of_user", get_mowers)
    monkeypatch.setattr(
        cutouts,
        "_signed_url",
        AsyncMock(side_effect=["https://signed.test/one", "https://signed.test/two"]),
    )
    blob = Mock()
    blob.exists.return_value = True
    blob.content_type = "image/png"
    blob.size = 42
    bucket = Mock()
    bucket.blob.return_value = blob
    monkeypatch.setattr(cutouts, "_client", lambda: Mock(bucket=lambda _name: bucket))
    db = Mock()
    session = Mock()

    await cutouts.record_cutout_upload_service(
        CutoutUploadNotification(
            id_token="token",
            cutout_id=cutout_id,
            object_key=object_key,
            content_type="image/png",
            success=True,
        ),
        db,
        session,
    )

    assert session.put.call_count == 2
    get_mowers.assert_awaited_once_with("user-1", db=db)
    assert (
        session.put.call_args_list[0].args[0] == f"mower/{MOWER_IDS[0]}/cutout/delivery"
    )
    assert (
        b'"download_url": "https://signed.test/one"'
        in session.put.call_args_list[0].args[1]
    )
    assert (
        session.put.call_args_list[1].args[0] == f"mower/{MOWER_IDS[1]}/cutout/delivery"
    )


@pytest.mark.asyncio
async def test_upload_notification_rejects_an_object_key_for_another_user(monkeypatch):
    monkeypatch.setattr(
        cutouts,
        "verify_firebase_id_token",
        AsyncMock(return_value={"user_id": "user-1"}),
    )
    session = Mock()

    with pytest.raises(cutouts.ForbiddenError, match="does not belong"):
        await cutouts.record_cutout_upload_service(
            CutoutUploadNotification(
                id_token="token",
                cutout_id="752d6676-1e6a-4f6a-baf3-f5262d06e342",
                object_key="users/user-2/cutouts/752d6676-1e6a-4f6a-baf3-f5262d06e342.png",
                content_type="image/png",
                success=True,
            ),
            Mock(),
            session,
        )
    session.put.assert_not_called()
