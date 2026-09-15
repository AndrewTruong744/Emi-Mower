"""One-way app completion notification for GCS boundary cutout uploads."""

from sqlalchemy.ext.asyncio import AsyncSession
import zenoh

from src.services.cutouts import record_cutout_upload_service
from src.zenoh.generated import CutoutUploadNotification
from src.zenoh.generated.paths import cutout_uploaded_path

CUTOUT_UPLOADED_KEY_EXPR = cutout_uploaded_path()


async def cutout_uploaded(
    payload: CutoutUploadNotification, db: AsyncSession, session: zenoh.Session
) -> None:
    await record_cutout_upload_service(payload, db, session)
