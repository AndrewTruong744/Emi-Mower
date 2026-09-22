# Backend Zenoh queries, replies, and paths

**Wire-contract source of truth:**
[`backend/zenoh_asyncapi.yaml`](../../backend/zenoh_asyncapi.yaml). This page
describes how the backend serves that contract; the AsyncAPI schema defines the
route payloads and must be changed first.

## Query/reply behavior

At FastAPI startup, `register_handlers` declares backend queryables and
subscribers on the backend's mTLS Zenoh session. `ZenohQueryHandler` converts a
JSON-object query payload into its generated Pydantic request model, opens an
async database session, calls the listener, and replies with JSON. It waits up
to five seconds for the coroutine scheduled from Zenoh's callback thread.

Expected application, validation, authentication, ownership, repository, and
external-service failures become RFC 9457-style `ProblemDetails` error replies.
Unexpected failures become a sanitized internal-error reply. Clients must not
assume every reply is a success payload.

`ZenohMessageHandler` serves one-way publications. It validates the JSON payload
and invokes the listener, but cannot reply to the sender; failures are logged.
Telemetry and cutout-upload completion use this pattern.

## Routes declared by the backend

| Path                                                     | Pattern                        | Backend action                                                                                                                     |
| -------------------------------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `user/login`                                             | Query/reply                    | Verifies Firebase identity, creates the user if needed, provisions a five-minute app-router credential/ACL, and returns user data. |
| `user/add_mower`                                         | Query/reply                    | Validates Firebase identity and assigns an unowned mower to the caller.                                                            |
| `user/update_name`                                       | Query/reply                    | Validates Firebase identity and changes the caller's display name.                                                                 |
| `user/update_email`                                      | Query/reply                    | Validates old/new identity tokens and changes the user's email.                                                                    |
| `mower/{mower_id}/update_name`                           | Query/reply                    | Extracts the mower ID from the key expression, verifies ownership, and updates the nickname.                                       |
| `mower/{mower_id}/telemetry/{telemetry_type}/old`        | Query/reply                    | Verifies Firebase identity and ownership, then returns a cursor-paginated historical metric page.                                  |
| `mower/{mower_id}/livekit/consume`                       | Query/reply                    | Issues a room-scoped, subscribe-only LiveKit token; router ACL scope authorizes the mower path.                                    |
| `mower/{mower_id}/livekit/upload`                        | Query/reply                    | Issues a room-scoped, publish-only LiveKit token for that mower.                                                                   |
| `user/cutouts/upload-url`                                | Query/reply                    | Verifies identity and that the user owns a mower, then returns a signed GCS PUT URL and opaque object key.                         |
| `mower/{mower_id}/cutout/delivery`                       | One-way publication            | After GCS verification, publishes that mower's short-lived signed GET URL.                                                         |
| `mower/{mower_id}/telemetry`                             | One-way publication            | Validates a telemetry list and buffers it in Valkey for the telemetry worker.                                                      |
| `mower/{mower_id}/liveliness`                            | Zenoh liveliness token          | Declared directly by the connected mower gateway; the app observes it directly as Zenoh connection state.                        |
| `user/cutouts/uploaded`                                  | One-way publication            | Revalidates identity, object key, and content type; verifies the GCS object, then best-effort delivers it to all currently owned mowers. |
| `bootstrap/mower/{mower_id}/certificate/renew/challenge` | Query/reply on bootstrap plane | Issues a short-lived renewal nonce for a registered mower TPM identity.                                                            |
| `bootstrap/mower/{mower_id}/certificate/renew/complete`  | Query/reply on bootstrap plane | Verifies TPM proof and CSR, then issues a replacement operational certificate.                                                     |

`mower/{mower_id}/joystick` and `mower/{mower_id}/command` are contract paths
used by the app and mower gateway. The backend does not declare handlers for
them; it provisions ACL scope and participates in the router mesh so the
gateway can own command handling. The STM32 remains the final motor-safety
authority.

The backend does not declare or cache the liveliness token. ACL provisioning
allows a mower certificate to declare only its own token and an app user to
observe tokens only below its owned mower paths. Token presence means the
gateway's Zenoh session is active, not that the mower is safe or healthy.

## Path handling rules

Listener constants come from generated path functions, with `*` only for a
backend declaration that accepts a parameterized route. The listener parses the
concrete key expression before using its mower ID or metric. Do not build route
strings by hand or expand a wildcard's authorization beyond the ACL supplied by
the router.

The normal handlers use the mTLS router session. Only renewal handlers register
on the TLS-only bootstrap session, keeping the expiry-recovery plane unable to
reach ordinary mower or user paths.
