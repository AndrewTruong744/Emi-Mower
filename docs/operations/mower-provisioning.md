# Mower provisioning

Provisioning runs on a trusted backend or factory host. It creates an unassigned
mower record, assigns a unique mower ID, issues a 90-day mower mTLS bundle,
grants that identity access only to its own Zenoh routes, and writes the Jetson
environment configuration.

The operational command and required inputs are documented in
[`docs/backend/development.md`](../backend/development.md). The Jetson deployment
expectations are documented in
[`nvidia_jetson/README.md`](../../nvidia_jetson/README.md).

## Invariants

- Never generate or retain the CA private key on a mower Jetson.
- Keep mower private keys and generated `.env` files out of Git and container
  images.
- Use the same mower ID and serial number when resuming a failed provisioning
  attempt to avoid creating a duplicate mower record.
- Verify the mower can authenticate only to its intended routes before treating
  provisioning as complete.
- Register the TPM device-root public key during initialization. Its private
  half remains in the TPM (or swtpm for a local simulator) and authorizes
  renewal after the operational mTLS certificate has expired.
- Use a separate UUID-named Compose project and persistent directory for every
  local simulated mower; never share swtpm state between mower identities.
