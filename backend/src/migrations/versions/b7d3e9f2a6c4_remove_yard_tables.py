"""Remove the obsolete persistent yard image and coordinate tables.

Revision ID: b7d3e9f2a6c4
Revises: a4c2b8d9e6f1
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d3e9f2a6c4"
down_revision: Union[str, Sequence[str], None] = "a4c2b8d9e6f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_yard_coordinates_yard_id", table_name="yard_coordinates")
    op.drop_table("yard_coordinates")
    op.drop_index("ix_yards_mower_id", table_name="yards")
    op.drop_table("yards")


def downgrade() -> None:
    op.create_table(
        "yards",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("mower_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("high_fidelity_img_url", sa.String(length=512), nullable=False),
        sa.Column("panoramic_img_url", sa.String(length=512), nullable=True),
        sa.Column("meters_per_pixel", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["mower_id"], ["mowers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_yards_mower_id", "yards", ["mower_id"])
    op.create_table(
        "yard_coordinates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("yard_id", sa.UUID(), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("pixel_x", sa.Integer(), nullable=True),
        sa.Column("pixel_y", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["yard_id"], ["yards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_yard_coordinates_yard_id", "yard_coordinates", ["yard_id"])
