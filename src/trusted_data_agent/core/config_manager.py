# src/trusted_data_agent/core/config_manager.py
"""
Persistent configuration management for TDA.
Handles saving and loading application configuration to/from tda_config.json.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

app_logger = logging.getLogger("quart.app")


class ConfigManager:
    """
    Manages persistent configuration stored in tda_config.json.
    
    The configuration file stores application objects that need to persist
    across application restarts, such as:
    - RAG collection metadata
    - User preferences (future)
    - Custom settings (future)
    """
    
    DEFAULT_CONFIG_FILENAME = "tda_config.json"
    
    # Schema version for future migration support
    CURRENT_SCHEMA_VERSION = "1.0"
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the config file. If None, uses project root.
        """
        if config_path is None:
            # Calculate project root (3 levels up from this file)
            project_root = Path(__file__).resolve().parents[3]
            config_path = project_root / self.DEFAULT_CONFIG_FILENAME
        
        self.config_path = Path(config_path)
        app_logger.info(f"ConfigManager initialized with path: {self.config_path}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Returns the default configuration structure.
        
        The default collection is NOT created here, but rather by RAGRetriever
        when it initializes, so it can use the current MCP server name.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "schema_version": self.CURRENT_SCHEMA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "rag_collections": []  # Empty - default collection created by RAGRetriever
        }
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from tda_config.json.
        
        If the file doesn't exist or is invalid, returns default configuration
        and creates the file.
        
        Returns:
            Configuration dictionary
        """
        try:
            if not self.config_path.exists():
                app_logger.info(f"Config file not found at {self.config_path}. Creating default config.")
                default_config = self._get_default_config()
                self.save_config(default_config)
                return default_config
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate schema version
            schema_version = config.get("schema_version", "unknown")
            if schema_version != self.CURRENT_SCHEMA_VERSION:
                app_logger.warning(
                    f"Config schema version mismatch. Expected {self.CURRENT_SCHEMA_VERSION}, "
                    f"got {schema_version}. Using existing config as-is."
                )
            
            app_logger.info(f"Loaded configuration from {self.config_path}")
            return config
            
        except json.JSONDecodeError as e:
            app_logger.error(f"Invalid JSON in config file: {e}. Using default config.")
            default_config = self._get_default_config()
            # Backup corrupted file
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix('.json.backup')
                self.config_path.rename(backup_path)
                app_logger.info(f"Backed up corrupted config to {backup_path}")
            self.save_config(default_config)
            return default_config
            
        except Exception as e:
            app_logger.error(f"Error loading config file: {e}. Using default config.", exc_info=True)
            return self._get_default_config()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to tda_config.json.
        
        Args:
            config: Configuration dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update last_modified timestamp
            config["last_modified"] = datetime.now(timezone.utc).isoformat()
            
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first, then rename (atomic operation)
            temp_path = self.config_path.with_suffix('.json.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_path.replace(self.config_path)
            
            app_logger.info(f"Saved configuration to {self.config_path}")
            return True
            
        except Exception as e:
            app_logger.error(f"Error saving config file: {e}", exc_info=True)
            return False
    
    def get_rag_collections(self) -> list:
        """
        Get RAG collections from the configuration.
        
        Returns:
            List of RAG collection metadata dictionaries
        """
        config = self.load_config()
        return config.get("rag_collections", [])
    
    def save_rag_collections(self, collections: list) -> bool:
        """
        Save RAG collections to the configuration.
        
        Args:
            collections: List of RAG collection metadata dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        config = self.load_config()
        config["rag_collections"] = collections
        return self.save_config(config)
    
    def add_rag_collection(self, collection_metadata: Dict[str, Any]) -> bool:
        """
        Add a new RAG collection to the configuration.
        
        Args:
            collection_metadata: Collection metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        collections = self.get_rag_collections()
        collections.append(collection_metadata)
        return self.save_rag_collections(collections)
    
    def update_rag_collection(self, collection_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update an existing RAG collection in the configuration.
        
        Args:
            collection_id: ID of the collection to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        collections = self.get_rag_collections()
        
        for collection in collections:
            if collection["id"] == collection_id:
                collection.update(updates)
                return self.save_rag_collections(collections)
        
        app_logger.warning(f"Collection with ID {collection_id} not found for update")
        return False
    
    def remove_rag_collection(self, collection_id: int) -> bool:
        """
        Remove a RAG collection from the configuration.
        
        Args:
            collection_id: ID of the collection to remove
            
        Returns:
            True if successful, False otherwise
        """
        if collection_id == 0:
            app_logger.warning("Cannot remove default collection (ID 0)")
            return False
        
        collections = self.get_rag_collections()
        original_count = len(collections)
        collections = [c for c in collections if c["id"] != collection_id]
        
        if len(collections) == original_count:
            app_logger.warning(f"Collection with ID {collection_id} not found for removal")
            return False
        
        return self.save_rag_collections(collections)


# Singleton instance
_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get the singleton ConfigManager instance.
    
    Returns:
        ConfigManager instance
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance
