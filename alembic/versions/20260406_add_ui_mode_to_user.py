"""Add ui_mode to users

Revision ID: 20260406_ui_mode
Revises: 2c92690c1613
Create Date: 2026-04-06 03:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260406_ui_mode"
down_revision: str | Sequence[str] | None = "20260330abcd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("users")]

    if "ui_mode" not in columns:
        # For SQLite, we define the enum as a string column with a server default
        op.add_column(
            "users",
            sa.Column(
                "ui_mode",
                sa.Enum("NONE", "BOT", "MINIAPP", name="uimode"),
                nullable=False,
                server_default="NONE",
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "ui_mode")
