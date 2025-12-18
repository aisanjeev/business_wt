"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================================================
# Base Schemas
# ============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================================
# Contact Schemas
# ============================================================================

class ContactBase(BaseSchema):
    """Base contact schema."""
    
    phone_number: str = Field(..., min_length=10, max_length=20)
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = Field(None, max_length=512)
    business_account_id: Optional[str] = Field(None, max_length=100)
    status: str = Field(default="active", max_length=20)


class ContactCreate(ContactBase):
    """Schema for creating a contact."""
    pass


class ContactUpdate(BaseSchema):
    """Schema for updating a contact."""
    
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = Field(None, max_length=512)
    status: Optional[str] = Field(None, max_length=20)


class ContactResponse(ContactBase):
    """Schema for contact response."""
    
    id: int
    created_at: datetime
    updated_at: datetime


class ContactWithConversation(ContactResponse):
    """Contact response with latest conversation info."""
    
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0


# ============================================================================
# Conversation Schemas
# ============================================================================

class ConversationBase(BaseSchema):
    """Base conversation schema."""
    
    thread_id: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    assigned_to: Optional[str] = Field(None, max_length=100)
    tags: Optional[dict] = Field(default_factory=dict)


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation."""
    
    contact_id: int


class ConversationUpdate(BaseSchema):
    """Schema for updating a conversation."""
    
    is_active: Optional[bool] = None
    assigned_to: Optional[str] = Field(None, max_length=100)
    tags: Optional[dict] = None


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""
    
    id: int
    contact_id: int
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    created_at: datetime


class ConversationWithContact(ConversationResponse):
    """Conversation response with contact info."""
    
    contact: ContactResponse


class ConversationListItem(BaseSchema):
    """Schema for conversation list item."""
    
    id: int
    contact_id: int
    contact_name: Optional[str] = None
    contact_phone: str
    contact_avatar: Optional[str] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_type: str = "text"
    unread_count: int = 0
    is_active: bool = True


# ============================================================================
# Message Schemas
# ============================================================================

class MessageBase(BaseSchema):
    """Base message schema."""
    
    message_type: str = Field(default="text", max_length=20)
    content: Optional[str] = None
    media_url: Optional[str] = Field(None, max_length=1024)


class MessageCreate(MessageBase):
    """Schema for creating a message (sending)."""
    
    conversation_id: int
    phone_number: Optional[str] = None  # Optional, can be derived from conversation


class MessageSend(BaseSchema):
    """Schema for sending a message to WhatsApp."""
    
    conversation_id: int
    content: str
    message_type: str = "text"
    template_name: Optional[str] = None
    template_variables: Optional[dict] = None


class MessageResponse(MessageBase):
    """Schema for message response."""
    
    id: int
    conversation_id: int
    message_id: Optional[str] = None
    sender_type: str
    status: str
    error_message: Optional[str] = None
    media_mime_type: Optional[str] = None
    media_filename: Optional[str] = None
    timestamp: datetime
    created_at: datetime


class MessageStatusUpdate(BaseSchema):
    """Schema for message status update."""
    
    message_id: str
    status: str
    timestamp: Optional[datetime] = None


# ============================================================================
# Message Template Schemas
# ============================================================================

class TemplateBase(BaseSchema):
    """Base template schema."""
    
    name: str = Field(..., max_length=100)
    content: str
    category: str = Field(default="utility", max_length=50)
    language: str = Field(default="en", max_length=10)
    variables: Optional[dict] = Field(default_factory=dict)


class TemplateCreate(TemplateBase):
    """Schema for creating a template."""
    
    template_id: Optional[str] = Field(None, max_length=100)


class TemplateUpdate(BaseSchema):
    """Schema for updating a template."""
    
    name: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = None
    category: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=20)
    variables: Optional[dict] = None


class TemplateResponse(TemplateBase):
    """Schema for template response."""
    
    id: int
    template_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


# ============================================================================
# User/Auth Schemas
# ============================================================================

class UserBase(BaseSchema):
    """Base user schema."""
    
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user."""
    
    password: str = Field(..., min_length=8)


class UserUpdate(BaseSchema):
    """Schema for updating a user."""
    
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    """Schema for user response."""
    
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class UserLogin(BaseSchema):
    """Schema for user login."""
    
    username: str
    password: str


class Token(BaseSchema):
    """Schema for JWT token response."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseSchema):
    """Schema for JWT token payload."""
    
    sub: str  # user_id or username
    exp: datetime
    iat: datetime


# ============================================================================
# WhatsApp Webhook Schemas
# ============================================================================

class WhatsAppWebhookVerify(BaseSchema):
    """Schema for webhook verification request."""
    
    hub_mode: str = Field(..., alias="hub.mode")
    hub_challenge: str = Field(..., alias="hub.challenge")
    hub_verify_token: str = Field(..., alias="hub.verify_token")


class WhatsAppMessageContext(BaseSchema):
    """Schema for message context (reply reference)."""
    
    message_id: Optional[str] = None
    from_: Optional[str] = Field(None, alias="from")


class WhatsAppTextMessage(BaseSchema):
    """Schema for text message content."""
    
    body: str


class WhatsAppMediaMessage(BaseSchema):
    """Schema for media message content."""
    
    id: str
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None


class WhatsAppMessage(BaseSchema):
    """Schema for individual WhatsApp message."""
    
    from_: str = Field(..., alias="from")
    id: str
    timestamp: str
    type: str
    text: Optional[WhatsAppTextMessage] = None
    image: Optional[WhatsAppMediaMessage] = None
    document: Optional[WhatsAppMediaMessage] = None
    audio: Optional[WhatsAppMediaMessage] = None
    video: Optional[WhatsAppMediaMessage] = None
    sticker: Optional[WhatsAppMediaMessage] = None
    context: Optional[WhatsAppMessageContext] = None


class WhatsAppContact(BaseSchema):
    """Schema for WhatsApp contact info."""
    
    wa_id: str
    profile: Optional[dict] = None


class WhatsAppStatus(BaseSchema):
    """Schema for message status update."""
    
    id: str
    status: str
    timestamp: str
    recipient_id: Optional[str] = None
    errors: Optional[list[dict]] = None


class WhatsAppMetadata(BaseSchema):
    """Schema for webhook metadata."""
    
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseSchema):
    """Schema for webhook value payload."""
    
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: Optional[list[WhatsAppContact]] = None
    messages: Optional[list[WhatsAppMessage]] = None
    statuses: Optional[list[WhatsAppStatus]] = None


class WhatsAppChange(BaseSchema):
    """Schema for webhook change entry."""
    
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseSchema):
    """Schema for webhook entry."""
    
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhookPayload(BaseSchema):
    """Schema for complete webhook payload."""
    
    object: str
    entry: list[WhatsAppEntry]


# ============================================================================
# WebSocket Schemas
# ============================================================================

class WSMessage(BaseSchema):
    """Schema for WebSocket messages."""
    
    type: str  # message, typing, read, status_update, error
    payload: dict


class WSNewMessage(BaseSchema):
    """Schema for new message WebSocket event."""
    
    type: str = "new_message"
    message: MessageResponse
    conversation_id: int


class WSTypingIndicator(BaseSchema):
    """Schema for typing indicator WebSocket event."""
    
    type: str = "typing"
    conversation_id: int
    is_typing: bool


class WSStatusUpdate(BaseSchema):
    """Schema for status update WebSocket event."""
    
    type: str = "status_update"
    message_id: str
    status: str
    conversation_id: int


# ============================================================================
# API Response Schemas
# ============================================================================

class PaginatedResponse(BaseSchema):
    """Schema for paginated responses."""
    
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


class SuccessResponse(BaseSchema):
    """Schema for success responses."""
    
    success: bool = True
    message: str


class ErrorResponse(BaseSchema):
    """Schema for error responses."""
    
    success: bool = False
    error: str
    detail: Optional[Any] = None
