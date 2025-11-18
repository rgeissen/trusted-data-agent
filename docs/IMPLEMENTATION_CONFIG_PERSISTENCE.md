# TDA Configuration Persistence - Implementation Summary

## Overview
Successfully implemented a persistent configuration system using `tda_config.json` to store application objects that need to survive application restarts. The first object type implemented is ChromaDB collection metadata.

## Files Created

### 1. `/src/trusted_data_agent/core/config_manager.py`
**New module for configuration management**
- `ConfigManager` class handles all operations with `tda_config.json`
- Supports loading, saving, and validating configuration
- Provides dedicated methods for RAG collection management:
  - `get_rag_collections()` - Retrieve all collections
  - `save_rag_collections(collections)` - Save collections to config
  - `add_rag_collection(metadata)` - Add a single collection
  - `update_rag_collection(id, updates)` - Update collection metadata
  - `remove_rag_collection(id)` - Remove a collection
- Includes atomic file writes (write to temp file, then rename)
- Automatic backup of corrupted config files
- Singleton pattern via `get_config_manager()`

### 2. `/docs/tda_config.md`
**Documentation for the configuration file**
- Example JSON structure
- Field descriptions
- API endpoint reference
- Management notes and best practices

## Files Modified

### 1. `/src/trusted_data_agent/agent/rag_retriever.py`
**Integrated persistent config for RAG collections**

Changes:
- Imported `get_config_manager` from `config_manager`
- Modified `_ensure_default_collection()` to load/save from persistent config
- Updated `add_collection()` to persist new collections to config file
- Updated `remove_collection()` to remove from config file
- Updated `toggle_collection()` to persist enabled/disabled state

### 2. `/src/trusted_data_agent/core/configuration_service.py`
**Load config on application startup**

Changes:
- Imported `get_config_manager` from `config_manager`
- Added config loading before RAGRetriever initialization
- Syncs persistent config to `APP_STATE["rag_collections"]`
- Logs number of collections loaded

### 3. `/src/trusted_data_agent/api/rest_routes.py`
**Persist changes from API endpoints**

Changes:
- Updated `update_rag_collection()` endpoint to save changes to config file
- Import `get_config_manager` when needed

## Configuration Schema

```json
{
  "schema_version": "1.0",
  "created_at": "ISO-8601 timestamp",
  "last_modified": "ISO-8601 timestamp",
  "rag_collections": [
    {
      "id": 0,
      "name": "Display name",
      "collection_name": "Internal ChromaDB name",
      "mcp_server_id": "Associated MCP server (REQUIRED except for default)",
      "enabled": true,
      "created_at": "ISO-8601 timestamp",
      "description": "Optional description"
    }
  ]
}
```

## MCP Server Association Rules

**CRITICAL**: Collections must be associated with an MCP server to be active.

### Enforcement:
1. **Required Field**: `mcp_server_id` is REQUIRED when creating new collections
2. **Loading Logic**: Only collections matching `APP_CONFIG.CURRENT_MCP_SERVER_NAME` are loaded
3. **One-to-Many**: One MCP server can have multiple collections
4. **Default Collection**: ID 0 can have `null` mcp_server_id for backwards compatibility
5. **Auto-Reload**: Collections reload automatically when MCP server changes

## How It Works

### On Application Startup
1. `configuration_service.py` calls `get_config_manager()`
2. ConfigManager loads `tda_config.json` from project root
3. If file doesn't exist, creates default config with default collection (ID 0)
4. RAG collections are loaded into `APP_STATE["rag_collections"]`
5. RAGRetriever initializes **only collections matching current MCP server**

### When MCP Server Changes
1. User configures new MCP server via `/configure` endpoint
2. `configuration_service.py` detects MCP server change
3. Calls `retriever.reload_collections_for_mcp_server()`
4. All collections are unloaded from memory
5. Only collections matching new MCP server are loaded
6. Collections for other servers remain in config but inactive

### When Collections are Modified
1. User creates/updates/deletes collection via UI or REST API
2. API endpoint calls corresponding method on RAGRetriever
3. RAGRetriever updates `APP_STATE["rag_collections"]`
4. RAGRetriever calls `config_manager.save_rag_collections()`
5. ConfigManager writes updated config to disk atomically

### Collection Loading Rules
A collection is loaded into memory if ALL of these are true:
1. `enabled` is `true`
2. EITHER:
   - It's the default collection (ID 0) with `mcp_server_id` = `null`, OR
   - Its `mcp_server_id` matches `APP_CONFIG.CURRENT_MCP_SERVER_NAME`

### On Application Restart
1. All collection metadata is loaded from `tda_config.json`
2. Collections are automatically recreated in ChromaDB
3. No manual re-configuration needed

## API Endpoints

All endpoints persist changes automatically:

- `POST /v1/rag/collections` - Create new collection
- `PUT /v1/rag/collections/<id>` - Update collection metadata  
- `DELETE /v1/rag/collections/<id>` - Delete collection
- `POST /v1/rag/collections/<id>/toggle` - Enable/disable collection

## Key Features

1. **Atomic Writes**: Config is written to temp file then renamed (atomic operation)
2. **Backup on Corruption**: Corrupted files are backed up before replacement
3. **Schema Versioning**: `schema_version` field enables future migrations
4. **Default Collection**: Collection ID 0 is always created and cannot be deleted
5. **Singleton Pattern**: Single ConfigManager instance across application
6. **Error Handling**: Graceful fallback to default config on errors
7. **UTF-8 Support**: Proper encoding for international characters
8. **Timestamp Tracking**: Both creation and modification timestamps

## Benefits

1. **Persistence**: Collections survive application restarts
2. **Reliability**: Atomic writes prevent corruption during crashes
3. **Extensibility**: Easy to add new config objects (future: user preferences, custom settings)
4. **Maintainability**: Centralized configuration management
5. **Transparency**: Human-readable JSON format
6. **Backup**: Automatic backup of corrupted files

## Future Enhancements

The `tda_config.json` structure is designed to be easily extended. Future additions could include:

- User preferences (theme, layout, defaults)
- Custom prompt templates
- Saved queries or workflows
- MCP server configurations
- Application settings

Simply add new top-level keys to the config schema and implement corresponding methods in `ConfigManager`.

## Testing Recommendations

1. Start application fresh - verify `tda_config.json` is created
2. Add a new collection via UI - verify it's saved to config
3. Restart application - verify collection is loaded automatically
4. Update collection metadata - verify changes are persisted
5. Delete collection - verify removal from config
6. Test with corrupted JSON - verify backup and recovery

## Location

The config file is created at: `<project_root>/tda_config.json`

Project root is automatically determined as 3 levels up from `config_manager.py`.
