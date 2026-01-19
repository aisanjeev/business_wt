"""add_campaign_recipient_logs

Revision ID: a1b2c3d4e5f6
Revises: 8a9b7c2d3e4f
Create Date: 2025-01-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '8a9b7c2d3e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add campaign_recipient_logs table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    # Create table only if it doesn't exist
    if 'campaign_recipient_logs' not in tables:
        op.create_table(
            'campaign_recipient_logs',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('cost', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['bulk_message_campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        # Create indexes for new table (they don't exist yet)
        op.create_index('ix_campaign_recipient_logs_campaign_id', 'campaign_recipient_logs', ['campaign_id'])
        op.create_index('ix_campaign_recipient_logs_contact_id', 'campaign_recipient_logs', ['contact_id'])
        op.create_index('ix_campaign_recipient_logs_message_id', 'campaign_recipient_logs', ['message_id'])
        op.create_index('ix_campaign_recipient_logs_phone_number', 'campaign_recipient_logs', ['phone_number'])
        op.create_index('ix_campaign_recipient_logs_status', 'campaign_recipient_logs', ['status'])
        op.create_index('ix_campaign_recipient_logs_created_at', 'campaign_recipient_logs', ['created_at'])
        op.create_index('idx_campaign_logs_campaign_status', 'campaign_recipient_logs', ['campaign_id', 'status'])
    
    # If table exists, ensure indexes exist
    else:
        index_names = [idx['name'] for idx in inspector.get_indexes('campaign_recipient_logs')]
        
        if 'ix_campaign_recipient_logs_campaign_id' not in index_names:
            op.create_index('ix_campaign_recipient_logs_campaign_id', 'campaign_recipient_logs', ['campaign_id'])
        if 'ix_campaign_recipient_logs_contact_id' not in index_names:
            op.create_index('ix_campaign_recipient_logs_contact_id', 'campaign_recipient_logs', ['contact_id'])
        if 'ix_campaign_recipient_logs_message_id' not in index_names:
            op.create_index('ix_campaign_recipient_logs_message_id', 'campaign_recipient_logs', ['message_id'])
        if 'ix_campaign_recipient_logs_phone_number' not in index_names:
            op.create_index('ix_campaign_recipient_logs_phone_number', 'campaign_recipient_logs', ['phone_number'])
        if 'ix_campaign_recipient_logs_status' not in index_names:
            op.create_index('ix_campaign_recipient_logs_status', 'campaign_recipient_logs', ['status'])
        if 'ix_campaign_recipient_logs_created_at' not in index_names:
            op.create_index('ix_campaign_recipient_logs_created_at', 'campaign_recipient_logs', ['created_at'])
        if 'idx_campaign_logs_campaign_status' not in index_names:
            op.create_index('idx_campaign_logs_campaign_status', 'campaign_recipient_logs', ['campaign_id', 'status'])


def downgrade() -> None:
    """Downgrade schema to remove campaign_recipient_logs table."""
    op.drop_index('idx_campaign_logs_campaign_status', table_name='campaign_recipient_logs')
    op.drop_index('ix_campaign_recipient_logs_created_at', table_name='campaign_recipient_logs')
    op.drop_index('ix_campaign_recipient_logs_status', table_name='campaign_recipient_logs')
    op.drop_index('ix_campaign_recipient_logs_phone_number', table_name='campaign_recipient_logs')
    op.drop_index('ix_campaign_recipient_logs_message_id', table_name='campaign_recipient_logs')
    op.drop_index('ix_campaign_recipient_logs_contact_id', table_name='campaign_recipient_logs')
    op.drop_index('ix_campaign_recipient_logs_campaign_id', table_name='campaign_recipient_logs')
    op.drop_table('campaign_recipient_logs')
