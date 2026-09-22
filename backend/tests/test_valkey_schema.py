import pytest

from src.schemas.valkey import (
    MOWER_CERTIFICATE_RENEWAL_NONCE_TTL_SECONDS,
    mower_certificate_renewal_nonce_key,
    mower_id_from_telemetry_key,
    mower_telemetry_key,
)


def test_certificate_renewal_nonce_key_contract():
    assert (
        mower_certificate_renewal_nonce_key("mower-1", "nonce-1")
        == "mower_certificate_renewal:mower-1:nonce-1"
    )
    assert MOWER_CERTIFICATE_RENEWAL_NONCE_TTL_SECONDS == 300


def test_telemetry_key_parser_uses_the_canonical_key_contract():
    key = mower_telemetry_key("mower-1")

    assert mower_id_from_telemetry_key(key) == "mower-1"


@pytest.mark.parametrize(
    "key",
    ("mower::telemetry:data", "mower:mower-1:telemetry:data:temp", "other:key"),
)
def test_telemetry_key_parser_rejects_noncanonical_keys(key):
    with pytest.raises(ValueError, match="canonical telemetry key"):
        mower_id_from_telemetry_key(key)
