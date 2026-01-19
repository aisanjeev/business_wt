# Environment Variables Guide

This document lists all environment variables needed for the SaaS WhatsApp platform.

## Backend Environment Variables

Create or update `backend/.env` with the following variables:

### Required New Variables for SaaS Features

```bash
# ============================================
# Meta OAuth Configuration (NEW - Required)
# ============================================
# Get these from your Meta App Dashboard: https://developers.facebook.com/apps
META_APP_ID=your_meta_app_id_here
META_APP_SECRET=your_meta_app_secret_here
META_OAUTH_REDIRECT_URI=http://localhost:8000/api/meta/oauth/callback

# ============================================
# Encryption Key (NEW - Required)
# ============================================
# Must be exactly 32 characters for AES-256 encryption
# Generate a secure random string for production!
ENCRYPTION_KEY=change_this_in_production_32_chars

# ============================================
# Meta Cost Calculation (NEW - Optional)
# ============================================
# These are default costs per message type (in USD)
# Update these based on Meta's actual pricing
META_COST_PER_TEXT_MESSAGE=0.005
META_COST_PER_TEMPLATE_MESSAGE=0.005
META_COST_PER_MEDIA_MESSAGE=0.010

# ============================================
# Azure Blob Storage Configuration (NEW - Required for media storage)
# ============================================
# Get connection string from Azure Portal:
# 1. Go to Azure Portal > Storage Accounts
# 2. Select your storage account
# 3. Go to "Access keys" or "Connection strings"
# 4. Copy the connection string
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=your_account;AccountKey=your_key;EndpointSuffix=core.windows.net
# Container name (default: techpath-ai-saas)
AZURE_STORAGE_CONTAINER_NAME=techpath-ai-saas
```

### Existing Variables (if not already set)

```bash
# Database
DATABASE_TYPE=mysql
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/whatsapp_chat

# JWT Authentication
JWT_SECRET=your_super_secret_jwt_key_here

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Frontend Environment Variables

Create or update `frontend/.env.local` with:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# WebSocket URL (for real-time features)
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## How to Get Meta OAuth Credentials

1. Go to [Meta for Developers](https://developers.facebook.com/apps)
2. Create a new app or use an existing one
3. Go to **Settings > Basic** to find:
   - **App ID** → Use as `META_APP_ID`
   - **App Secret** → Use as `META_APP_SECRET`
4. Go to **WhatsApp > API Setup** to configure:
   - **Webhook URL**: `https://yourdomain.com/api/webhook`
   - **Verify Token**: Use as `WEBHOOK_VERIFY_TOKEN`
5. In **Settings > Basic**, add **OAuth Redirect URI**:
   - `http://localhost:8000/api/meta/oauth/callback` (for development)
   - `https://yourdomain.com/api/meta/oauth/callback` (for production)

## How to Get Azure Blob Storage Connection String

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Storage accounts** (or create a new one)
3. Select your storage account
4. Go to **Access keys** under "Security + networking"
5. Click **Show** next to one of the keys
6. Copy the **Connection string** (it will look like: `DefaultEndpointsProtocol=https;AccountName=...`)
7. Use this as `AZURE_STORAGE_CONNECTION_STRING` in your `.env` file
8. The container `techpath-ai-saas` will be created automatically if it doesn't exist

## Important Notes

1. **ENCRYPTION_KEY**: Must be exactly 32 characters. Generate a secure random string:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(24)[:32])"
   ```

2. **META_OAUTH_REDIRECT_URI**: Must match exactly what you configure in Meta App settings.

3. **NEXT_PUBLIC_***: Only variables prefixed with `NEXT_PUBLIC_` are exposed to the browser in Next.js.

4. **Security**: Never commit `.env` files to version control. They are already in `.gitignore`.

5. **Azure Storage**: If `AZURE_STORAGE_CONNECTION_STRING` is not set, the system will fall back to local file storage. However, Azure Blob Storage is recommended for production deployments.
