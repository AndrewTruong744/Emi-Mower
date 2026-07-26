from pathlib import Path
import zenoh

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CERTS_DIR = BASE_DIR / "certs"


def get_zenoh_config() -> zenoh.Config:
    """Builds and returns a Zenoh configuration for client mTLS authentication."""
    config = zenoh.Config()

    # 1. Set operation mode to client
    config.insert_json5("mode", '"client"')

    # 2. Point to local Zenoh router endpoint
    config.insert_json5("connect/endpoints", '["tls/127.0.0.1:7448"]')

    # 3. Resolve certificate paths
    ca_cert = CERTS_DIR / "ca" / "ca.crt"

    fastapi_cert = CERTS_DIR / "fastapi" / "server.crt"

    fastapi_key = CERTS_DIR / "fastapi" / "server.key"

    # Ensure all certificate files actually exist before attempting connection
    for p in [ca_cert, fastapi_cert, fastapi_key]:
        if not p.exists():
            raise FileNotFoundError(
                f"Required Zenoh mTLS certificate file not found: {p}"
            )

    # Insert mTLS paths formatted cleanly for JSON5 (.as_posix() prevents escaping issues)
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

    # Force client to send its mTLS certificate during handshake
    config.insert_json5("transport/link/tls/enable_mtls", "true")

    # Disable hostname verification for self-signed development certs
    config.insert_json5("transport/link/tls/verify_name_on_connect", "false")

    return config