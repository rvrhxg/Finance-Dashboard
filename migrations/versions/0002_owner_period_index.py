"""Owner and date range index for aggregate reports."""
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_transactions_owner_period', 'transactions', ['user_id', 'occurred_on'])


def downgrade():
    op.drop_index('ix_transactions_owner_period', table_name='transactions')
