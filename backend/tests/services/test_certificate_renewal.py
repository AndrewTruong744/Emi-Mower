import base64
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.exceptions import AuthenticationError
from src.services import certificate_renewal
from src.services.certificate_renewal import _verify_tpm_signature, renewal_message


def test_renewal_message_binds_mower_nonce_and_exact_csr_bytes():
    message = renewal_message("mower-1", "nonce-1", "csr-1")

    assert message.startswith(b"emi-mower-renew-v1\0mower-1\0nonce-1\0")
    assert message != renewal_message("mower-1", "nonce-1", "csr-2")
    assert message != renewal_message("mower-2", "nonce-1", "csr-1")


def test_tpm_signature_verification_accepts_only_the_registered_public_key():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    ).decode()
    message = renewal_message(str(uuid.uuid4()), "nonce", "csr")
    signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))

    _verify_tpm_signature(public_pem, message, base64.b64encode(signature).decode())

    with pytest.raises(AuthenticationError):
        _verify_tpm_signature(
            public_pem,
            message + b"changed",
            base64.b64encode(signature).decode(),
        )


@pytest.mark.asyncio
async def test_complete_renewal_verifies_tpm_proof_and_refreshes_mtls_acl(monkeypatch):
    mower_id = str(uuid.uuid4())
    device_key = ec.generate_private_key(ec.SECP256R1())
    public_pem = device_key.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    ).decode()
    operational_key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name(
        [x509.NameAttribute(x509.NameOID.COMMON_NAME, f"mower:{mower_id}")]
    )
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject)
        .sign(operational_key, hashes.SHA256())
        .public_bytes(Encoding.PEM)
        .decode()
    )
    nonce = "one-time-nonce"
    signature = base64.b64encode(
        device_key.sign(
            renewal_message(mower_id, nonce, csr), ec.ECDSA(hashes.SHA256())
        )
    ).decode()
    consume_nonce = AsyncMock()
    admin = Mock()
    admin.configure_mower_device = AsyncMock()
    monkeypatch.setattr(
        certificate_renewal,
        "get_active_mower_device_identity",
        AsyncMock(return_value=SimpleNamespace(public_key_pem=public_pem)),
    )
    monkeypatch.setattr(certificate_renewal, "_consume_nonce", consume_nonce)
    monkeypatch.setattr(
        certificate_renewal,
        "_issue_from_csr",
        Mock(
            return_value=(
                "certificate",
                "ca-chain",
                datetime(2026, 1, 1, tzinfo=UTC),
            )
        ),
    )
    monkeypatch.setattr(
        certificate_renewal, "ZenohAdminClient", Mock(return_value=admin)
    )

    result = await certificate_renewal.complete_certificate_renewal(
        mower_id, nonce, csr, signature, object()
    )

    assert result["certificate_pem"] == "certificate"
    consume_nonce.assert_awaited_once_with(mower_id, nonce)
    admin.configure_mower_device.assert_awaited_once_with(mower_id)
