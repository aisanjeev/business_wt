"""Application constants and enumerations."""

from enum import Enum


class MessageStatus(str, Enum):
    """Message delivery status values."""
    
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class SenderType(str, Enum):
    """Message sender type values."""
    
    INBOUND = "inbound"  # Message from customer to business
    OUTBOUND = "outbound"  # Message from business to customer


class MessageType(str, Enum):
    """WhatsApp message types."""
    
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    REACTION = "reaction"
    BUTTON = "button"


class ContactStatus(str, Enum):
    """Contact status values."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class TemplateCategory(str, Enum):
    """WhatsApp template categories."""
    
    MARKETING = "marketing"
    UTILITY = "utility"
    AUTHENTICATION = "authentication"


class TemplateStatus(str, Enum):
    """Template approval status values."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    REJECTED = "rejected"


class WSEventType(str, Enum):
    """WebSocket event types."""
    
    NEW_MESSAGE = "new_message"
    STATUS_UPDATE = "status_update"
    TYPING = "typing"
    READ = "read"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


# WhatsApp API constants
WHATSAPP_API_BASE_URL = "https://graph.facebook.com"
WHATSAPP_MESSAGING_PRODUCT = "whatsapp"

# Rate limiting constants
MAX_MESSAGES_PER_SECOND = 15
MAX_TEMPLATE_MESSAGES_PER_DAY = 1000

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# WebSocket constants
WS_PING_INTERVAL = 30  # seconds
WS_CONNECTION_TIMEOUT = 60  # seconds
WS_MAX_RECONNECT_ATTEMPTS = 5

# Message constants
MAX_TEXT_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
SUPPORTED_DOCUMENT_TYPES = ["application/pdf", "application/msword", "text/plain"]
SUPPORTED_AUDIO_TYPES = ["audio/aac", "audio/mp4", "audio/mpeg", "audio/amr", "audio/ogg"]
SUPPORTED_VIDEO_TYPES = ["video/mp4", "video/3gpp"]

# Error messages
ERROR_MESSAGES = {
    "INVALID_TOKEN": "Invalid or expired token",
    "UNAUTHORIZED": "Authentication required",
    "FORBIDDEN": "Insufficient permissions",
    "NOT_FOUND": "Resource not found",
    "VALIDATION_ERROR": "Validation failed",
    "INTERNAL_ERROR": "Internal server error",
    "WHATSAPP_API_ERROR": "WhatsApp API error",
    "WEBHOOK_VERIFICATION_FAILED": "Webhook verification failed",
    "DATABASE_ERROR": "Database error occurred",
    "RATE_LIMIT_EXCEEDED": "Rate limit exceeded",
}
