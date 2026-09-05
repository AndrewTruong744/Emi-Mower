"""App query listener that creates a signed GCS cutout upload URL."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.cutouts import request_cutout_upload_service
from src.zenoh.generated import CutoutUploadUrlRequest, CutoutUploadUrlResponse
from src.zenoh.generated.paths import cutout_upload_url_path

CUTOUT_UPLOAD_URL_KEY_EXPR = cutout_upload_url_path()


async def cutout_upload_url(
    payload: CutoutUploadUrlRequest, db: AsyncSession
) -> CutoutUploadUrlResponse:
    return await request_cutout_upload_service(payload, db)
