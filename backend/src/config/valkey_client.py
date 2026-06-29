from typing import AsyncGenerator
import valkey.asyncio as valkey
from src.config.settings import settings

# Initialize Valkey connection pool
# decode_responses=True automatically decodes binary responses to string UTF-8
pool = valkey.ConnectionPool(
    host=settings.VALKEY_HOST,
    port=settings.VALKEY_PORT,
    db=settings.VALKEY_DB,
    password=settings.VALKEY_PASSWORD,
    decode_responses=True,
)


def get_valkey_client() -> valkey.Valkey:
    """
    Creates and returns a Valkey client instance linked to the global connection pool.
    """
    return valkey.Valkey(connection_pool=pool)


async def get_valkey() -> AsyncGenerator[valkey.Valkey, None]:
    """
    FastAPI dependency to yield a Valkey client instance per request.
    """
    client = get_valkey_client()
    try:
        yield client
    finally:
        await client.close()


async def close_valkey_pool() -> None:
    """
    Disconnects the connection pool. Call this during application shutdown.
    """
    await pool.disconnect()
