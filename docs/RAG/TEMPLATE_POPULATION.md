# RAG Template-Based Population

## Overview

The RAG system now supports **template-based population**, allowing you to quickly bootstrap RAG collections with synthetic cases derived from templates and user-provided examples.

Instead of waiting for organic usage to build up RAG cases, you can provide a list of questions and SQL statements to populate a collection immediately.

## Directory Structure Changes

RAG cases are now organized by collection in nested directories:

```
rag/tda_rag_cases/
  collection_0/          # Default collection
    case_xxx.json
    case_yyy.json
  collection_1/          # MCP server 1 collection
    case_aaa.json
    case_bbb.json
  collection_2/          # MCP server 2 collection
    case_ccc.json
```

**Migration**: Existing cases are automatically migrated to `collection_0/` on first startup after this update.

## Supported Templates

### SQL Query Template

The SQL Query Template creates a two-phase plan:
- **Phase 1**: Execute SQL statement using an MCP tool
- **Phase 2**: Generate final report with TDA_FinalReport

This is the most common pattern for database queries.

## API Usage

### 1. Get Available Templates

```bash
GET /api/v1/rag/templates
```

**Response:**
```json
{
  "status": "success",
  "templates": {
    "sql_query": {
      "name": "SQL Query Template",
      "description": "Two-phase plan for executing SQL queries and generating reports",
      "phases": [
        {
          "phase": 1,
          "description": "Execute SQL statement using MCP tool",
          "required_inputs": ["sql_statement"],
          "default_tool": "base_executeRawSQLStatement"
        },
        {
          "phase": 2,
          "description": "Generate final report from results",
          "required_inputs": [],
          "default_tool": "TDA_FinalReport"
        }
      ],
      "required_example_fields": ["user_query", "sql_statement"],
      "optional_fields": ["database_name", "table_names", "mcp_tool_name"]
    }
  }
}
```

### 2. Populate Collection from Template

```bash
POST /api/v1/rag/collections/{collection_id}/populate
Content-Type: application/json
```

**Request Body:**
```json
{
  "template_type": "sql_query",
  "examples": [
    {
      "user_query": "Show me all users older than 25",
      "sql_statement": "SELECT * FROM users WHERE age > 25"
    },
    {
      "user_query": "Count completed orders",
      "sql_statement": "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
    },
    {
      "user_query": "List all products in stock",
      "sql_statement": "SELECT product_id, name, quantity FROM inventory WHERE quantity > 0"
    }
  ],
  "database_name": "mydb",
  "mcp_tool_name": "base_executeRawSQLStatement"
}
```

**Optional Fields:**
- `database_name` (string): Database context for metadata
- `mcp_tool_name` (string): MCP tool to use for SQL execution (default: `base_executeRawSQLStatement`)

**Response:**
```json
{
  "status": "success",
  "message": "Successfully populated 3 cases",
  "results": {
    "collection_id": 1,
    "collection_name": "MySQL Production DB",
    "total_examples": 3,
    "successful": 3,
    "failed": 0,
    "case_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "c3d4e5f6-a7b8-9012-cdef-123456789012"
    ],
    "errors": []
  }
}
```

## Example Workflow

### Step 1: Create a Collection

```bash
POST /api/v1/rag/collections
Content-Type: application/json

{
  "name": "Customer DB Queries",
  "description": "Common queries for customer database",
  "mcp_server_id": "mysql-prod-server"
}
```

### Step 2: Populate with SQL Examples

```bash
POST /api/v1/rag/collections/1/populate
Content-Type: application/json

{
  "template_type": "sql_query",
  "examples": [
    {
      "user_query": "Find customers by email",
      "sql_statement": "SELECT * FROM customers WHERE email = ?"
    },
    {
      "user_query": "Get customer order history",
      "sql_statement": "SELECT o.* FROM orders o JOIN customers c ON o.customer_id = c.id WHERE c.email = ?"
    }
  ],
  "database_name": "customer_db"
}
```

### Step 3: Enable the Collection

```bash
POST /api/v1/rag/collections/1/toggle
Content-Type: application/json

{
  "enabled": true
}
```

### Step 4: Query Uses Template Cases

When a user asks: "Show me the order history for john@example.com"

The planner will:
1. Retrieve the most similar template case from the collection
2. Use it as a few-shot example in the planning prompt
3. Generate a plan following the proven pattern

## Template Case Properties

Template-generated cases have these special properties:

- **`is_most_efficient: true`** - Start as champions by default
- **`template_generated: true`** - Marked as template-generated in metadata
- **`template_type`** - Identifies which template was used
- **Token estimates** - Approximate token counts (not from actual LLM execution)
- **Session metadata** - Generic template session IDs

## Benefits

1. **Instant Knowledge Base**: Bootstrap collections without waiting for organic usage
2. **Transfer Expertise**: Convert existing SQL query libraries into RAG cases
3. **Consistent Patterns**: Ensure the agent follows proven strategies
4. **Collection Isolation**: Each MCP server gets its own collection with relevant examples

## Validation

The API validates examples before generation:
- Empty user queries or SQL statements are rejected
- SQL statements must contain valid SQL keywords
- Collection must exist and be valid

**Validation Error Example:**
```json
{
  "status": "error",
  "message": "Validation failed for some examples",
  "validation_issues": [
    {
      "example_index": 2,
      "field": "sql_statement",
      "issue": "Empty or whitespace-only SQL statement"
    }
  ]
}
```

## Future Template Types

The architecture supports additional template types:
- API request templates
- Multi-step data transformation templates
- Report generation templates
- Custom domain-specific templates

## Notes

- Template cases compete with organically-generated cases based on feedback and token efficiency
- Users can upvote/downvote template cases just like organic cases
- Downvoted template cases are automatically demoted from champion status
- Template cases are stored in `collection_{id}/` directories alongside organic cases
