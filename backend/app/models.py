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
    phone_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    business_account_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    
    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="contact", cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_contacts_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, phone={self.phone_number}, name={self.name})>"


class Conversation(Base):
    """Conversation model - represents individual chat threads."""
    
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    thread_id: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True
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
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"
