"""add protocol and location to vpn_requests

Revision ID: eaa828d8e9f2
Revises: 20260406_ui_mode
Create Date: 2026-04-06 11:33:58.014279

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eaa828d8e9f2"
down_revision: str | Sequence[str] | None = "20260406_ui_mode"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("vpn_requests", sa.Column("protocol", sa.String(length=50), nullable=True))
    op.add_column("vpn_requests", sa.Column("location", sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("vpn_requests", "location")
    op.drop_column("vpn_requests", "protocol")
