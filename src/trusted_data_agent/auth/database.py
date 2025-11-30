"""
Database connection and initialization for authentication.

Manages SQLAlchemy engine, session factory, and database initialization.
"""

import os
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from trusted_data_agent.auth.models import Base

# Get logger
logger = logging.getLogger("quart.app")

# Database configuration
DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "tda_auth.db"
DATABASE_URL = os.environ.get(
    'TDA_AUTH_DB_URL',
    f'sqlite:///{DEFAULT_DB_PATH}'
)

# Create engine
# Use StaticPool for SQLite to avoid threading issues
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=os.environ.get('TDA_SQL_ECHO', 'false').lower() == 'true'
    )
    
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL or other databases
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        echo=os.environ.get('TDA_SQL_ECHO', 'false').lower() == 'true'
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """
    Initialize the database by creating all tables.
    Safe to call multiple times (won't recreate existing tables).
    
    On first initialization, creates a default admin account.
    """
    try:
        logger.info(f"Initializing authentication database at: {DATABASE_URL}")
        Base.metadata.create_all(bind=engine)
        logger.info("Authentication database initialized successfully")
        
        # Create collections table (for marketplace)
        _create_collections_table()
        
        # Create template defaults table (for template configuration)
        _create_template_defaults_table()
        
        # Create default admin account if no users exist
        _create_default_admin_if_needed()
        
        # Initialize system settings
        _initialize_default_system_settings()
        
        # Initialize document upload configurations
        _initialize_document_upload_configs()
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize authentication database: {e}", exc_info=True)
        return False


def _create_collections_table():
    """
    Create the collections table for the marketplace feature.
    Safe to call multiple times (won't recreate if exists).
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(DATABASE_URL.replace('sqlite:///', ''))
        cursor = conn.cursor()
        
        # Create collections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                collection_name VARCHAR(255) NOT NULL UNIQUE,
                mcp_server_id VARCHAR(100),
                enabled BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL,
                description TEXT,
                owner_user_id VARCHAR(36) NOT NULL,
                visibility VARCHAR(20) NOT NULL DEFAULT 'private',
                is_marketplace_listed BOOLEAN NOT NULL DEFAULT 0,
                subscriber_count INTEGER NOT NULL DEFAULT 0,
                marketplace_category VARCHAR(50),
                marketplace_tags TEXT,
                marketplace_long_description TEXT,
                repository_type TEXT DEFAULT 'planner',
                chunking_strategy TEXT DEFAULT 'none',
                chunk_size INTEGER DEFAULT 1000,
                chunk_overlap INTEGER DEFAULT 200,
                FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_owner ON collections(owner_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_marketplace ON collections(is_marketplace_listed, visibility)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collections_name ON collections(collection_name)")
        
        # Create document_chunks table for Knowledge repositories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                document_id TEXT NOT NULL,
                chunk_id TEXT UNIQUE NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                embedding_model TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_collection ON document_chunks(collection_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id)")
        
        # Create knowledge_documents table for tracking original documents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                document_id TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                document_type TEXT,
                title TEXT,
                author TEXT,
                source TEXT,
                category TEXT,
                tags TEXT,
                file_size INTEGER,
                page_count INTEGER,
                content_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                metadata TEXT,
                FOREIGN KEY (collection_id) REFERENCES collections (id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_docs_collection ON knowledge_documents(collection_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_docs_category ON knowledge_documents(category)")
        
        # Create collection_subscriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_subscriptions (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                source_collection_id INTEGER NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                subscribed_at DATETIME NOT NULL,
                last_synced_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (source_collection_id) REFERENCES collections(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_subscription_user_collection ON collection_subscriptions(user_id, source_collection_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_user ON collection_subscriptions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscription_collection ON collection_subscriptions(source_collection_id)")
        
        conn.commit()
        conn.close()
        
        logger.info("Collections and subscriptions tables initialized successfully")
        
    except Exception as e:
        logger.error(f"Error creating collections table: {e}", exc_info=True)


def _create_template_defaults_table():
    """
    Create the template_defaults table for storing user/system template parameter overrides.
    Safe to call multiple times (won't recreate if exists).
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(DATABASE_URL.replace('sqlite:///', ''))
        cursor = conn.cursor()
        
        # Create template_defaults table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS template_defaults (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id VARCHAR(100) NOT NULL,
                user_id VARCHAR(36),
                parameter_name VARCHAR(100) NOT NULL,
                parameter_value TEXT NOT NULL,
                parameter_type VARCHAR(20) NOT NULL,
                is_system_default BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                updated_by VARCHAR(36),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE(template_id, user_id, parameter_name)
            )
        """)
        
        # Create indexes for efficient queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_defaults_template ON template_defaults(template_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_defaults_user ON template_defaults(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_defaults_system ON template_defaults(is_system_default)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_template_defaults_lookup ON template_defaults(template_id, user_id)")
        
        conn.commit()
        conn.close()
        
        logger.info("Template defaults table initialized successfully")
        
    except Exception as e:
        logger.error(f"Error creating template defaults table: {e}", exc_info=True)


def _create_default_admin_if_needed():
    """
    Create default admin account (admin/admin) if no users exist in the database.
    This runs only once on first database initialization.
    """
    from trusted_data_agent.auth.models import User
    from trusted_data_agent.auth.security import hash_password
    
    try:
        with get_db_session() as session:
            # Check if any users exist
            user_count = session.query(User).count()
            
            if user_count == 0:
                # Create default admin account
                admin_user = User(
                    username='admin',
                    email='admin@example.com',
                    password_hash=hash_password('admin'),
                    is_admin=True,
                    is_active=True,
                    profile_tier='admin',
                    full_name='System Administrator'
                )
                session.add(admin_user)
                session.commit()
                
                logger.warning(
                    "⚠️  Default admin account created: username='admin', password='admin' "
                    "⚠️  CHANGE THIS PASSWORD IMMEDIATELY after first login!"
                )
            else:
                logger.info(f"Database already has {user_count} user(s), skipping default admin creation")
                
    except Exception as e:
        logger.error(f"Error checking/creating default admin account: {e}", exc_info=True)


def _initialize_default_system_settings():
    """
    Initialize default system settings if they don't exist.
    This includes rate limiting configuration.
    """
    from trusted_data_agent.auth.models import SystemSettings
    
    # Default rate limiting settings (disabled by default)
    default_settings = {
        'rate_limit_enabled': ('false', 'Enable or disable rate limiting system-wide'),
        'rate_limit_user_prompts_per_hour': ('100', 'Maximum prompts per hour for authenticated users'),
        'rate_limit_user_prompts_per_day': ('1000', 'Maximum prompts per day for authenticated users'),
        'rate_limit_user_configs_per_hour': ('10', 'Maximum configuration changes per hour for authenticated users'),
        'rate_limit_ip_login_per_minute': ('5', 'Maximum login attempts per minute per IP address'),
        'rate_limit_ip_register_per_hour': ('3', 'Maximum registrations per hour per IP address'),
        'rate_limit_ip_api_per_minute': ('60', 'Maximum API calls per minute per IP address'),
    }
    
    try:
        with get_db_session() as session:
            for key, (value, description) in default_settings.items():
                # Check if setting already exists
                existing = session.query(SystemSettings).filter_by(setting_key=key).first()
                if not existing:
                    setting = SystemSettings(
                        setting_key=key,
                        setting_value=value,
                        description=description
                    )
                    session.add(setting)
                    logger.debug(f"Initialized system setting: {key} = {value}")
            
            session.commit()
            logger.info("System settings initialized successfully")
            
    except Exception as e:
        logger.error(f"Error initializing system settings: {e}", exc_info=True)


def _initialize_document_upload_configs():
    """
    Initialize default document upload configurations for all LLM providers.
    Sets up sensible defaults that can be overridden by admins.
    """
    from trusted_data_agent.auth.models import DocumentUploadConfig
    
    # Default configurations for all supported providers
    # use_native_upload=True, enabled=True by default
    # Admins can override these settings via the UI
    default_providers = [
        'Google',      # Native File API support
        'Anthropic',   # Native base64 upload support
        'Amazon',      # Bedrock with Claude models
        'OpenAI',      # Vision models only
        'Azure',       # Vision deployments only
        'Friendli',    # Text extraction fallback
        'Ollama'       # Text extraction fallback
    ]
    
    try:
        with get_db_session() as session:
            for provider in default_providers:
                # Check if config already exists
                existing = session.query(DocumentUploadConfig).filter_by(provider=provider).first()
                if not existing:
                    config = DocumentUploadConfig(
                        provider=provider,
                        use_native_upload=True,
                        enabled=True,
                        max_file_size_mb=None,  # Use provider defaults from DocumentUploadConfig class
                        supported_formats_override=None,  # Use provider defaults
                        notes='Default configuration - auto-initialized'
                    )
                    session.add(config)
                    logger.debug(f"Initialized document upload config for provider: {provider}")
            
            session.commit()
            logger.info("Document upload configurations initialized successfully")
            
    except Exception as e:
        logger.error(f"Error initializing document upload configs: {e}", exc_info=True)


def drop_all_tables():
    """
    Drop all tables. USE WITH CAUTION - this is destructive!
    Only for development/testing.
    """
    if os.environ.get('TDA_ENV') == 'production':
        raise RuntimeError("Cannot drop tables in production environment")
    
    logger.warning("Dropping all authentication database tables")
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_session() as session:
            user = session.query(User).first()
    
    Automatically commits on success, rolls back on error.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        session.close()


def get_db():
    """
    Dependency injection function for FastAPI/Quart.
    Returns a database session that auto-closes.
    
    Usage in routes:
        db = next(get_db())
        try:
            # use db
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database on module import (authentication is always enabled)
init_database()
