"""GCS signed-URL handling and lifecycle services for boundary cutouts."""

import asyncio
import json
import uuid
from datetime import timedelta

from google.cloud import storage
from sqlalchemy.ext.asyncio import AsyncSession

import zenoh
from src.config.settings import settings
from src.exceptions import ForbiddenError, ValidationError
from src.repositories import verify_ownership
from src.services.auth import verify_zenoh_google_id_token
from src.zenoh.generated import (
    CutoutUploadNotification,
    CutoutUploadUrlRequest,
    CutoutUploadUrlResponse,
)
from src.zenoh.generated.paths import mower_cutout_delivery_path


def _client() -> storage.Client:
    """Build a GCS client from ADC only when the route is used."""
    return storage.Client(project=settings.GCP_PROJECT_ID)


def _object_key(user_id: str, cutout_id: uuid.UUID, content_type: str) -> str:
    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[
        content_type
    ]
    return f"users/{user_id}/cutouts/{cutout_id}.{extension}"


async def _signed_url(*, object_key: str, method: str, content_type: str | None) -> str:
    ttl = (
        settings.GCS_UPLOAD_URL_TTL_SECONDS
        if method == "PUT"
        else settings.GCS_DOWNLOAD_URL_TTL_SECONDS
    )

    def generate() -> str:
        blob = _client().bucket(settings.GCS_CUTOUT_BUCKET).blob(object_key)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=ttl),
            method=method,
            content_type=content_type,
        )

    return await asyncio.to_thread(generate)


async def request_cutout_upload_service(
    payload: CutoutUploadUrlRequest, db: AsyncSession
) -> CutoutUploadUrlResponse:
    """Authorize owned mowers and create a transient signed GCS upload."""
    identity = await verify_zenoh_google_id_token(payload.id_token)
    user_id = identity.get("uid") or identity.get("user_id")
    if not user_id:
        raise ForbiddenError("Authenticated identity does not contain a user id")

    mower_ids = list(dict.fromkeys(mower_id.strip() for mower_id in payload.mower_ids))
    if not mower_ids or any(not mower_id for mower_id in mower_ids):
        raise ValidationError("At least one mower id is required")
    for mower_id in mower_ids:
        if not await verify_ownership(user_id, mower_id, db=db):
            raise ForbiddenError("A cutout can only be sent to mowers you own")

    cutout_id = uuid.uuid4()
    object_key = _object_key(user_id, cutout_id, payload.content_type)
    upload_url = await _signed_url(
        object_key=object_key, method="PUT", content_type=payload.content_type
    )
    return CutoutUploadUrlResponse(
        cutout_id=str(cutout_id),
        upload_url=upload_url,
        expires_in=settings.GCS_UPLOAD_URL_TTL_SECONDS,
        object_key=object_key,
        content_type=payload.content_type,
    )


async def record_cutout_upload_service(
    payload: CutoutUploadNotification, db: AsyncSession, session: zenoh.Session
) -> None:
    """Verify an upload, then immediately deliver it to selected mowers."""
    identity = await verify_zenoh_google_id_token(payload.id_token)
    user_id = identity.get("uid") or identity.get("user_id")
    if not user_id:
        raise ForbiddenError("Authenticated identity does not contain a user id")
    try:
        cutout_id = uuid.UUID(payload.cutout_id)
    except ValueError as error:
        raise ValidationError("cutout_id must be a UUID") from error
    if payload.object_key != _object_key(user_id, cutout_id, payload.content_type):
        raise ForbiddenError("Cutout object key does not belong to this upload")
    mower_ids = list(dict.fromkeys(mower_id.strip() for mower_id in payload.mower_ids))
    if not mower_ids or any(not mower_id for mower_id in mower_ids):
        raise ValidationError("At least one mower id is required")
    for mower_id in mower_ids:
        if not await verify_ownership(user_id, mower_id, db=db):
            raise ForbiddenError("A cutout can only be sent to mowers you own")
    if not payload.success:
        return

    def uploaded() -> bool:
        blob = _client().bucket(settings.GCS_CUTOUT_BUCKET).blob(payload.object_key)
        if not blob.exists():
            return False
        blob.reload()
        return blob.content_type == payload.content_type and (blob.size or 0) > 0

    if not await asyncio.to_thread(uploaded):
        raise ValidationError("The uploaded cutout could not be verified in GCS")
    for mower_id in mower_ids:
        download_url = await _signed_url(
            object_key=payload.object_key, method="GET", content_type=None
        )
        session.put(
            mower_cutout_delivery_path(mower_id),
            json.dumps(
                {
                    "cutout_id": payload.cutout_id,
                    "download_url": download_url,
                    "expires_in": settings.GCS_DOWNLOAD_URL_TTL_SECONDS,
                    "content_type": payload.content_type,
                }
            ).encode("utf-8"),
        )
