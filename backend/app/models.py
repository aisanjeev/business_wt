"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Contact(Base):
    """Contact model - stores information about leads/customers."""
    
    __tablename__ = "contacts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    phone_number: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    business_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", index=True
    )
    source: Mapped[str] = mapped_column(
        String(20), default="manual", index=True
    )  # "imported", "chat", "manual"
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="contacts")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="contact", cascade="all, delete-orphan"
    )
    list_memberships: Mapped[list["ContactListMembership"]] = relationship(
        "ContactListMembership", back_populates="contact", cascade="all, delete-orphan"
    )
    lists: Mapped[list["ContactList"]] = relationship(
        "ContactList", secondary="contact_list_memberships", back_populates="contacts"
    )
    
    __table_args__ = (
        Index("idx_contacts_created_at", "created_at"),
        Index("idx_contacts_user_phone", "user_id", "phone_number", unique=True),
    )
    
    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, phone={self.phone_number}, name={self.name})>"


class Conversation(Base):
    """Conversation model - represents individual chat threads."""
    
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    thread_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    unread_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    contact: Mapped["Contact"] = relationship("Contact", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_conversations_created_at", "created_at"),
        Index("idx_conversations_last_message_at", "last_message_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, contact_id={self.contact_id})>"


class MessageStatus:
    """Message status constants."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class SenderType:
    """Sender type constants."""
    INBOUND = "inbound"  # From customer
    OUTBOUND = "outbound"  # From business


class MessageType:
    """Message type constants."""
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


class Message(Base):
    """Message model - stores all messages in conversations."""
    
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )
    sender_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # inbound or outbound
    message_type: Mapped[str] = mapped_column(
        String(20), default="text"
    )  # text, image, document, audio, etc.
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    media_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    media_mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    media_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, sent, delivered, read, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
    
    __table_args__ = (
        Index("idx_messages_created_at", "created_at"),
        Index("idx_messages_timestamp", "timestamp"),
        Index("idx_messages_conversation_status", "conversation_id", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<Message(id={self.id}, type={self.sender_type}, status={self.status})>"


class MessageTemplate(Base):
    """Message template model - stores approved WhatsApp message templates."""
    
    __tablename__ = "message_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    template_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="utility"
    )  # marketing, utility, authentication
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )  # active, inactive, pending, rejected
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="templates")
    
    __table_args__ = (
        Index("idx_templates_category", "category"),
        Index("idx_templates_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<MessageTemplate(id={self.id}, name={self.name})>"


class User(Base):
    """User model - for dashboard authentication."""
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    templates: Mapped[list["MessageTemplate"]] = relationship(
        "MessageTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    meta_connection: Mapped[Optional["MetaAccountConnection"]] = relationship(
        "MetaAccountConnection", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    
    # Subscription fields (no enforcement logic yet)
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free", index=True)
    subscription_status: Mapped[str] = mapped_column(String(20), default="active")
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    max_contacts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    max_messages_per_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    max_campaigns_per_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    max_lists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    
    media_files: Mapped[list["MediaFile"]] = relationship(
        "MediaFile", back_populates="user", cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class MediaFile(Base):
    """Media file model - tracks files stored in Azure Blob Storage."""
    
    __tablename__ = "media_files"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    blob_name: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="media_files")
    
    def __repr__(self) -> str:
        return f"<MediaFile(id={self.id}, blob_name={self.blob_name}, size={self.file_size_bytes})>"


class MetaAccountConnection(Base):
    """Meta account connection - stores customer's Meta account credentials."""
    
    __tablename__ = "meta_account_connections"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    meta_business_account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    business_phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)  # Encrypted
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted
    status: Mapped[str] = mapped_column(
        String(20), default="pending_verification", index=True
    )  # connected, disconnected, pending_verification
    business_verification_status: Mapped[str] = mapped_column(
        String(20), default="unverified"
    )  # verified, unverified
    webhook_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    usage_tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="meta_connection")
    
    __table_args__ = (
        Index("idx_meta_connections_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<MetaAccountConnection(id={self.id}, user_id={self.user_id}, status={self.status})>"


class ApiUsage(Base):
    """API usage tracking - tracks API calls per user/customer."""
    
    __tablename__ = "api_usage"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meta_phone_number_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False)  # text, template, media
    api_endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_cost: Mapped[Optional[float]] = mapped_column(String(20), nullable=True)  # Store as string for precision
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        Index("idx_api_usage_user_timestamp", "user_id", "timestamp"),
        Index("idx_api_usage_timestamp", "timestamp"),
    )
    
    def __repr__(self) -> str:
        return f"<ApiUsage(id={self.id}, user_id={self.user_id}, endpoint={self.api_endpoint})>"


class ContactImport(Base):
    """Contact import - tracks bulk import jobs."""
    
    __tablename__ = "contact_imports"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False)  # csv, excel, json
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, processing, completed, failed
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    successful_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    
    __table_args__ = (
        Index("idx_contact_imports_status", "status"),
        Index("idx_contact_imports_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ContactImport(id={self.id}, user_id={self.user_id}, status={self.status})>"


class BulkMessageCampaign(Base):
    """Bulk message campaign - tracks bulk message campaigns."""
    
    __tablename__ = "bulk_message_campaigns"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("message_templates.id", ondelete="SET NULL"), nullable=True
    )
    target_contacts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Filter criteria or contact list
    message_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", index=True
    )  # draft, scheduled, sending, completed, failed
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    template: Mapped[Optional["MessageTemplate"]] = relationship("MessageTemplate")
    
    __table_args__ = (
        Index("idx_campaigns_status", "status"),
        Index("idx_campaigns_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<BulkMessageCampaign(id={self.id}, user_id={self.user_id}, name={self.name})>"


class CampaignRecipientLog(Base):
    """Campaign recipient log - tracks individual recipient status for campaign messages."""
    
    __tablename__ = "campaign_recipient_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bulk_message_campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, sent, delivered, read, failed
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Store as string for precision
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    
    # Relationships
    campaign: Mapped["BulkMessageCampaign"] = relationship("BulkMessageCampaign")
    contact: Mapped["Contact"] = relationship("Contact")
    message: Mapped[Optional["Message"]] = relationship("Message")
    
    __table_args__ = (
        Index("idx_campaign_logs_campaign_status", "campaign_id", "status"),
        Index("idx_campaign_logs_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CampaignRecipientLog(id={self.id}, campaign_id={self.campaign_id}, phone={self.phone_number}, status={self.status})>"


class ContactListFolder(Base):
    """Contact list folder - organizes contact lists into folders."""
    
    __tablename__ = "contact_list_folders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color code
    parent_folder_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("contact_list_folders.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    parent_folder: Mapped[Optional["ContactListFolder"]] = relationship(
        "ContactListFolder", remote_side=[id], back_populates="child_folders"
    )
    child_folders: Mapped[list["ContactListFolder"]] = relationship(
        "ContactListFolder", back_populates="parent_folder", cascade="all, delete-orphan"
    )
    lists: Mapped[list["ContactList"]] = relationship(
        "ContactList", back_populates="folder", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_contact_list_folders_user_id", "user_id"),
        Index("idx_contact_list_folders_parent_folder_id", "parent_folder_id"),
    )
    
    def __repr__(self) -> str:
        return f"<ContactListFolder(id={self.id}, name={self.name}, user_id={self.user_id})>"


class ContactList(Base):
    """Contact list - groups contacts for campaigns and organization."""
    
    __tablename__ = "contact_lists"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("contact_list_folders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color code
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User")
    folder: Mapped[Optional["ContactListFolder"]] = relationship(
        "ContactListFolder", back_populates="lists"
    )
    memberships: Mapped[list["ContactListMembership"]] = relationship(
        "ContactListMembership", back_populates="contact_list", cascade="all, delete-orphan"
    )
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", secondary="contact_list_memberships", back_populates="lists"
    )
    
    __table_args__ = (
        Index("idx_contact_lists_user_id", "user_id"),
        Index("idx_contact_lists_folder_id", "folder_id"),
    )
    
    def __repr__(self) -> str:
        return f"<ContactList(id={self.id}, name={self.name}, user_id={self.user_id})>"


class ContactListMembership(Base):
    """Junction table for many-to-many relationship between Contact and ContactList."""
    
    __tablename__ = "contact_list_memberships"
    
    contact_list_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contact_lists.id", ondelete="CASCADE"), primary_key=True
    )
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    
    # Relationships
    contact_list: Mapped["ContactList"] = relationship("ContactList", back_populates="memberships")
    contact: Mapped["Contact"] = relationship("Contact", back_populates="list_memberships")
    
    __table_args__ = (
        Index("idx_contact_list_memberships_contact_id", "contact_id"),
        Index("idx_contact_list_memberships_contact_list_id", "contact_list_id"),
    )
    
    def __repr__(self) -> str:
        return f"<ContactListMembership(contact_list_id={self.contact_list_id}, contact_id={self.contact_id})>"
