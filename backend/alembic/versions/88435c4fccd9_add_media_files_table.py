"""add_media_files_table

Revision ID: 88435c4fccd9
Revises: 341e2aa16332
Create Date: 2026-01-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88435c4fccd9'
down_revision: Union[str, Sequence[str], None] = '341e2aa16332'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add media_files table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    # Create media_files table
    if 'media_files' not in tables:
        op.create_table(
            'media_files',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('blob_name', sa.String(length=512), nullable=False),
            sa.Column('file_size_bytes', sa.Integer(), nullable=False),
            sa.Column('mime_type', sa.String(length=100), nullable=False),
            sa.Column('original_filename', sa.String(length=255), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_media_files_user_id', 'media_files', ['user_id'])
        op.create_index('ix_media_files_blob_name', 'media_files', ['blob_name'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()
    
    # Drop media_files table
    if 'media_files' in tables:
        op.drop_index('ix_media_files_blob_name', table_name='media_files')
        op.drop_index('ix_media_files_user_id', table_name='media_files')
        op.drop_table('media_files')
