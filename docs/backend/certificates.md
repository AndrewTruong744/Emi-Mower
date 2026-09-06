# Certificates and the `certs/` folder

The backend's `certs/` directory contains local development trust material and
certificate-request configuration. It is an operational boundary, not a place
to store customer credentials or distribute the CA private key.

| Directory           | Contents and role                                                                                                                                                    |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `certs/ca/`         | The trust anchor (`ca.crt`), local CA serial state, and the CA private key (`ca.key`, ignored by Git). The private key stays on a trusted backend provisioning host. |
| `certs/fastapi/`    | FastAPI's mTLS client certificate, key, CSR, and `server.cnf`. The backend uses this identity to connect to the normal mTLS Zenoh router.                            |
| `certs/zenoh_app/`  | The app router's certificate, key, CSR, and `router.cnf`. It authenticates the router-to-router mTLS link to the private router.                                     |
| `certs/zenoh_mtls/` | The private router's certificate, key, CSR, and `router.cnf`. The same server identity is used by the TLS-only bootstrap router.                                     |

Private keys match the `*.key` Git ignore rule. A repository checkout must not
contain a real production CA key, Firebase credential, router administrator
secret, or mower private key.

## Trust and connection roles

The backend verifies the mTLS router with `ZENOH_CA_CERT` and presents
`ZENOH_FASTAPI_CERT` plus `ZENOH_FASTAPI_KEY`. The app router and private router
mutually authenticate their bridge with the CA-issued router certificates. The
bootstrap router uses server-authenticated TLS only: renewal requests are
authorized by a TPM signature and one-time nonce rather than an operational
mower certificate that may have expired.

Mower operational bundles are generated outside this directory into a protected
Jetson credential directory. A bundle contains `mower.crt`, `mower.key`, and
`root_ca.pem`; its certificate common name is `mower:{uuid}` and it has a
90-day lifetime. The CA private key must never be copied into a Jetson, image,
container, or `.env` file.

## Issuance and renewal

The `*.cnf` files control certificate subject/SAN extensions. Update them when
the development DNS name or IP changes, then reissue the matching server or
router certificate with the CA on the trusted host. Every hostname a Zenoh
client uses must appear in the server certificate SAN.

`tools/issue_mower_certificate.sh` issues a mower client certificate from a
validated mower UUID. It protects output with `umask 077`, reuses only a
matching existing bundle, and accepts a mower-generated CSR during renewal so
the mower's private key is never exported. See
[mower initialization](mower-initialization.md) for the full identity lifecycle.
