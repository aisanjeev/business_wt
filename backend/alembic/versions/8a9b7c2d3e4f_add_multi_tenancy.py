"""add_multi_tenancy

Revision ID: 8a9b7c2d3e4f
Revises: 657d415d6df6
Create Date: 2025-01-18 10:51:46.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '8a9b7c2d3e4f'
down_revision: Union[str, Sequence[str], None] = '657d415d6df6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add multi-tenancy support."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if columns exist before adding
    contacts_columns = [col['name'] for col in inspector.get_columns('contacts')]
    conversations_columns = [col['name'] for col in inspector.get_columns('conversations')]
    message_templates_columns = [col['name'] for col in inspector.get_columns('message_templates')]
    
    # Add user_id to contacts table (if not exists)
    if 'user_id' not in contacts_columns:
        op.add_column('contacts', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Create foreign key and indexes (if not exists)
    fk_names = [fk['name'] for fk in inspector.get_foreign_keys('contacts')]
    if 'fk_contacts_user_id' not in fk_names:
        op.create_foreign_key(
            'fk_contacts_user_id',
            'contacts',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )
    
    # Create indexes (if not exists)
    index_names = [idx['name'] for idx in inspector.get_indexes('contacts')]
    if 'ix_contacts_user_id' not in index_names:
        op.create_index('ix_contacts_user_id', 'contacts', ['user_id'])
    if 'idx_contacts_user_phone' not in index_names:
        op.create_index('idx_contacts_user_phone', 'contacts', ['user_id', 'phone_number'], unique=True)
    
    # Remove old unique constraint on phone_number (if exists)
    # Try to drop index if it exists (MySQL unique constraints are indexes)
    try:
        op.execute(sa.text("DROP INDEX `ix_contacts_phone_number` ON `contacts`"))
    except Exception:
        # Index doesn't exist, try constraint name
        try:
            op.execute(sa.text("DROP INDEX `contacts_phone_number_key` ON `contacts`"))
        except Exception:
            # Neither exists, skip
            pass
    
    # Try to drop constraint by name if it exists
    try:
        op.drop_constraint('contacts_phone_number_key', 'contacts', type_='unique')
    except Exception:
        # Constraint doesn't exist, skip
        pass
    
    # Add user_id to conversations table (if not exists)
    if 'user_id' not in conversations_columns:
        op.add_column('conversations', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Create foreign key (if not exists)
    conv_fk_names = [fk['name'] for fk in inspector.get_foreign_keys('conversations')]
    if 'fk_conversations_user_id' not in conv_fk_names:
        op.create_foreign_key(
            'fk_conversations_user_id',
            'conversations',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )
    
    # Create index (if not exists)
    conv_index_names = [idx['name'] for idx in inspector.get_indexes('conversations')]
    if 'ix_conversations_user_id' not in conv_index_names:
        op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    
    # Remove unique constraint on thread_id (now scoped by user) - if exists
    try:
        op.drop_index('ix_conversations_thread_id', table_name='conversations')
    except Exception:
        pass
    try:
        op.drop_constraint('conversations_thread_id_key', 'conversations', type_='unique')
    except Exception:
        pass
    
    # Add user_id to message_templates table (if not exists)
    if 'user_id' not in message_templates_columns:
        op.add_column('message_templates', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_message_templates_user_id',
        'message_templates',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create index (if not exists)
    template_index_names = [idx['name'] for idx in inspector.get_indexes('message_templates')]
    if 'ix_message_templates_user_id' not in template_index_names:
        op.create_index('ix_message_templates_user_id', 'message_templates', ['user_id'])
    
    # Create meta_account_connections table (if not exists)
    tables = inspector.get_table_names()
    if 'meta_account_connections' not in tables:
        op.create_table(
        'meta_account_connections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('meta_business_account_id', sa.String(length=100), nullable=False),
        sa.Column('phone_number_id', sa.String(length=100), nullable=False),
        sa.Column('business_phone_number', sa.String(length=20), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending_verification'),
        sa.Column('business_verification_status', sa.String(length=20), nullable=False, server_default='unverified'),
        sa.Column('webhook_url', sa.String(length=512), nullable=True),
        sa.Column('usage_tracking_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('connected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
        # Create indexes for meta_account_connections
        op.create_index('ix_meta_account_connections_user_id', 'meta_account_connections', ['user_id'], unique=True)
        op.create_index('ix_meta_account_connections_phone_number_id', 'meta_account_connections', ['phone_number_id'])
        op.create_index('idx_meta_connections_status', 'meta_account_connections', ['status'])
    
    # Create api_usage table (if not exists)
    if 'api_usage' not in tables:
        op.create_table(
            'api_usage',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('meta_phone_number_id', sa.String(length=100), nullable=True),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('api_endpoint', sa.String(length=255), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=False),
        sa.Column('estimated_cost', sa.String(length=20), nullable=True),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        # Create indexes for api_usage
        op.create_index('ix_api_usage_user_id', 'api_usage', ['user_id'])
        op.create_index('ix_api_usage_meta_phone_number_id', 'api_usage', ['meta_phone_number_id'])
        op.create_index('ix_api_usage_request_id', 'api_usage', ['request_id'])
        op.create_index('ix_api_usage_timestamp', 'api_usage', ['timestamp'])
        op.create_index('idx_api_usage_user_timestamp', 'api_usage', ['user_id', 'timestamp'])
    
    # Create contact_imports table (if not exists)
    if 'contact_imports' not in tables:
        op.create_table(
            'contact_imports',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_format', sa.String(length=10), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_log', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        # Create indexes for contact_imports
        op.create_index('ix_contact_imports_user_id', 'contact_imports', ['user_id'])
        op.create_index('idx_contact_imports_status', 'contact_imports', ['status'])
        op.create_index('idx_contact_imports_created_at', 'contact_imports', ['created_at'])
    
    # Create bulk_message_campaigns table (if not exists)
    if 'bulk_message_campaigns' not in tables:
        op.create_table(
            'bulk_message_campaigns',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('target_contacts', sa.JSON(), nullable=True),
        sa.Column('message_content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('total_recipients', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['message_templates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        # Create indexes for bulk_message_campaigns
        op.create_index('ix_bulk_message_campaigns_user_id', 'bulk_message_campaigns', ['user_id'])
        op.create_index('idx_campaigns_status', 'bulk_message_campaigns', ['status'])
        op.create_index('idx_campaigns_created_at', 'bulk_message_campaigns', ['created_at'])
    
    # Migrate existing data: assign all existing records to a default user (if any users exist)
    # This is a data migration - in production, you'd want to handle this more carefully
    # Note: For SQLite, we'll need to handle this differently
    # For now, we'll make user_id nullable first, migrate data, then make it NOT NULL
    
    # For MySQL/PostgreSQL, we can query and update
    # For SQLite, this is simpler - just use a default value
    try:
        conn = op.get_bind()
        if hasattr(conn, 'execute'):  # SQLAlchemy 2.0+
            result = conn.execute(sa.text("SELECT id FROM users LIMIT 1"))
            first_user = result.fetchone()
        else:  # SQLAlchemy 1.x
            result = conn.execute("SELECT id FROM users LIMIT 1")
            first_user = result.fetchone()
        
        if first_user:
            default_user_id = first_user[0] if isinstance(first_user, tuple) else first_user[0]
            # Update existing records with default user
            op.execute(sa.text(f"UPDATE contacts SET user_id = {default_user_id} WHERE user_id IS NULL"))
            op.execute(sa.text(f"UPDATE conversations SET user_id = {default_user_id} WHERE user_id IS NULL"))
            op.execute(sa.text(f"UPDATE message_templates SET user_id = {default_user_id} WHERE user_id IS NULL"))
    except Exception:
        # If migration fails, user_id will remain nullable - admin can fix manually
        pass
    
    # Now make user_id NOT NULL after data migration (if possible)
    # Note: SQLite may not support altering nullable columns - may need to recreate table
    try:
        op.alter_column('contacts', 'user_id', nullable=False)
        op.alter_column('conversations', 'user_id', nullable=False)
        op.alter_column('message_templates', 'user_id', nullable=False)
    except Exception:
        # If altering fails (e.g., SQLite), the columns will remain nullable
        # This can be fixed in a later migration or manually
        pass


def downgrade() -> None:
    """Downgrade schema - remove multi-tenancy support."""
    # Drop new tables
    op.drop_table('bulk_message_campaigns')
    op.drop_table('contact_imports')
    op.drop_table('api_usage')
    op.drop_table('meta_account_connections')
    
    # Remove user_id from message_templates
    op.drop_index('ix_message_templates_user_id', table_name='message_templates')
    op.drop_constraint('fk_message_templates_user_id', 'message_templates', type_='foreignkey')
    op.drop_column('message_templates', 'user_id')
    
    # Remove user_id from conversations
    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_constraint('fk_conversations_user_id', 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'user_id')
    # Restore unique constraint on thread_id
    op.create_index('ix_conversations_thread_id', 'conversations', ['thread_id'], unique=True)
    
    # Remove user_id from contacts
    op.drop_index('idx_contacts_user_phone', table_name='contacts')
    op.drop_index('ix_contacts_user_id', table_name='contacts')
    op.drop_constraint('fk_contacts_user_id', 'contacts', type_='foreignkey')
    op.drop_column('contacts', 'user_id')
    # Restore unique constraint on phone_number
    op.create_unique_constraint('contacts_phone_number_key', 'contacts', ['phone_number'])
    op.create_index('ix_contacts_phone_number', 'contacts', ['phone_number'])
