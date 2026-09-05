"""Add GCS boundary cutout state and mower assignments.

Revision ID: e1f4c7a9b2d3
Revises: d6c83c7f31a2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f4c7a9b2d3"
down_revision: Union[str, Sequence[str], None] = "d6c83c7f31a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cutouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_cutouts_owner_id", "cutouts", ["owner_id"])
    op.create_index("ix_cutouts_status", "cutouts", ["status"])
    op.create_table(
        "cutout_mower_assignments",
        sa.Column("cutout_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mower_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["cutout_id"], ["cutouts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mower_id"], ["mowers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("cutout_id", "mower_id"),
    )
    op.create_index(
        "ix_cutout_mower_assignments_mower_id",
        "cutout_mower_assignments",
        ["mower_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cutout_mower_assignments_mower_id", table_name="cutout_mower_assignments")
    op.drop_table("cutout_mower_assignments")
    op.drop_index("ix_cutouts_status", table_name="cutouts")
    op.drop_index("ix_cutouts_owner_id", table_name="cutouts")
    op.drop_table("cutouts")
