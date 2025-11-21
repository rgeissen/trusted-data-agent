# RAG Template System - User Guide

## Overview

The RAG Template System enables automatic generation of RAG case studies through a modular plugin architecture. Templates define reusable patterns for specific use cases (SQL queries, API calls, workflows) and support both manual and LLM-assisted population.

## Key Features

✅ **LLM-Assisted Question Generation** - Automatically generate question/answer pairs from database schemas  
✅ **Modular Plugin System** - Templates are self-contained plugins with manifest files  
✅ **Two-Phase Strategy Templates** - Execute queries and generate natural language reports  
✅ **Multiple Database Support** - Teradata, PostgreSQL, MySQL, and others via MCP tools  
✅ **UI-Based Workflow** - Complete end-to-end workflow in the web interface  
✅ **Template Validation** - Automatic validation of inputs and arguments

## Quick Start

### 1. Create a Collection

In the TDA web interface:
1. Navigate to **RAG Collections** tab
2. Click **Add RAG Collection**
3. Enter collection name and select MCP server
4. Choose **Populate with SQL Template**

### 2. Generate Questions (LLM-Assisted)

With **Auto-Generate (LLM)** selected:

1. **Generate Context** - Execute a sample query to extract database schema
2. **Enter Configuration**:
   - **Context Topic**: e.g., "Employee analytics and reporting"
   - **Num Examples**: 1-1000 (number of question/SQL pairs to generate)
   - **Database Name**: Your target database
3. **Generate Questions** - LLM creates question/SQL pairs based on schema
4. **Review & Edit** - Verify and modify generated examples
5. **Populate Collection** - Add cases to the collection
6. **Create Collection** - Finalize and activate

### 3. Manual Population

Alternatively, use **Manual Input** to enter question/SQL pairs directly:
- Add multiple question/SQL examples
- Specify database name and MCP tool
- Populate collection immediately

## Template Structure

### Plugin Directory Layout

```
rag_templates/templates/
├── sql-query-basic/
│   ├── manifest.json           # Plugin metadata and UI configuration
│   ├── sql_query_v1.json       # Template definition (strategy)
│   └── README.md               # Documentation
└── sql-query-doc-context/
    ├── manifest.json
    ├── sql_query_doc_context_v1.json
    └── README.md
```

### Manifest.json

Defines plugin metadata, UI fields, and validation rules:

```json
{
  "name": "sql-query-basic",
  "version": "1.0.0",
  "template_id": "sql_query_v1",
  "display_name": "SQL Query Template - Business Context",
  "description": "Two-phase strategy...",
  
  "population_modes": {
    "manual": {
      "enabled": true,
      "input_variables": {
        "database_name": {
          "required": true,
          "description": "Target database name"
        }
      }
    },
    "auto_generate": {
      "enabled": true,
      "input_variables": {
        "context_topic": {
          "required": true,
          "type": "string",
          "description": "Business context for question generation"
        },
        "num_examples": {
          "required": true,
          "type": "integer",
          "default": 5,
          "min": 1,
          "max": 1000,
          "description": "Number of question/SQL pairs to generate"
        },
        "database_name": {
          "required": false,
          "description": "Target database name"
        }
      }
    }
  }
}
```

### Template JSON (Strategy Definition)

Defines the execution strategy with phases and arguments:

```json
{
  "template_id": "sql_query_v1",
  "template_version": "1.0.0",
  "strategy_template": {
    "strategy_name": "SQL Query Strategy",
    "phases": [
      {
        "phase_number": 1,
        "phase_description": "Execute SQL query",
        "tool": "base_readQuery",
        "arguments": [
          {
            "name": "sql",
            "type": "sql_statement",
            "required": true,
            "description": "The SQL query to execute (includes database name)"
          }
        ]
      },
      {
        "phase_number": 2,
        "phase_description": "Generate final report",
        "tool": "TDA_FinalReport",
        "arguments": [
          {
            "name": "user_query",
            "type": "user_query",
            "required": true
          }
        ]
      }
    ]
  }
}
```

## LLM Question Generation

### How It Works

1. **Context Extraction**: Execute a sample query (e.g., `HELP TABLE tablename;`) to get schema information
2. **Schema Analysis**: Extract table structures, columns, data types, and constraints
3. **Prompt Construction**: Build a detailed prompt with:
   - Business context topic
   - Complete schema information
   - Number of examples to generate
   - Target database name
4. **LLM Generation**: Generate diverse, realistic question/SQL pairs
5. **Validation**: Ensure SQL is syntactically valid and questions are meaningful

### Best Practices

- **Context Topic**: Be specific (e.g., "Customer order analysis" vs "general queries")
- **Sample Queries**: Use `HELP TABLE` or `DESCRIBE` to get comprehensive schema
- **Review Generated Cases**: Always review before populating - edit if needed
- **Incremental Generation**: Start with 5-10 examples to test, then scale up

## Template Registry

Templates are registered in `rag_templates/template_registry.json`:

```json
{
  "templates": [
    {
      "template_id": "sql_query_v1",
      "template_file": "sql-query-basic/sql_query_v1.json",
      "plugin_directory": "sql-query-basic",
      "status": "active",
      "priority": 1
    }
  ]
}
```

## API Endpoints

### Get Available Templates
```bash
GET /api/v1/rag/templates
```

### Get Template Plugin Info
```bash
GET /api/v1/rag/templates/{template_id}/plugin-info
```

### Generate Questions (LLM)
```bash
POST /api/v1/rag/generate-questions
{
  "template_id": "sql_query_v1",
  "execution_context": "{...extracted schema...}",
  "subject": "Customer analytics",
  "count": 10,
  "database_name": "sales_db"
}
```

### Populate Collection
```bash
POST /api/v1/rag/collections/{collection_id}/populate
{
  "template_type": "sql_query",
  "examples": [
    {
      "user_query": "Show all active customers",
      "sql_statement": "SELECT * FROM customers WHERE status = 'active'"
    }
  ],
  "database_name": "sales_db"
}
```

## Troubleshooting

### Template Not Loading
- Check `template_registry.json` for correct `template_id` and file paths
- Verify manifest.json has required fields
- Restart server to reload templates

### Validation Errors
- Ensure `num_examples` is within min/max range (1-1000)
- Verify all required fields are provided
- Check that SQL statements include database name in the query string

### Generated Questions Poor Quality
- Refine context topic to be more specific
- Provide more comprehensive schema information in sample query
- Adjust the number of examples (fewer can be higher quality)

## Advanced: Creating Custom Templates

See `TEMPLATE_PLUGIN_DEVELOPMENT.md` for detailed guide on:
- Template plugin structure
- Manifest configuration
- Strategy definition
- UI field customization
- Validation rules
- Distribution and installation

## Migration Notes

### From Legacy System
- Old flat template files (`sql_query_v1.json` at root) are deprecated
- Use plugin directory structure (`templates/plugin-name/`)
- Manifest files now required for UI integration
- Template arguments refined (database_name removed from Phase 1)

## Support

For issues or questions:
- GitHub: https://github.com/rgeissen/trusted-data-agent
- Check logs: `logs/` directory
- Validate templates: Check browser console and server logs
