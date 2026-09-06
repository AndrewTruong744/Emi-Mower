# Valkey keys and lifecycles

Valkey is a cache-aside store for user/mower reads, a durable-enough handoff
buffer for telemetry persistence, and a small registry for temporary Zenoh
credentials. The key definitions and Pydantic value models live in
[`src/schemas/valkey.py`](../../backend/src/schemas/valkey.py).

## Cache keys

These values are JSON strings and use the common cache TTL of 86,400 seconds
(one day). Repository reads refresh the TTL when they use a cached value.

| Key                       | Value                           | Purpose                                                   |
| ------------------------- | ------------------------------- | --------------------------------------------------------- |
| `user:{user_id}:mowers`   | JSON list of mower IDs          | Avoids re-reading a user's mower list.                    |
| `user:{user_id}:data`     | JSON user data                  | Caches ID, email, name, and creation time.                |
| `mower:{mower_id}:data`   | JSON mower data                 | Caches ID, serial number, nickname, and owner ID.         |
| `mower:{mower_id}:status` | Plain status string             | Keeps status separately from mower data.                  |
| `mower:{mower_id}:owner`  | Plain owner ID or literal `dne` | Caches ownership lookup, including a known unowned mower. |

Write paths must invalidate or refresh every affected cache key. For example,
the fake-mower seed script invalidates the user mower list and each seeded
mower's data, owner, and status keys.

## Telemetry buffer keys

| Key pattern                            | Type                                         | Lifecycle                                                                                                                                     |
| -------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `mower:{mower_id}:telemetry:data`      | Valkey LIST of JSON `TelemetryRecord` values | The live telemetry listener appends records here.                                                                                             |
| `mower:{mower_id}:telemetry:data:temp` | Valkey LIST                                  | The telemetry worker atomically renames the active list before writing it to PostgreSQL. A leftover temp key is retried after a worker crash. |

The worker deletes a temporary list only after the PostgreSQL transaction
succeeds. Invalid records are logged and skipped; database failures preserve
the temporary list for a later retry. These lists are not ordinary cache entries
and do not use the one-day `setex` TTL.

## Zenoh credential-expiry key

`user:zenoh_tokens` is a Valkey HASH mapping user ID to a Unix expiry time. On
successful `user/login`, the backend records the five-minute router-password
expiry. The `remove_usrpwds_from_zenoh` worker checks it every 60 seconds,
deletes expired router passwords through the app-router admin API, and removes
the corresponding hash field. It is an expiry registry, not a token store: do
not put the actual JWT/password in Valkey.

## Operations

Use `SCAN`, then `TYPE`, `GET`, `HGETALL`, or `LRANGE` to inspect local keys.
Avoid `KEYS` against a production-sized database. `clear_all_data` calls
`FLUSHDB` for the configured logical database, so it is a destructive local
development reset rather than a routine troubleshooting command.
