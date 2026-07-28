import logging
import httpx

logger = logging.getLogger("config.http_client")

_http_client: httpx.AsyncClient | None = None


def init_http_client() -> httpx.AsyncClient:
    """
    Explicitly initializes the global shared httpx.AsyncClient connection pool instance.
    Call this during application startup.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
        logger.info("Shared HTTP client pool initialized successfully.")
    return _http_client


def get_http_client() -> httpx.AsyncClient:
    """
    Returns the global shared httpx.AsyncClient connection pool instance.
    Lazy-initializes the pool if not already created or if closed.
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        return init_http_client()
    return _http_client


async def close_http_client() -> None:
    """
    Closes the global httpx.AsyncClient connection pool instance.
    Call this during application shutdown.
    """
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        logger.info("Shared HTTP client pool closed successfully.")
        _http_client = None
