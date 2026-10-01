"""Bootstrap-router handlers for TPM-authorized mower certificate renewal."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.certificate_renewal import (
    complete_certificate_renewal,
    issue_renewal_challenge,
)
from src.services.mower import mower_route_params
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


async def mower_certificate_renew_challenge(
    payload: MowerCertificateRenewChallengeRequest, db: AsyncSession, key_expr: str
) -> MowerCertificateRenewChallengeResponse:
    del payload
    (mower_id,) = mower_route_params(
        key_expr, MOWER_CERTIFICATE_RENEW_CHALLENGE_KEY_EXPR
    )
    return MowerCertificateRenewChallengeResponse(
        **await issue_renewal_challenge(mower_id, db)
    )


async def mower_certificate_renew_complete(
    payload: MowerCertificateRenewCompleteRequest, db: AsyncSession, key_expr: str
) -> MowerCertificateRenewCompleteResponse:
    (mower_id,) = mower_route_params(
        key_expr, MOWER_CERTIFICATE_RENEW_COMPLETE_KEY_EXPR
    )
    return MowerCertificateRenewCompleteResponse(
        **await complete_certificate_renewal(
            mower_id,
            payload.nonce,
            payload.csr_pem,
            payload.tpm_signature,
            db,
        )
    )
