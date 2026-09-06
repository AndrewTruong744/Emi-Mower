# Zenoh contract

**Authoritative source:** [`backend/zenoh_asyncapi.yaml`](../../backend/zenoh_asyncapi.yaml).

This AsyncAPI document defines the native Zenoh routes and telemetry schemas
used by the app, backend, and Jetson gateway. In particular, mower commands and
telemetry are scoped by `mower_id`.

Generated outputs are committed in the backend, app, and Jetson workspace. Do
not edit them by hand. From `backend/`, regenerate them with:

```sh
sh tools/generate_types.sh
```

Then run the backend telemetry contract tests and the affected app and Jetson
tests. The gateway's ROS messages are a separate ROS IDL contract and should
not be conflated with native Zenoh payloads.

## Certificate-renewal bootstrap routes

The only routes on the TLS-only bootstrap plane are
`bootstrap/mower/{mower_id}/certificate/renew/challenge` and
`bootstrap/mower/{mower_id}/certificate/renew/complete`. They are intentionally
two queries: the first returns an expiring one-time nonce and the second binds
the replacement CSR to a TPM signature. This lets a mower renew even when its
normal mTLS certificate is expired, without exposing normal mower routes on
the bootstrap listener.
