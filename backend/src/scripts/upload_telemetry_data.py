"""Run the periodic telemetry-buffer flush worker."""

import asyncio
import logging
import sys
import time

from src.services.telemetry_buffer import flush_pending_telemetry_buffers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("upload_telemetry_worker")


async def main() -> None:
    """Flush buffered telemetry every 60 seconds."""
    logger.info("Starting telemetry upload worker daemon...")
    while True:
        start_time = time.time()
        logger.info("Starting telemetry sync cycle...")
        await flush_pending_telemetry_buffers()
        logger.info("Telemetry sync cycle finished.")

        sleep_duration = max(1.0, 60.0 - (time.time() - start_time))
        logger.info("Sleeping for %.2f seconds...", sleep_duration)
        await asyncio.sleep(sleep_duration)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Telemetry worker daemon stopped by user.")
    except Exception:
        logger.critical("Telemetry worker daemon crashed.", exc_info=True)
