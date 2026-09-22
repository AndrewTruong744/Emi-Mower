import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from src.exceptions import MowerNotFoundError, ValidationError
from src.models.mower import MowerModel
from src.repositories.mower_identity import (
    get_active_mower_identity,
    register_mower_identity,
)

pytestmark = pytest.mark.repository


@pytest.mark.asyncio
async def test_registers_and_reuses_the_same_mower_tpm_public_key(db_session):
    mower_id = uuid.uuid4()
    db_session.add(MowerModel(id=mower_id, nickname="TPM test mower"))
    await db_session.commit()
    public_key = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )

    first = await register_mower_identity(mower_id, public_key, db_session)
    second = await register_mower_identity(mower_id, public_key.rstrip(), db_session)

    assert first.id == second.id == mower_id
    assert first.device_public_key_pem == public_key
    assert first.device_key_fingerprint is not None
    assert (await get_active_mower_identity(mower_id, db_session)).id == mower_id


@pytest.mark.asyncio
async def test_rejects_replacing_an_active_mower_tpm_public_key(db_session):
    mower_id = uuid.uuid4()
    db_session.add(MowerModel(id=mower_id, nickname="TPM test mower"))
    await db_session.commit()
    first_key = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    second_key = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    await register_mower_identity(mower_id, first_key, db_session)

    with pytest.raises(ValidationError, match="different TPM identity"):
        await register_mower_identity(mower_id, second_key, db_session)


@pytest.mark.asyncio
async def test_decommissioned_mower_has_no_active_tpm_identity(db_session):
    mower_id = uuid.uuid4()
    db_session.add(
        MowerModel(
            id=mower_id,
            nickname="Decommissioned mower",
            lifecycle_status="decommissioned",
        )
    )
    await db_session.commit()

    with pytest.raises(MowerNotFoundError, match="no active TPM identity"):
        await get_active_mower_identity(mower_id, db_session)
