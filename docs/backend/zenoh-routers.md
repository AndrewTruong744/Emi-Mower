# Zenoh routers and runtime permissions

All three router images build from the sibling `../zenoh` checkout using
`ci/Dockerfile.runtime-access`. The fork currently starts from Zenoh 1.10.1.
The backend Python binding remains a wire-compatible protocol client; runtime
administration uses the fork's protected REST API.

| Configuration | Listeners | Purpose |
| --- | --- | --- |
| `zenoh-router-app.json5` | Native TLS 7447; loopback management 8001 | Guest login, captured client connections and per-user mower permissions. |
| `zenoh-router-mtls.json5` | mTLS 7448; loopback management 8002 | Backend, app-router uplink and certificate-scoped mower access. |
| `zenoh-router-bootstrap.json5` | Server-authenticated TLS 7449 | Only TPM-proven certificate renewal routes. |

The test app router uses native TCP on 17447 (host mapping) and protected REST
on 18001. The test mTLS router's management port maps to 18002. These are
isolated test settings. Remote API/WebSocket and router passwords are no longer
part of app communication.

## Login on the existing connection

1. The native app connects as a Zenoh **client**. Default-deny guest ACLs allow
   only querying `user/login` and receiving its reply.
2. The app router replaces that query's attachment with a random connection
   reference and a one-time nonce. The nonce expires in 30 seconds and binds to
   exactly one transport link. It is internal metadata forwarded to the backend.
3. The backend verifies Firebase, reads ownership, replaces that user's route
   policy, then authorizes the captured reference through REST for five minutes.
4. Only after the router acknowledges authorization does the backend reply
   `authorized: true`. The app declares subscriptions on the same session.

The app cannot create the internal authorization by editing its payload or
attachment. The backend needs the management credential, and the router checks
its own fresh nonce. No grant/password is returned to the app. Multiple devices
may bind different captured connections to the same principal; refreshing one
connection does not extend another connection's lifetime.

Native routing announcements (`declare_subscriber` / `declare_queryable` in
**egress**) are permitted so native clients can discover wildcard backend
handlers. They carry route metadata, not application payloads. Ingress command
puts, queries, subscription declarations and egress telemetry/replies remain
limited to their allowed operations and owned mower keys. Apps cannot publish
telemetry, serve backend queryables or create mower liveliness tokens.

## Protected management API

Set `plugins/rest/runtime_access_control` with `token_file` and
`capture_query_keys: ["user/login"]` on the app router; the mTLS router uses an
empty capture list. Capture requires enabled default-deny ACLs and
`transport/unicast/max_links: 1`.

All REST endpoints, including the original REST publish/query interface, require
`Authorization: Bearer <management token>` when this option is enabled. Compose
creates a persistent, random token in a dedicated volume and mounts it only to
routers, the backend and the ACL reconciler. Administrator access must use a
private loopback/network endpoint. Across hosts, protect management traffic with
TLS. Neither the token nor CA private key belongs in the app or mower.

| Method and path under `/@/runtime` | Action |
| --- | --- |
| `GET /connections` | List live references, Zenoh IDs and active principals. |
| `GET`, `PUT /acl` | Read or replace the global ACL snapshot. |
| `PUT /principals/{id}` | Replace `{ "rules": [...] }` for that user's live connections. |
| `DELETE /principals/{id}` | Remove policy, deny affected sessions and close their transports. |
| `PUT /connections/{id}/authorization` | Bind `{ "principal", "nonce", "ttl_seconds" }`; lifetime 1–3600 seconds. |
| `DELETE /connections/{id}/authorization` | Revoke and close one transport. |
| `PUT /policies/{id}` | Upsert `{ "subject": {...}, "rules": [...] }`, including certificate-CN policies. |
| `DELETE /policies/{id}` | Remove identity policy and close only matching transports to clear declarations. |

Invalid snapshots fail validation before publication. Readers use immutable
snapshots and versioned caches. Compilation runs outside routing-table locks;
REST compilation runs on blocking workers. Updating one user's permissions
requires no router restart or app reconnect. Other transports stay active.
Already queued/in-flight data cannot be recalled. Previously denied declarations
are not replayed by an ACL addition; clients should declare them after successful
login or redeclare them when gaining new routes.

## Restart, ownership and certificates

Policies and bindings are in memory. Backend startup and `src.scripts.add_all_acls`
restore database user/mower policy sources; login establishes connection bindings.
After independently restarting a router, run the reconciler. Existing native
clients reconnect, authenticate again, and redeclare subscriptions.

Provisioning both physical and simulated mowers calls the live policy API; it
no longer rewrites startup ACLs or recreates the mTLS router. Ownership transfers
revoke the old owner's sessions before committing and refresh both user policies.
Failures during revocation abort the transfer. A later policy refresh failure
revokes the affected user rather than retaining stale permissions.

Renewing a mower leaf certificate under the same trusted CA and unchanged CN
requires no ACL change. Certificate/CA listener hot reload is **not** implemented
by this feature. Service listener certificates and trust roots still follow the
existing rollout/restart procedure. Removing a CN policy denies and disconnects
matching transports; it is not an X.509 serial-number revocation mechanism.


## Google-account replacement

`user/update_email` verifies the original and replacement Firebase identities and
moves all source mowers to the replacement UID. It retires the original principal
before committing: the only retained permission is the operation's final reply,
with no ingress queries, publications, subscription declarations or mower data.
The app then changes Firebase identity and establishes its new Zenoh session.

PostgreSQL account locks serialize login, account changes and ACL reconciliation.
Permission publication reads current database ownership rather than cached mower
lists. Account transfer removes the original user row and clears profile,
ownership and legacy credential-registry caches. A later signup using the
original Google account starts with an empty mower list. Mower certificates and
telemetry remain attached to the same mower UUIDs throughout.
