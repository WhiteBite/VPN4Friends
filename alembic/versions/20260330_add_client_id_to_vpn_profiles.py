"""Add client_id to vpn_profiles.

Revision ID: 20260330abcd
Revises: 2c92690c1613
Create Date: 2026-03-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260330abcd"
down_revision: str | None = "08940f47ba4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _get_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Add client_id column to vpn_profiles table."""
    columns = _get_columns("vpn_profiles")
    if not columns:
        return

    if "client_id" not in columns:
        op.add_column("vpn_profiles", sa.Column("client_id", sa.String(length=50), nullable=True))
        # Create index separately for client_id
        op.create_index("ix_vpn_profiles_client_id", "vpn_profiles", ["client_id"], unique=False)


def downgrade() -> None:
    """Remove client_id column from vpn_profiles table."""
    columns = _get_columns("vpn_profiles")
    if "client_id" in columns:
        op.drop_index("ix_vpn_profiles_client_id", table_name="vpn_profiles")
        op.drop_column("vpn_profiles", "client_id")
