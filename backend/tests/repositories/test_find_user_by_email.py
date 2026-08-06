import pytest
from sqlalchemy import select

from src.models.user import UserModel
from src.repositories.find_user_by_email import find_user_by_email

pytestmark = pytest.mark.repository


async def test_find_user_by_email_returns_matching_user(db_session, seed_user):
    await seed_user(email="one@example.test")

    assert await find_user_by_email("one@example.test", db_session) == "user-1"
    assert (
        await db_session.execute(select(UserModel.email))
    ).scalar_one() == "one@example.test"


async def test_find_user_by_email_returns_none_for_unknown_email(db_session):
    assert await find_user_by_email("missing@example.test", db_session) is None
