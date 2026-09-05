"""Mower query listener that issues a fresh cutout download URL."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.cutouts import get_mower_cutout_download_service
from src.zenoh.generated import (
    MowerCutoutDownloadUrlRequest,
    MowerCutoutDownloadUrlResponse,
)
from src.zenoh.generated.paths import mower_cutout_download_url_path

MOWER_CUTOUT_DOWNLOAD_URL_KEY_EXPR = mower_cutout_download_url_path("*")


async def mower_cutout_download_url(
    payload: MowerCutoutDownloadUrlRequest, db: AsyncSession, key_expr: str
) -> MowerCutoutDownloadUrlResponse:
    del payload
    mower_id = key_expr.split("/")[1]
    return await get_mower_cutout_download_service(mower_id, db)
