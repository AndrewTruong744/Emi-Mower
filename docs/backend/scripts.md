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
| `src.scripts.clear_all_data`   | An explicitly approved local reset                               | Truncates all public application tables except `alembic_version` and flushes the configured Valkey database. It is destructive. |

## Persistent workers

| Script                                  | Compose service    | Loop and responsibility                                                                                                                                                                                                  |
| --------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src.scripts.upload_telemetry_data`     | `upload-telemetry` | Every 60 seconds, schedules the telemetry-buffer service, which atomically moves active mower telemetry lists to temporary keys, persists valid records to PostgreSQL, and deletes only successfully saved batches. Leftover temporary keys are retried after a crash. |
| `src.scripts.remove_usrpwds_from_zenoh` | `remove-usrpwds`   | Every 60 seconds, removes expired dynamic app-router passwords and their Valkey expiry entries.                                                                                                                          |

These workers are separate from FastAPI so request handling does not perform
long-lived batch persistence or credential cleanup. Start them when their
respective lifecycle is needed; local Compose does not make their completion a
substitute for monitoring failed work.

## Shell and Node tools

| Tool                                      | Lifecycle                                                                                                                                                           |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `npm --prefix tools run generate`         | Run after a native Zenoh AsyncAPI change. Validates the schema and regenerates committed paths/types.                                                               |
| `tools/generate_zenoh_bindings.mjs`       | Invoked by the npm command; uses Modelina and the AsyncAPI schema to write all native Zenoh types and paths for backend, app, and gateway.                        |
| `tools/refresh_service_certificates.sh`   | Runs only inside the dedicated step-ca container. Creates or refreshes backend and Zenoh-router leaf identities in their persistent volumes. |
| `tools/ensure_step_ca.sh`                 | Runs only inside the dedicated step-ca container. Creates the local persistent CA root when no CA state exists and refuses to overwrite partial state. |
| `tools/initialize_simulated_mower.sh`     | Local-only simulator setup. Creates per-mower swtpm state, provisions its public identity and certificate, then starts its ROS Compose project.                     |

`initialize_simulated_mower.sh` creates state under ignored Jetson simulation
directories. It is not a physical-mower deployment tool.
`provision_mower` signs a mower CSR through step-ca using a scoped issuer
credential. It does not require or receive a CA private key.
