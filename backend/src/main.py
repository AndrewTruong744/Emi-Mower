import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import zenoh
from src.api import health_router
from src.config import (
    Base,
    close_http_client,
    close_valkey_pool,
    engine,
    get_zenoh_config,
    get_zenoh_bootstrap_config,
    init_http_client,
)
from src.services import initialize_backend_auth
from src.zenoh import ZenohMessageHandler, ZenohQueryHandler
from src.zenoh.register_handlers import register_bootstrap_handlers, register_handlers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend")


# Lifespan manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize shared HTTP client pool
    logger.info("Initializing HTTP client pool...")
    init_http_client()

    # Startup: Initialize Firebase Admin SDK
    initialize_backend_auth()

    # Startup: Initialize database tables
    logger.info("Initializing database tables (if they don't exist)...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")

    # Startup: Verify Valkey connection
    logger.info("Testing Valkey connection...")
    try:
        from src.config import get_valkey_client

        v_client = get_valkey_client()
        await v_client.ping()
        await v_client.close()
        logger.info("Valkey connection verified successfully.")
    except Exception as e:
        logger.error(f"Valkey connection failed: {e}")

    # Startup: Initialize Zenoh session
    logger.info("Starting Zenoh client connection...")
    try:
        zenoh_config = get_zenoh_config()
        app.state.zenoh_session = zenoh.open(zenoh_config)
        app.state.zenoh_query_handler = ZenohQueryHandler(
            app.state.zenoh_session, asyncio.get_running_loop()
        )
        app.state.zenoh_message_handler = ZenohMessageHandler(
            app.state.zenoh_session, asyncio.get_running_loop()
        )
        register_handlers(
            app.state.zenoh_query_handler, app.state.zenoh_message_handler
        )
        logger.info("Zenoh session started successfully.")
    except Exception as e:
        logger.error(f"Zenoh failed to connect on server startup: {e}")
        logger.warning("Application running without active Zenoh connection.")

    logger.info("Starting Zenoh bootstrap renewal connection...")
    try:
        bootstrap_session = zenoh.open(get_zenoh_bootstrap_config())
        app.state.zenoh_bootstrap_session = bootstrap_session
        app.state.zenoh_bootstrap_query_handler = ZenohQueryHandler(
            bootstrap_session, asyncio.get_running_loop()
        )
        register_bootstrap_handlers(app.state.zenoh_bootstrap_query_handler)
        logger.info("Zenoh bootstrap renewal connection started successfully.")
    except Exception as e:
        logger.error(f"Bootstrap Zenoh failed to connect on server startup: {e}")

    yield

    # Shutdown: Clean up connections
    if hasattr(app.state, "zenoh_session") and app.state.zenoh_session is not None:
        if hasattr(app.state, "zenoh_query_handler"):
            app.state.zenoh_query_handler.close()
        if hasattr(app.state, "zenoh_message_handler"):
            app.state.zenoh_message_handler.close()
        logger.info("Closing Zenoh session...")
        try:
            app.state.zenoh_session.close()
            logger.info("Zenoh session cleanly closed.")
        except Exception as e:
            logger.error(f"Error closing Zenoh session: {e}")

    if (
        hasattr(app.state, "zenoh_bootstrap_session")
        and app.state.zenoh_bootstrap_session is not None
    ):
        app.state.zenoh_bootstrap_query_handler.close()
        app.state.zenoh_bootstrap_session.close()

    logger.info("Closing Valkey connection pool...")
    await close_valkey_pool()
    logger.info("Valkey connection pool closed.")

    logger.info("Closing HTTP client pool...")
    await close_http_client()
    logger.info("HTTP client pool closed.")


app = FastAPI(
    title="Emi Mower Backend",
    description="FastAPI with PostgreSQL, SQLAlchemy, and Valkey integration",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)
