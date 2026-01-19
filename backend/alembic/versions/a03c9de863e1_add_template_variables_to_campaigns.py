"""add_template_variables_to_campaigns

Revision ID: a03c9de863e1
Revises: c5b23ec34c53
Create Date: 2026-01-19 19:58:54.139261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a03c9de863e1'
down_revision: Union[str, Sequence[str], None] = 'c5b23ec34c53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add template_variables column to bulk_message_campaigns table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'bulk_message_campaigns' not in tables:
        return
    
    with op.batch_alter_table('bulk_message_campaigns') as batch_op:
        batch_op.add_column(sa.Column('template_variables', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove template_variables column from bulk_message_campaigns table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'bulk_message_campaigns' not in tables:
        return
    
    with op.batch_alter_table('bulk_message_campaigns') as batch_op:
        batch_op.drop_column('template_variables')
