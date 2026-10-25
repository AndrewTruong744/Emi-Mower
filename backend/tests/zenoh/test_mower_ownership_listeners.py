from unittest.mock import AsyncMock, Mock

import pytest

from src.zenoh.generated import RemoveMowerFromUserRequest, TransferMowerRequest
from src.zenoh.listeners import mower_ownership as listener


@pytest.mark.parametrize("action", ["remove", "transfer"])
async def test_owner_is_taken_from_verified_token_not_supplied_by_app(
    monkeypatch, action
):
    verify = AsyncMock(return_value={"user_id": "real-owner"})
    service = AsyncMock()
    monkeypatch.setattr(listener, "verify_firebase_id_token", verify)
    monkeypatch.setattr(listener, "update_mower_ownership_service", service)
    db = Mock()
    if action == "remove":
        result = await listener.remove_mower(
            RemoveMowerFromUserRequest(id_token="token", mower_id="mower"), db
        )
        service.assert_awaited_once_with("real-owner", None, "mower", db)
    else:
        result = await listener.transfer_mower(
            TransferMowerRequest(
                id_token="token", mower_id="mower", new_owner_id="recipient"
            ),
            db,
        )
        service.assert_awaited_once_with("real-owner", "recipient", "mower", db)
        assert result.new_owner_id == "recipient"
    assert result.user_id == "real-owner"
    verify.assert_awaited_once_with("token")
