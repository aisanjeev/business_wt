# WhatsApp Business Chat Backend

A production-ready FastAPI backend for WhatsApp Business Chat Dashboard.

## Features

- ✅ WhatsApp Cloud API integration
- ✅ Real-time WebSocket messaging
- ✅ SQLite (development) / MySQL (production) support
- ✅ JWT authentication
- ✅ Message status tracking
- ✅ Contact management
- ✅ Conversation history

## Tech Stack

- **FastAPI** - Modern async web framework
- **SQLAlchemy** - ORM with async support
- **Poetry** - Dependency management
- **JWT** - Authentication
- **WebSocket** - Real-time communication

## Quick Start

### Prerequisites

- Python 3.10+
- Poetry (install via `curl -sSL https://install.python-poetry.org | python3 -`)

### Installation

```bash
# Navigate to backend directory
cd backend

# Install dependencies
poetry install

# Copy environment file and configure
cp .env.example .env
# Edit .env with your settings

# Run the application
poetry run python run.py
```

### Development

```bash
# Activate virtual environment
poetry shell

# Run with auto-reload
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the run script
poetry run python run.py
```

### Docker

```bash
# Build and run with Docker Compose (includes MySQL)
docker-compose up -d

# Or build and run standalone
docker build -t whatsapp-backend .
docker run -p 8000:8000 --env-file .env whatsapp-backend
```

## Configuration

The application is configured via environment variables. Key settings:

### Database

```env
# SQLite (development)
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite+aiosqlite:///./whatsapp_chat.db

# MySQL (production)
DATABASE_TYPE=mysql
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/whatsapp_chat
```

### WhatsApp API

```env
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
WHATSAPP_API_TOKEN=your_meta_api_token
WEBHOOK_VERIFY_TOKEN=your_custom_verify_token
```

### Authentication

```env
JWT_SECRET=your_super_secret_key_min_32_chars
JWT_ALGORITHM=HS256
JWT_EXPIRATION=86400
```

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh JWT token

### Webhook

- `GET /api/webhook` - Webhook verification (Meta)
- `POST /api/webhook` - Receive WhatsApp events
- `GET /api/webhook/health` - Webhook health check

### Messages

- `GET /api/messages` - Get messages for conversation
- `GET /api/messages/{id}` - Get specific message
- `POST /api/messages/send` - Send message
- `POST /api/messages/{id}/mark-read` - Mark message as read

### Contacts

- `GET /api/contacts` - List contacts
- `POST /api/contacts` - Create contact
- `GET /api/contacts/{id}` - Get contact
- `PATCH /api/contacts/{id}` - Update contact
- `DELETE /api/contacts/{id}` - Delete contact
- `GET /api/contacts/conversations/list` - Get conversation list

### WebSocket

- `WS /ws/chat/{conversation_id}?token=JWT` - Chat WebSocket
- `WS /ws/global?token=JWT` - Global notifications WebSocket

## Testing

### Webhook Verification

```bash
curl "http://localhost:8000/api/webhook?hub.mode=subscribe&hub.challenge=123456&hub.verify_token=your_token"
```

### Send Message

```bash
curl -X POST "http://localhost:8000/api/messages/send" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": 1, "content": "Hello!", "message_type": "text"}'
```

### WebSocket Test

```bash
# Install wscat
npm install -g wscat

# Connect to WebSocket
wscat -c "ws://localhost:8000/ws/chat/1?token=YOUR_JWT_TOKEN"
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings & environment
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── api/
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── webhook.py       # WhatsApp webhook
│   │   ├── messages.py      # Message endpoints
│   │   └── contacts.py      # Contact management
│   ├── websocket/
│   │   ├── manager.py       # Connection manager
│   │   └── handlers.py      # WebSocket handlers
│   ├── services/
│   │   ├── auth.py          # JWT authentication
│   │   ├── whatsapp.py      # Meta API client
│   │   └── message_processor.py
│   └── utils/
│       ├── logger.py        # Logging setup
│       └── constants.py     # App constants
├── pyproject.toml           # Poetry config
├── .env                     # Environment variables
├── .env.example             # Example env file
├── Dockerfile               # Docker config
├── docker-compose.yml       # Docker Compose
├── run.py                   # Entry point script
└── README.md
```

## Deployment

### Railway/Render

1. Connect your GitHub repository
2. Set environment variables
3. Deploy

Build command:
```bash
poetry install
```

Start command:
```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Webhook Setup

1. Deploy your backend to get a public HTTPS URL
2. In Meta Business Manager:
   - Go to WhatsApp > API Setup > Webhook
   - Set Callback URL: `https://your-domain.com/api/webhook`
   - Set Verify Token: Same as `WEBHOOK_VERIFY_TOKEN`
   - Subscribe to: messages, message_status

## License

MIT
