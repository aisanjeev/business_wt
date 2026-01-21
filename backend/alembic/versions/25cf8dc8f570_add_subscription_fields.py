"""add_subscription_fields

Revision ID: 25cf8dc8f570
Revises: 341e2aa16332
Create Date: 2026-01-18 18:06:38.130644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25cf8dc8f570'
down_revision: Union[str, Sequence[str], None] = '341e2aa16332'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add subscription fields to users table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'users' not in tables:
        return
    
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add subscription_tier
    if 'subscription_tier' not in columns:
        op.add_column('users', sa.Column('subscription_tier', sa.String(length=20), server_default='free', nullable=False))
        op.create_index('ix_users_subscription_tier', 'users', ['subscription_tier'])
    
    # Add subscription_status
    if 'subscription_status' not in columns:
        op.add_column('users', sa.Column('subscription_status', sa.String(length=20), server_default='active', nullable=False))
    
    # Add subscription_expires_at
    if 'subscription_expires_at' not in columns:
        op.add_column('users', sa.Column('subscription_expires_at', sa.DateTime(), nullable=True))
    
    # Add max_contacts
    if 'max_contacts' not in columns:
        op.add_column('users', sa.Column('max_contacts', sa.Integer(), nullable=True))
    
    # Add max_messages_per_month
    if 'max_messages_per_month' not in columns:
        op.add_column('users', sa.Column('max_messages_per_month', sa.Integer(), nullable=True))
    
    # Add max_campaigns_per_month
    if 'max_campaigns_per_month' not in columns:
        op.add_column('users', sa.Column('max_campaigns_per_month', sa.Integer(), nullable=True))
    
    # Add max_lists
    if 'max_lists' not in columns:
        op.add_column('users', sa.Column('max_lists', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema to remove subscription fields."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    if 'users' not in tables:
        return
    
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Remove subscription fields
    if 'max_lists' in columns:
        op.drop_column('users', 'max_lists')
    if 'max_campaigns_per_month' in columns:
        op.drop_column('users', 'max_campaigns_per_month')
    if 'max_messages_per_month' in columns:
        op.drop_column('users', 'max_messages_per_month')
    if 'max_contacts' in columns:
        op.drop_column('users', 'max_contacts')
    if 'subscription_expires_at' in columns:
        op.drop_column('users', 'subscription_expires_at')
    if 'subscription_status' in columns:
        op.drop_column('users', 'subscription_status')
    if 'subscription_tier' in columns:
        op.drop_index('ix_users_subscription_tier', table_name='users')
        op.drop_column('users', 'subscription_tier')
