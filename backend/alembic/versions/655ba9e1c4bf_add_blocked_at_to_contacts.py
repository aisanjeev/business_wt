"""add_blocked_at_to_contacts

Revision ID: 655ba9e1c4bf
Revises: a03c9de863e1
Create Date: 2026-01-19 20:12:46.046875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '655ba9e1c4bf'
down_revision: Union[str, Sequence[str], None] = 'a03c9de863e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add blocked_at column to contacts table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'contacts' not in tables:
        return
    
    with op.batch_alter_table('contacts') as batch_op:
        batch_op.add_column(sa.Column('blocked_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove blocked_at column from contacts table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'contacts' not in tables:
        return
    
    with op.batch_alter_table('contacts') as batch_op:
        batch_op.drop_column('blocked_at')
