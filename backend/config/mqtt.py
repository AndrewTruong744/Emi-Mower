import asyncio
import logging
import re
from typing import Awaitable, Callable

import aiomqtt

from config.settings import settings

# Configure logging
logger = logging.getLogger("mqtt")
logger.setLevel(logging.INFO)

# Global variables
mqtt_client: aiomqtt.Client | None = None
_mqtt_task: asyncio.Task | None = None
_stop_event = asyncio.Event()

# Callback registry
MQTTCallback = Callable[[str, bytes], Awaitable[None]]
_callbacks: list[tuple[str, MQTTCallback]] = []


def topic_matches(pattern: str, topic: str) -> bool:
    """
    Checks if an MQTT topic matches an MQTT topic pattern (supporting + and #).
    """
    # Escape regex characters except + and #
    re_pattern = re.escape(pattern)
    re_pattern = re_pattern.replace(r"\+", r"[^/]+")
    re_pattern = re_pattern.replace(r"\#", r".*")
    return bool(re.match(f"^{re_pattern}$", topic))


def register_mqtt_callback(topic_pattern: str, callback: MQTTCallback) -> None:
    """
    Register a callback to be executed when a message matches topic_pattern.
    """
    _callbacks.append((topic_pattern, callback))
    logger.info(f"Registered MQTT callback for pattern: {topic_pattern}")

    # If the client is connected, subscribe dynamically in the background
    if mqtt_client is not None:
        asyncio.create_task(_subscribe_safe(topic_pattern))


async def _subscribe_safe(topic_pattern: str) -> None:
    if mqtt_client is not None:
        try:
            await mqtt_client.subscribe(topic_pattern)
            logger.info(f"Dynamically subscribed to: {topic_pattern}")
        except Exception as e:
            logger.error(f"Failed to dynamically subscribe to {topic_pattern}: {e}")


async def _dispatch_message(topic: str, payload: bytes) -> None:
    """
    Dispatches received messages to matching registered callbacks.
    """
    for pattern, callback in _callbacks:
        if topic_matches(pattern, topic):
            try:
                await callback(topic, payload)
            except Exception as e:
                logger.error(
                    f"Error executing MQTT callback for topic {topic}: {e}",
                    exc_info=True,
                )


async def mqtt_loop() -> None:
    """
    The background connection loop for the aiomqtt client.
    Handles connection, subscription to registered topics, listening for messages,
    and automatic reconnection with backoff on failure.
    """
    global mqtt_client
    reconnect_interval = 5

    while not _stop_event.is_set():
        try:
            logger.info(
                "Connecting to MQTT broker at %s:%d...",
                settings.MQTT_HOST,
                settings.MQTT_PORT,
            )

            async with aiomqtt.Client(
                hostname=settings.MQTT_HOST,
                port=settings.MQTT_PORT,
                username=settings.MQTT_USERNAME,
                password=settings.MQTT_PASSWORD,
                keepalive=settings.MQTT_KEEPALIVE,
            ) as client:
                logger.info("Successfully connected to MQTT broker.")
                mqtt_client = client

                # Subscribe to all unique registered topic patterns
                unique_patterns = set(pattern for pattern, _ in _callbacks)
                for pattern in unique_patterns:
                    logger.info(f"Subscribing to: {pattern}")
                    await client.subscribe(pattern)

                # Process messages as they arrive
                async for message in client.messages:
                    topic = str(message.topic)
                    # message.payload is bytes or a bytearray
                    payload = (
                        message.payload
                        if isinstance(message.payload, bytes)
                        else bytes(message.payload)
                    )
                    await _dispatch_message(topic, payload)

        except aiomqtt.MqttError as e:
            mqtt_client = None
            logger.error(
                "MQTT connection error: %s. Reconnecting in %ds...",
                e,
                reconnect_interval,
            )
            try:
                await asyncio.sleep(reconnect_interval)
            except asyncio.CancelledError:
                break
        except asyncio.CancelledError:
            break
        except Exception as e:
            mqtt_client = None
            logger.error(
                "Unexpected error in MQTT loop: %s. Reconnecting in %ds...",
                e,
                reconnect_interval,
                exc_info=True,
            )
            try:
                await asyncio.sleep(reconnect_interval)
            except asyncio.CancelledError:
                break

    mqtt_client = None
    logger.info("MQTT loop exited.")


async def start_mqtt() -> None:
    """
    Starts the MQTT client background connection task.
    """
    global _mqtt_task
    _stop_event.clear()
    _mqtt_task = asyncio.create_task(mqtt_loop())
    logger.info("MQTT background client task started.")


async def stop_mqtt() -> None:
    """
    Stops the MQTT client background connection task.
    """
    global _mqtt_task
    logger.info("Stopping MQTT client...")
    _stop_event.set()
    if _mqtt_task:
        _mqtt_task.cancel()
        try:
            await _mqtt_task
        except asyncio.CancelledError:
            pass
        _mqtt_task = None
    logger.info("MQTT client stopped.")


async def publish_message(
    topic: str,
    payload: str | bytes | int | float,
    qos: int = 0,
    retain: bool = False,
) -> None:
    """
    Publish a message to a topic.
    """
    if mqtt_client is None:
        raise RuntimeError("MQTT client is not connected")
    await mqtt_client.publish(topic, payload=payload, qos=qos, retain=retain)


def get_mqtt_client() -> aiomqtt.Client:
    """
    FastAPI dependency to get the connected MQTT client.
    """
    if mqtt_client is None:
        raise RuntimeError("MQTT client is not connected")
    return mqtt_client
