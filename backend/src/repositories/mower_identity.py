"""Persistence for each mower's one TPM device-root public identity."""

import hashlib
import uuid

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import MowerNotFoundError, ValidationError
from src.models.mower import MowerModel


def public_key_fingerprint(public_key_pem: str) -> str:
    normalized = public_key_pem.strip() + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def register_mower_identity(
    mower_id: uuid.UUID,
    public_key_pem: str,
    db: AsyncSession,
) -> MowerModel:
    """Bind the mower's one immutable TPM public key to its record."""
    if not public_key_pem.strip():
        raise ValidationError("mower TPM public key must not be empty")
    try:
        public_key = load_pem_public_key(public_key_pem.encode("utf-8"))
    except ValueError as error:
        raise ValidationError("mower TPM public key must be PEM-encoded") from error
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(
        public_key.curve, ec.SECP256R1
    ):
        raise ValidationError("mower TPM public key must use the P-256 EC curve")

    mower = await db.get(MowerModel, mower_id)
    if mower is None:
        raise MowerNotFoundError(f"mower {mower_id} was not found")
    normalized_public_key = public_key_pem.strip() + "\n"
    fingerprint = public_key_fingerprint(normalized_public_key)
    if mower.device_key_fingerprint is not None:
        if mower.device_key_fingerprint != fingerprint:
            raise ValidationError("mower already has a different TPM identity")
        return mower

    mower.device_public_key_pem = normalized_public_key
    mower.device_key_fingerprint = fingerprint
    await db.commit()
    await db.refresh(mower)
    return mower


async def get_active_mower_identity(
    mower_id: uuid.UUID, db: AsyncSession
) -> MowerModel:
    """Return an active mower with a registered TPM public key."""
    mower = await db.get(MowerModel, mower_id)
    if mower is None or mower.lifecycle_status != "active":
        raise MowerNotFoundError(f"mower {mower_id} has no active TPM identity")
    if mower.device_public_key_pem is None:
        raise MowerNotFoundError(f"mower {mower_id} has no active TPM identity")
    return mower
