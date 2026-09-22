"""Use the mower UUID and one TPM identity record on the mower itself.

Revision ID: c8e5f7a1d2b4
Revises: b7d3e9f2a6c4
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c8e5f7a1d2b4"
down_revision = "b7d3e9f2a6c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicate_active_identity = bind.execute(
        sa.text(
            """
            SELECT mower_id
            FROM mower_device_identities
            WHERE status = 'active'
            GROUP BY mower_id
            HAVING count(*) > 1
            """
        )
    ).scalar_one_or_none()
    if duplicate_active_identity is not None:
        raise RuntimeError(
            "cannot migrate multiple active TPM identities for mower "
            f"{duplicate_active_identity}"
        )

    op.add_column(
        "mowers",
        sa.Column(
            "lifecycle_status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "mowers", sa.Column("device_public_key_pem", sa.Text(), nullable=True)
    )
    op.add_column(
        "mowers",
        sa.Column("device_key_fingerprint", sa.String(length=128), nullable=True),
    )
    op.create_check_constraint(
        "ck_mowers_lifecycle_status",
        "mowers",
        "lifecycle_status IN ('active', 'decommissioned')",
    )
    op.create_index("ix_mowers_lifecycle_status", "mowers", ["lifecycle_status"])
    op.create_unique_constraint(
        "uq_mowers_device_key_fingerprint", "mowers", ["device_key_fingerprint"]
    )

    # Retain the one active key used for renewal. Revoked historical keys are
    # intentionally discarded with the history table.
    op.execute(
        """
        UPDATE mowers AS mower
        SET
            device_public_key_pem = identity.public_key_pem,
            device_key_fingerprint = identity.fingerprint
        FROM mower_device_identities AS identity
        WHERE identity.mower_id = mower.id AND identity.status = 'active'
        """
    )

    op.drop_index(
        "ix_mower_device_identities_status", table_name="mower_device_identities"
    )
    op.drop_index(
        "ix_mower_device_identities_mower_id", table_name="mower_device_identities"
    )
    op.drop_table("mower_device_identities")
    op.drop_index("ix_mowers_serial_number", table_name="mowers")
    op.drop_column("mowers", "serial_number")


def downgrade() -> None:
    op.add_column(
        "mowers", sa.Column("serial_number", sa.String(length=100), nullable=True)
    )
    op.execute("UPDATE mowers SET serial_number = id::text")
    op.alter_column("mowers", "serial_number", nullable=False)
    op.create_index("ix_mowers_serial_number", "mowers", ["serial_number"], unique=True)

    op.create_table(
        "mower_device_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_key_pem", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("algorithm", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["mower_id"], ["mowers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )
    op.create_index(
        "ix_mower_device_identities_mower_id", "mower_device_identities", ["mower_id"]
    )
    op.create_index(
        "ix_mower_device_identities_status", "mower_device_identities", ["status"]
    )
    op.execute(
        """
        INSERT INTO mower_device_identities (
            id, mower_id, public_key_pem, fingerprint, algorithm, status, created_at
        )
        SELECT id, id, device_public_key_pem, device_key_fingerprint,
               'ECDSA_P256_SHA256', 'active', now()
        FROM mowers
        WHERE device_public_key_pem IS NOT NULL
        """
    )

    op.drop_constraint("uq_mowers_device_key_fingerprint", "mowers", type_="unique")
    op.drop_index("ix_mowers_lifecycle_status", table_name="mowers")
    op.drop_constraint("ck_mowers_lifecycle_status", "mowers", type_="check")
    op.drop_column("mowers", "device_key_fingerprint")
    op.drop_column("mowers", "device_public_key_pem")
    op.drop_column("mowers", "lifecycle_status")
