from unittest.mock import Mock

import pytest

from src.exceptions import TokenGenerationError, ValidationError
from src.services import livekit


class FakeAccessToken:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.identity = None
        self.ttl = None
        self.grants = None
        self.__class__.instances.append(self)

    def with_ttl(self, ttl):
        self.ttl = ttl
        return self

    def with_identity(self, identity):
        self.identity = identity
        return self

    def with_grants(self, grants):
        self.grants = grants
        return self

    def to_jwt(self):
        return "livekit-jwt"


async def test_consume_service_mints_subscriber_token(monkeypatch):
    monkeypatch.setattr(livekit.api, "AccessToken", FakeAccessToken)
    monkeypatch.setattr(livekit.settings, "LIVEKIT_API_KEY", "key")
    monkeypatch.setattr(livekit.settings, "LIVEKIT_API_SECRET", "secret")
    monkeypatch.setattr(livekit.settings, "LIVEKIT_URL", "wss://livekit.test")
    FakeAccessToken.instances.clear()

    result = await livekit.livekit_consume_service("mower-1")

    token = FakeAccessToken.instances[0]
    assert token.identity.startswith("consumer-")
    assert token.grants.room == "mower-1"
    assert token.grants.room_join is True
    assert token.grants.can_publish is False
    assert token.grants.can_subscribe is True
    assert result.token == "livekit-jwt"
    assert result.url == "wss://livekit.test"


async def test_livekit_services_reject_empty_mower_ids():
    with pytest.raises(ValidationError):
        await livekit.livekit_consume_service("")

    with pytest.raises(ValidationError):
        await livekit.livekit_upload_service("")


async def test_upload_service_mints_publisher_token(monkeypatch):
    monkeypatch.setattr(livekit.api, "AccessToken", FakeAccessToken)
    FakeAccessToken.instances.clear()

    result = await livekit.livekit_upload_service("mower-1")

    token = FakeAccessToken.instances[0]
    assert token.identity == "mower-1"
    assert token.grants.room == "mower-1"
    assert token.grants.can_publish is True
    assert token.grants.can_subscribe is False
    assert result.expires_in == livekit.LIVEKIT_TOKEN_TTL_SECONDS


async def test_livekit_token_generation_errors_are_domain_errors(monkeypatch):
    monkeypatch.setattr(
        livekit.api,
        "AccessToken",
        Mock(side_effect=RuntimeError("invalid credentials")),
    )

    with pytest.raises(TokenGenerationError):
        await livekit.livekit_upload_service("mower-1")
