# Backend scripts and lifecycles

Scripts are grouped by whether they run once, run continuously, or generate
artifacts. Run them from `backend/` with `uv run` unless a command below says
otherwise. Do not schedule a destructive or provisioning script without the
appropriate environment approval.

## One-shot Python scripts

| Script                         | When to run it                                                   | Why it exists                                                                                                                   |
| ------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `src.scripts.add_all_acls`     | After router recreation, database restore, or ACL loss           | Reconciles users/mowers in PostgreSQL into runtime Zenoh ACL configuration. It does not provision user passwords.               |
| `src.scripts.provision_mower`  | A trusted provisioning operation for one mower                   | Creates/reuses mower identity, configures mower ACL, issues an operational certificate, and writes the Jetson environment file. |
| `src.scripts.seed_fake_mowers` | Local UI/demo development after the seed user has logged in once | Upserts three deterministic fake mowers and telemetry history, then invalidates affected caches.                                |
| `src.scripts.clear_all_data`   | An explicitly approved local reset                               | Truncates all public application tables except `alembic_version` and flushes the configured Valkey database. It is destructive. |

## Persistent workers

| Script                                  | Compose service    | Loop and responsibility                                                                                                                                                                                                  |
| --------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src.scripts.upload_telemetry_data`     | `upload-telemetry` | Every 60 seconds, atomically moves active mower telemetry lists to temporary keys, persists valid records to PostgreSQL, and deletes only successfully saved batches. Leftover temporary keys are retried after a crash. |
| `src.scripts.remove_usrpwds_from_zenoh` | `remove-usrpwds`   | Every 60 seconds, removes expired dynamic app-router passwords and their Valkey expiry entries.                                                                                                                          |

These workers are separate from FastAPI so request handling does not perform
long-lived batch persistence or credential cleanup. Start them when their
respective lifecycle is needed; local Compose does not make their completion a
substitute for monitoring failed work.

## Shell and Node tools

| Tool                                      | Lifecycle                                                                                                                                                           |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/generate_types.sh`                 | Run after a native Zenoh AsyncAPI change. Validates the schema and regenerates committed paths/types.                                                               |
| `tools/generate_zenoh_paths.mjs`          | Invoked by `generate_types.sh`; writes generated paths for backend, app, and Jetson consumers.                                                                      |
| `tools/generate_rust_zenoh_types.mjs`     | Invoked by `generate_types.sh`; writes the gateway's native Zenoh Rust types.                                                                                       |
| `tools/generate_renewal_python_types.mjs` | Invoked by `generate_types.sh`; updates renewal types in backend and app generated files.                                                                           |
| `tools/issue_mower_certificate.sh`        | Invoked by provisioning or a trusted renewal issuer. Issues/reuses a 90-day mower certificate bundle and accepts a mower CSR without exporting a mower private key. |
| `tools/initialize_simulated_mower.sh`     | Local-only simulator setup. Creates per-mower swtpm state, provisions its public identity and certificate, then starts its ROS Compose project.                     |

`initialize_simulated_mower.sh` creates state under ignored Jetson simulation
directories. It is not a physical-mower deployment tool.
`issue_mower_certificate.sh` and `provision_mower` require access to the CA key
and must run only on the trusted backend provisioning host.
