"""Failure-path and cache-aside unit tests for repository modules.

These tests deliberately do not carry the ``repository`` marker.  The marked
tests exercise real Postgres/Valkey containers; these tests keep the ordinary
unit test command useful when Docker is unavailable.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from src.exceptions import (
    MowerNotFoundError,
    RepositoryError,
    UserNotFoundError,
)
from src.schemas.valkey import (
    MowerDataCache,
    UserDataCache,
    UserMowersCache,
)

add_mower_module = import_module("src.repositories.add_mower_to_user")
check_owner_module = import_module("src.repositories.check_mower_ownership")
create_user_module = import_module("src.repositories.create_user")
find_email_module = import_module("src.repositories.find_user_by_email")
find_mower_module = import_module("src.repositories.find_user_by_mower")
get_all_module = import_module("src.repositories.get_all_mowers_and_users")
mower_data_module = import_module("src.repositories.get_mower_data")
mowers_module = import_module("src.repositories.get_mowers_of_user")
user_data_module = import_module("src.repositories.get_user_data")
update_mower_module = import_module("src.repositories.update_mower_name")
update_email_module = import_module("src.repositories.update_user_email")
update_name_module = import_module("src.repositories.update_user_name")
verify_module = import_module("src.repositories.verify_ownership")
credentials_module = import_module("src.repositories.zenoh_credentials")
history_module = import_module("src.repositories.get_telemetry_history")


@asynccontextmanager
async def cache_context(client):
    yield client


def db_with(*results):
    db = Mock()
    db.execute = AsyncMock(side_effect=list(results))
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


def successful_cache(*, get=None, pipeline_results=None):
    client = Mock()
    client.get = AsyncMock(return_value=get)
    client.expire = AsyncMock()
    client.setex = AsyncMock()
    client.delete = AsyncMock()
    client.hset = AsyncMock()
    client.hgetall = AsyncMock(return_value={})
    client.hdel = AsyncMock()
    pipeline = Mock()
    pipeline.execute = AsyncMock(return_value=pipeline_results or [])
    client.pipeline.return_value = pipeline
    return client


async def test_create_user_rolls_back_on_database_failure(monkeypatch):
    db = Mock()
    db.add.side_effect = RuntimeError("database down")
    db.rollback = AsyncMock()

    with pytest.raises(RepositoryError):
        await create_user_module.create_user("user-1", "one@example.test", "One", db)

    db.rollback.assert_awaited_once()


async def test_create_user_returns_data_when_cache_write_fails(monkeypatch):
    db = db_with()
    broken_cache = successful_cache()
    broken_cache.setex.side_effect = RuntimeError("cache down")
    monkeypatch.setattr(
        create_user_module, "get_valkey_client", lambda: cache_context(broken_cache)
    )

    result = await create_user_module.create_user(
        "user-1", "one@example.test", "One", db
    )

    assert result["id"] == "user-1"
    db.commit.assert_awaited_once()


async def test_find_user_by_email_wraps_database_errors():
    db = Mock()
    db.execute = AsyncMock(side_effect=RuntimeError("database down"))

    with pytest.raises(RepositoryError):
        await find_email_module.find_user_by_email("one@example.test", db)


@pytest.mark.parametrize(
    ("module", "function", "args"),
    [
        (
            update_name_module,
            update_name_module.update_user_name,
            (
                "user-1",
                "New",
            ),
        ),
        (
            update_email_module,
            update_email_module.update_user_email,
            (
                "user-1",
                "new@example.test",
            ),
        ),
    ],
)
async def test_user_updates_handle_missing_rows_and_database_failures(
    module, function, args
):
    missing = db_with(SimpleNamespace(rowcount=0))
    with pytest.raises(UserNotFoundError):
        await function(*args, db=missing)

    broken = db_with()
    broken.execute.side_effect = RuntimeError("database down")
    with pytest.raises(RepositoryError):
        await function(*args, db=broken)
    broken.rollback.assert_awaited_once()


@pytest.mark.parametrize(
    ("module", "function", "args"),
    [
        (
            update_name_module,
            update_name_module.update_user_name,
            (
                "user-1",
                "New",
            ),
        ),
        (
            update_email_module,
            update_email_module.update_user_email,
            (
                "user-1",
                "new@example.test",
            ),
        ),
    ],
)
async def test_user_updates_tolerate_cache_invalidation_failure(
    monkeypatch, module, function, args
):
    db = db_with(SimpleNamespace(rowcount=1))
    broken_cache = successful_cache()
    broken_cache.delete.side_effect = RuntimeError("cache down")
    monkeypatch.setattr(
        module, "get_valkey_client", lambda: cache_context(broken_cache)
    )

    assert await function(*args, db=db) is None
    db.commit.assert_awaited_once()


async def test_update_mower_name_validates_uuid_and_missing_rows():
    with pytest.raises(MowerNotFoundError, match="Invalid mower ID"):
        await update_mower_module.update_mower_name("not-a-uuid", "New", Mock())

    db = db_with(SimpleNamespace(rowcount=0))
    with pytest.raises(MowerNotFoundError, match="No mower found"):
        await update_mower_module.update_mower_name(str(uuid4()), "New", db)


async def test_update_mower_name_tolerates_cache_invalidation_failure(monkeypatch):
    db = db_with(SimpleNamespace(rowcount=1))
    broken_cache = successful_cache()
    broken_cache.delete.side_effect = RuntimeError("cache down")
    monkeypatch.setattr(
        update_mower_module, "get_valkey_client", lambda: cache_context(broken_cache)
    )

    await update_mower_module.update_mower_name(str(uuid4()), "New", db)
    db.commit.assert_awaited_once()


async def test_add_mower_to_user_handles_validation_not_found_and_cache_errors(
    monkeypatch,
):
    with pytest.raises(MowerNotFoundError):
        await add_mower_module.add_mower_to_user("user-1", "bad-id", Mock())

    missing_db = db_with(SimpleNamespace(fetchone=lambda: None))
    with pytest.raises(MowerNotFoundError):
        await add_mower_module.add_mower_to_user("user-1", str(uuid4()), missing_db)

    mower_id = uuid4()
    db = db_with(
        SimpleNamespace(fetchone=lambda: ("old-user",)),
        SimpleNamespace(scalar_one_or_none=lambda: "new-user"),
        SimpleNamespace(),
    )
    cache = successful_cache()
    cache.pipeline.return_value.execute = AsyncMock(
        side_effect=RuntimeError("cache down")
    )
    monkeypatch.setattr(
        add_mower_module, "get_valkey_client", lambda: cache_context(cache)
    )
    await add_mower_module.add_mower_to_user("new-user", str(mower_id), db)
    db.commit.assert_awaited_once()


async def test_add_mower_to_user_rejects_unknown_user_and_db_failures():
    mower_id = uuid4()
    unknown_user = db_with(
        SimpleNamespace(fetchone=lambda: (None,)),
        SimpleNamespace(scalar_one_or_none=lambda: None),
    )
    with pytest.raises(UserNotFoundError):
        await add_mower_module.add_mower_to_user("missing", str(mower_id), unknown_user)

    broken = Mock()
    broken.execute = AsyncMock(side_effect=RuntimeError("database down"))
    broken.rollback = AsyncMock()
    with pytest.raises(RepositoryError):
        await add_mower_module.add_mower_to_user(None, str(mower_id), broken)
    broken.rollback.assert_awaited_once()


@pytest.mark.parametrize("cached", ["owner-1", "dne", "none", ""])
async def test_ownership_cache_hits_return_owner_or_none(monkeypatch, cached):
    client = successful_cache(get=cached)
    monkeypatch.setattr(
        check_owner_module, "get_valkey_client", lambda: cache_context(client)
    )

    result = await check_owner_module.check_mower_ownership(" mower-1 ", Mock())

    assert result == (cached if cached == "owner-1" else None)
    client.expire.assert_awaited_once()


async def test_ownership_cache_miss_queries_and_caches(monkeypatch):
    mower_id = uuid4()
    db = db_with(SimpleNamespace(fetchone=lambda: ("owner-1",)))
    client = successful_cache()
    monkeypatch.setattr(
        check_owner_module, "get_valkey_client", lambda: cache_context(client)
    )

    assert (
        await check_owner_module.check_mower_ownership(str(mower_id), db) == "owner-1"
    )
    client.setex.assert_awaited_once()

    invalid = await check_owner_module.check_mower_ownership("not-a-uuid", db)
    assert invalid is None


async def test_ownership_cache_and_database_failures(monkeypatch):
    mower_id = str(uuid4())
    broken_cache = successful_cache()
    broken_cache.get.side_effect = RuntimeError("cache down")
    monkeypatch.setattr(
        check_owner_module, "get_valkey_client", lambda: cache_context(broken_cache)
    )
    db = db_with(SimpleNamespace(fetchone=lambda: None))
    assert await check_owner_module.check_mower_ownership(mower_id, db) is None

    broken_db = Mock()
    broken_db.execute = AsyncMock(side_effect=RuntimeError("database down"))
    with pytest.raises(RepositoryError):
        await check_owner_module.check_mower_ownership(mower_id, broken_db)


async def test_find_user_by_mower_handles_cache_hit_uuid_and_database_failure(
    monkeypatch,
):
    mower_id = uuid4()
    client = successful_cache(get="owner-1")
    monkeypatch.setattr(
        find_mower_module, "get_valkey_client", lambda: cache_context(client)
    )
    assert (
        await find_mower_module.find_user_by_mower(str(mower_id), Mock()) == "owner-1"
    )

    miss_client = successful_cache()
    monkeypatch.setattr(
        find_mower_module, "get_valkey_client", lambda: cache_context(miss_client)
    )
    db = db_with(SimpleNamespace(fetchone=lambda: (None,)))
    assert await find_mower_module.find_user_by_mower(mower_id, db) is None

    broken_db = Mock()
    broken_db.execute = AsyncMock(side_effect=RuntimeError("database down"))
    with pytest.raises(RepositoryError):
        await find_mower_module.find_user_by_mower(mower_id, broken_db)


@pytest.mark.parametrize("cached", ["dne", "none", ""])
async def test_find_user_by_mower_treats_empty_owner_markers_as_unassigned(
    monkeypatch, cached
):
    client = successful_cache(get=cached)
    monkeypatch.setattr(
        find_mower_module, "get_valkey_client", lambda: cache_context(client)
    )

    assert await find_mower_module.find_user_by_mower(str(uuid4()), Mock()) is None


async def test_find_user_by_mower_handles_invalid_ids_and_cache_write_errors(
    monkeypatch,
):
    assert await find_mower_module.find_user_by_mower("not-a-uuid", Mock()) is None

    mower_id = uuid4()
    client = successful_cache()
    client.setex.side_effect = RuntimeError("cache down")
    monkeypatch.setattr(
        find_mower_module, "get_valkey_client", lambda: cache_context(client)
    )
    db = db_with(SimpleNamespace(fetchone=lambda: ("owner-1",)))

    assert await find_mower_module.find_user_by_mower(str(mower_id), db) == "owner-1"


async def test_get_mowers_of_user_cache_hit_and_cache_miss(monkeypatch):
    cached = UserMowersCache(["mower-1"]).model_dump_json()
    client = successful_cache(get=cached)
    monkeypatch.setattr(
        mowers_module, "get_valkey_client", lambda: cache_context(client)
    )
    assert await mowers_module.get_mowers_of_user("user-1", Mock()) == ["mower-1"]

    miss_client = successful_cache()
    monkeypatch.setattr(
        mowers_module, "get_valkey_client", lambda: cache_context(miss_client)
    )
    db = db_with(
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [UUID(int=1)]))
    )
    assert await mowers_module.get_mowers_of_user("user-1", db) == [str(UUID(int=1))]


async def test_get_mowers_of_user_handles_cache_and_database_failures(monkeypatch):
    client = successful_cache()
    client.get.side_effect = RuntimeError("cache down")
    monkeypatch.setattr(
        mowers_module, "get_valkey_client", lambda: cache_context(client)
    )
    broken_db = Mock()
    broken_db.execute = AsyncMock(side_effect=RuntimeError("database down"))
    with pytest.raises(RepositoryError):
        await mowers_module.get_mowers_of_user("user-1", broken_db)


async def test_get_user_data_cache_hit_and_database_fallback(monkeypatch):
    cached = UserDataCache(
        id="user-1", email="one@example.test", name="One"
    ).model_dump_json()
    client = successful_cache(get=cached)
    monkeypatch.setattr(
        user_data_module, "get_valkey_client", lambda: cache_context(client)
    )
    assert (await user_data_module.get_user_data("user-1", Mock()))["id"] == "user-1"

    bad_cache = successful_cache(get="not-json")
    monkeypatch.setattr(
        user_data_module, "get_valkey_client", lambda: cache_context(bad_cache)
    )
    user = SimpleNamespace(
        id="user-1", email="one@example.test", name="One", created_at=None
    )
    db = db_with(SimpleNamespace(scalar_one_or_none=lambda: user))
    assert (await user_data_module.get_user_data("user-1", db))[
        "email"
    ] == "one@example.test"


async def test_get_user_data_handles_missing_user_db_and_cache_failures(monkeypatch):
    client = successful_cache()
    monkeypatch.setattr(
        user_data_module, "get_valkey_client", lambda: cache_context(client)
    )
    missing = db_with(SimpleNamespace(scalar_one_or_none=lambda: None))
    with pytest.raises(UserNotFoundError):
        await user_data_module.get_user_data("missing", missing)

    broken = Mock()
    broken.execute = AsyncMock(side_effect=RuntimeError("database down"))
    with pytest.raises(RepositoryError):
        await user_data_module.get_user_data("user-1", broken)


async def test_get_all_mowers_and_users_builds_relationships_and_survives_cache_error(
    monkeypatch,
):
    user_result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: ["user-1"])
    )
    mower_result = SimpleNamespace(
        all=lambda: [(UUID(int=1), "user-1"), (UUID(int=2), None)]
    )
    db = db_with(user_result, mower_result)
    cache = successful_cache()
    cache.pipeline.return_value.execute = AsyncMock(
        side_effect=RuntimeError("cache down")
    )
    monkeypatch.setattr(
        get_all_module, "get_valkey_client", lambda: cache_context(cache)
    )

    result = await get_all_module.get_all_mowers_and_users(db)

    assert result["users"] == [{"user_id": "user-1", "mower_ids": [str(UUID(int=1))]}]
    assert result["mowers"][1]["owner_id"] is None


async def test_get_all_mowers_and_users_wraps_database_errors():
    db = Mock()
    db.execute = AsyncMock(side_effect=RuntimeError("database down"))
    with pytest.raises(RepositoryError):
        await get_all_module.get_all_mowers_and_users(db)


async def test_get_mower_data_uses_cache_and_statuses(monkeypatch):
    mower_id = str(UUID(int=1))
    data_json = MowerDataCache(
        id=mower_id, serial_number="serial", nickname="One", owner_id="user-1"
    ).model_dump_json()
    client = successful_cache(
        get=UserMowersCache([mower_id]).model_dump_json(),
        pipeline_results=[data_json, "online"],
    )
    client.pipeline.side_effect = [
        client.pipeline.return_value,
        client.pipeline.return_value,
    ]
    monkeypatch.setattr(
        mower_data_module, "get_valkey_client", lambda: cache_context(client)
    )

    result = await mower_data_module.get_mower_data("user-1", Mock())

    assert result[0]["status"] == "online"
    assert result[0]["id"] == mower_id


async def test_get_mower_data_falls_back_to_db_and_returns_offline_on_cache_write_error(
    monkeypatch,
):
    mower = SimpleNamespace(
        id=UUID(int=1), serial_number="serial", nickname="One", owner_id="user-1"
    )
    client = successful_cache()
    client.pipeline.return_value.execute = AsyncMock(
        side_effect=RuntimeError("cache down")
    )
    monkeypatch.setattr(
        mower_data_module, "get_valkey_client", lambda: cache_context(client)
    )
    db = db_with(SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [mower])))

    result = await mower_data_module.get_mower_data("user-1", db)

    assert result[0]["status"] == "offline"


async def test_get_mower_data_wraps_database_errors(monkeypatch):
    client = successful_cache()
    client.get.side_effect = RuntimeError("cache down")
    monkeypatch.setattr(
        mower_data_module, "get_valkey_client", lambda: cache_context(client)
    )
    db = Mock()
    db.execute = AsyncMock(side_effect=RuntimeError("database down"))
    with pytest.raises(RepositoryError):
        await mower_data_module.get_mower_data("user-1", db)


async def test_verify_ownership_handles_cache_hit_miss_and_database_failure(
    monkeypatch,
):
    mower_id = str(uuid4())
    client = successful_cache(get=UserMowersCache([mower_id]).model_dump_json())
    monkeypatch.setattr(
        verify_module, "get_valkey_client", lambda: cache_context(client)
    )
    assert await verify_module.verify_ownership("user-1", mower_id, Mock()) is True

    miss_client = successful_cache()
    monkeypatch.setattr(
        verify_module, "get_valkey_client", lambda: cache_context(miss_client)
    )
    db = db_with(
        SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [UUID(mower_id)]))
    )
    assert await verify_module.verify_ownership("user-1", mower_id, db) is True

    broken_db = Mock()
    broken_db.execute = AsyncMock(side_effect=RuntimeError("database down"))
    with pytest.raises(RepositoryError):
        await verify_module.verify_ownership("user-1", mower_id, broken_db)


async def test_zenoh_credential_repository_wraps_valkey_failures(monkeypatch):
    for function, args, method in [
        (credentials_module.record_zenoh_credential_expiry, ("user-1", 1), "hset"),
        (credentials_module.get_expired_zenoh_credential_user_ids, (1,), "hgetall"),
        (credentials_module.remove_zenoh_credential_expiry, ("user-1",), "hdel"),
    ]:
        client = successful_cache()
        getattr(client, method).side_effect = RuntimeError("cache down")
        monkeypatch.setattr(
            credentials_module,
            "get_valkey_client",
            lambda client=client: cache_context(client),
        )
        with pytest.raises(RepositoryError):
            await function(*args)


async def test_zenoh_credential_repository_reads_and_removes_expirations(monkeypatch):
    client = successful_cache()
    monkeypatch.setattr(
        credentials_module, "get_valkey_client", lambda: cache_context(client)
    )

    await credentials_module.record_zenoh_credential_expiry("user-1", 100)
    client.hset.assert_awaited_once()

    client.hgetall.return_value = {"due": "100", "future": "101", "bad": "nope"}
    assert await credentials_module.get_expired_zenoh_credential_user_ids(100) == [
        "due"
    ]

    await credentials_module.remove_zenoh_credential_expiry("user-1")
    client.hdel.assert_awaited_once()


def test_telemetry_cursor_round_trip_and_invalid_values():
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    telemetry_id = uuid4()
    cursor = history_module.encode_telemetry_cursor(timestamp, telemetry_id)

    decoded_timestamp, decoded_id = history_module.decode_telemetry_cursor(cursor)
    assert decoded_timestamp == timestamp
    assert decoded_id == telemetry_id

    for invalid in ["", "not-base64", "e30", "eyJ0aW1lc3RhbXAiOiJub3QtaW1lIn0"]:
        with pytest.raises(history_module.ValidationError):
            history_module.decode_telemetry_cursor(invalid)

    with pytest.raises(history_module.ValidationError):
        history_module._mower_uuid("not-a-uuid")


async def test_get_telemetry_history_validates_graph_and_mower_ids():
    with pytest.raises(history_module.ValidationError, match="Unsupported"):
        await history_module.get_telemetry_history("mower-1", "unknown", None, Mock())
    with pytest.raises(history_module.ValidationError, match="UUID"):
        await history_module.get_telemetry_history("mower-1", "accel_x", None, Mock())


async def test_get_telemetry_history_returns_page_and_cursor(monkeypatch):
    mower_id = str(uuid4())
    first_timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        SimpleNamespace(timestamp=first_timestamp, id=uuid4())
        for _ in range(history_module.TELEMETRY_PAGE_SIZE + 1)
    ]
    db = Mock()
    db.scalar = AsyncMock(return_value=history_module.TELEMETRY_PAGE_SIZE + 1)
    db.execute = AsyncMock(return_value=SimpleNamespace(all=lambda: rows))

    total, points, cursor = await history_module.get_telemetry_history(
        mower_id, "accel_x", None, db
    )

    assert total == history_module.TELEMETRY_PAGE_SIZE + 1
    assert len(points) == history_module.TELEMETRY_PAGE_SIZE
    assert cursor is not None
    db.scalar.assert_awaited_once()
    db.execute.assert_awaited_once()

    next_total, next_points, next_cursor = await history_module.get_telemetry_history(
        mower_id, "accel_x", cursor, db
    )
    assert next_total == total
    assert next_points == points
    assert next_cursor is not None


async def test_get_telemetry_history_handles_empty_and_database_error():
    empty_db = Mock()
    empty_db.scalar = AsyncMock(return_value=0)
    empty_db.execute = AsyncMock(return_value=SimpleNamespace(all=lambda: []))
    assert await history_module.get_telemetry_history(
        str(uuid4()), "battery_percentage", None, empty_db
    ) == (0, [], None)

    broken_db = Mock()
    broken_db.scalar = AsyncMock(side_effect=RuntimeError("database down"))
    with pytest.raises(RepositoryError):
        await history_module.get_telemetry_history(
            str(uuid4()), "battery_percentage", None, broken_db
        )
