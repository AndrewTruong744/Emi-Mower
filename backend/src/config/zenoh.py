"""
Zenoh Configuration module for mTLS connections.
"""

from pathlib import Path

import zenoh
from src.config.settings import settings


def get_zenoh_config() -> zenoh.Config:
    """
    Creates and returns a Zenoh Config object pre-configured with mTLS certificates.
    """
    config = zenoh.Config()

    ca_cert = Path(settings.ZENOH_CA_CERT)
    fastapi_cert = Path(settings.ZENOH_FASTAPI_CERT)
    fastapi_key = Path(settings.ZENOH_FASTAPI_KEY)

    # Ensure all certificate files actually exist before attempting connection
    for p in [ca_cert, fastapi_cert, fastapi_key]:
        if not p.exists():
            raise FileNotFoundError(
                f"Required Zenoh mTLS certificate file not found: {p}"
            )

    # Insert mTLS paths formatted cleanly for JSON5
    # (.as_posix() prevents escaping issues)
    config.insert_json5(
        "transport/link/tls/root_ca_certificate", f'"{ca_cert.as_posix()}"'
    )
    config.insert_json5(
        "transport/link/tls/connect_certificate",
        f'"{fastapi_cert.as_posix()}"',
    )
    config.insert_json5(
        "transport/link/tls/connect_private_key",
        f'"{fastapi_key.as_posix()}"',
    )

    return config
