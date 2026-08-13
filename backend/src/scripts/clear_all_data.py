"""Delete application data from PostgreSQL and the configured Valkey database."""

import asyncio
import logging

from sqlalchemy import text

from src.config.database import AsyncSessionLocal, engine
from src.config.valkey_client import close_valkey_pool, get_valkey_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("scripts.clear_all_data")


def _quote_identifier(identifier: str) -> str:
    """Quote a PostgreSQL identifier returned by the system catalog."""

    return '"' + identifier.replace('"', '""') + '"'


async def clear_postgres() -> int:
    """Truncate every public table except Alembic's migration table."""

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                text(
                    """
                    SELECT tablename
                    FROM pg_catalog.pg_tables
                    WHERE schemaname = 'public'
                      AND tablename <> 'alembic_version'
                    ORDER BY tablename
                    """
                )
            )
            table_names = result.scalars().all()
            if table_names:
                tables = ", ".join(_quote_identifier(name) for name in table_names)
                await db.execute(
                    text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
                )
            await db.commit()
            logger.info("Cleared %d PostgreSQL table(s)", len(table_names))
            return len(table_names)
        except Exception:
            await db.rollback()
            raise


async def clear_valkey() -> None:
    """Flush every key in the configured Valkey logical database."""

    async with get_valkey_client() as client:
        await client.flushdb()
    logger.info("Flushed the configured Valkey database")


async def clear_all_data() -> None:
    """Clear PostgreSQL application tables and all configured Valkey keys."""

    await clear_postgres()
    await clear_valkey()


async def main() -> None:
    try:
        await clear_all_data()
    finally:
        await close_valkey_pool()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
