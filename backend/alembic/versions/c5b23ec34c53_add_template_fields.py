"""add_template_fields

Revision ID: c5b23ec34c53
Revises: 88435c4fccd9
Create Date: 2026-01-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'c5b23ec34c53'
down_revision: Union[str, Sequence[str], None] = '25cf8dc8f570'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to add new template fields."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # Check if message_templates table exists
    tables = inspector.get_table_names()
    if 'message_templates' not in tables:
        return
    
    # Get existing columns
    columns = [col['name'] for col in inspector.get_columns('message_templates')]
    
    # Add new template structure fields
    if 'header_type' not in columns:
        op.add_column('message_templates', sa.Column('header_type', sa.String(length=20), nullable=True))
    
    if 'header_content' not in columns:
        op.add_column('message_templates', sa.Column('header_content', sa.Text(), nullable=True))
    
    if 'body_text' not in columns:
        op.add_column('message_templates', sa.Column('body_text', sa.Text(), nullable=True))
    
    if 'footer_text' not in columns:
        op.add_column('message_templates', sa.Column('footer_text', sa.String(length=60), nullable=True))
    
    if 'buttons' not in columns:
        op.add_column('message_templates', sa.Column('buttons', sa.JSON(), nullable=True))
    
    # Add Meta API integration fields
    if 'meta_template_id' not in columns:
        op.add_column('message_templates', sa.Column('meta_template_id', sa.String(length=100), nullable=True))
    
    if 'waba_id' not in columns:
        op.add_column('message_templates', sa.Column('waba_id', sa.String(length=100), nullable=True))
    
    if 'rejection_reason' not in columns:
        op.add_column('message_templates', sa.Column('rejection_reason', sa.Text(), nullable=True))
    
    # Migrate existing data: copy content to body_text if body_text is null
    op.execute(text("""
        UPDATE message_templates 
        SET body_text = content 
        WHERE body_text IS NULL AND content IS NOT NULL
    """))
    
    # Migrate existing data: copy template_id to meta_template_id if meta_template_id is null
    op.execute(text("""
        UPDATE message_templates 
        SET meta_template_id = template_id 
        WHERE meta_template_id IS NULL AND template_id IS NOT NULL
    """))
    
    # Update status values: convert legacy 'active'/'inactive' to new statuses
    op.execute(text("""
        UPDATE message_templates 
        SET status = 'APPROVED' 
        WHERE status = 'active'
    """))
    
    op.execute(text("""
        UPDATE message_templates 
        SET status = 'DISABLED' 
        WHERE status = 'inactive'
    """))
    
    # Create index on waba_id
    try:
        op.create_index('idx_templates_waba_id', 'message_templates', ['waba_id'])
    except Exception:
        pass  # Index might already exist


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    tables = inspector.get_table_names()
    if 'message_templates' not in tables:
        return
    
    columns = [col['name'] for col in inspector.get_columns('message_templates')]
    
    # Drop index
    try:
        op.drop_index('idx_templates_waba_id', table_name='message_templates')
    except Exception:
        pass
    
    # Drop new columns
    if 'rejection_reason' in columns:
        op.drop_column('message_templates', 'rejection_reason')
    
    if 'waba_id' in columns:
        op.drop_column('message_templates', 'waba_id')
    
    if 'meta_template_id' in columns:
        op.drop_column('message_templates', 'meta_template_id')
    
    if 'buttons' in columns:
        op.drop_column('message_templates', 'buttons')
    
    if 'footer_text' in columns:
        op.drop_column('message_templates', 'footer_text')
    
    if 'body_text' in columns:
        op.drop_column('message_templates', 'body_text')
    
    if 'header_content' in columns:
        op.drop_column('message_templates', 'header_content')
    
    if 'header_type' in columns:
        op.drop_column('message_templates', 'header_type')
