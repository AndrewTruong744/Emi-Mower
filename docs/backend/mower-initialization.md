# Mower initialization and provisioning

Provisioning creates one mower identity across PostgreSQL, the mTLS router, and
the Jetson runtime. It is a trusted fleet operation: it does not flash firmware
or start physical motion, but it grants a new device credentials and route
access. Use the fleet provisioning procedure for target/environment approval.

## Physical mower flow

[`src/scripts/provision_mower.py`](../../backend/src/scripts/provision_mower.py)
is idempotent for the same mower UUID. It performs this sequence:

1. Choose the supplied UUID or generate one, then create/upsert an unassigned
   `mowers` row with that canonical ID and a nickname.
2. The mower initializer exports its TPM P-256 device-root **public** key to a
   protected PEM file. For a physical mower, this handoff is currently
   operator/factory-mediated: the trusted provisioner reads that file through
   `--device-root-public-key`; a running mower does not automatically upload
   it. The provisioner validates and normalizes the PEM, stores it in
   `mowers.device_public_key_pem`, and stores its normalized SHA-256 digest in
   `mowers.device_key_fingerprint`. The private half never leaves the mower.
3. Configure the mTLS-router ACL subject for `CN=mower:{uuid}` and restrict it
   to `mower/{uuid}/**`.
4. Generate a separate operational mTLS key and CSR on the trusted
   provisioner, submit that CSR to step-ca, and write the resulting 90-day
   certificate bundle to the protected mower credential directory. The CA
   private key is not read by the provisioning process.
5. Write a mode-600 Jetson Compose environment file with the mower UUID,
   credential mount directory, router endpoint, TLS verification setting, and
   real/simulation launch mode.

The provisioner requires the public step-ca root and its scoped issuance
credential, but never CA-key material. Its `--output-dir` is the protected
mower credential directory; it must not be tracked. Re-run with `--mower-id`
after a partial failure instead of creating a second mower record.

## Local TPM simulation flow

[`tools/initialize_simulated_mower.sh`](../../backend/tools/initialize_simulated_mower.sh)
creates a self-contained local simulator under
`nvidia_jetson/.sim/mowers/{uuid}/`. For each simulated mower it:

1. Creates a per-mower mode-700 directory, a mode-600 environment file,
   credential directory, swtpm state directory, and Compose project name.
2. Starts the `swtpm` sidecar and runs the TPM initializer, which creates the
   device-root key inside the emulator and exports only its public key.
3. Calls the backend provisioner with that public key, simulation mode, and
   local non-production TLS-name verification disabled.
4. Starts the ROS simulator container after the operational credentials and ACL
   have been created.

Start the local backend dependencies, including PostgreSQL, Valkey, mTLS and
bootstrap routers, and FastAPI before running the simulator tool. Each simulator
has its own state, credentials, and Compose project, so multiple local mowers
can coexist. Stopping its project preserves local simulator state unless its
directories are explicitly removed.

## Renewal after initialization

At gateway startup, an operational certificate that is expired or within the
renewal window triggers the bootstrap challenge/complete flow. The mower signs
the challenge-bound CSR digest with its TPM device-root key; the backend checks
the registered public key, consumes the one-time nonce, renews the mTLS ACL,
and requests a replacement certificate from step-ca. The gateway verifies the
replacement against its already-mounted CA before atomically switching its own
versioned operational credential bundle. Root-CA replacement is intentionally
out of band.
