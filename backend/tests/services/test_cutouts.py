from unittest.mock import AsyncMock, Mock

import pytest

from src.services import cutouts
from src.zenoh.generated import (
    CutoutUploadNotification,
    CutoutUploadUrlRequest,
)


@pytest.mark.asyncio
async def test_request_cutout_upload_authorizes_all_mowers_and_returns_signed_url(monkeypatch):
    monkeypatch.setattr(cutouts, "verify_zenoh_google_id_token", AsyncMock(return_value={"uid": "user-1"}))
    monkeypatch.setattr(cutouts, "verify_ownership", AsyncMock(return_value=True))
    created = Mock(id="cutout-id", object_key="users/user-1/cutouts/id.png", content_type="image/png")
    monkeypatch.setattr(cutouts, "create_cutout", AsyncMock(return_value=created))
    monkeypatch.setattr(cutouts, "_signed_url", AsyncMock(return_value="https://signed.test/upload"))
    db = Mock(commit=AsyncMock())

    result = await cutouts.request_cutout_upload_service(
        CutoutUploadUrlRequest(id_token="token", mower_ids=["mower-1"], content_type="image/png"), db
    )

    assert result.upload_url == "https://signed.test/upload"
    assert result.object_key.startswith("users/user-1/cutouts/")
    cutouts.verify_ownership.assert_awaited_once_with("user-1", "mower-1", db=db)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_notification_marks_missing_object_as_failed(monkeypatch):
    monkeypatch.setattr(cutouts, "verify_zenoh_google_id_token", AsyncMock(return_value={"uid": "user-1"}))
    record = Mock(object_key="users/user-1/cutouts/id.png", content_type="image/png", status="pending")
    monkeypatch.setattr(cutouts, "get_cutout_for_owner", AsyncMock(return_value=record))

    class Blob:
        def exists(self): return False
    class Bucket:
        def blob(self, _key): return Blob()
    monkeypatch.setattr(cutouts, "_client", lambda: Mock(bucket=lambda _name: Bucket()))
    db = Mock(commit=AsyncMock())

    with pytest.raises(cutouts.ValidationError, match="could not be verified"):
        await cutouts.record_cutout_upload_service(
            CutoutUploadNotification(id_token="token", cutout_id="id", success=True), db
        )
    assert record.status == "failed"
    db.commit.assert_awaited_once()
