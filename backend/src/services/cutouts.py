"""GCS signed-URL handling and lifecycle services for boundary cutouts."""

import asyncio
import uuid
from datetime import timedelta

from google.cloud import storage
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.exceptions import ForbiddenError, NotFoundError, ValidationError
from src.repositories import (
    create_cutout,
    get_cutout_for_owner,
    get_latest_ready_cutout_for_mower,
    verify_ownership,
)
from src.services.auth import verify_zenoh_google_id_token
from src.zenoh.generated import (
    CutoutUploadNotification,
    CutoutUploadUrlRequest,
    CutoutUploadUrlResponse,
    MowerCutoutDownloadUrlResponse,
)


def _client() -> storage.Client:
    """Build a GCS client from ADC only when the route is used."""
    return storage.Client(project=settings.GCP_PROJECT_ID)


def _object_key(user_id: str, cutout_id: uuid.UUID, content_type: str) -> str:
    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[content_type]
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
    """Authorize owned mowers and create a private, pending GCS cutout."""
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
    cutout = await create_cutout(
        owner_id=user_id,
        object_key=object_key,
        content_type=payload.content_type,
        mower_ids=mower_ids,
        db=db,
    )
    await db.commit()
    upload_url = await _signed_url(
        object_key=cutout.object_key, method="PUT", content_type=cutout.content_type
    )
    return CutoutUploadUrlResponse(
        cutout_id=str(cutout.id),
        upload_url=upload_url,
        expires_in=settings.GCS_UPLOAD_URL_TTL_SECONDS,
        object_key=cutout.object_key,
        content_type=cutout.content_type,
    )


async def record_cutout_upload_service(
    payload: CutoutUploadNotification, db: AsyncSession
) -> None:
    """Verify a completed signed PUT before exposing it to any mower."""
    identity = await verify_zenoh_google_id_token(payload.id_token)
    user_id = identity.get("uid") or identity.get("user_id")
    if not user_id:
        raise ForbiddenError("Authenticated identity does not contain a user id")
    cutout = await get_cutout_for_owner(
        cutout_id=payload.cutout_id, owner_id=user_id, db=db
    )
    if cutout is None:
        raise NotFoundError("Cutout was not found")
    if not payload.success:
        cutout.status = "failed"
        await db.commit()
        return

    def uploaded() -> bool:
        blob = _client().bucket(settings.GCS_CUTOUT_BUCKET).blob(cutout.object_key)
        if not blob.exists():
            return False
        blob.reload()
        return blob.content_type == cutout.content_type and (blob.size or 0) > 0

    if not await asyncio.to_thread(uploaded):
        cutout.status = "failed"
        await db.commit()
        raise ValidationError("The uploaded cutout could not be verified in GCS")

    cutout.status = "ready"
    await db.commit()


async def get_mower_cutout_download_service(
    mower_id: str, db: AsyncSession
) -> MowerCutoutDownloadUrlResponse:
    """Issue a fresh GET URL only for the mower's latest verified assignment."""
    cutout = await get_latest_ready_cutout_for_mower(mower_id=mower_id, db=db)
    if cutout is None:
        raise NotFoundError("No verified boundary cutout is assigned to this mower")
    download_url = await _signed_url(
        object_key=cutout.object_key, method="GET", content_type=None
    )
    return MowerCutoutDownloadUrlResponse(
        cutout_id=str(cutout.id),
        download_url=download_url,
        expires_in=settings.GCS_DOWNLOAD_URL_TTL_SECONDS,
        content_type=cutout.content_type,
    )
