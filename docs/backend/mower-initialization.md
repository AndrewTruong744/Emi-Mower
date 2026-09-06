# Mower initialization and provisioning

Provisioning creates one mower identity across PostgreSQL, the mTLS router, and
the Jetson runtime. It is a trusted fleet operation: it does not flash firmware
or start physical motion, but it grants a new device credentials and route
access. Use the fleet provisioning procedure for target/environment approval.

## Physical mower flow

[`src/scripts/provision_mower.py`](../../backend/src/scripts/provision_mower.py)
is idempotent for the same mower UUID and serial number. It performs this
sequence:

1. Choose the supplied UUID or generate one, then create/upsert an unassigned
   `mowers` row with serial number and nickname.
2. If supplied, validate and store the mower TPM P-256 device-root **public**
   key in `mower_device_identities`. The private half never leaves the mower.
3. Configure the mTLS-router ACL subject for `CN=mower:{uuid}` and restrict it
   to `mower/{uuid}/**`.
4. Run `tools/issue_mower_certificate.sh` on the trusted provisioning host to
   create a 90-day operational certificate bundle.
5. Write a mode-600 Jetson Compose environment file with the mower UUID,
   credential mount directory, router endpoint, TLS verification setting, and
   real/simulation launch mode.

The provisioner requires readable CA certificate/key material and fails before
issuance if they are absent. Its `--output-dir` is the protected mower
credential directory; it must not be tracked. Re-run with `--mower-id` after a
partial failure instead of creating a second mower record.

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
and issues a replacement certificate. The gateway verifies the replacement
against its already-mounted CA before atomically replacing its own operational
certificate and key. Root-CA replacement is intentionally out of band.
