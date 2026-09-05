import uuid

import pytest
from sqlalchemy import select

from src.exceptions import ValidationError
from src.models.mower import MowerModel
from src.repositories.create_mower import create_mower

pytestmark = pytest.mark.repository


async def test_create_mower_persists_an_unassigned_mower(db_session):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")

    mower = await create_mower(mower_id, "SN-42", "Front yard", db_session)

    assert mower.id == mower_id
    assert mower.owner_id is None
    persisted = await db_session.scalar(
        select(MowerModel).where(MowerModel.id == mower_id)
    )
    assert persisted is not None
    assert persisted.serial_number == "SN-42"


async def test_create_mower_allows_an_identical_provisioning_retry(db_session):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")
    first = await create_mower(mower_id, "SN-42", "Front yard", db_session)

    retry = await create_mower(mower_id, "SN-42", "Different name", db_session)

    assert retry.id == first.id
    assert retry.nickname == "Front yard"


async def test_create_mower_rejects_a_duplicate_serial_number(db_session):
    await create_mower(uuid.uuid4(), "SN-42", "Front yard", db_session)

    with pytest.raises(ValidationError, match="already provisioned"):
        await create_mower(uuid.uuid4(), "SN-42", "Back yard", db_session)
