"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, contacts, messages, webhook
from app.config import settings
from app.database import close_db, init_db
from app.services.message_processor import message_processor
from app.utils.logger import get_logger, setup_logging
from app.websocket.handlers import router as ws_router
from app.websocket.manager import ws_manager

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting WhatsApp Business Chat API...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database type: {settings.database_type}")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Connect WebSocket manager to message processor
    message_processor.set_websocket_manager(ws_manager)
    logger.info("WebSocket manager connected")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Database connections closed")
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="WhatsApp Business Chat API",
    description="Backend API for WhatsApp Business Chat Dashboard",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.
    
    Returns:
        Health status information.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.environment,
        "database_type": settings.database_type,
    }


# Root endpoint
@app.get("/")
async def root() -> dict:
    """Root endpoint.
    
    Returns:
        Welcome message and API info.
    """
    return {
        "message": "WhatsApp Business Chat API",
        "version": "0.1.0",
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else None,
        },
    )


# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(webhook.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(contacts.router, prefix="/api")
app.include_router(ws_router)


# API information endpoint
@app.get("/api")
async def api_info() -> dict:
    """API information endpoint.
    
    Returns:
        Available API endpoints information.
    """
    return {
        "name": "WhatsApp Business Chat API",
        "version": "0.1.0",
        "endpoints": {
            "auth": {
                "register": "POST /api/auth/register",
                "login": "POST /api/auth/login",
                "me": "GET /api/auth/me",
                "refresh": "POST /api/auth/refresh",
            },
            "webhook": {
                "verify": "GET /api/webhook",
                "receive": "POST /api/webhook",
                "health": "GET /api/webhook/health",
            },
            "messages": {
                "list": "GET /api/messages",
                "send": "POST /api/messages/send",
                "get": "GET /api/messages/{message_id}",
                "mark_read": "POST /api/messages/{message_id}/mark-read",
            },
            "contacts": {
                "list": "GET /api/contacts",
                "create": "POST /api/contacts",
                "get": "GET /api/contacts/{contact_id}",
                "update": "PATCH /api/contacts/{contact_id}",
                "delete": "DELETE /api/contacts/{contact_id}",
                "conversations": "GET /api/contacts/{contact_id}/conversations",
                "conversation_list": "GET /api/contacts/conversations/list",
            },
            "websocket": {
                "chat": "WS /ws/chat/{conversation_id}?token=JWT",
                "global": "WS /ws/global?token=JWT",
            },
        },
    }
