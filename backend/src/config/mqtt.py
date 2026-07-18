import logging
from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig
from src.config.settings import settings

# Configure logging
logger = logging.getLogger("mqtt")
logger.setLevel(logging.INFO)

# 1. Define the core MQTT configuration profile
mqtt_config = MQTTConfig(
    host=settings.MQTT_HOST,
    port=settings.MQTT_PORT,
    username=settings.MQTT_USERNAME,
    password=settings.MQTT_PASSWORD,
    keepalive=settings.MQTT_KEEPALIVE,
)

# 2. Instantiate the FastMQTT manager
# This handles the background connection, auto-reconnection, and internal routing.
fast_mqtt = FastMQTT(config=mqtt_config)

# 3. Connection Lifecycles (Cleanly handles logging state)
@fast_mqtt.on_connect()
def connect(client, flags, rc, properties):
    logger.info(f"Successfully connected to MQTT broker. Return code: {rc}")

@fast_mqtt.on_disconnect()
def disconnect(client, packet, exc=None):
    logger.info("MQTT client disconnected from broker.")

# 4. Global fallback for topics that don't match explicit decorators
@fast_mqtt.on_message()
async def default_message_handler(client, topic, payload, qos, properties):
    logger.debug(f"Unrouted message received on topic {topic}: {payload[:50]}")

# 5. Clean abstraction for outbound message production
async def publish_message(
    topic: str,
    payload: str | bytes | int | float,
    qos: int = 0,
    retain: bool = False,
) -> None:
    """
    Public API to publish a message from anywhere in the application.
    """
    await fast_mqtt.publish(topic, payload, qos=qos, retain=retain)

def register_mqtt_routes():
    """Explicitly imports modules to trigger their @fast_mqtt.subscribe decorators."""
    import src.services.mqtt.handle_mower_offer
    import src.services.mqtt.handle_mower_status
    import src.services.mqtt.handle_telemetry_data