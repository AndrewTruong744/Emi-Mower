# PostgreSQL models and relationships

**Database schema source of truth:** the ordered Alembic migrations in
[`backend/src/migrations/versions/`](../../backend/src/migrations/versions/).
SQLAlchemy models in `src/models/` express the runtime mapping; make a migration
for every persistent schema change and apply it with `uv run alembic upgrade head`.

## Core ownership model

```text
users 1 ──< mowers 1 ──< mower_telemetry 1 ── 0..1 mower_imu_data
```

| Table                      | Primary contents                                                       | Relationships                                                                                                                       |
| -------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `users`                    | Firebase user ID, unique email, display name, creation time            | One user may own many mowers.                                                                                                       |
| `mowers`                   | UUID, nickname, optional owner, lifecycle status, one TPM public-key identity, creation time | The UUID is the canonical mower ID. An unassigned mower has a null owner. `lifecycle_status` is `active` or `decommissioned`; the TPM private key remains on the mower. |
| `mower_telemetry`          | Timestamped location, battery, motor data, and safety flag             | Many records belong to one mower. Multiple records with the same mower/timestamp are allowed.                                       |
| `mower_imu_data`           | Accelerometer, gyro, and magnetometer measurements                     | A one-to-one extension of a telemetry row, enforced by a unique `telemetry_id`.                                                     |

## Deletion and integrity rules

Mower deletion cascades to telemetry. Deleting a user leaves their mowers
unassigned rather than deleting physical mower records. Unique indexes protect
user emails and TPM-key fingerprints.

Ownership checks must be made against PostgreSQL before an operation that
changes ownership or exposes historical telemetry.
Valkey accelerates reads but does not replace database authorization.

## Migrations

Alembic records the applied revision in `alembic_version`. The model set has
evolved from the initial users table to mower/telemetry data, duplicate telemetry
support, and mower TPM identities. Cutout uploads are deliberately ephemeral GCS
objects: their recipient list and status are not database state. Generate an inspected
migration for a model change, test it on the disposable integration database,
then apply it; do not rely on `Base.metadata.create_all()` as a replacement for
an audited migration history.
