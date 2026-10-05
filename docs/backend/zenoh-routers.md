# Zenoh routers and ACL startup

The backend operates three Zenoh router planes. Their configuration files are
executable configuration; this page explains their roles but does not replace
them as the source of truth.

| Configuration                                                                | Plane and listeners                                                                        | Purpose                                                                                                                                                                                    |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [`zenoh-router-app.json5`](../../backend/zenoh-router-app.json5)             | Non-TLS Zenoh `ws` listener on 7447, remote-API WebSocket on 10000, REST admin API on 8001 | The app-facing router. It bridges to the mTLS router, permits only guest `user/login` initially, and receives runtime user ACLs and passwords through its admin API.                       |
| [`zenoh-router-mtls.json5`](../../backend/zenoh-router-mtls.json5)           | mTLS listener on 7448, loopback REST admin API on 8002                                     | The private backend/mower/router mesh. It validates client certificates and starts with access for the backend and app-router peer; local simulated provisioning adds mower ACLs to a generated startup configuration. |
| [`zenoh-router-bootstrap.json5`](../../backend/zenoh-router-bootstrap.json5) | TLS-only listener on 7449                                                                  | An isolated certificate-renewal plane. It allows only the two `bootstrap/mower/*/certificate/renew/**` query routes and intentionally exposes no normal app, command, or telemetry routes. |

The app router uses [`zenoh-router-users.txt`](../../backend/zenoh-router-users.txt)
as its static username/password dictionary, but anonymous clients can reach
only `user/login`. The login handler validates the Firebase ID token and then
creates the user's short-lived router password and route-specific ACL.

## Startup configurations

The local Compose stack starts `zenoh-mtls`, then `zenoh-app`, and starts the
independent `zenoh-bootstrap` router. On Linux it uses host networking, so the
production-like config files bind their documented local ports. The app-router
image is built from `Dockerfile.zenoh-app` because the remote-API plugin is
required for the TypeScript client.

`zenoh-router-app.test.json5` and `zenoh-router-mtls.test.json5` are
integration-test variants: they use bridge-network service names and expose
their REST endpoints to the test stack. The app test plane omits transport
passwords so tests can directly exercise invalid application-token rejection.
They are not production security
configuration and should be changed only with the matching integration tests.

## `add-all-acls` lifecycle

[`src/scripts/add_all_acls.py`](../../backend/src/scripts/add_all_acls.py) is a
one-shot reconciler, not a router startup hook. It reads all users, their owned
mowers, and all mower identities from PostgreSQL, then uses both router REST
admin APIs to recreate the ACL rule, subject, and policy for each record.

The `add-all-acls` Compose service waits for the backend health check; the
backend in turn waits for PostgreSQL, Valkey, and all three routers. Start it
after persistent services are up:

```sh
docker compose -f local-docker-compose.yml run --rm add-all-acls
```

The reconciler and physical provisioning currently attempt REST ACL writes.
Zenoh 1.9 rejects runtime `access_control` changes, so these paths need a
compatible router configuration/deployment workflow before use with that
version. The reconciler deliberately does **not** create user passwords;
those are created by `user/login` and removed by the credential-expiry worker.

## ACL ownership

`ZenohAdminClient` attempts router admin-space writes. Local simulated
provisioning instead installs startup configuration. Both construct a rule,
subject, and policy triad for each identity:

- an app user can access `user/**` and only that user's owned
  `mower/{mower_id}/**` paths; and
- a mower certificate with `CN=mower:{mower_id}` can access only its own
  `mower/{mower_id}/**` paths on the mTLS plane. Zenoh 1.9 only supports runtime
  configuration updates under `plugins/`; its ACL cannot be changed through
  the REST admin API. Local simulated provisioning therefore writes a complete
  router configuration under the ignored `backend/.sim/` directory, preserving
  the internal backend/router subjects and all canonical mower IDs from
  PostgreSQL, then recreates the local mTLS router. The selected configuration
  is recorded in `backend/.env` for subsequent local stack restarts.

Keep the routers default-deny. A UI check or a route parser is not a substitute
for the router ACL, and router administration endpoints must remain inaccessible
to untrusted clients.
