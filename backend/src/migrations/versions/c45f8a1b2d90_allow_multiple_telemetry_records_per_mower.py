"""Allow a mower to retain multiple telemetry records.

Revision ID: c45f8a1b2d90
Revises: a8acdc13d4e9
Create Date: 2026-08-15
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c45f8a1b2d90"
down_revision = "a8acdc13d4e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_mower_telemetry_mower_id", table_name="mower_telemetry")
    op.create_index(
        "ix_mower_telemetry_mower_id",
        "mower_telemetry",
        ["mower_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mower_telemetry_mower_id", table_name="mower_telemetry")
    op.create_index(
        "ix_mower_telemetry_mower_id",
        "mower_telemetry",
        ["mower_id"],
        unique=True,
    )
