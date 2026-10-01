"""Mower route parsing preserves the declared route and bootstrap boundary."""

import pytest

from src.exceptions import ValidationError
from src.services.mower import mower_route_params
from src.zenoh.listeners.livekit_consume import LIVEKIT_CONSUME_KEY_EXPR
from src.zenoh.listeners.mower_certificate_renewal import (
    MOWER_CERTIFICATE_RENEW_CHALLENGE_KEY_EXPR,
)


def test_mower_route_params_extracts_normal_and_bootstrap_ids():
    assert mower_route_params(
        "mower/mower-1/livekit/consume", LIVEKIT_CONSUME_KEY_EXPR
    ) == ("mower-1",)
    assert mower_route_params(
        "bootstrap/mower/mower-1/certificate/renew/challenge",
        MOWER_CERTIFICATE_RENEW_CHALLENGE_KEY_EXPR,
    ) == ("mower-1",)


@pytest.mark.parametrize(
    "key_expr",
    [
        "mower//livekit/consume",
        "mower/mower-1/livekit/upload",
        "mower/mower-1/livekit/consume/extra",
        "bootstrap/mower/mower-1/livekit/consume",
    ],
)
def test_mower_route_params_rejects_non_matching_normal_routes(key_expr):
    with pytest.raises(ValidationError):
        mower_route_params(key_expr, LIVEKIT_CONSUME_KEY_EXPR)


def test_mower_route_params_rejects_a_bootstrap_route_with_wrong_action():
    with pytest.raises(ValidationError):
        mower_route_params(
            "bootstrap/mower/mower-1/certificate/renew/complete",
            MOWER_CERTIFICATE_RENEW_CHALLENGE_KEY_EXPR,
        )
