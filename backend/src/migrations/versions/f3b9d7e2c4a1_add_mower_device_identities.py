"""Add registered mower TPM device-root public identities.

Revision ID: f3b9d7e2c4a1
Revises: e1f4c7a9b2d3
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f3b9d7e2c4a1"
down_revision = "e1f4c7a9b2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index(
        "ix_mower_device_identities_status", table_name="mower_device_identities"
    )
    op.drop_index(
        "ix_mower_device_identities_mower_id", table_name="mower_device_identities"
    )
    op.drop_table("mower_device_identities")
