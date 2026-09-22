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

## Renewal architecture

Operational certificates are short-lived, but a mower must be able to renew
when its current operational certificate is expired. Renewal therefore uses a
separate TLS-only bootstrap router rather than the normal mTLS router. The
bootstrap router permits only these two query/reply routes:

- `bootstrap/mower/{mower_id}/certificate/renew/challenge`
- `bootstrap/mower/{mower_id}/certificate/renew/complete`

The first route is the mower's request for a challenge. It has no credential
payload; the mower ID comes from the scoped route. The backend confirms that
the mower is an active registered identity, creates a cryptographically random
nonce, and stores it in Valkey under a mower- and nonce-specific key. The
nonce expires after five minutes and is single-use.

The second route completes the renewal. Its request contains the nonce, a new
CSR, and a TPM signature. The mower's sequence is:

1. Request a fresh nonce from the challenge route.
2. Generate a new operational keypair locally. The private key remains on the
   mower.
3. Create a CSR containing the new public key and exactly one subject common
   name, `mower:{mower_id}`. Sign the CSR with the new operational private key.
4. Construct the canonical renewal message:

   ```text
   emi-mower-renew-v1\0{mower_id}\0{nonce}\0SHA-256(exact CSR PEM bytes)
   ```

5. Ask the TPM device-root private key to produce a DER ECDSA/SHA-256
   signature over that message, then Base64-encode that signature.
6. Send the nonce, CSR, and TPM signature to the completion route.

The nonce comes before the TPM signature so that the proof is fresh and bound
to one particular request. Including the hash of the exact CSR prevents a
captured TPM signature from authorizing a different public key, identity, or
certificate request. Atomic Valkey `GETDEL` consumption prevents replay after
the request succeeds; expiration rejects delayed requests.

### Backend verification and issuance

The backend treats the TPM device-root key and the operational certificate key
as separate keys with separate purposes:

- The **new operational key** will later authenticate normal mTLS sessions.
  The backend parses the CSR, verifies its self-signature using the public key
  inside that CSR, and requires `CN=mower:{mower_id}`. This confirms that the
  requester controls the private key corresponding to the public key it wants
  certified, and detects tampering or malformed CSR data. It does not by itself
  authorize the mower identity.
- The **TPM device-root key** authorizes the renewal. Its public half was
  registered during provisioning and is stored for that mower. The backend
  recreates the canonical renewal message and verifies the supplied TPM
  signature with that stored public key. A valid result proves that the TPM
  private key registered for this mower approved this exact nonce and CSR.

After these checks, the backend consumes the nonce and passes the readable CSR
unchanged to `step ca sign`. A CSR signature is a proof, not encrypted content:
the backend and Step CA do not decrypt it and never receive the mower's new
operational private key. Step CA signs the requested public key and identity
into a leaf certificate; it does not create or return an operational private
key. The backend returns the leaf certificate and public CA trust material to
the mower.

The mower verifies the returned certificate against its already-installed root
CA, stages the certificate with its locally generated private key, and
atomically switches its active credential bundle. Root CA replacement is an
out-of-band operation.

### What mTLS proves after renewal

In a normal mTLS connection, the mTLS router performs two independent checks:

1. **CA authenticity:** the leaf certificate signature must chain to the
   configured trusted CA, showing that the trusted Step CA issued the mower
   identity certificate.
2. **Private-key possession:** the mower must complete the TLS handshake proof
   for the private key matching the public key embedded in that leaf
   certificate. This proves control of the certificate's key, not that the
   private key created the CA signature.

Together, these checks establish that a trusted CA issued the identity
certificate and that the connecting mower controls the corresponding
operational private key. The TPM private key is not the normal mTLS key; it is
used only to authorize renewal when the normal operational certificate cannot
be relied on.

## Target automated signer

`local-docker-compose.yml` starts step-ca before the backend and routers. Its
idempotent bootstrap script creates a fresh local root only when its persistent
volume has no CA state, then refreshes the backend and router leaf identities
into separate credential volumes. The backend remains the mower-renewal policy
gate: it validates the TPM proof and CSR before requesting a certificate from
step-ca. FastAPI, Zenoh routers, and Jetsons receive only their own leaf
private keys and the public trust chain.
