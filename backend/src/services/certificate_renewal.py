"""TPM-authorized issuance of short-lived mower operational certificates."""

import asyncio
import base64
import hashlib
import secrets
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.config.valkey_client import get_valkey_client
from src.config.zenoh_client import ZenohAdminClient
from src.exceptions import AuthenticationError, ValidationError
from src.repositories.mower_device_identities import get_active_mower_device_identity

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ISSUER = BACKEND_ROOT / "tools" / "issue_mower_certificate.sh"
NONCE_TTL_SECONDS = 300


def renewal_message(mower_id: str, nonce: str, csr_pem: str) -> bytes:
    csr_digest = hashlib.sha256(csr_pem.encode("utf-8")).digest()
    return b"\0".join(
        (
            b"emi-mower-renew-v1",
            mower_id.encode("utf-8"),
            nonce.encode("ascii"),
            csr_digest,
        )
    )


def _nonce_key(mower_id: str, nonce: str) -> str:
    return f"mower_certificate_renewal:{mower_id}:{nonce}"


async def issue_renewal_challenge(
    mower_id: str, db: AsyncSession
) -> dict[str, object]:
    # Do not allocate challenge state for arbitrary key expressions. The
    # completion path will verify this identity again before signing anything.
    await get_active_mower_device_identity(uuid.UUID(mower_id), db)
    nonce = secrets.token_urlsafe(32)
    client = get_valkey_client()
    try:
        await client.set(_nonce_key(mower_id, nonce), mower_id, ex=NONCE_TTL_SECONDS)
    finally:
        await client.close()
    return {"nonce": nonce, "expires_in": NONCE_TTL_SECONDS}


def _validate_csr(mower_id: str, csr_pem: str) -> x509.CertificateSigningRequest:
    try:
        csr = x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
    except ValueError as error:
        raise ValidationError(
            "csr_pem is not a valid PEM certificate request"
        ) from error
    if not csr.is_signature_valid:
        raise ValidationError("CSR signature is invalid")
    expected_cn = f"mower:{mower_id}"
    names = csr.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if len(names) != 1 or names[0].value != expected_cn:
        raise ValidationError(f"CSR common name must be {expected_cn!r}")
    return csr


async def _consume_nonce(mower_id: str, nonce: str) -> None:
    client = get_valkey_client()
    try:
        value = await client.getdel(_nonce_key(mower_id, nonce))
    finally:
        await client.close()
    if value != mower_id:
        raise AuthenticationError(
            "renewal challenge is missing, expired, or already used"
        )


def _verify_tpm_signature(
    public_key_pem: str, message: bytes, signature_b64: str
) -> None:
    try:
        public_key = load_pem_public_key(public_key_pem.encode("utf-8"))
        signature = base64.b64decode(signature_b64, validate=True)
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            raise ValidationError("registered TPM key must be an EC public key")
        public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as error:
        raise AuthenticationError(
            "TPM signature did not match the renewal request"
        ) from error
    except ValueError as error:
        raise ValidationError(
            "TPM signature must be base64-encoded DER ECDSA"
        ) from error


def _issue_from_csr(mower_id: str, csr_pem: str) -> tuple[str, str, datetime]:
    with tempfile.TemporaryDirectory(prefix="emi-mower-renew-") as directory:
        output = Path(directory) / "credentials"
        csr = Path(directory) / "renewal.csr"
        csr.write_text(csr_pem)
        command = [
            "bash",
            str(ISSUER),
            "--mower-id",
            mower_id,
            "--output-dir",
            str(output),
            "--csr",
            str(csr),
        ]
        if settings.MOWER_CA_KEY_PASSPHRASE_FILE:
            command.extend(
                ("--ca-key-passphrase-file", settings.MOWER_CA_KEY_PASSPHRASE_FILE)
            )
        subprocess.run(command, check=True, capture_output=True, text=True)
        certificate_pem = (output / "mower.crt").read_text()
        ca_chain_pem = (output / "root_ca.pem").read_text()
        certificate = x509.load_pem_x509_certificate(certificate_pem.encode("utf-8"))
        return certificate_pem, ca_chain_pem, certificate.not_valid_after_utc


async def complete_certificate_renewal(
    mower_id: str, nonce: str, csr_pem: str, tpm_signature: str, db: AsyncSession
) -> dict[str, object]:
    mower_uuid = uuid.UUID(mower_id)
    _validate_csr(mower_id, csr_pem)
    identity = await get_active_mower_device_identity(mower_uuid, db)
    message = renewal_message(mower_id, nonce, csr_pem)
    _verify_tpm_signature(identity.public_key_pem, message, tpm_signature)
    await _consume_nonce(mower_id, nonce)
    certificate_pem, ca_chain_pem, expires_at = await asyncio.to_thread(
        _issue_from_csr, mower_id, csr_pem
    )
    await ZenohAdminClient().configure_mower_device(mower_id)
    return {
        "certificate_pem": certificate_pem,
        "ca_chain_pem": ca_chain_pem,
        "expires_at": expires_at.astimezone(UTC),
    }
