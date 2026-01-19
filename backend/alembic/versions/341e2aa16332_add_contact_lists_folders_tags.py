"""add_contact_lists_folders_tags

Revision ID: 341e2aa16332
Revises: e11ed1fd7e41
Create Date: 2026-01-18 18:06:10.922227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '341e2aa16332'
down_revision: Union[str, Sequence[str], None] = 'e11ed1fd7e41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add contact lists, folders, tags, and subscription fields."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    # Create contact_list_folders table
    if 'contact_list_folders' not in tables:
        op.create_table(
            'contact_list_folders',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('color', sa.String(length=7), nullable=True),
            sa.Column('parent_folder_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['parent_folder_id'], ['contact_list_folders.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_contact_list_folders_user_id', 'contact_list_folders', ['user_id'])
        op.create_index('idx_contact_list_folders_parent_folder_id', 'contact_list_folders', ['parent_folder_id'])
    
    # Create contact_lists table
    if 'contact_lists' not in tables:
        op.create_table(
            'contact_lists',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('folder_id', sa.Integer(), nullable=True),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('color', sa.String(length=7), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['folder_id'], ['contact_list_folders.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_contact_lists_user_id', 'contact_lists', ['user_id'])
        op.create_index('idx_contact_lists_folder_id', 'contact_lists', ['folder_id'])
    
    # Create contact_list_memberships junction table
    if 'contact_list_memberships' not in tables:
        op.create_table(
            'contact_list_memberships',
            sa.Column('contact_list_id', sa.Integer(), nullable=False),
            sa.Column('contact_id', sa.Integer(), nullable=False),
            sa.Column('added_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['contact_list_id'], ['contact_lists.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('contact_list_id', 'contact_id')
        )
        op.create_index('idx_contact_list_memberships_contact_id', 'contact_list_memberships', ['contact_id'])
        op.create_index('idx_contact_list_memberships_contact_list_id', 'contact_list_memberships', ['contact_list_id'])
    
    # Add tags column to contacts table
    if 'contacts' in tables:
        columns = [col['name'] for col in inspector.get_columns('contacts')]
        if 'tags' not in columns:
            op.add_column('contacts', sa.Column('tags', sa.JSON(), nullable=True))
    
    # Add contact_list_id to contact_imports table
    if 'contact_imports' in tables:
        columns = [col['name'] for col in inspector.get_columns('contact_imports')]
        if 'contact_list_id' not in columns:
            op.add_column('contact_imports', sa.Column('contact_list_id', sa.Integer(), nullable=True))
            op.create_foreign_key(
                'fk_contact_imports_contact_list_id',
                'contact_imports',
                'contact_lists',
                ['contact_list_id'],
                ['id'],
                ondelete='SET NULL'
            )
            op.create_index('ix_contact_imports_contact_list_id', 'contact_imports', ['contact_list_id'])


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    # Drop contact_list_memberships
    if 'contact_list_memberships' in tables:
        op.drop_index('idx_contact_list_memberships_contact_list_id', table_name='contact_list_memberships')
        op.drop_index('idx_contact_list_memberships_contact_id', table_name='contact_list_memberships')
        op.drop_table('contact_list_memberships')
    
    # Drop contact_lists
    if 'contact_lists' in tables:
        op.drop_index('idx_contact_lists_folder_id', table_name='contact_lists')
        op.drop_index('idx_contact_lists_user_id', table_name='contact_lists')
        op.drop_table('contact_lists')
    
    # Drop contact_list_folders
    if 'contact_list_folders' in tables:
        op.drop_index('idx_contact_list_folders_parent_folder_id', table_name='contact_list_folders')
        op.drop_index('idx_contact_list_folders_user_id', table_name='contact_list_folders')
        op.drop_table('contact_list_folders')
    
    # Remove tags from contacts
    if 'contacts' in tables:
        columns = [col['name'] for col in inspector.get_columns('contacts')]
        if 'tags' in columns:
            op.drop_column('contacts', 'tags')
    
    # Remove contact_list_id from contact_imports
    if 'contact_imports' in tables:
        columns = [col['name'] for col in inspector.get_columns('contact_imports')]
        if 'contact_list_id' in columns:
            op.drop_index('ix_contact_imports_contact_list_id', table_name='contact_imports')
            op.drop_constraint('fk_contact_imports_contact_list_id', 'contact_imports', type_='foreignkey')
            op.drop_column('contact_imports', 'contact_list_id')
