# Certificates

The backend repository holds no CA or service-certificate directory. The local
step-ca container keeps the active local CA in its persistent Docker volume
and writes each service identity into a separate credential volume. A
repository checkout must not contain a real production CA key, Firebase
credential, router administrator secret, or mower private key.

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
90-day lifetime. The CA private key must never be copied into a Jetson,
application image, ordinary backend/router container, `.env` file, or the
repository. The dedicated local step-ca workload is the sole exception: its
persistent volume holds the active local root and intermediate keys. This is a
local-development trust root; use a separate offline root and online
intermediate before adopting the design in a long-lived production VPC.

## Issuance and renewal

The active local Step CA flow issues service leaf certificates from
`tools/refresh_service_certificates.sh`. Its `ZENOH_ROUTER_SANS` input defines
the mTLS router certificate SANs, which also serve the bootstrap router. Every
hostname or literal IP a Zenoh client uses must appear in that server
certificate's SAN. The local stack supplies `localhost`, `127.0.0.1`, and
`host.docker.internal`; production must supply only its deployment endpoint
names/IPs.

The provisioner generates a mower-owned private key and CSR for initial
enrollment, then submits that CSR to step-ca. During renewal the mower itself
generates the CSR, so its replacement private key is never exported. See
[mower initialization](mower-initialization.md) for the full identity lifecycle.

## Target automated signer

`local-docker-compose.yml` starts step-ca before the backend and routers. Its
idempotent bootstrap script creates a fresh local root only when its persistent
volume has no CA state, then refreshes the backend and router leaf identities
into separate credential volumes. The backend remains the mower-renewal policy
gate: it validates the TPM proof and CSR before requesting a certificate from
step-ca. FastAPI, Zenoh routers, and Jetsons receive only their own leaf
private keys and the public trust chain.
