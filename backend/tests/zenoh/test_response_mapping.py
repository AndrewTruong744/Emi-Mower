"""Query listeners own the generated Zenoh response models."""

from importlib import import_module
from unittest.mock import AsyncMock, Mock

from src.zenoh.generated import (
    CutoutUploadUrlRequest,
    CutoutUploadUrlResponse,
    UserLoginRequest,
    UserLoginResponse,
)


async def test_login_listener_maps_service_result_to_wire_response(monkeypatch):
    listener = import_module("src.zenoh.listeners.user_login")
    service = AsyncMock(
        return_value={
            "user_id": "user-1",
            "token": "jwt",
            "expires_in": 300,
            "user_data": {
                "id": "user-1",
                "email": "one@example.test",
                "name": "One",
                "mowers": [],
            },
        }
    )
    monkeypatch.setattr(listener, "user_login_service", service)
    request = UserLoginRequest(id_token="firebase-token")
    db = Mock()

    response = await listener.user_login(request, db)

    service.assert_awaited_once_with(request, db)
    assert isinstance(response, UserLoginResponse)
    assert response.user_data.id == "user-1"
    assert response.token == "jwt"


async def test_cutout_listener_maps_service_result_to_wire_response(monkeypatch):
    listener = import_module("src.zenoh.listeners.cutout_upload_url")
    service = AsyncMock(
        return_value={
            "cutout_id": "cutout-1",
            "upload_url": "https://signed.test/upload",
            "expires_in": 300,
            "object_key": "users/user-1/cutouts/cutout-1.png",
            "content_type": "image/png",
        }
    )
    monkeypatch.setattr(listener, "request_cutout_upload_service", service)
    request = CutoutUploadUrlRequest(
        id_token="firebase-token", content_type="image/png"
    )
    db = Mock()

    response = await listener.cutout_upload_url(request, db)

    service.assert_awaited_once_with(request, db)
    assert isinstance(response, CutoutUploadUrlResponse)
    assert response.upload_url == "https://signed.test/upload"
    assert response.object_key == "users/user-1/cutouts/cutout-1.png"
