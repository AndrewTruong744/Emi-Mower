import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from sqlalchemy import select

from src.exceptions import ValidationError
from src.models.mower import MowerDeviceIdentityModel, MowerModel
from src.repositories.mower_device_identities import (
    get_active_mower_device_identity,
    register_mower_device_identity,
)

pytestmark = pytest.mark.repository


@pytest.mark.asyncio
async def test_registers_and_reuses_the_same_mower_tpm_public_key(db_session):
    mower_id = uuid.uuid4()
    db_session.add(
        MowerModel(id=mower_id, serial_number="TPM-42", nickname="TPM test mower")
    )
    await db_session.commit()
    public_key = (
        ec.generate_private_key(ec.SECP256R1())
        .public_key()
        .public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )

    first = await register_mower_device_identity(mower_id, public_key, db_session)
    second = await register_mower_device_identity(
        mower_id, public_key.rstrip(), db_session
    )

    assert first.id == second.id
    assert (await db_session.scalars(select(MowerDeviceIdentityModel))).all() == [first]
    assert (await get_active_mower_device_identity(mower_id, db_session)).id == first.id


@pytest.mark.asyncio
async def test_rejects_replacing_an_active_mower_tpm_public_key(db_session):
    mower_id = uuid.uuid4()
    db_session.add(
        MowerModel(id=mower_id, serial_number="TPM-43", nickname="TPM test mower")
    )
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
    await register_mower_device_identity(mower_id, first_key, db_session)

    with pytest.raises(ValidationError, match="different active TPM identity"):
        await register_mower_device_identity(mower_id, second_key, db_session)
