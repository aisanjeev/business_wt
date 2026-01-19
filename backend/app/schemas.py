"""Pydantic schemas for request/response validation."""

from datetime import datetime
from enum import Enum
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
    source: str = Field(default="manual", max_length=20)  # "imported", "chat", "manual"


class ContactCreate(ContactBase):
    """Schema for creating a contact."""
    pass


class ContactUpdate(BaseSchema):
    """Schema for updating a contact."""
    
    name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = Field(None, max_length=512)
    status: Optional[str] = Field(None, max_length=20)
    source: Optional[str] = Field(None, max_length=20)


class ContactResponse(ContactBase):
    """Schema for contact response."""
    
    id: int
    tags: Optional[list[str]] = Field(default_factory=list)
    list_ids: Optional[list[int]] = Field(default_factory=list)  # Populated from relationships
    blocked_at: Optional[datetime] = None
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
    last_message_sender_type: Optional[str] = None  # "inbound" or "outbound"
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
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None


class MessageSendByPhone(BaseSchema):
    """Schema for sending a message to WhatsApp by phone number (creates/finds contact and conversation)."""
    
    phone_number: str = Field(..., min_length=10, max_length=20)
    content: str
    message_type: str = "text"
    contact_name: Optional[str] = Field(None, max_length=255)


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
    category: str = Field(default="utility", max_length=50)  # marketing, utility, authentication
    language: str = Field(default="en", max_length=10)
    # Template structure
    header_type: Optional[str] = Field(None, max_length=20)  # TEXT, IMAGE, VIDEO, DOCUMENT, None
    header_content: Optional[str] = None  # Header text or media URL
    body_text: str = Field(..., max_length=1024)  # Main message body with variables {{1}}, {{2}}
    footer_text: Optional[str] = Field(None, max_length=60)  # Footer text
    buttons: Optional[dict] = None  # JSON structure for buttons
    # Meta API fields
    waba_id: Optional[str] = Field(None, max_length=100)  # WhatsApp Business Account ID
    variables: Optional[dict] = Field(default_factory=dict)  # Variable definitions and sample data
    # Legacy fields (for backward compatibility)
    content: Optional[str] = None  # Legacy field, use body_text instead


class TemplateCreate(TemplateBase):
    """Schema for creating a template."""
    
    # Override body_text to be optional for drafts
    body_text: Optional[str] = Field(None, max_length=1024)
    # Optional fields for draft creation
    status: Optional[str] = Field(default="PENDING", max_length=20)


class TemplateUpdate(BaseSchema):
    """Schema for updating a template."""
    
    name: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    status: Optional[str] = Field(None, max_length=20)
    # Template structure
    header_type: Optional[str] = Field(None, max_length=20)
    header_content: Optional[str] = None
    body_text: Optional[str] = Field(None, max_length=1024)
    footer_text: Optional[str] = Field(None, max_length=60)
    buttons: Optional[dict] = None
    variables: Optional[dict] = None
    # Legacy field
    content: Optional[str] = None


class TemplateResponse(TemplateBase):
    """Schema for template response."""
    
    id: int
    user_id: int
    # Meta API fields
    meta_template_id: Optional[str] = None  # Meta API template ID
    template_id: Optional[str] = None  # Legacy field
    waba_id: Optional[str] = None
    status: str  # PENDING, APPROVED, REJECTED, DISABLED, FLAGGED
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TemplatePreviewRequest(BaseSchema):
    """Schema for template preview request."""
    
    sample_variables: Optional[dict] = Field(default_factory=dict)  # Sample data for variables


class TemplatePreviewResponse(BaseSchema):
    """Schema for template preview response."""
    
    header: Optional[str] = None
    body: str
    footer: Optional[str] = None
    buttons: Optional[list] = None


class TemplateSyncResponse(BaseSchema):
    """Schema for template sync response."""
    
    success: bool
    created: int = 0
    updated: int = 0
    errors: list[str] = Field(default_factory=list)
    message: Optional[str] = None


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


class AdminUserCreate(UserCreate):
    """Schema for admin creating a user."""
    
    is_superuser: bool = False
    is_active: bool = True


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
    
    email: EmailStr
    password: str


class Token(BaseSchema):
    """Schema for JWT token response."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional["UserResponse"] = None


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
# Contact List Folder Schemas
# ============================================================================

class ContactListFolderBase(BaseSchema):
    """Base contact list folder schema."""
    
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern="^#[0-9A-Fa-f]{6}$")
    parent_folder_id: Optional[int] = None


class ContactListFolderCreate(ContactListFolderBase):
    """Schema for creating a contact list folder."""
    pass


class ContactListFolderUpdate(BaseSchema):
    """Schema for updating a contact list folder."""
    
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern="^#[0-9A-Fa-f]{6}$")
    parent_folder_id: Optional[int] = None


class ContactListFolderResponse(ContactListFolderBase):
    """Schema for contact list folder response."""
    
    id: int
    user_id: int
    lists_count: Optional[int] = 0  # Number of lists in this folder
    created_at: datetime
    updated_at: datetime


class MoveFolderRequest(BaseSchema):
    """Schema for moving a folder to another folder."""
    
    parent_folder_id: Optional[int] = None  # None means move to root


# ============================================================================
# Contact List Schemas
# ============================================================================

class ContactListBase(BaseSchema):
    """Base contact list schema."""
    
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern="^#[0-9A-Fa-f]{6}$")
    folder_id: Optional[int] = None


class ContactListCreate(ContactListBase):
    """Schema for creating a contact list."""
    pass


class ContactListUpdate(BaseSchema):
    """Schema for updating a contact list."""
    
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7, pattern="^#[0-9A-Fa-f]{6}$")
    folder_id: Optional[int] = None


class ContactListResponse(ContactListBase):
    """Schema for contact list response."""
    
    id: int
    user_id: int
    contacts_count: Optional[int] = 0  # Number of contacts in this list
    created_at: datetime
    updated_at: datetime


class ContactListMembershipResponse(BaseSchema):
    """Schema for contact list membership response."""
    
    contact_list_id: int
    contact_id: int
    added_at: datetime


class MoveListRequest(BaseSchema):
    """Schema for moving a list to another folder."""
    
    folder_id: Optional[int] = None  # None means move to root


# ============================================================================
# Meta Account Connection Schemas
# ============================================================================

class MetaAccountConnectionBase(BaseSchema):
    """Base Meta account connection schema."""
    
    meta_business_account_id: str = Field(..., max_length=100)
    phone_number_id: str = Field(..., max_length=100)
    business_phone_number: Optional[str] = Field(None, max_length=20)
    status: str = Field(default="pending_verification", max_length=20)
    business_verification_status: str = Field(default="unverified", max_length=20)
    webhook_url: Optional[str] = Field(None, max_length=512)
    usage_tracking_enabled: bool = True


class MetaAccountConnectionCreate(MetaAccountConnectionBase):
    """Schema for creating Meta account connection."""
    
    access_token: str
    refresh_token: Optional[str] = None


class MetaAccountConnectionUpdate(BaseSchema):
    """Schema for updating Meta account connection."""
    
    status: Optional[str] = Field(None, max_length=20)
    business_verification_status: Optional[str] = Field(None, max_length=20)
    webhook_url: Optional[str] = Field(None, max_length=512)
    usage_tracking_enabled: Optional[bool] = None


class MetaAccountConnectionResponse(MetaAccountConnectionBase):
    """Schema for Meta account connection response."""
    
    id: int
    user_id: int
    connected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# OAuth Exchange Schemas
class OAuthExchangeRequest(BaseSchema):
    """Schema for OAuth code exchange request."""
    
    code: str = Field(..., description="Authorization code from Meta")


class BusinessAccountInfo(BaseSchema):
    """Schema for Meta Business Account information."""
    
    id: str
    name: Optional[str] = None
    timezone_id: Optional[str] = None
    primary_page_id: Optional[str] = None


class PhoneNumberInfo(BaseSchema):
    """Schema for WhatsApp phone number information."""
    
    id: str
    display_phone_number: Optional[str] = None
    verified_name: Optional[str] = None
    code_verification_status: Optional[str] = None
    eligibility_for_api_business_global_search: Optional[str] = None


class OAuthExchangeResponse(BaseSchema):
    """Schema for OAuth exchange response."""
    
    access_token: str
    expires_in: int
    business_accounts: list[BusinessAccountInfo]
    phone_numbers: list[PhoneNumberInfo]  # Phone numbers for the first business account


class ConnectionCompleteRequest(BaseSchema):
    """Schema for completing Meta connection with selected phone number."""
    
    business_account_id: str = Field(..., description="Meta Business Account ID")
    phone_number_id: str = Field(..., description="WhatsApp Phone Number ID")
    access_token: str = Field(..., description="Access token from OAuth exchange")
    business_phone_number: Optional[str] = Field(None, description="Display phone number")


# ============================================================================
# API Usage Schemas
# ============================================================================

class ApiUsageBase(BaseSchema):
    """Base API usage schema."""
    
    meta_phone_number_id: Optional[str] = Field(None, max_length=100)
    message_type: str = Field(..., max_length=20)
    api_endpoint: str = Field(..., max_length=255)
    response_status: int
    estimated_cost: Optional[str] = Field(None, max_length=20)
    request_id: Optional[str] = Field(None, max_length=100)


class ApiUsageResponse(ApiUsageBase):
    """Schema for API usage response."""
    
    id: int
    user_id: int
    timestamp: datetime


class UsageStatsResponse(BaseSchema):
    """Schema for usage statistics response."""
    
    user_id: int
    total_messages: int
    total_api_calls: int
    total_cost: float
    period_start: datetime
    period_end: datetime
    breakdown_by_type: dict[str, int] = Field(default_factory=dict)


class UsageCostResponse(BaseSchema):
    """Schema for usage cost response."""
    
    user_id: int
    total_cost: float
    period_start: datetime
    period_end: datetime
    cost_breakdown: dict[str, float] = Field(default_factory=dict)  # by message_type


# ============================================================================
# Contact List Folder Schemas
# ============================================================================

class ContactListFolderBase(BaseSchema):
    """Base contact list folder schema."""
    
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7)
    parent_folder_id: Optional[int] = None


class ContactListFolderCreate(ContactListFolderBase):
    """Schema for creating a contact list folder."""
    pass


class ContactListFolderUpdate(BaseSchema):
    """Schema for updating a contact list folder."""
    
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7)
    parent_folder_id: Optional[int] = None


class ContactListFolderResponse(ContactListFolderBase):
    """Schema for contact list folder response."""
    
    id: int
    user_id: int
    lists_count: Optional[int] = 0  # Number of lists in this folder
    created_at: datetime
    updated_at: datetime


class MoveFolderRequest(BaseSchema):
    """Schema for moving a folder to another folder."""
    
    parent_folder_id: Optional[int] = None  # None means move to root


# ============================================================================
# Contact List Schemas
# ============================================================================

class ContactListBase(BaseSchema):
    """Base contact list schema."""
    
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7)
    folder_id: Optional[int] = None


class ContactListCreate(ContactListBase):
    """Schema for creating a contact list."""
    pass


class ContactListUpdate(BaseSchema):
    """Schema for updating a contact list."""
    
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=7)
    folder_id: Optional[int] = None


class ContactListResponse(ContactListBase):
    """Schema for contact list response."""
    
    id: int
    user_id: int
    contacts_count: Optional[int] = 0  # Number of contacts in this list
    created_at: datetime
    updated_at: datetime


class ContactListMembershipResponse(BaseSchema):
    """Schema for contact list membership response."""
    
    contact_list_id: int
    contact_id: int
    added_at: datetime


class MoveListRequest(BaseSchema):
    """Schema for moving a list to another folder."""
    
    folder_id: Optional[int] = None  # None means move to root


# ============================================================================
# Contact Import Schemas
# ============================================================================

class ContactImportBase(BaseSchema):
    """Base contact import schema."""
    
    filename: str = Field(..., max_length=255)
    file_format: str = Field(..., max_length=10)  # csv, excel, json


class ContactImportCreate(ContactImportBase):
    """Schema for creating contact import."""
    
    contact_list_id: Optional[int] = Field(None, description="Contact list to import contacts into")


class ContactImportResponse(ContactImportBase):
    """Schema for contact import response."""
    
    id: int
    user_id: int
    status: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    error_log: Optional[dict] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ContactImportStatus(BaseSchema):
    """Schema for contact import status check."""
    
    id: int
    status: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    progress_percentage: float


# ============================================================================
# Bulk Message Campaign Schemas
# ============================================================================

class BulkMessageCampaignBase(BaseSchema):
    """Base bulk message campaign schema."""
    
    name: str = Field(..., max_length=255)
    template_id: Optional[int] = None
    template_variables: Optional[dict] = None  # Template variable values
    target_contacts: Optional[dict] = None  # Filter criteria or contact list
    message_content: str


class BulkMessageCampaignCreate(BulkMessageCampaignBase):
    """Schema for creating bulk message campaign."""
    
    scheduled_at: Optional[datetime] = None
    list_ids: Optional[list[int]] = Field(None, description="Contact list IDs to target")
    tag_names: Optional[list[str]] = Field(None, description="Tag names to filter contacts by")
    contact_ids: Optional[list[int]] = Field(None, description="Direct contact IDs (optional)")


class BulkMessageCampaignUpdate(BaseSchema):
    """Schema for updating bulk message campaign."""
    
    name: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = Field(None, max_length=20)
    message_content: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class BulkMessageCampaignResponse(BulkMessageCampaignBase):
    """Schema for bulk message campaign response."""
    
    id: int
    user_id: int
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CampaignStatusResponse(BaseSchema):
    """Schema for campaign status response."""
    
    id: int
    status: str
    total_recipients: int
    sent_count: int
    failed_count: int
    progress_percentage: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


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
