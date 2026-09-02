"""Remove image URLs from telemetry records.

Revision ID: d6c83c7f31a2
Revises: c45f8a1b2d90
Create Date: 2026-09-02
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d6c83c7f31a2"
down_revision = "c45f8a1b2d90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("mower_telemetry", "rgb_image_url")
    op.drop_column("mower_telemetry", "lidar_image_url")


def downgrade() -> None:
    op.add_column(
        "mower_telemetry",
        sa.Column("rgb_image_url", sa.String(512), nullable=True),
    )
    op.add_column(
        "mower_telemetry",
        sa.Column("lidar_image_url", sa.String(512), nullable=True),
    )
