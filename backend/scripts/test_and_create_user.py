"""Script to test API and create a user if none exists."""

import asyncio
import sys
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_context
from app.models import User
from app.services.auth import create_user as create_user_service
from app.schemas import UserCreate


async def check_and_create_user():
    """Check if users exist, create one if not."""
    async with get_db_context() as db:
        try:
            # Check if any users exist
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            if users:
                print(f"[OK] Found {len(users)} user(s) in database:")
                for user in users:
                    print(f"  - ID: {user.id}, Email: {user.email}, Username: {user.username}, Admin: {user.is_superuser}")
            else:
                print("[INFO] No users found in database. Creating a default admin user...")
                
                # Create default admin user
                user_data = UserCreate(
                    email="admin@example.com",
                    username="admin",
                    password="admin123",
                    full_name="Admin User",
                )
                
                new_user = await create_user_service(db, user_data)
                
                # Make the user a superuser
                new_user.is_superuser = True
                await db.commit()
                
                print(f"[OK] Created admin user:")
                print(f"  - ID: {new_user.id}")
                print(f"  - Email: {new_user.email}")
                print(f"  - Username: {new_user.username}")
                print(f"  - Admin: {new_user.is_superuser}")
                print(f"\nLogin credentials:")
                print(f"  Email: {new_user.email}")
                print(f"  Password: admin123")
                
        except Exception as e:
            print(f"[ERROR] Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("Testing API User Management...")
    print("=" * 50)
    asyncio.run(check_and_create_user())
    print("=" * 50)
