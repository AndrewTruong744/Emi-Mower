import json
import logging

import httpx

from src.config.mqtt import fast_mqtt, publish_message
from src.config.settings import settings
from src.config.valkey_client import get_valkey_client

logger = logging.getLogger("mqtt.handle_mower_offer")


@fast_mqtt.subscribe("/mower/+/video/offer")
async def handle_mower_offer_callback(client, topic: str, payload: bytes, qos: int, properties) -> None:
    logger.info(f"Received mower offer on topic: {topic}")
    try:
        data = json.loads(payload.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse JSON payload from MQTT: {e}")
        return

    # Extract uuid and sdp_offer
    uuid = data.get("uuid")
    sdp_offer = data.get("sdp_offer") or data.get("sdp")

    # Fallback to parsing uuid from topic if not present in payload
    if not uuid:
        parts = topic.strip("/").split("/")
        if len(parts) >= 2:
            uuid = parts[1]

    if not uuid or not sdp_offer:
        logger.error(
            "Missing uuid or sdp_offer in payload/topic. "
            f"uuid: {uuid}, has sdp_offer: {bool(sdp_offer)}"
        )
        return

    # Call Cloudflare Realtime API
    secret = settings.CLOUDFLARE_API_TOKEN
    rtc_url = settings.CF_RTC_URL

    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient() as http_client:
            # 1. Create a session on Cloudflare Calls
            session_url = f"{rtc_url}/sessions/new"
            logger.info(f"Creating Cloudflare Calls session at {session_url}...")

            session_payload = {
                "sessionDescription": {"type": "offer", "sdp": sdp_offer}
            }

            session_resp = await http_client.post(session_url, headers=headers, json=session_payload)
            session_resp.raise_for_status()
            session_data = session_resp.json()
            session_id = session_data.get("sessionId")

            if not session_id:
                logger.error("Failed to retrieve sessionId from Cloudflare response")
                return

            # 2. Add track to the session using the sdp_offer
            track_url = f"{rtc_url}/sessions/{session_id}/tracks/new"
            logger.info(f"Adding track to session at {track_url}...")

            track_payload = {
                "tracks": [{"mid": "0", "trackName": "video"}],
            }

            track_resp = await http_client.post(
                track_url, headers=headers, json=track_payload
            )
            track_resp.raise_for_status()
            track_data = track_resp.json()

            # Extract sdp answer and trackId
            sdp_answer = track_data.get("sessionDescription", {}).get("sdp")
            tracks_list = track_data.get("tracks", [])
            track_id = tracks_list[0].get("trackId") if tracks_list else None

            if not sdp_answer or not track_id:
                logger.error(
                    "Failed to retrieve sdp_answer or track_id from track response. "
                    f"track_id: {track_id}"
                )
                return

            # 3. Save sessionId and trackId in Valkey
            v_client = get_valkey_client()
            try:
                valkey_key = f"mower:{uuid}:stream"
                valkey_value = json.dumps(
                    {"sessionId": session_id, "trackId": track_id}
                )
                logger.info(f"Saving stream info in Valkey under key {valkey_key}...")
                await v_client.set(valkey_key, valkey_value)
            finally:
                await v_client.close()

            # 4. Return the Cloudflare's sdp answer back using MQTT topic:
            # /mower/{uuid}/video/answer
            answer_topic = f"/mower/{uuid}/video/answer"
            answer_payload = json.dumps(
                {"uuid": uuid, "sdp_answer": sdp_answer, "sdp": sdp_answer}
            )
            logger.info(f"Publishing SDP answer to MQTT topic {answer_topic}...")
            await publish_message(answer_topic, answer_payload)

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Cloudflare API error: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Error handling mower offer: {e}", exc_info=True)
