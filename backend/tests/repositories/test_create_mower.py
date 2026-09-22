import uuid

import pytest
from sqlalchemy import select

from src.models.mower import MowerModel
from src.repositories.create_mower import create_mower

pytestmark = pytest.mark.repository


async def test_create_mower_persists_an_unassigned_mower(db_session):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")

    mower = await create_mower(mower_id, "Front yard", db_session)

    assert mower.id == mower_id
    assert mower.owner_id is None
    persisted = await db_session.scalar(
        select(MowerModel).where(MowerModel.id == mower_id)
    )
    assert persisted is not None
    assert persisted.nickname == "Front yard"


async def test_create_mower_allows_an_identical_provisioning_retry(db_session):
    mower_id = uuid.UUID("0a35e3e0-ff31-4b58-bc88-31f6e288fdb2")
    first = await create_mower(mower_id, "Front yard", db_session)

    retry = await create_mower(mower_id, "Different name", db_session)

    assert retry.id == first.id
    assert retry.nickname == "Front yard"
