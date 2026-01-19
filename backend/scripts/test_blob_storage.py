"""Script to test Azure Blob Storage connection and functionality."""

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

from app.config import settings
from app.database import get_db_context
from app.models import User
from app.services.blob_storage import blob_storage


async def test_blob_storage():
    """Test Azure Blob Storage functionality."""
    print("Testing Azure Blob Storage...")
    print("=" * 60)
    
    # Check configuration
    print("\n1. Checking Configuration...")
    has_connection_string = bool(settings.azure_storage_connection_string)
    print(f"   Connection String: {'✓ Set' if has_connection_string else '✗ Not Set'}")
    print(f"   Container Name: {settings.azure_storage_container_name}")
    
    if not has_connection_string:
        print("\n❌ Azure storage connection string not configured!")
        print("   Set AZURE_STORAGE_CONNECTION_STRING in .env file")
        print("=" * 60)
        return False
    
    # Test connection
    print("\n2. Testing Connection...")
    try:
        blob_service_client = blob_storage._get_blob_service_client()
        print("   ✓ Blob service client created successfully")
        
        container_client = blob_storage._get_container_client()
        print(f"   ✓ Container '{settings.azure_storage_container_name}' accessible")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False
    
    # Get a test user
    print("\n3. Getting Test User...")
    try:
        async with get_db_context() as db:
            result = await db.execute(select(User).limit(1))
            test_user = result.scalar_one_or_none()
            
            if not test_user:
                print("   ✗ No users found in database. Create a user first.")
                print("=" * 60)
                return False
            
            user_id = test_user.id
            print(f"   ✓ Using test user ID: {user_id} (Email: {test_user.email})")
    except Exception as e:
        print(f"   ✗ Error getting user: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False
    
    # Test upload
    print("\n4. Testing Upload...")
    test_content = b"Hello, Azure Blob Storage! This is a test file created by test_blob_storage.py"
    test_blob_name = f"test/test_file_{Path(__file__).stem}.txt"
    
    try:
        success = await blob_storage.upload_file(
            user_id=user_id,
            file_content=test_content,
            blob_name=test_blob_name,
            mime_type="text/plain",
            original_filename="test_file.txt"
        )
        
        if success:
            print(f"   ✓ Upload successful: {test_blob_name}")
        else:
            print(f"   ✗ Upload failed (check logs for details)")
            print("=" * 60)
            return False
    except Exception as e:
        print(f"   ✗ Upload error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False
    
    # Test download
    print("\n5. Testing Download...")
    try:
        downloaded_content = await blob_storage.download_file(test_blob_name)
        if downloaded_content:
            if downloaded_content == test_content:
                print(f"   ✓ Download successful: Content matches ({len(downloaded_content)} bytes)")
            else:
                print(f"   ✗ Download failed: Content mismatch")
                print(f"      Expected: {len(test_content)} bytes")
                print(f"      Got: {len(downloaded_content)} bytes")
                print("=" * 60)
                return False
        else:
            print(f"   ✗ Download failed: No content returned")
            print("=" * 60)
            return False
    except Exception as e:
        print(f"   ✗ Download error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        return False
    
    # Test storage usage
    print("\n6. Testing Storage Usage...")
    try:
        async with get_db_context() as db:
            usage = await blob_storage.get_user_storage_usage(user_id, db)
            formatted = blob_storage.format_storage_size(usage)
            print(f"   ✓ User {user_id} storage: {formatted}")
    except Exception as e:
        print(f"   ⚠ Storage usage error: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup test file
    print("\n7. Cleaning Up...")
    try:
        deleted = await blob_storage.delete_file(test_blob_name)
        if deleted:
            print(f"   ✓ Test file deleted: {test_blob_name}")
        else:
            print(f"   ⚠ Could not delete test file (may not exist)")
    except Exception as e:
        print(f"   ⚠ Cleanup error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ All Tests Passed! Azure Blob Storage is working correctly.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_blob_storage())
    sys.exit(0 if success else 1)
