from unittest.mock import AsyncMock

import pytest

from src.scripts import remove_usrpwds_from_zenoh as checker


@pytest.mark.asyncio
async def test_main_delegates_to_credential_service(monkeypatch):
    monkeypatch.setattr(checker.time, "time", lambda: 100)
    remove_expired = AsyncMock()
    monkeypatch.setattr(checker, "remove_expired_zenoh_credentials", remove_expired)

    async def stop(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(checker.asyncio, "sleep", stop)

    with pytest.raises(KeyboardInterrupt):
        await checker.main()

    remove_expired.assert_awaited_once_with(100)


@pytest.mark.asyncio
async def test_main_closes_http_client_when_stopped(monkeypatch):
    monkeypatch.setattr(checker, "remove_expired_zenoh_credentials", AsyncMock())
    close = AsyncMock()
    monkeypatch.setattr(checker, "close_http_client", close)

    async def stop(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(checker.asyncio, "sleep", stop)

    with pytest.raises(KeyboardInterrupt):
        await checker.main()
    close.assert_awaited_once()
