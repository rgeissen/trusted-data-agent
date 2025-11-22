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
            "rag_collections": [],  # Empty - default collection created by RAGRetriever
            "mcp_servers": [],  # MCP server configurations
            "active_mcp_server_id": None,  # ID of currently active MCP server
            "profiles": [],  # Profile configurations
            "default_profile_id": None,  # ID of the default profile
            "active_for_consumption_profile_ids": []  # IDs of profiles active for consumption
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
    
    # ========================================================================
    # MCP SERVER CONFIGURATION METHODS
    # ========================================================================
    
    def get_mcp_servers(self) -> list:
        """
        Get all MCP server configurations.
        
        Returns:
            List of MCP server configuration dictionaries
        """
        config = self.load_config()
        return config.get("mcp_servers", [])
    
    def save_mcp_servers(self, servers: list) -> bool:
        """
        Save MCP server configurations.
        
        Args:
            servers: List of MCP server configuration dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        config = self.load_config()
        config["mcp_servers"] = servers
        return self.save_config(config)
    
    def add_mcp_server(self, server: Dict[str, Any]) -> bool:
        """
        Add a new MCP server configuration.
        
        Args:
            server: MCP server configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        servers = self.get_mcp_servers()
        servers.append(server)
        return self.save_mcp_servers(servers)
    
    def update_mcp_server(self, server_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing MCP server configuration.
        
        Args:
            server_id: Unique ID of the server to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        servers = self.get_mcp_servers()
        server = next((s for s in servers if s.get("id") == server_id), None)
        
        if not server:
            app_logger.warning(f"MCP server with ID {server_id} not found for update")
            return False
        
        server.update(updates)
        return self.save_mcp_servers(servers)
    
    def remove_mcp_server(self, server_id: str) -> tuple[bool, Optional[str]]:
        """
        Remove an MCP server configuration.
        Prevents deletion if any RAG collections are assigned to this server.
        
        Args:
            server_id: Unique ID of the server to remove
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
            If successful, error_message is None
            If failed, error_message contains the reason
        """
        # Check if any collections are assigned to this server
        collections = self.get_rag_collections()
        assigned_collections = [
            c for c in collections 
            if c.get("mcp_server_id") == server_id
        ]
        
        if assigned_collections:
            collection_names = [c.get("name", "Unknown") for c in assigned_collections]
            names_list = ", ".join(collection_names)
            error_msg = f"Cannot delete MCP server: {len(assigned_collections)} collection(s) assigned: {names_list}"
            app_logger.warning(f"{error_msg} (Server ID: {server_id})")
            return False, error_msg
        
        servers = self.get_mcp_servers()
        original_count = len(servers)
        servers = [s for s in servers if s.get("id") != server_id]
        
        if len(servers) == original_count:
            error_msg = "MCP server not found"
            app_logger.warning(f"MCP server with ID {server_id} not found for removal")
            return False, error_msg
        
        success = self.save_mcp_servers(servers)
        return success, None if success else "Failed to save configuration"
    
    def get_active_mcp_server_id(self) -> Optional[str]:
        """
        Get the ID of the currently active MCP server.
        
        Returns:
            Active MCP server ID or None
        """
        config = self.load_config()
        return config.get("active_mcp_server_id")
    
    def set_active_mcp_server_id(self, server_id: Optional[str]) -> bool:
        """
        Set the active MCP server ID.
        
        Args:
            server_id: ID of the server to set as active, or None to clear
            
        Returns:
            True if successful, False otherwise
        """
        config = self.load_config()
        config["active_mcp_server_id"] = server_id
        return self.save_config(config)

    # ========================================================================
    # PROFILE CONFIGURATION METHODS
    # ========================================================================

    def get_profiles(self) -> list:
        """
        Get all profile configurations.
        
        Returns:
            List of profile configuration dictionaries
        """
        config = self.load_config()
        return config.get("profiles", [])

    def save_profiles(self, profiles: list) -> bool:
        """
        Save profile configurations.
        
        Args:
            profiles: List of profile configuration dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        config = self.load_config()
        config["profiles"] = profiles
        return self.save_config(config)

    def add_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Add a new profile configuration.
        
        Args:
            profile: Profile configuration dictionary
            
        Returns:
            True if successful, False otherwise
        """
        profiles = self.get_profiles()
        profiles.append(profile)
        return self.save_profiles(profiles)

    def update_profile(self, profile_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing profile configuration.
        
        Args:
            profile_id: Unique ID of the profile to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        profiles = self.get_profiles()
        profile = next((p for p in profiles if p.get("id") == profile_id), None)
        
        if not profile:
            app_logger.warning(f"Profile with ID {profile_id} not found for update")
            return False
        
        profile.update(updates)
        return self.save_profiles(profiles)

    def remove_profile(self, profile_id: str) -> bool:
        """
        Remove a profile configuration.
        
        Args:
            profile_id: Unique ID of the profile to remove
            
        Returns:
            True if successful, False otherwise
        """
        profiles = self.get_profiles()
        original_count = len(profiles)
        profiles = [p for p in profiles if p.get("id") != profile_id]
        
        if len(profiles) == original_count:
            app_logger.warning(f"Profile with ID {profile_id} not found for removal")
            return False
        
        return self.save_profiles(profiles)

    def get_default_profile_id(self) -> Optional[str]:
        """
        Get the ID of the currently default profile.
        
        Returns:
            Default profile ID or None
        """
        config = self.load_config()
        return config.get("default_profile_id")

    def set_default_profile_id(self, profile_id: Optional[str]) -> bool:
        """
        Set the default profile ID.
        
        Args:
            profile_id: ID of the profile to set as default, or None to clear
            
        Returns:
            True if successful, False otherwise
        """
        config = self.load_config()
        config["default_profile_id"] = profile_id
        return self.save_config(config)

    def get_active_for_consumption_profile_ids(self) -> list:
        """
        Get the IDs of the profiles active for consumption.
        
        Returns:
            List of active profile IDs
        """
        config = self.load_config()
        return config.get("active_for_consumption_profile_ids", [])

    def set_active_for_consumption_profile_ids(self, profile_ids: list) -> bool:
        """
        Set the IDs of the profiles active for consumption.
        
        Args:
            profile_ids: List of profile IDs to set as active
            
        Returns:
            True if successful, False otherwise
        """
        config = self.load_config()
        config["active_for_consumption_profile_ids"] = profile_ids
        return self.save_config(config)


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
