"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_portfolios_owner_id", "portfolios", ["owner_id"])

    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "portfolio_id",
            sa.Integer(),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("avg_cost", sa.Numeric(20, 8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("portfolio_id", "symbol", name="uq_position_portfolio_symbol"),
    )
    op.create_index("ix_positions_portfolio_id", "positions", ["portfolio_id"])
    op.create_index("ix_positions_symbol", "positions", ["symbol"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("close_price", sa.Numeric(20, 8), nullable=False),
        sa.UniqueConstraint("symbol", "price_date", name="uq_price_symbol_date"),
    )
    op.create_index(
        "ix_price_history_symbol_date", "price_history", ["symbol", "price_date"]
    )


def downgrade() -> None:
    op.drop_table("price_history")
    op.drop_table("positions")
    op.drop_table("portfolios")
    op.drop_table("users")
