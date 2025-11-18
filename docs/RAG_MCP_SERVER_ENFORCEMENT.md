# RAG Collection MCP Server Association - Implementation Summary

## Overview
Implemented enforcement rule: **ALL ChromaDB collections MUST be associated with a specific MCP server to be active**.

This ensures that RAG examples are contextually relevant to the currently connected MCP server, preventing cross-contamination of query patterns between different data sources.

**Note**: The default collection (ID 0) is automatically created with the current MCP server when first initialized. There is NO exception for null `mcp_server_id`.

## Enforcement Points

### 1. Collection Creation (`add_collection()`)
**File**: `src/trusted_data_agent/agent/rag_retriever.py`

```python
def add_collection(self, name: str, description: str = "", mcp_server_id: Optional[str] = None):
    # ENFORCEMENT: mcp_server_id is required
    if mcp_server_id is None:
        logger.error("Cannot add collection: mcp_server_id is required")
        return None
```

**Behavior**:
- `mcp_server_id` is REQUIRED (cannot be None)
- Returns None if mcp_server_id not provided
- Collection is created in ChromaDB only if it matches current MCP server

### 2. Collection Loading (`_load_active_collections()`)
**File**: `src/trusted_data_agent/agent/rag_retriever.py`

```python
def _load_active_collections(self):
    current_mcp_server = APP_CONFIG.CURRENT_MCP_SERVER_NAME
    
    for coll_meta in collections_list:
        coll_mcp_server = coll_meta.get("mcp_server_id")
        
        # Strict enforcement: Must match current MCP server
        if coll_mcp_server != current_mcp_server:
            # Skip - doesn't match current server
            continue
```

**Behavior**:
- Only loads collections where `mcp_server_id` matches `CURRENT_MCP_SERVER_NAME`
- NO exceptions - all collections must have a valid mcp_server_id
- Logs which collections are skipped and why

### 3. Collection Toggle (`toggle_collection()`)
**File**: `src/trusted_data_agent/agent/rag_retriever.py`

```python
def toggle_collection(self, collection_id: int, enabled: bool):
    mcp_server_matches = (coll_mcp_server == current_mcp_server)
    
    if enabled and not mcp_server_matches:
        logger.info(f"Collection enabled but not loaded: different MCP server")
        return True  # Config updated, but not loaded
```

**Behavior**:
- Enables/disables collection in config
- Only loads to memory if MCP server matches
- Returns success even if not loaded (config is still valid)

### 4. REST API Validation
**File**: `src/trusted_data_agent/api/rest_routes.py`

#### Create Endpoint
```python
@rest_api_bp.route("/v1/rag/collections", methods=["POST"])
async def create_rag_collection():
    if not data.get("mcp_server_id"):
        return jsonify({
            "status": "error", 
            "message": "mcp_server_id is required. Collections must be associated with an MCP server."
        }), 400
```

#### Update Endpoint
```python
@rest_api_bp.route("/v1/rag/collections/<int:collection_id>", methods=["PUT"])
async def update_rag_collection(collection_id: int):
    if "mcp_server_id" in data:
        new_mcp_server_id = data["mcp_server_id"]
        if not new_mcp_server_id:
            return jsonify({
                "status": "error", 
                "message": "Cannot remove mcp_server_id. All collections must be associated with an MCP server."
            }), 400
```

**Behavior**:
- POST: Returns 400 if `mcp_server_id` not provided
- PUT: Returns 400 if trying to remove `mcp_server_id` from ANY collection
- Clear error messages for users

### 5. MCP Server Change Handling
**File**: `src/trusted_data_agent/core/configuration_service.py`

```python
async def setup_and_categorize_services(config_data: dict):
    existing_retriever = APP_STATE.get('rag_retriever_instance')
    
    if existing_retriever:
        # MCP server changed - reload collections
        existing_retriever.reload_collections_for_mcp_server()
```

**New Method** (`rag_retriever.py`):
```python
def reload_collections_for_mcp_server(self):
    # Clear currently loaded collections
    self.collections.clear()
    
    # Reload collections using the standard method (with MCP filtering)
    self._load_active_collections()
```

**Behavior**:
- Detects when MCP server changes
- Automatically unloads all collections
- Reloads only collections matching new MCP server
- Seamless transition without restart

## Exception: Default Collection (ID 0)

The default collection is created automatically when RAGRetriever initializes:

```python
{
  "id": 0,
  "name": "Default TDA RAG Cases",
  "collection_name": "tda_rag_cases_collection",
  "mcp_server_id": "teradata_mcp_server",  // Automatically set to current MCP server
  "enabled": true
}
```

**Behavior:**
- Created automatically on first initialization
- Associated with the MCP server that was active at creation time
- Follows the same rules as all other collections (no special exceptions)
- Will only be active when its associated MCP server is current

## Use Cases

### Use Case 1: Dedicated Collections Per MCP Server
```json
{
  "rag_collections": [
    {
      "id": 1,
      "name": "Teradata SQL Patterns",
      "mcp_server_id": "teradata_prod",
      "enabled": true
    },
    {
      "id": 2,
      "name": "Snowflake SQL Patterns",
      "mcp_server_id": "snowflake_analytics",
      "enabled": true
    }
  ]
}
```

**Behavior**:
- Connected to `teradata_prod`: Only collection 1 is active
- Switch to `snowflake_analytics`: Collection 1 unloads, collection 2 loads
- No cross-contamination of SQL patterns

### Use Case 2: Multiple Collections for One MCP Server
```json
{
  "rag_collections": [
    {
      "id": 1,
      "name": "Basic Queries",
      "mcp_server_id": "teradata_prod",
      "enabled": true
    },
    {
      "id": 2,
      "name": "DBA Operations",
      "mcp_server_id": "teradata_prod",
      "enabled": true
    },
    {
      "id": 3,
      "name": "Performance Tuning",
      "mcp_server_id": "teradata_prod",
      "enabled": true
    }
  ]
}
```

**Behavior**:
- Connected to `teradata_prod`: All three collections load
- Planner retrieves examples from all active collections
- Organized by use case/category

## Benefits

1. **Context Relevance**: RAG examples match the current data source
2. **Clean Separation**: Prevent mixing query patterns from different systems
3. **Multi-Environment Support**: Same config works for dev/test/prod servers
4. **Automatic Switching**: Collections reload when MCP server changes
5. **Organizational Clarity**: Collections clearly labeled by their target system

## Error Messages

Users will see clear error messages when violating the rules:

```
POST /v1/rag/collections without mcp_server_id:
→ "mcp_server_id is required. Collections must be associated with an MCP server."

PUT /v1/rag/collections/1 attempting to remove mcp_server_id:
→ "Cannot remove mcp_server_id. All collections must be associated with an MCP server."
```

## Logging

Enhanced logging shows MCP server association:

```
INFO - Loading RAG collections for MCP server: 'teradata_prod'
INFO - Loaded collection '1' (ChromaDB: 'tda_rag_coll_1_a3f9e2', MCP: 'teradata_prod')
DEBUG - Skipping collection '2': associated with 'snowflake_analytics', current server is 'teradata_prod'
INFO - Loaded 1 collection(s) for MCP server 'teradata_prod'
```

## Migration Guide

For existing installations with a default collection that has `null` mcp_server_id:

**Option 1: Update the existing default collection** (Recommended)
```bash
curl -X PUT http://localhost:5050/v1/rag/collections/0 \
  -H "Content-Type: application/json" \
  -d '{
    "mcp_server_id": "your_mcp_server_name"
  }'
```

**Option 2: Delete tda_config.json and restart**
- The default collection will be recreated automatically with the current MCP server

**Note**: After migration, the default collection will only be active when its associated MCP server is current.

## Testing

The enforcement can be tested by:

1. Attempting to create collection without mcp_server_id (should fail)
2. Creating collections for different MCP servers
3. Switching MCP servers and verifying collection reload
4. Checking that only matching collections are active
5. Attempting to remove mcp_server_id from existing collection (should fail)

All enforcement rules are in place and active!
