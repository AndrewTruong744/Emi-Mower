import json
import logging

import httpx

from src.config.settings import settings
from src.config.socketio import sio
from src.config.valkey_client import get_valkey_client
from src.repositories.verify_ownership import verify_ownership

logger = logging.getLogger("socketio.consume_video")


@sio.on("consume-video")
async def handle_consume_video(sid, data):
    """
    Socket.IO handler for consuming mower video stream.
    Verifies ownership of the mower before calling Cloudflare Calls
    to pull the video track.
    Returns the SDP offer from Cloudflare.
    """
    logger.info(f"Received consume-video event from sid {sid} with data: {data}")

    # Extract mower_uuid from data
    mower_uuid = None
    if isinstance(data, dict):
        mower_uuid = data.get("mower_uuid") or data.get("uuid") or data.get("mowerId")
    elif isinstance(data, str):
        mower_uuid = data

    if not mower_uuid:
        logger.warning(f"No mower uuid provided by sid {sid}")
        await sio.emit(
            "consume-video",
            {"error": "Missing mower_uuid parameter"},
            to=sid,
        )
        return

    # Retrieve user_id from session
    async with sio.session(sid) as session:
        user_id = session.get("user_id")

    if not user_id:
        logger.warning(f"Unauthenticated session {sid} attempted to consume video.")
        await sio.emit(
            "consume-video",
            {"error": "Session is not authenticated"},
            to=sid,
        )
        return

    # Check mower ownership
    is_owner = await verify_ownership(user_id, mower_uuid)
    if not is_owner:
        logger.warning(f"User {user_id} does not own mower {mower_uuid}")
        await sio.emit(
            "consume-video",
            {"error": "Lack of ownership error"},
            to=sid,
        )
        return

    # Retrieve stream information (sessionId and trackId) from Valkey
    valkey_key = f"mower-{mower_uuid}-stream"
    v_client = get_valkey_client()
    try:
        cached_stream = await v_client.get(valkey_key)
    except Exception as e:
        logger.error(f"Failed to query Valkey for stream info: {e}")
        await sio.emit(
            "consume-video",
            {"error": "Internal cache error"},
            to=sid,
        )
        return
    finally:
        await v_client.close()

    if not cached_stream:
        logger.warning(f"No active video stream found for mower {mower_uuid}")
        await sio.emit(
            "consume-video",
            {"error": "No active stream for this mower"},
            to=sid,
        )
        return

    try:
        stream_info = json.loads(cached_stream)
        publisher_session_id = stream_info.get("sessionId")
        publisher_track_id = stream_info.get("trackId")
    except Exception as e:
        logger.error(f"Failed to parse Valkey stream info: {e}")
        await sio.emit(
            "consume-video",
            {"error": "Failed to parse stream info"},
            to=sid,
        )
        return

    if not publisher_session_id or not publisher_track_id:
        logger.error(f"Valkey stream info incomplete for mower {mower_uuid}")
        await sio.emit(
            "consume-video",
            {"error": "Stream session information is incomplete"},
            to=sid,
        )
        return

    # Call Cloudflare Realtime API to consume the track
    secret = settings.secret
    rtc_url = settings.CF_RTC_URL

    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient() as client:
            # 1. Create a consumer session
            session_url = f"{rtc_url}/sessions/new"
            logger.info(f"Creating consumer Calls session at {session_url}...")
            session_resp = await client.post(session_url, headers=headers, json={})
            session_resp.raise_for_status()
            session_data = session_resp.json()
            consumer_session_id = session_data.get("sessionId")

            if not consumer_session_id:
                logger.error("Failed to retrieve sessionId from Cloudflare response")
                await sio.emit(
                    "consume-video",
                    {"error": "Failed to create video session"},
                    to=sid,
                )
                return

            # 2. Pull the publisher's track into the consumer session
            track_url = f"{rtc_url}/sessions/{consumer_session_id}/tracks/new"
            logger.info(f"Pulling track into session at {track_url}...")

            track_payload = {
                "tracks": [
                    {
                        "location": "remote",
                        "sessionId": publisher_session_id,
                        "trackId": publisher_track_id,
                    }
                ]
            }

            track_resp = await client.post(
                track_url, headers=headers, json=track_payload
            )
            track_resp.raise_for_status()
            track_data = track_resp.json()

            # Extract the SDP offer from response sessionDescription
            sdp_offer = track_data.get("sessionDescription", {}).get("sdp")

            if not sdp_offer:
                logger.error(
                    "Cloudflare track response missing sessionDescription.sdp"
                )
                await sio.emit(
                    "consume-video",
                    {"error": "Failed to retrieve video session description"},
                    to=sid,
                )
                return

            # 3. Emit SDP offer back to the user
            await sio.emit(
                "consume-video",
                {
                    "sdp_offer": sdp_offer,
                    "sdp": sdp_offer,
                    "sessionId": consumer_session_id,
                },
                to=sid,
            )
            logger.info(
                f"Successfully sent SDP offer for mower {mower_uuid} to sid {sid}"
            )

    except httpx.HTTPStatusError as e:
        logger.error(
            f"Cloudflare Calls API error: {e.response.status_code} - {e.response.text}"
        )
        await sio.emit(
            "consume-video",
            {"error": f"Cloudflare API error: {e.response.status_code}"},
            to=sid,
        )
    except Exception as e:
        logger.error(f"Error handling video consumption: {e}", exc_info=True)
        await sio.emit(
            "consume-video",
            {"error": "Internal server error during video consumption"},
            to=sid,
        )
