"""Persistence for the public half of mower TPM device-root identities."""

import hashlib
import uuid

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.exceptions import MowerNotFoundError, ValidationError
from src.models.mower import MowerDeviceIdentityModel, MowerModel


def public_key_fingerprint(public_key_pem: str) -> str:
    normalized = public_key_pem.strip() + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def register_mower_device_identity(
    mower_id: uuid.UUID,
    public_key_pem: str,
    db: AsyncSession,
    *,
    algorithm: str = "ECDSA_P256_SHA256",
) -> MowerDeviceIdentityModel:
    """Bind one immutable mower TPM public key to a provisioned mower."""
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
    existing = await db.scalar(
        select(MowerDeviceIdentityModel).where(
            MowerDeviceIdentityModel.mower_id == mower_id,
            MowerDeviceIdentityModel.status == "active",
        )
    )
    if existing is not None:
        if existing.fingerprint != fingerprint:
            raise ValidationError("mower already has a different active TPM identity")
        return existing
    identity = MowerDeviceIdentityModel(
        mower_id=mower_id,
        public_key_pem=normalized_public_key,
        fingerprint=fingerprint,
        algorithm=algorithm,
    )
    db.add(identity)
    await db.commit()
    await db.refresh(identity)
    return identity


async def get_active_mower_device_identity(
    mower_id: uuid.UUID, db: AsyncSession
) -> MowerDeviceIdentityModel:
    identity = await db.scalar(
        select(MowerDeviceIdentityModel).where(
            MowerDeviceIdentityModel.mower_id == mower_id,
            MowerDeviceIdentityModel.status == "active",
        )
    )
    if identity is None:
        raise MowerNotFoundError(f"mower {mower_id} has no active TPM identity")
    return identity
