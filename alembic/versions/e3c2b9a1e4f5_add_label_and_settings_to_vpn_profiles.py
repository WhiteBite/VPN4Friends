"""Add label and settings columns to vpn_profiles.

This migration is safe for legacy SQLite databases where vpn_profiles exists
without these columns and for new databases where the table is already created
with the full schema.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3c2b9a1e4f5"
down_revision: Union[str, Sequence[str], None] = "08940f47ba4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_vpn_profiles_columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("vpn_profiles"):
        return set()

    return {col["name"] for col in inspector.get_columns("vpn_profiles")}


def upgrade() -> None:
    """Upgrade schema.

    Ensure vpn_profiles has label and settings columns on legacy DBs.
    """

    columns = _get_vpn_profiles_columns()
    if not columns:
        # Table does not exist (e.g. brand new DB where previous migration
        # created it with full schema) or cannot be inspected.
        return

    if "label" not in columns:
        op.add_column(
            "vpn_profiles",
            sa.Column("label", sa.String(length=100), nullable=True),
        )

    if "settings" not in columns:
        op.add_column(
            "vpn_profiles",
            sa.Column("settings", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema.

    Drop label and settings columns if they exist.
    """

    columns = _get_vpn_profiles_columns()
    if not columns:
        return

    if "settings" in columns:
        op.drop_column("vpn_profiles", "settings")
        columns.remove("settings")

    if "label" in columns:
        op.drop_column("vpn_profiles", "label")
