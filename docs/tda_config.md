# tda_config.json - Example Configuration File

This file is automatically created and managed by the TDA application. It stores persistent configuration for application objects that need to survive application restarts.

## Example Structure

```json
{
  "schema_version": "1.0",
  "created_at": "2025-11-18T10:30:00.000000+00:00",
  "last_modified": "2025-11-18T10:30:00.000000+00:00",
  "rag_collections": [
    {
      "id": 0,
      "name": "Default TDA RAG Cases",
      "collection_name": "tda_rag_cases_collection",
      "mcp_server_id": "teradata_mcp_server",
      "enabled": true,
      "created_at": "2025-11-18T10:30:00.000000+00:00",
      "description": "Default collection for TDA RAG cases (MCP: teradata_mcp_server)"
    },
    {
      "id": 1,
      "name": "My Custom Collection",
      "collection_name": "tda_rag_coll_1_a3f9e2",
      "mcp_server_id": "teradata_mcp_server",
      "enabled": true,
      "created_at": "2025-11-18T11:45:00.000000+00:00",
      "description": "Custom collection for specific use cases"
    }
  ]
}
```

## Fields

### Top-Level
- `schema_version`: Version of the configuration schema (for future migrations)
- `created_at`: ISO timestamp when the config file was first created
- `last_modified`: ISO timestamp when the config file was last updated

### RAG Collections
- `id`: Unique numeric identifier for the collection (0 = default collection)
- `name`: Display name for the collection
- `collection_name`: Internal ChromaDB collection name
- `mcp_server_id`: **REQUIRED** - ID of associated MCP server
- `enabled`: Whether the collection is currently active
- `created_at`: ISO timestamp when the collection was created
- `description`: Optional description of the collection's purpose

## Collection-to-MCP Server Association Rules

**IMPORTANT**: ALL ChromaDB collections MUST be associated with a specific MCP server to be active.

### Enforcement Rules:
1. **Creation**: ALL collections (including default) REQUIRE an `mcp_server_id`
2. **Loading**: Only collections matching the current MCP server are loaded into memory
3. **Multiple Collections**: One MCP server can have multiple collections
4. **Exclusive Association**: Each collection belongs to exactly one MCP server
5. **Default Collection**: When first created, the default collection (ID 0) is automatically associated with the current MCP server

### Example Scenarios:

**Scenario 1: Single MCP Server with Multiple Collections**
```json
{
  "rag_collections": [
    {
      "id": 0,
      "name": "Default TDA RAG Cases",
      "mcp_server_id": "teradata_mcp_server",
      "enabled": true
    },
    {
      "id": 1,
      "name": "Teradata Query Patterns",
      "mcp_server_id": "teradata_mcp_server",
      "enabled": true
    },
    {
      "id": 2,
      "name": "Teradata DBA Operations",
      "mcp_server_id": "teradata_mcp_server",
      "enabled": true
    }
  ]
}
```
When `teradata_mcp_server` is active, collections 0, 1, and 2 are loaded.

**Scenario 2: Multiple MCP Servers with Dedicated Collections**
```json
{
  "rag_collections": [
    {
      "id": 1,
      "name": "Snowflake Queries",
      "mcp_server_id": "snowflake_mcp_server",
      "enabled": true
    },
    {
      "id": 2,
      "name": "PostgreSQL Queries",
      "mcp_server_id": "postgres_mcp_server",
      "enabled": true
    }
  ]
}
```
- When `snowflake_mcp_server` is active: Only collection 1 is loaded
- When `postgres_mcp_server` is active: Only collection 2 is loaded

### MCP Server Change Behavior:

When you switch MCP servers (via `/configure` endpoint):
1. Currently loaded collections are unloaded
2. Collections matching the new MCP server are loaded automatically
3. Enabled collections for other servers remain in config but are not active

## Management

The configuration is managed through:
- **Module**: `src/trusted_data_agent/core/config_manager.py`
- **API Endpoints**: 
  - `POST /v1/rag/collections` - Create new collection
  - `PUT /v1/rag/collections/<id>` - Update collection metadata
  - `DELETE /v1/rag/collections/<id>` - Delete collection
  - `POST /v1/rag/collections/<id>/toggle` - Enable/disable collection

Collections are automatically loaded on application startup and changes are persisted immediately.

## Notes

- The default collection (ID 0) cannot be deleted
- Collection names are auto-generated with a unique suffix to avoid conflicts
- The file is created automatically if it doesn't exist
- Corrupted files are backed up with a `.backup` suffix before being replaced
