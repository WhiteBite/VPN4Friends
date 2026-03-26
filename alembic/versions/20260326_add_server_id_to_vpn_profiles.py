"""Add server_id to vpn_profiles

Revision ID: 20260326abcd
Revises: e3c2b9a1e4f5
Create Date: 2026-03-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260326abcd"
down_revision: Union[str, None] = "e3c2b9a1e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add server_id column to vpn_profiles if not exists."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Check if column already exists
    columns = [col["name"] for col in inspector.get_columns("vpn_profiles")]

    if "server_id" not in columns:
        op.add_column("vpn_profiles", sa.Column("server_id", sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Remove server_id column from vpn_profiles."""
    op.drop_column("vpn_profiles", "server_id")
