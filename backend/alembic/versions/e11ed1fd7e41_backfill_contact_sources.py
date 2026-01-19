"""backfill_contact_sources

Revision ID: e11ed1fd7e41
Revises: 15106ca0c6fa
Create Date: 2026-01-18 17:40:06.307781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e11ed1fd7e41'
down_revision: Union[str, Sequence[str], None] = '15106ca0c6fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill source field for existing contacts."""
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
    
    # Check if contact_imports table exists
    has_imports_table = 'contact_imports' in tables
    
    # Check if conversations table exists
    has_conversations_table = 'conversations' in tables
    
    # Backfill logic:
    # 1. Contacts that were imported (have associated ContactImport records) -> "imported"
    # 2. Contacts with conversations -> "chat"
    # 3. Others -> "manual"
    
    # First, mark imported contacts
    if has_imports_table:
        # This is a simplified approach - in reality, we'd need to track which contacts
        # came from which import. For now, we'll use a heuristic: contacts created around
        # the same time as imports might be imported. But the safest is to mark all
        # contacts with conversations as "chat" first, then mark others as "manual"
        # and let the import logic handle new imports going forward.
        pass
    
    # Mark contacts with conversations as "chat"
    if has_conversations_table:
        op.execute(sa.text("""
            UPDATE contacts c
            SET c.source = 'chat'
            WHERE EXISTS (
                SELECT 1 FROM conversations conv
                WHERE conv.contact_id = c.id
            )
            AND c.source = 'manual'
        """))
    
    # All remaining contacts stay as "manual" (default)


def downgrade() -> None:
    """No downgrade needed for data backfill."""
    pass
