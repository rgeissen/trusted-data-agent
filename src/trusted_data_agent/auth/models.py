"""
SQLAlchemy models for authentication.

Defines User, AuthToken, and related database models.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Index, text
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


class User(Base):
    """User model for authentication and profile management."""
    
    __tablename__ = 'users'
    
    # Primary fields
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(30), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Profile fields
    display_name = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Security fields
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    profile_tier = Column(String(20), default='user', nullable=False)  # user, developer, admin
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    auth_tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")
    credentials = relationship("UserCredential", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id='{self.id}', username='{self.username}', email='{self.email}')>"
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary for API responses."""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'profile_tier': self.profile_tier
        }
        
        if include_sensitive:
            data['failed_login_attempts'] = self.failed_login_attempts
            data['locked_until'] = self.locked_until.isoformat() if self.locked_until else None
        
        return data


class AuthToken(Base):
    """Authentication token model for session management."""
    
    __tablename__ = 'auth_tokens'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True, unique=True)
    
    # Token metadata
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    
    # Status
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="auth_tokens")
    
    # Indexes
    __table_args__ = (
        Index('idx_token_user_active', 'user_id', 'revoked', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<AuthToken(id='{self.id}', user_id='{self.user_id}', expires_at='{self.expires_at}')>"
    
    def is_valid(self):
        """Check if token is still valid."""
        now = datetime.now(timezone.utc)
        return not self.revoked and self.expires_at > now


class UserCredential(Base):
    """Encrypted credentials storage for user API keys."""
    
    __tablename__ = 'user_credentials'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # Amazon, Google, OpenAI, etc.
    credentials_encrypted = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="credentials")
    
    # Unique constraint: one credential set per user per provider
    __table_args__ = (
        Index('idx_user_provider', 'user_id', 'provider', unique=True),
    )
    
    def __repr__(self):
        return f"<UserCredential(user_id='{self.user_id}', provider='{self.provider}')>"


class UserPreference(Base):
    """User preferences and settings."""
    
    __tablename__ = 'user_preferences'
    
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    
    # UI preferences
    theme = Column(String(20), default='light')  # light, dark
    default_profile_id = Column(String(36), nullable=True)
    notification_enabled = Column(Boolean, default=True)
    
    # Extended preferences (JSON)
    preferences_json = Column(Text, nullable=True)  # Store as JSON string
    
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    def __repr__(self):
        return f"<UserPreference(user_id='{self.user_id}', theme='{self.theme}')>"


class AuditLog(Base):
    """Audit log for tracking user actions."""
    
    __tablename__ = 'audit_logs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Action details
    action = Column(String(50), nullable=False, index=True)  # login, logout, configure, execute, etc.
    resource = Column(String(255), nullable=True)  # endpoint path or resource identifier
    status = Column(String(20), nullable=False)  # success, failure
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Additional details
    details = Column(Text, nullable=True)  # JSON string for extensibility
    
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'timestamp'),
        Index('idx_audit_action_time', 'action', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AuditLog(action='{self.action}', user_id='{self.user_id}', status='{self.status}')>"


class PasswordResetToken(Base):
    """Temporary tokens for password reset flow."""
    
    __tablename__ = 'password_reset_tokens'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, index=True, unique=True)
    
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 1 hour expiry
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<PasswordResetToken(user_id='{self.user_id}', used={self.used})>"
    
    def is_valid(self):
        """Check if reset token is still valid."""
        now = datetime.now(timezone.utc)
        return not self.used and self.expires_at > now


class AccessToken(Base):
    """Long-lived access tokens for REST API authentication."""
    
    __tablename__ = 'access_tokens'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Token details
    token_prefix = Column(String(10), nullable=False, index=True)  # First 8 chars for display (e.g., "tda_abcd")
    token_hash = Column(String(255), nullable=False, index=True, unique=True)  # SHA256 hash of full token
    name = Column(String(100), nullable=False)  # User-friendly name (e.g., "Production Server")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)  # NULL = never expires
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    use_count = Column(Integer, default=0, nullable=False)
    last_ip_address = Column(String(45), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_access_token_user_active', 'user_id', 'revoked'),
    )
    
    def __repr__(self):
        return f"<AccessToken(id='{self.id}', name='{self.name}', prefix='{self.token_prefix}')>"
    
    def is_valid(self):
        """Check if access token is still valid."""
        if self.revoked:
            return False
        if self.expires_at:
            now = datetime.now(timezone.utc)
            # Handle both timezone-aware and timezone-naive datetimes
            expires_at = self.expires_at
            if expires_at.tzinfo is None:
                # If naive, assume it's UTC
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return expires_at > now
        return True
    
    def to_dict(self, include_token=False):
        """Convert access token to dictionary for API responses."""
        # Helper to ensure timezone-aware datetime for ISO format
        def to_iso(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                # Assume UTC if naive
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        
        data = {
            'id': self.id,
            'name': self.name,
            'token_prefix': self.token_prefix,
            'created_at': to_iso(self.created_at),
            'expires_at': to_iso(self.expires_at),
            'last_used_at': to_iso(self.last_used_at),
            'revoked': self.revoked,
            'revoked_at': to_iso(self.revoked_at),
            'use_count': self.use_count
        }
        return data


class PaneVisibility(Base):
    """Pane visibility configuration for tier-based access control."""
    
    __tablename__ = 'pane_visibility'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pane_id = Column(String(50), nullable=False, unique=True, index=True)  # conversation, executions, rag-maintenance, marketplace, credentials, admin
    pane_name = Column(String(100), nullable=False)  # Display name
    
    # Tier visibility flags
    visible_to_user = Column(Boolean, default=True, nullable=False)
    visible_to_developer = Column(Boolean, default=True, nullable=False)
    visible_to_admin = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    description = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<PaneVisibility(pane_id='{self.pane_id}', user={self.visible_to_user}, dev={self.visible_to_developer}, admin={self.visible_to_admin})>"
    
    def to_dict(self):
        """Convert pane visibility to dictionary for API responses."""
        return {
            'id': self.id,
            'pane_id': self.pane_id,
            'pane_name': self.pane_name,
            'visible_to_user': self.visible_to_user,
            'visible_to_developer': self.visible_to_developer,
            'visible_to_admin': self.visible_to_admin,
            'description': self.description,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SystemSettings(Base):
    """System-wide configuration settings including rate limiting."""
    
    __tablename__ = 'system_settings'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    setting_key = Column(String(100), nullable=False, unique=True, index=True)
    setting_value = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<SystemSettings(key='{self.setting_key}', value='{self.setting_value}')>"
    
    def to_dict(self):
        """Convert system setting to dictionary for API responses."""
        return {
            'id': self.id,
            'key': self.setting_key,
            'value': self.setting_value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CollectionSubscription(Base):
    """User subscriptions to shared marketplace RAG collections (reference-based)."""
    
    __tablename__ = 'collection_subscriptions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    source_collection_id = Column(Integer, nullable=False, index=True)  # References collection ID in tda_config.json
    
    # Subscription configuration
    enabled = Column(Boolean, default=True, nullable=False)  # Can be toggled on/off without unsubscribing
    
    # Timestamps
    subscribed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_synced_at = Column(DateTime(timezone=True), nullable=True)  # For future sync tracking
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_subscription_user_collection', 'user_id', 'source_collection_id', unique=True),
    )
    
    def __repr__(self):
        return f"<CollectionSubscription(user_id='{self.user_id}', collection_id={self.source_collection_id}, enabled={self.enabled})>"
    
    def to_dict(self):
        """Convert subscription to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'source_collection_id': self.source_collection_id,
            'enabled': self.enabled,
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else None,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None
        }


class CollectionRating(Base):
    """User ratings and reviews for marketplace RAG collections."""
    
    __tablename__ = 'collection_ratings'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collection_id = Column(Integer, nullable=False, index=True)  # References collection ID in tda_config.json
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Rating details
    rating = Column(Integer, nullable=False)  # 1-5 stars
    comment = Column(Text, nullable=True)  # Optional review text
    helpful_count = Column(Integer, default=0, nullable=False)  # For future "helpful" voting
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_rating_collection_user', 'collection_id', 'user_id', unique=True),
        Index('idx_rating_collection', 'collection_id'),
    )
    
    def __repr__(self):
        return f"<CollectionRating(collection_id={self.collection_id}, user_id='{self.user_id}', rating={self.rating})>"
    
    def to_dict(self, include_user_info: bool = False):
        """Convert rating to dictionary for API responses."""
        data = {
            'id': self.id,
            'collection_id': self.collection_id,
            'user_id': self.user_id,
            'rating': self.rating,
            'comment': self.comment,
            'helpful_count': self.helpful_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_user_info and self.user:
            data['username'] = self.user.username
            data['user_display_name'] = self.user.display_name or self.user.username
        
        return data


class DocumentUploadConfig(Base):
    """Configuration for document upload capabilities per LLM provider."""
    
    __tablename__ = 'document_upload_config'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), nullable=False, unique=True, index=True)  # Google, Anthropic, OpenAI, Amazon, Azure, Friendli, Ollama
    
    # Configuration flags
    use_native_upload = Column(Boolean, nullable=False, default=True)  # Whether to use native upload API or fallback to text extraction
    enabled = Column(Boolean, nullable=False, default=True)  # Whether this provider supports document upload at all
    
    # Override default limits (NULL = use provider defaults from DocumentUploadConfig class)
    max_file_size_mb = Column(Integer, nullable=True)  # Override default file size limit
    supported_formats_override = Column(Text, nullable=True)  # JSON array of formats like ["pdf", "docx", "txt"]
    
    # Additional configuration
    notes = Column(Text, nullable=True)  # Admin notes about why config was changed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<DocumentUploadConfig(provider='{self.provider}', enabled={self.enabled}, native={self.use_native_upload})>"
    
    def to_dict(self):
        """Convert document upload config to dictionary for API responses."""
        return {
            'id': self.id,
            'provider': self.provider,
            'use_native_upload': self.use_native_upload,
            'enabled': self.enabled,
            'max_file_size_mb': self.max_file_size_mb,
            'supported_formats_override': self.supported_formats_override,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LLMModelCost(Base):
    """LLM model pricing information for cost tracking and analytics."""
    
    __tablename__ = 'llm_model_costs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(50), nullable=False, index=True)  # Google, Anthropic, OpenAI, Amazon, Azure, Friendli, Ollama
    model = Column(String(100), nullable=False, index=True)  # Model name (e.g., gemini-2.0-flash, claude-3-5-haiku)
    
    # Pricing in USD per 1 million tokens
    input_cost_per_million = Column(Integer, nullable=False)  # Input token cost per 1M
    output_cost_per_million = Column(Integer, nullable=False)  # Output token cost per 1M
    
    # Metadata
    is_manual_entry = Column(Boolean, nullable=False, default=False)  # True if manually entered by admin
    is_fallback = Column(Boolean, nullable=False, default=False, index=True)  # True for fallback/default pricing
    source = Column(String(50), nullable=False)  # 'litellm', 'manual', 'system_default'
    last_updated = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, nullable=True)  # Admin notes
    
    # Unique constraint: one price per provider/model combination
    __table_args__ = (
        Index('idx_llm_cost_provider_model', 'provider', 'model', unique=True),
    )
    
    def __repr__(self):
        return f"<LLMModelCost(provider='{self.provider}', model='{self.model}', in=${self.input_cost_per_million}/1M, out=${self.output_cost_per_million}/1M)>"
    
    def to_dict(self):
        """Convert model cost to dictionary for API responses."""
        return {
            'id': self.id,
            'provider': self.provider,
            'model': self.model,
            'input_cost_per_million': self.input_cost_per_million,
            'output_cost_per_million': self.output_cost_per_million,
            'is_manual_entry': self.is_manual_entry,
            'is_fallback': self.is_fallback,
            'source': self.source,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'notes': self.notes
        }
