# PostgreSQL models and relationships

**Database schema source of truth:** the ordered Alembic migrations in
[`backend/src/migrations/versions/`](../../backend/src/migrations/versions/).
SQLAlchemy models in `src/models/` express the runtime mapping; make a migration
for every persistent schema change and apply it with `uv run alembic upgrade head`.

## Core ownership model

```text
users 1 ──< mowers 1 ──< mower_telemetry 1 ── 0..1 mower_imu_data
                  └──< mower_device_identities
users 1 ──< cutouts 1 ──< cutout_mower_assignments >── 1 mowers
mowers 1 ──< yards 1 ──< yard_coordinates
```

| Table                      | Primary contents                                                       | Relationships                                                                                                                       |
| -------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `users`                    | Firebase user ID, unique email, display name, creation time            | One user may own many mowers and cutouts.                                                                                           |
| `mowers`                   | UUID, unique serial number, nickname, optional owner, creation time    | An unassigned mower has a null owner. Removing a user sets `owner_id` to null.                                                      |
| `mower_device_identities`  | TPM public key PEM, SHA-256 fingerprint, algorithm, status, timestamps | Each record belongs to a mower. Active identities support TPM-authorized certificate renewal; the private key remains on the mower. |
| `mower_telemetry`          | Timestamped location, battery, motor data, and safety flag             | Many records belong to one mower. Multiple records with the same mower/timestamp are allowed.                                       |
| `mower_imu_data`           | Accelerometer, gyro, and magnetometer measurements                     | A one-to-one extension of a telemetry row, enforced by a unique `telemetry_id`.                                                     |
| `cutouts`                  | GCS object key, content type, status, owner, creation time             | A boundary image is `pending`, `ready`, or `failed`; it has one or more mower assignments.                                          |
| `cutout_mower_assignments` | Composite cutout/mower key                                             | Many-to-many association between a cutout and its intended mowers. The mower uses only its latest `ready` assignment.               |
| `yards`                    | Mower-linked image assets and calibration data                         | Legacy/current yard-mapping model with ordered perimeter coordinates.                                                               |
| `yard_coordinates`         | Sequence index, geographic coordinate, optional image pixel coordinate | Many ordered coordinates belong to one yard.                                                                                        |

## Deletion and integrity rules

Mower deletion cascades to telemetry, TPM identities, cutout assignments, and
yard data. Cutout deletion cascades to its assignments. Deleting a user removes
that user's cutouts and leaves their mowers unassigned rather than deleting
physical mower records. Unique indexes protect user emails, mower serial
numbers, cutout object keys, and TPM-key fingerprints.

Ownership checks must be made against PostgreSQL before an operation that
changes ownership, exposes historical telemetry, or creates a cutout assignment.
Valkey accelerates reads but does not replace database authorization.

## Migrations

Alembic records the applied revision in `alembic_version`. The model set has
evolved from the initial users table to mower/telemetry/yard data, duplicate
telemetry support, cutouts, and mower TPM identities. Generate an inspected
migration for a model change, test it on the disposable integration database,
then apply it; do not rely on `Base.metadata.create_all()` as a replacement for
an audited migration history.
