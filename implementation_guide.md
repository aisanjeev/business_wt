# WhatsApp Business Chat Application - Complete Implementation Guide

**Complete step-by-step instructions for building a production-ready WhatsApp conversational chat application with FastAPI, MySQL, WebSocket, and Next.js. Ready to implement with Cursor AI.**

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Phase 1: Backend Setup with FastAPI](#phase-1-backend-setup-with-fastapi)
4. [Phase 2: Database Schema & Configuration](#phase-2-database-schema--configuration)
5. [Phase 3: Webhook Implementation](#phase-3-webhook-implementation)
6. [Phase 4: WebSocket Real-Time Server](#phase-4-websocket-real-time-server)
7. [Phase 5: Frontend Integration](#phase-5-frontend-integration)
8. [Phase 6: Production Deployment](#phase-6-production-deployment)
9. [Testing & Debugging](#testing--debugging)
10. [Troubleshooting Guide](#troubleshooting-guide)

---

## Project Overview

### What You're Building

A **complete WhatsApp Business Chat Dashboard** where you can:
- ✅ Receive messages from leads via WhatsApp webhook
- ✅ Chat with leads in real-time via a web interface
- ✅ Send messages to WhatsApp using Meta API
- ✅ Track message delivery status (sent, delivered, read)
- ✅ Store complete conversation history in MySQL
- ✅ Manage multiple conversations simultaneously
- ✅ Support message templates for quick responses

### Why This Stack?

| Component | Why Selected |
|-----------|-------------|
| **FastAPI** | Async-first, production-ready, excellent WebSocket support |
| **WebSocket** | Real-time bidirectional communication (native to FastAPI) |
| **MySQL** | Structured data, reliable for conversation history, connection pooling support |
| **SQLAlchemy** | ORM with connection pool management built-in |
| **Next.js** | Modern frontend, built-in API integration, great DX |
| **Poetry** | Dependency management, lock files, virtual environment handling |

---

## Architecture & Technology Stack

### System Architecture Flow

```
Meta WhatsApp Cloud API
    ↓ (Incoming message webhook)
FastAPI Backend (Webhook Receiver)
    ↓ (Store message)
MySQL Database (conversations, messages, contacts)
    ↓ (Real-time broadcast via WebSocket)
Next.js Frontend (Chat Dashboard)
    ↓ (User sends reply)
FastAPI Backend (Message Sender)
    ↓ (Send via Meta API)
Meta WhatsApp Cloud API → Recipient
```

### Technology Stack Details

**Backend:**
- Python 3.10+
- FastAPI (web framework)
- Uvicorn (ASGI server)
- SQLAlchemy (ORM)
- PyMySQL (MySQL driver)
- Python-dotenv (environment config)
- PyJWT (authentication)
- httpx (HTTP client for Meta API)
- python-multipart (form parsing)

**Database:**
- MySQL 8.0+
- Connection pooling (SQLAlchemy managed)
- Indexed queries for performance

**Frontend:**
- Next.js 14+
- React 18+
- TypeScript
- WebSocket client
- TailwindCSS (optional)

**DevOps:**
- Poetry (dependency management)
- Docker (containerization)
- Railway/Render (backend hosting)
- Vercel (frontend hosting)
- ngrok (local webhook testing)

---

## Phase 1: Backend Setup with FastAPI

### Step 1.1: Create Project Directory Structure

```
Create a new folder called whatsapp-business-chat
Inside, create these subfolders:

whatsapp-business-chat/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Settings & environment
│   │   ├── database.py        # MySQL connection & session
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── webhook.py     # WhatsApp webhook receiver
│   │   │   ├── messages.py    # Message endpoints
│   │   │   └── contacts.py    # Contact management
│   │   ├── websocket/
│   │   │   ├── __init__.py
│   │   │   ├── manager.py     # Connection manager
│   │   │   └── handlers.py    # WebSocket handlers
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── whatsapp.py    # Meta API client
│   │   │   ├── auth.py        # JWT authentication
│   │   │   └── message_processor.py  # Message business logic
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logger.py      # Logging setup
│   │       └── constants.py   # App constants
│   ├── pyproject.toml         # Poetry config
│   ├── poetry.lock            # Locked dependencies (auto-generated)
│   ├── .env                   # Environment variables
│   ├── .env.example           # Template for .env
│   ├── Dockerfile            # Docker configuration
│   └── run.py                # Entry point script
│
├── frontend/                  # Next.js frontend
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── pages/
│   ├── package.json
│   └── .env.local
│
└── README.md
```

### Step 1.2: Initialize Poetry Project

Open terminal in the `backend/` folder and run:

```
# Initialize Poetry project
poetry init

# When prompted, answer:
# - Name: whatsapp-business-chat
# - Description: WhatsApp Business Chat Application
# - Author: Your Name <your@email.com>
# - License: MIT
# - Requires: Python ^3.10
# - Add dependencies interactively: No (we'll add them next)

# Add dependencies using Poetry
poetry add fastapi uvicorn
poetry add sqlalchemy pymysql
poetry add python-dotenv pydantic
poetry add httpx aioredis
poetry add pyjwt python-multipart
poetry add python-jose[cryptography]

# Add development dependencies
poetry add --group dev black flake8 pytest pytest-asyncio

# Create virtual environment and install
poetry install
```

### Step 1.3: Activate Poetry Environment

```
# Activate Poetry shell
poetry shell

# Or run commands with poetry run prefix
poetry run python -m uvicorn app.main:app --reload
```

### Step 1.4: Create Initial .env File

Create `.backend/.env` file with these variables:

```
# Server Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=info

# Database Configuration
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/whatsapp_chat
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
DB_ECHO=false

# Meta WhatsApp API
WHATSAPP_BUSINESS_ACCOUNT_ID=your_phone_number_id
WHATSAPP_API_TOKEN=your_meta_api_token
WEBHOOK_VERIFY_TOKEN=your_custom_verify_token_string
WHATSAPP_API_VERSION=v18.0

# JWT Authentication
JWT_SECRET=your_super_secret_key_change_this_in_production
JWT_ALGORITHM=HS256
JWT_EXPIRATION=86400

# CORS (for frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Server
HOST=0.0.0.0
PORT=8000
```

Create `.backend/.env.example` as a template (same as above but with placeholder values).

### Step 1.5: Create `.gitignore`

Create `backend/.gitignore`:

```
# Poetry
dist/
build/
*.egg-info/
__pycache__/
.venv/
venv/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Database
*.db
*.sqlite
*.sqlite3

# Logs
*.log
logs/

# Testing
.pytest_cache/
.coverage
htmlcov/

# OS
Thumbs.db
.DS_Store
```

---

## Phase 2: Database Schema & Configuration

### Step 2.1: Setup MySQL Database

**Create MySQL database:**

```
# Open MySQL CLI or MySQL Workbench
# Create database
CREATE DATABASE whatsapp_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Create user (optional but recommended)
CREATE USER 'whatsapp_user'@'localhost' IDENTIFIED BY 'strong_password_here';
GRANT ALL PRIVILEGES ON whatsapp_chat.* TO 'whatsapp_user'@'localhost';
FLUSH PRIVILEGES;
```

Update your `.env` file with correct credentials:
```
DATABASE_URL=mysql+pymysql://whatsapp_user:strong_password_here@localhost:3306/whatsapp_chat
```

### Step 2.2: Create Database Schema Tables

Connect to your MySQL database and create these tables:

**Table 1: Contacts**
```
This table stores information about leads/customers you chat with on WhatsApp.

Fields:
- id: Primary key, auto-increment
- phone_number: WhatsApp phone number (unique, indexed)
- name: Contact name
- email: Contact email (optional)
- avatar_url: Profile picture URL
- business_account_id: Meta account identifier
- status: "active" or "inactive" (indexed)
- created_at: Timestamp when contact was added
- updated_at: Timestamp of last update

Indexes:
- phone_number (for quick lookup)
- status (for filtering)
- created_at (for sorting)
```

**Table 2: Conversations**
```
This table represents individual chat threads with contacts.

Fields:
- id: Primary key, auto-increment
- contact_id: Foreign key to contacts table
- thread_id: Unique identifier for conversation (from Meta)
- last_message_at: Timestamp of most recent message
- is_active: Boolean flag for active conversations (indexed)
- assigned_to: User ID if assigned to team member
- tags: JSON field for custom tags/labels
- created_at: When conversation started

Indexes:
- contact_id (for joining conversations by contact)
- is_active (for filtering active chats)
- created_at (for sorting)
```

**Table 3: Messages**
```
This table stores all messages in conversations.

Fields:
- id: Primary key, auto-increment
- conversation_id: Foreign key to conversations
- message_id: Unique identifier from Meta API (unique, indexed)
- sender_type: "inbound" (from customer) or "outbound" (from you)
- message_type: "text", "image", "document", "audio"
- content: Message text content
- media_url: URL for media attachments
- status: "pending", "sent", "delivered", "read", "failed" (indexed)
- timestamp: When message was sent
- created_at: When message was stored

Indexes:
- conversation_id (for retrieving chat history)
- message_id (for status updates)
- status (for tracking delivery)
- created_at (for sorting chronologically)
```

**Table 4: Message Templates**
```
This table stores approved WhatsApp message templates.

Fields:
- id: Primary key, auto-increment
- name: Template name (indexed)
- template_id: ID from Meta API
- content: Template message body
- category: "marketing", "utility", "authentication"
- language: Language code (default "en")
- created_at: When template was added

These are pre-approved messages on WhatsApp platform.
```

### Step 2.3: Create Configuration Files

Create `app/config.py` - This file manages all environment variables:

**What this file does:**
- Reads all environment variables from `.env`
- Validates that required settings are present
- Provides defaults for optional settings
- Uses Pydantic for type safety
- Creates a singleton settings object used throughout the app

**Include:**
- Database URL and connection pool settings
- WhatsApp API credentials
- JWT secret and algorithm
- CORS origins
- Log level configuration
- Debug mode flag

### Step 2.4: Create Database Connection Setup

Create `app/database.py` - This file handles MySQL connection:

**What this file does:**
- Creates SQLAlchemy engine with connection pooling
- Configures pool_size=10 (max idle connections)
- Configures max_overflow=20 (additional connections beyond pool_size)
- Sets pool_recycle=3600 (recycle connections every hour)
- Enables pool_pre_ping to check connections before use
- Creates SessionLocal for database queries
- Provides get_db() dependency for FastAPI endpoints

**Key settings:**
- Connection pooling prevents database connection exhaustion
- Lazy initialization improves startup speed
- Echo can be enabled for debugging SQL queries

---

## Phase 3: Webhook Implementation

### Step 3.1: Understand WhatsApp Webhook Flow

**Webhook Verification (Setup):**
1. You register webhook URL in Meta Business Manager
2. Meta sends GET request with: `hub_mode`, `hub_challenge`, `hub_verify_token`
3. You must verify token matches your WEBHOOK_VERIFY_TOKEN
4. Return `hub_challenge` value to confirm ownership

**Webhook Events (Ongoing):**
1. Customer sends WhatsApp message
2. Meta sends POST request to your webhook URL with message data
3. You must return HTTP 200 within 5 seconds
4. Process message data asynchronously (don't block the response)
5. Broadcast to connected WebSocket clients in real-time

### Step 3.2: Create Webhook Verification Endpoint

Create `app/api/webhook.py`:

**What this file does:**
- Implements GET /api/webhook for verification
- Implements POST /api/webhook for receiving messages
- Verifies incoming requests are from Meta
- Processes webhook payloads asynchronously
- Handles different message types (text, image, document)
- Updates message status when Meta sends delivery confirmations
- Broadcasts events to connected WebSocket clients

**Key features:**
- Webhook responds with 200 OK immediately
- Message processing happens in background tasks
- Retry logic if database insert fails
- Logging for debugging and monitoring

### Step 3.3: Create Message Processor Service

Create `app/services/message_processor.py`:

**What this file does:**
- Extracts contact info from webhook payload
- Creates or updates Contact record
- Creates or retrieves Conversation
- Stores Message in database
- Broadcasts to all connected WebSocket clients for that conversation
- Handles different message types and media

**Processing flow:**
1. Parse incoming webhook data
2. Verify it's valid and from Meta
3. Extract phone_number, message_content, timestamp
4. Create/update Contact record
5. Create/retrieve Conversation for contact
6. Store Message record with status "received"
7. Broadcast via WebSocket to dashboard
8. Update conversation's last_message_at timestamp

---

## Phase 4: WebSocket Real-Time Server

### Step 4.1: Understand WebSocket Architecture

**What WebSocket does:**
- Maintains persistent bidirectional connection between browser and server
- Allows server to send updates to client instantly (no polling)
- Browser sends message → server broadcasts to all connected clients
- Server receives webhook → broadcasts to connected WebSocket clients

**Connection Management:**
- Track active WebSocket connections per conversation
- Handle automatic reconnection when browser loses connection
- Clean up connections when client disconnects
- Broadcast to multiple clients viewing same conversation

### Step 4.2: Create Connection Manager

Create `app/websocket/manager.py`:

**What this file does:**
- Maintains dictionary of active WebSocket connections
- Key: conversation_id, Value: list of WebSocket connections
- Methods to connect, disconnect, broadcast to conversation
- Handles disconnections gracefully
- Prevents broadcast to closed connections

**Key methods:**
- `connect(websocket, conversation_id)`: Accept connection and register
- `disconnect(websocket, conversation_id)`: Remove from active connections
- `broadcast_to_conversation(conversation_id, message)`: Send to all clients in conversation
- `broadcast_status_update(update)`: Send status updates globally

### Step 4.3: Create WebSocket Event Handlers

Create `app/websocket/handlers.py`:

**What this file does:**
- Endpoint: `GET /ws/chat/{conversation_id}?token=JWT_TOKEN`
- Verify JWT token before accepting WebSocket connection
- Accept WebSocket connection
- Listen for messages from client
- Handle typing indicators
- Handle connection drops with automatic reconnection
- Handle client disconnect gracefully

**Message types to handle:**
1. `typing` - User is typing indicator (broadcast to others)
2. `message` - User sent message (already processed by API endpoint)
3. `read` - User read messages (update status)
4. `reconnect` - Client reconnecting (resend recent messages)

### Step 4.4: Broadcast on Message Received

When webhook receives a message:
1. Store in database
2. Emit via WebSocket to all connected clients viewing that conversation
3. Update conversation's last_message_at
4. Send response back to dashboard immediately

---

## Phase 5: Frontend Integration

### Step 5.1: Setup Next.js Project

```
# Create Next.js project in frontend folder
cd frontend
npx create-next-app@latest . --typescript --tailwind

# Install additional packages
npm install socket.io-client
npm install zustand (for state management)
npm install axios
npm install date-fns
```

### Step 5.2: Create WebSocket Hook

Create `hooks/useWebSocket.ts`:

**What this hook does:**
- Manages WebSocket connection lifecycle
- Establishes connection to FastAPI WebSocket endpoint
- Handles automatic reconnection with exponential backoff
- Provides methods to send messages
- Handles connection errors gracefully
- Auto-reconnects up to 5 times with 3-second delays

**Features:**
- Automatic reconnection on disconnect
- Exponential backoff (1st retry 3s, 2nd retry 6s, etc.)
- Error logging and handling
- Clean up on component unmount
- TypeScript types for safety

### Step 5.3: Create Chat Components

Create `components/ChatWindow.tsx`:

**What this component does:**
- Displays conversation with a contact
- Shows message history (loads from database)
- Real-time message updates via WebSocket
- Message input box and send button
- Auto-scroll to latest message
- Shows message status (pending, sent, delivered, read)
- Shows typing indicator when other person is typing
- Handles connection status indicator

**Features:**
- Message pagination for older messages
- Rich message display (text, images, documents)
- Sender type styling (inbound vs outbound)
- Timestamp for each message
- Status badges (✓ sent, ✓✓ delivered, ✓✓ read)

Create `components/ConversationList.tsx`:

**What this component does:**
- Shows list of all conversations with contacts
- Displays last message preview
- Shows unread message count
- Highlights active conversation
- Search/filter conversations
- Sorts by most recent

Create `components/Dashboard.tsx`:

**What this component does:**
- Main layout component
- Left sidebar: conversation list
- Main area: chat window
- Shows connection status
- Handles conversation selection

### Step 5.4: Create API Service

Create `services/api.ts`:

**What this file does:**
- Centralized API client for backend communication
- Methods for:
  - Getting conversations list
  - Getting message history
  - Sending message
  - Getting contacts
  - Updating message status
- Error handling and logging
- JWT token management

### Step 5.5: Create State Management

Create `hooks/useAppState.ts` (using Zustand):

**What this manages:**
- Current selected conversation
- Active WebSocket connection status
- Unread message counts
- User authentication state
- Message draft text

---

## Phase 6: Production Deployment

### Step 6.1: Prepare Backend for Deployment

**Create Dockerfile** in `backend/`:

```
Container image that includes:
- Python 3.10 base image
- Poetry for dependency management
- Copy project files
- Install dependencies
- Expose port 8000
- Run Uvicorn with 4 workers
```

**Create docker-compose.yml** (for local testing):

```
Services:
- FastAPI backend (port 8000)
- MySQL database (port 3306)
- Network connection between services
```

**Create deployment configuration**:
- Environment variables for production
- Database URL for hosted MySQL
- JWT secret (generate strong random string)
- WhatsApp API token
- Webhook verify token

### Step 6.2: Deploy Backend to Railway or Render

**Railway steps:**
```
1. Create Railway account
2. Connect GitHub repository
3. Set up MySQL database in Railway
4. Configure environment variables
5. Deploy from main branch
6. Get public URL for backend
```

**Render steps:**
```
1. Create Render account
2. Create new Web Service
3. Connect GitHub repository
4. Set build command: poetry install && poetry run uvicorn app.main:app --host 0.0.0.0
5. Set start command: poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT
6. Configure environment variables
7. Add PostgreSQL/MySQL database
8. Deploy
```

### Step 6.3: Deploy Frontend to Vercel

```
1. Create Vercel account
2. Import Next.js project from GitHub
3. Set environment variable: NEXT_PUBLIC_API_URL=your_backend_url
4. Deploy
5. Vercel automatically rebuilds on git push
```

### Step 6.4: Configure WhatsApp Webhook

In Meta Business Manager:
```
1. Go to WhatsApp > API Setup > Webhook
2. Callback URL: https://your-backend-url.com/api/webhook
3. Verify Token: Use your WEBHOOK_VERIFY_TOKEN value
4. Subscribe to events: messages, message_status
5. Click Verify and Save
6. Meta will send verification request - backend must respond correctly
```

### Step 6.5: HTTPS & SSL Certificates

```
- Railway/Render provide automatic HTTPS
- Certificates auto-renewed
- No action needed from you
```

---

## Testing & Debugging

### Step 7.1: Local Testing with ngrok

**Why ngrok?**
- WhatsApp webhook requires public HTTPS URL
- ngrok creates tunnel from your machine to internet
- Allows testing webhook locally before deployment

**Steps:**
```
1. Download ngrok from ngrok.com
2. Run: ngrok http 8000
3. Copy provided public URL (e.g., https://abc123.ngrok.io)
4. In Meta webhook settings, temporarily set callback URL to: https://abc123.ngrok.io/api/webhook
5. Send test message from WhatsApp
6. Check backend logs for webhook payload
7. Verify database records created
8. Check browser for real-time message display
```

### Step 7.2: Test Webhook Verification

```
# Test webhook setup
curl -X GET "http://localhost:8000/api/webhook?hub_mode=subscribe&hub_challenge=TEST_VALUE&hub_verify_token=YOUR_TOKEN"

# Should return: TEST_VALUE (as integer)
```

### Step 7.3: Test Sending Messages

```
# Test sending message via API
curl -X POST "http://localhost:8000/api/messages" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": 1,
    "content": "Hello from API",
    "phone_number": "1234567890"
  }'
```

### Step 7.4: Test WebSocket Connection

```
# Using wscat (npm install -g wscat)
wscat -c "ws://localhost:8000/ws/chat/1?token=YOUR_JWT_TOKEN"

# Type messages to test real-time communication
```

### Step 7.5: Database Verification

```
# Connect to MySQL and verify data
mysql -u whatsapp_user -p whatsapp_chat

# Check contacts created
SELECT * FROM contacts;

# Check conversations
SELECT c.id, c.contact_id, COUNT(m.id) as message_count 
FROM conversations c 
LEFT JOIN messages m ON c.id = m.conversation_id 
GROUP BY c.id;

# Check messages
SELECT * FROM messages ORDER BY created_at DESC LIMIT 10;
```

---

## Troubleshooting Guide

### Issue: Webhook Not Receiving Messages

**Symptoms:** No messages appearing in dashboard

**Troubleshooting steps:**
```
1. Verify webhook URL is public and HTTPS
   - Use ngrok to test locally
   - Check Meta webhook settings
   
2. Check webhook logs
   - Backend should log every request
   - Look for "Webhook received" messages
   
3. Verify token matches
   - WEBHOOK_VERIFY_TOKEN in .env
   - Verify token in Meta settings
   - Must be exact match (case-sensitive)
   
4. Test webhook endpoint directly
   - curl with hub_mode=subscribe
   - Should return hub_challenge value
   
5. Check database permissions
   - Insert into contacts table
   - Insert into messages table
   
6. Verify WhatsApp API token is valid
   - Try sending message via API
   - Check token expiration
```

### Issue: WebSocket Not Connecting

**Symptoms:** Real-time updates not working, stuck on "Connecting..."

**Troubleshooting steps:**
```
1. Check WebSocket URL
   - Should be wss:// for HTTPS
   - ws:// for local HTTP
   - Include conversation ID and JWT token
   
2. Verify JWT token is valid
   - Token generated during login
   - Not expired
   - Signed with same JWT_SECRET
   
3. Check CORS settings
   - Backend must allow frontend origin
   - Frontend origin in CORS_ORIGINS env var
   
4. Browser developer tools
   - Network tab → WS
   - Look for connection errors
   - Check WebSocket frame data
   
5. Server logs
   - Look for WebSocket accept/reject messages
   - Connection manager logs
```

### Issue: Messages Sending but Not to WhatsApp

**Symptoms:** Messages appear in dashboard but don't reach contact

**Troubleshooting steps:**
```
1. Verify WhatsApp API token
   - Token might be expired
   - Check token permissions in Meta
   - Regenerate if needed
   
2. Check phone number format
   - Must include country code
   - Example: 919876543210 (not +91 or spaces)
   
3. Verify phone_id in environment
   - Should be WhatsApp Business Account ID
   - Not personal phone number
   
4. Check API response
   - Log Meta API response
   - Look for error messages
   - Check rate limiting (15 messages/sec max)
   
5. Message template issues
   - If using templates, must be pre-approved
   - Templates are language-specific
   
6. Recipient status
   - Recipient must have contacted you first
   - Or use approved message template
```

### Issue: Database Connection Pool Exhausted

**Symptoms:** Errors like "QueuePool limit reached"

**Troubleshooting:**
```
1. Increase pool size in .env
   - DB_POOL_SIZE=20
   - DB_MAX_OVERFLOW=40
   
2. Check for connection leaks
   - Verify all db.close() calls
   - Use with statements: with db()
   - Check for infinite loops
   
3. Monitor active connections
   - MySQL: SHOW PROCESSLIST;
   - Kill old connections if needed
   
4. Enable pool_pre_ping
   - Automatically validates connections
   - Removes stale connections
   
5. Reduce pool_recycle time
   - Default 3600s (1 hour)
   - Can try 1800s (30 min) for troubleshooting
```

### Issue: High Latency in Message Delivery

**Symptoms:** Delay between sending and receiving

**Performance optimization:**
```
1. Database indexes
   - Ensure all indexes from schema are created
   - Add indexes on frequently queried fields
   
2. Connection pooling
   - Use persistent connections
   - Increase pool_size to 20-30
   
3. WebSocket broadcasts
   - Only broadcast to relevant conversations
   - Not to all connections
   
4. Async/await usage
   - Use await consistently
   - Don't block event loop
   
5. Message processing
   - Process in background tasks
   - Return webhook response immediately
   
6. Frontend optimization
   - Lazy load old messages
   - Use pagination for history
   
7. Reduce database queries
   - Use SQL JOINs instead of N+1 queries
   - Cache frequently accessed data
```

---

## Cursor AI Workflow Tips

### How to Use Cursor Effectively

**When creating files:**
1. Ask Cursor to create full file content with type hints
2. Ask for proper error handling
3. Ask for logging statements
4. Request SQLAlchemy best practices
5. Ask for async/await patterns

**Example Cursor prompts:**

```
"Create app/config.py using Pydantic BaseSettings for FastAPI. 
Include database URL, WhatsApp API settings, JWT config. 
Add environment variable validation with helpful error messages."

"Create app/database.py with SQLAlchemy engine setup. 
Use connection pooling with size=10, max_overflow=20. 
Enable pool_pre_ping. Create SessionLocal. Add get_db dependency."

"Create app/api/webhook.py with webhook verification and message receiver. 
Handle GET for verification, POST for messages. 
Process in background tasks. Add comprehensive logging."

"Create app/websocket/manager.py for WebSocket connection management. 
Track connections by conversation_id. Add broadcast methods. 
Handle disconnections gracefully."
```

**File generation in order:**
1. Start with config.py (dependencies needed everywhere)
2. Then database.py (needed for models)
3. Then models.py (needed for schemas)
4. Then schemas.py (needed for API endpoints)
5. Then services (whatsapp.py, auth.py, message_processor.py)
6. Then API routes (webhook.py, messages.py, contacts.py)
7. Then WebSocket (manager.py, handlers.py)
8. Finally main.py (ties everything together)

---

## Security Best Practices

### Essential Security Measures

```
1. Webhook Verification
   - Always verify WEBHOOK_VERIFY_TOKEN
   - Never trust incoming requests
   
2. JWT Tokens
   - Generate strong JWT_SECRET (use secrets module)
   - Set reasonable expiration time
   - Validate token on every WebSocket connection
   
3. Database Security
   - Use strong passwords for MySQL
   - Limit database user permissions (only whatsapp_chat database)
   - Encrypt database passwords (never commit to git)
   
4. API Security
   - HTTPS only (enforce in production)
   - CORS: Allow specific origins only (not *)
   - Rate limiting on public endpoints
   - Input validation and sanitization
   
5. WhatsApp API Token
   - Regenerate regularly
   - Never commit to git
   - Use environment variables only
   - Monitor token usage in Meta
   
6. Data Privacy
   - Comply with WhatsApp terms
   - Don't store sensitive payment info
   - Implement proper logging (no passwords in logs)
   - Backup database regularly
   
7. Deployment Security
   - Use HTTPS with valid certificates
   - Set DEBUG=false in production
   - Use strong random strings for JWT_SECRET
   - Implement rate limiting
```

---

## Next Steps Checklist

Use this checklist as you build:

### Backend Development
- [ ] Create Poetry project and install dependencies
- [ ] Create `.env` file with all variables
- [ ] Create database and tables in MySQL
- [ ] Build config.py with Pydantic settings
- [ ] Build database.py with connection pooling
- [ ] Create SQLAlchemy models (Contact, Conversation, Message, Template)
- [ ] Create Pydantic schemas for request/response
- [ ] Build WhatsApp API client service (whatsapp.py)
- [ ] Build message processor service
- [ ] Build JWT authentication service
- [ ] Implement webhook endpoints (GET for verify, POST for messages)
- [ ] Create WebSocket connection manager
- [ ] Create WebSocket event handlers
- [ ] Build message API endpoints (send, get history)
- [ ] Build contact management endpoints
- [ ] Test all endpoints locally with curl/Postman
- [ ] Test with ngrok for webhook

### Frontend Development
- [ ] Setup Next.js project with TypeScript
- [ ] Create useWebSocket hook
- [ ] Create API service module
- [ ] Build ChatWindow component
- [ ] Build ConversationList component
- [ ] Build Dashboard layout
- [ ] Implement real-time message updates
- [ ] Add message input and send functionality
- [ ] Style components with TailwindCSS
- [ ] Test with local backend

### Deployment
- [ ] Create Dockerfile for backend
- [ ] Create .dockerignore
- [ ] Test Docker build locally
- [ ] Setup Railway/Render account
- [ ] Deploy backend to Railway/Render
- [ ] Deploy MySQL to Railway
- [ ] Deploy frontend to Vercel
- [ ] Configure WhatsApp webhook URL in Meta
- [ ] Test end-to-end in production
- [ ] Setup monitoring and logging
- [ ] Create deployment documentation

---

## Resources & Documentation

### Official Documentation
- Meta WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api/
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Next.js: https://nextjs.org/docs
- Poetry: https://python-poetry.org/docs/
- Uvicorn: https://www.uvicorn.org/

### Useful Tools
- Postman: API testing
- MySQL Workbench: Database management
- ngrok: Webhook local testing
- wscat: WebSocket testing
- Railway: Backend hosting
- Vercel: Frontend hosting

### Learning Resources
- FastAPI Tutorial: https://fastapi.tiangolo.com/tutorial/
- WebSocket Guide: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- WhatsApp API Guide: https://www.twilio.com/blog/send-whatsapp-messages-python-fastapi

---

**Ready to build? Start with Phase 1, follow each step in order, and use Cursor AI to generate code with the prompts provided. Good luck! 🚀**

