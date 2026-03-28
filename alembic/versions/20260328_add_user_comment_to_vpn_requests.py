"""Add user_comment to vpn_requests

Revision ID: 20260328ef12
Revises: 20260326abcd
Create Date: 2026-03-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260328ef12"
down_revision: str | None = "20260326abcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add user_comment column to vpn_requests."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("vpn_requests")]

    if "user_comment" not in columns:
        op.add_column(
            "vpn_requests", sa.Column("user_comment", sa.String(length=500), nullable=True)
        )


def downgrade() -> None:
    """Remove user_comment column from vpn_requests."""
    op.drop_column("vpn_requests", "user_comment")
