
import sqlalchemy as sa
from alembic import op

revision = "001_market_history"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # The CLI may already have created this table. Do not drop or overwrite it.
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "market" not in tables:
        op.create_table(
            "market",
            sa.Column("symbol", sa.String(50), primary_key=True),
            sa.Column("price", sa.Text(), nullable=False),
            sa.Column(
                "updated_at", sa.Text(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
            ),
        )
    op.add_column(
        "market", sa.Column("quote_asset", sa.String(10), nullable=False, server_default="")
    )
    op.add_column(
        "market", sa.Column("quote_volume", sa.Text(), nullable=False, server_default="0")
    )
    op.execute("UPDATE market SET quote_asset = 'USDT' WHERE symbol LIKE '%USDT'")
    op.execute("UPDATE market SET quote_asset = 'TMN' WHERE symbol LIKE '%TMN'")
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(50), sa.ForeignKey("market.symbol"), nullable=False),
        sa.Column("price", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.Text(), nullable=False),
    )
    op.create_index("ix_history_symbol_id", "price_history", ["symbol", "id"])
    state = op.create_table(
        "sync_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_success", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_attempt", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lease_until", sa.Float(), nullable=False, server_default="0"),
        sa.Column("token", sa.String(32), nullable=True),
    )
    op.bulk_insert(state, [{"id": 1}])


def downgrade():
    op.drop_table("sync_state")
    op.drop_index("ix_history_symbol_id", table_name="price_history")
    op.drop_table("price_history")
    with op.batch_alter_table("market") as batch:
        batch.drop_column("quote_volume")
        batch.drop_column("quote_asset")
