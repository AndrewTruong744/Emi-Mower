from importlib import import_module
from unittest.mock import AsyncMock, Mock

from src.zenoh.generated import (
    LiveKitConsumeRequest,
    LiveKitTokenResponse,
    LiveKitUploadRequest,
)
from src.zenoh.listeners import (
    LIVEKIT_CONSUME_KEY_EXPR,
    LIVEKIT_UPLOAD_KEY_EXPR,
    livekit_consume,
    livekit_upload,
)


async def test_livekit_consume_listener_delegates_request(monkeypatch):
    listener_module = import_module("src.zenoh.listeners.livekit_consume")
    service = AsyncMock(
        return_value=LiveKitTokenResponse(
            token="token", url="wss://test", expires_in=60
        )
    )
    monkeypatch.setattr(listener_module, "livekit_consume_service", service)
    request = LiveKitConsumeRequest()
    db = Mock()

    result = await livekit_consume(request, db, "mower/mower-1/livekit/consume")

    service.assert_awaited_once_with("mower-1")
    assert result.token == "token"


async def test_livekit_upload_listener_delegates_request(monkeypatch):
    listener_module = import_module("src.zenoh.listeners.livekit_upload")
    service = AsyncMock(
        return_value=LiveKitTokenResponse(
            token="token", url="wss://test", expires_in=60
        )
    )
    monkeypatch.setattr(listener_module, "livekit_upload_service", service)
    db = Mock()

    await livekit_upload(
        LiveKitUploadRequest(), db, "mower/mower-1/livekit/upload"
    )

    service.assert_awaited_once_with("mower-1")


def test_livekit_listeners_use_mower_scoped_query_paths():
    assert LIVEKIT_CONSUME_KEY_EXPR == "mower/*/livekit/consume"
    assert LIVEKIT_UPLOAD_KEY_EXPR == "mower/*/livekit/upload"


async def test_livekit_listener_rejects_a_non_matching_query_path():
    from src.exceptions import ValidationError

    try:
        await livekit_upload(
            LiveKitUploadRequest(), Mock(), "mower/mower-1/livekit/consume"
        )
    except ValidationError:
        pass
    else:  # pragma: no cover
        raise AssertionError("listener accepted a mismatched LiveKit query path")
