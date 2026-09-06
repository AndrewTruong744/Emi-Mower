"""Bootstrap-router handlers for TPM-authorized mower certificate renewal."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.certificate_renewal import (
    complete_certificate_renewal,
    issue_renewal_challenge,
)
from src.zenoh.generated import (
    MowerCertificateRenewChallengeRequest,
    MowerCertificateRenewChallengeResponse,
    MowerCertificateRenewCompleteRequest,
    MowerCertificateRenewCompleteResponse,
)
from src.zenoh.generated.paths import (
    mower_certificate_renew_challenge_path,
    mower_certificate_renew_complete_path,
)

MOWER_CERTIFICATE_RENEW_CHALLENGE_KEY_EXPR = mower_certificate_renew_challenge_path("*")
MOWER_CERTIFICATE_RENEW_COMPLETE_KEY_EXPR = mower_certificate_renew_complete_path("*")


def _mower_id(key_expr: str) -> str:
    segments = key_expr.split("/")
    if len(segments) != 6 or segments[:2] != ["bootstrap", "mower"]:
        raise ValueError("unexpected mower certificate renewal key expression")
    return segments[2]


async def mower_certificate_renew_challenge(
    payload: MowerCertificateRenewChallengeRequest, db: AsyncSession, key_expr: str
) -> MowerCertificateRenewChallengeResponse:
    del payload
    return MowerCertificateRenewChallengeResponse(
        **await issue_renewal_challenge(_mower_id(key_expr), db)
    )


async def mower_certificate_renew_complete(
    payload: MowerCertificateRenewCompleteRequest, db: AsyncSession, key_expr: str
) -> MowerCertificateRenewCompleteResponse:
    return MowerCertificateRenewCompleteResponse(
        **await complete_certificate_renewal(
            _mower_id(key_expr),
            payload.nonce,
            payload.csr_pem,
            payload.tpm_signature,
            db,
        )
    )
