"""add_contact_source

Revision ID: 15106ca0c6fa
Revises: a1b2c3d4e5f6
Create Date: 2026-01-18 17:39:39.897185

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15106ca0c6fa'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add source field to contacts."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if contacts table exists
    tables = inspector.get_table_names()
    if 'contacts' not in tables:
        return
    
    # Check if source column already exists
    columns = [col['name'] for col in inspector.get_columns('contacts')]
    if 'source' in columns:
        return
    
    # Add source column with default value
    op.add_column('contacts', sa.Column('source', sa.String(length=20), server_default='manual', nullable=False))
    
    # Create index on source column
    op.create_index('ix_contacts_source', 'contacts', ['source'])


def downgrade() -> None:
    """Downgrade schema to remove source field."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if contacts table exists
    tables = inspector.get_table_names()
    if 'contacts' not in tables:
        return
    
    # Check if source column exists
    columns = [col['name'] for col in inspector.get_columns('contacts')]
    if 'source' not in columns:
        return
    
    # Drop index
    try:
        op.drop_index('ix_contacts_source', table_name='contacts')
    except Exception:
        pass
    
    # Drop column
    op.drop_column('contacts', 'source')
