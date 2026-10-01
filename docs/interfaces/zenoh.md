# Zenoh contract

**Authoritative source:** [`backend/zenoh_asyncapi.yaml`](../../backend/zenoh_asyncapi.yaml).

This AsyncAPI document defines native Zenoh routes and wire payload shapes used
by the app, backend, and Jetson gateway. Value checks such as joystick limits,
date parsing, and URL safety belong to the functions handling those payloads.
Mower commands and telemetry are scoped by `mower_id`.

## Connection planes

The router configuration files define three local connection planes: the
app-router Zenoh WebSocket listener on 7447, the private mTLS router on 7448,
and the TLS-only certificate renewal router on 7449. Router ACLs limit the two
`bootstrap/` channels to the renewal plane. See
[Zenoh routers](../backend/zenoh-routers.md) for the executable configuration.

The mobile app uses the app router's separate remote-API WebSocket endpoint on
port 10000. Its URL is configured through `EXPO_PUBLIC_ZENOH_URL`.

## Mower liveliness

The Rust mower gateway declares the payload-less token
`mower/{mower_id}/liveliness` for the lifetime of its authenticated mTLS
Zenoh session. The app directly declares a historical liveliness subscriber
for its ACL-scoped mower routes; a token declaration means `connected` and a
token deletion means `disconnected`. This avoids a FastAPI/Valkey status
projection and makes reconnects visible immediately. It is strictly Zenoh
connectivity, not a mower health, safety, or telemetry-freshness signal.

Generated outputs are committed in the backend, app, and Jetson workspace. Do
not edit them by hand. From `backend/`, regenerate them with:

```sh
npm --prefix tools run generate
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
