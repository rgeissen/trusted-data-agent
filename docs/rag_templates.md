# RAG Template System

## Overview

The RAG Template System provides a flexible, JSON-driven approach to generating RAG case studies from predefined templates. Templates define the structure, input variables, and output configuration for automatically generating complete case studies that can be used to populate RAG collections.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Template Library (rag_templates/)                          │
│  ├── template_registry.json    ← Template metadata         │
│  └── templates/                                             │
│      ├── sql_query_v1.json     ← Template definitions      │
│      ├── api_request_v1.json   (one JSON file per template)│
│      └── custom_workflow_v1.json                            │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  RAGTemplateManager                                          │
│  - Loads templates at startup                               │
│  - Validates template structure                             │
│  - Provides template access                                 │
│  - Manages runtime configuration                            │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  RAGTemplateGenerator                                        │
│  - generate_case_from_template() ← Generic method           │
│  - Reads template definition                                │
│  - Builds case study from input values                      │
│  - Applies template rules & transformations                 │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Generated Case Study (JSON)                                │
│  Ready to be saved to collection                            │
└─────────────────────────────────────────────────────────────┘
```

## Template Structure

Every template is a JSON file with the following sections:

### 1. Template Metadata

Identifies and describes the template:

```json
{
  "template_id": "sql_query_v1",
  "template_name": "SQL Query Template",
  "template_version": "1.0.0",
  "template_type": "sql_query",
  "description": "Two-phase strategy: Execute SQL statement and generate final report",
  "status": "active",
  "created_at": "2025-11-20T00:00:00Z",
  "updated_at": "2025-11-20T00:00:00Z"
}
```

**Fields:**
- `template_id` (string, required): Unique identifier, used in code
- `template_name` (string, required): Display name for UI
- `template_version` (string, required): Semantic version (e.g., "1.0.0")
- `template_type` (string, required): Category identifier
- `description` (string, required): Brief description
- `status` (string, required): Template status ("active", "beta", "deprecated", "draft")
- `created_at` (ISO datetime): Creation timestamp
- `updated_at` (ISO datetime): Last update timestamp

### 2. Input Variables

Defines what users must provide:

```json
{
  "input_variables": {
    "user_query": {
      "type": "string",
      "required": true,
      "description": "The user's natural language question",
      "placeholder": "Show me all users older than 25",
      "validation": {
        "min_length": 5,
        "max_length": 500
      }
    },
    "sql_statement": {
      "type": "string",
      "required": true,
      "description": "The SQL statement to execute",
      "placeholder": "SELECT * FROM users WHERE age > 25",
      "validation": {
        "min_length": 10,
        "max_length": 5000
      }
    },
    "database_name": {
      "type": "string",
      "required": false,
      "description": "Target database name",
      "placeholder": "production_db"
    }
  }
}
```

**Variable Properties:**
- `type`: Data type ("string", "number", "boolean", "array", "object")
- `required`: Whether the variable is mandatory
- `description`: User-facing description
- `placeholder`: Example value for UI
- `default`: Default value if not provided
- `validation`: Validation rules (min_length, max_length, pattern, etc.)

### 3. Output Configuration

Defines auto-generated values:

```json
{
  "output_configuration": {
    "session_id": {
      "type": "constant",
      "value": "00000000-0000-0000-0000-000000000000",
      "description": "All template-generated cases share this session ID"
    },
    "is_most_efficient": {
      "type": "boolean",
      "value": true,
      "editable": true,
      "description": "Template cases start as champions by default"
    },
    "estimated_tokens": {
      "input_tokens": {
        "type": "number",
        "value": 150,
        "editable": true,
        "description": "Approximate tokens for planning phase"
      },
      "output_tokens": {
        "type": "number",
        "value": 180,
        "editable": true,
        "description": "Approximate tokens for response"
      }
    }
  }
}
```

**Configuration Types:**
- `constant`: Fixed value, cannot be changed
- `boolean`: True/false value
- `number`: Numeric value
- `string`: Text value

**Properties:**
- `value`: The default value
- `editable`: If true, can be modified via template editor UI
- `description`: Explains the purpose

### 4. Strategy Template

Defines the multi-phase execution strategy:

```json
{
  "strategy_template": {
    "phase_count": 2,
    "phases": [
      {
        "phase": 1,
        "goal_template": "Execute SQL query{database_context}: {sql_preview}",
        "goal_variables": {
          "database_context": {
            "condition": "if database_name",
            "format": " on {database_name}"
          },
          "sql_preview": {
            "source": "sql_statement",
            "transform": "truncate",
            "max_length": 50
          }
        },
        "relevant_tools_source": "mcp_tool_name",
        "arguments": {
          "sql": {
            "source": "sql_statement",
            "description": "The SQL query to execute"
          },
          "database_name": {
            "source": "database_name",
            "condition": "if database_name"
          }
        }
      },
      {
        "phase": 2,
        "goal": "Generate the final report based on the query results.",
        "relevant_tools": ["TDA_FinalReport"],
        "arguments": {}
      }
    ]
  }
}
```

**Phase Properties:**
- `phase` (number): Phase number (1-indexed)
- `goal` (string): Static goal description
- `goal_template` (string): Dynamic goal with variable substitution
- `goal_variables` (object): Variables used in goal_template
- `relevant_tools` (array): Static list of tool names
- `relevant_tools_source` (string): Input variable name containing tool name
- `arguments` (object): Phase arguments mapping

**Goal Variables:**
- `condition`: Conditional inclusion (e.g., "if database_name")
- `format`: String format template
- `source`: Input variable to use
- `transform`: Transformation to apply ("truncate", etc.)
- `max_length`: Maximum length for truncate transform

**Arguments:**
- `source`: Input variable name to map
- `condition`: Conditional inclusion
- `description`: Documentation

### 5. Metadata Mapping

Maps input variables to case metadata:

```json
{
  "metadata_mapping": {
    "database_name": {
      "source": "database_name",
      "condition": "if database_name"
    },
    "table_names": {
      "source": "table_names",
      "condition": "if table_names"
    }
  }
}
```

Only includes metadata fields that should be added conditionally or from input.

### 6. Validation Rules

Defines validation logic for inputs:

```json
{
  "validation_rules": {
    "sql_statement": {
      "not_empty": true,
      "sql_keywords": ["SELECT", "INSERT", "UPDATE", "DELETE"]
    }
  }
}
```

### 7. Usage Examples

Provides reference examples:

```json
{
  "usage_examples": [
    {
      "name": "Simple SELECT query",
      "user_query": "Show me all active users",
      "sql_statement": "SELECT * FROM users WHERE status = 'active'",
      "database_name": "app_db"
    }
  ]
}
```

## Implementation Steps

### Step 1: Create Template JSON File

1. Create new file: `rag_templates/templates/<your_template>_v1.json`
2. Follow the structure outlined above
3. Define all required sections
4. Add validation rules and examples

### Step 2: Register Template

Add entry to `rag_templates/template_registry.json`:

```json
{
  "templates": [
    {
      "template_id": "your_template_v1",
      "template_file": "your_template_v1.json",
      "status": "active",
      "display_order": 2
    }
  ]
}
```

**Status Values:**
- `active`: Available for use
- `beta`: Available but still testing
- `deprecated`: Being phased out
- `draft`: Not yet available

### Step 3: Test Template Loading

Restart application and check logs:

```
INFO - RAG Template Manager initialized with 2 template(s): ['sql_query_v1', 'your_template_v1']
```

### Step 4: Use Template

**Via API:**
```python
from trusted_data_agent.agent.rag_template_generator import RAGTemplateGenerator

generator = RAGTemplateGenerator(rag_retriever)

# Generate case from template
case = generator.generate_case_from_template(
    template_id="your_template_v1",
    collection_id=1,
    input_values={
        "user_query": "What is the revenue?",
        "parameter1": "value1",
        "parameter2": "value2"
    }
)

# Save to collection
rag_retriever.save_case(collection_id, case)
```

**Via REST API:**
```bash
POST /api/v1/rag/collections/{collection_id}/populate
{
  "template_type": "your_template",
  "examples": [
    {
      "user_query": "...",
      "parameter1": "...",
      "parameter2": "..."
    }
  ]
}
```

## Template Processing Flow

1. **Load Template**: `RAGTemplateManager` loads JSON at startup
2. **Validate Structure**: Checks required fields are present
3. **Accept Input**: User provides input values via UI or API
4. **Generate Case**:
   - Create unique case_id
   - Build metadata from output_configuration
   - Apply editable configuration values
   - Process each phase:
     - Build goal from goal_template with variable substitution
     - Resolve tools from relevant_tools or relevant_tools_source
     - Build arguments from arguments mapping
   - Apply metadata_mapping
5. **Save Case**: Write to collection directory as JSON

## Variable Substitution

Templates support dynamic content using variable substitution:

**Simple Substitution:**
```json
"goal_template": "Query database {database_name}"
```
→ `"Query database production_db"`

**Conditional Inclusion:**
```json
"goal_variables": {
  "db_context": {
    "condition": "if database_name",
    "format": " on {database_name}"
  }
}
```
→ Included only if `database_name` is provided

**Transformations:**
```json
"goal_variables": {
  "sql_preview": {
    "source": "sql_statement",
    "transform": "truncate",
    "max_length": 50
  }
}
```
→ `"SELECT * FROM users WHERE age > 25 AND status = '..."`

## Configuration Management

Templates support runtime configuration via Template Editor UI:

**Editable Values:**
- Mark with `"editable": true` in output_configuration
- Users can modify via gear icon on template cards
- Changes persist during session

**API Endpoints:**
- `GET /api/v1/rag/templates/<template_id>/config` - Get config
- `PUT /api/v1/rag/templates/<template_id>/config` - Update config
- `GET /api/v1/rag/templates/list` - List all templates

## Best Practices

### 1. Template Versioning
- Use semantic versioning: `v1.0.0`, `v1.1.0`, `v2.0.0`
- Create new version rather than breaking changes
- Keep old versions for backwards compatibility

### 2. Input Validation
- Define comprehensive validation rules
- Set appropriate min/max lengths
- Use descriptive error messages

### 3. Documentation
- Write clear descriptions for all variables
- Provide realistic placeholder examples
- Include multiple usage examples

### 4. Goal Templates
- Keep goals concise and descriptive
- Use conditional sections for optional context
- Truncate long values to prevent clutter

### 5. Tool Selection
- Use `relevant_tools_source` for flexible tool selection
- Provide sensible defaults
- Document tool requirements

### 6. Metadata Mapping
- Only map essential metadata
- Use conditional mapping for optional fields
- Document what each metadata field represents

## Example: Complete SQL Template

See `rag_templates/templates/sql_query_v1.json` for a production-ready example demonstrating:
- Required and optional input variables
- Editable output configuration
- Dynamic goal generation with conditionals
- Conditional argument inclusion
- Metadata mapping
- Validation rules
- Usage examples

## Troubleshooting

**Template Not Loading:**
- Check template_registry.json includes entry
- Verify status is "active"
- Check logs for validation errors
- Ensure JSON is valid (no syntax errors)

**Missing Required Fields:**
- Review template structure against this guide
- Check all required sections are present
- Validate field types match expected values

**Variable Substitution Not Working:**
- Verify goal_variables definitions
- Check variable names match input_values keys
- Ensure source fields reference correct input variables

**Arguments Not Mapping:**
- Check arguments.source references valid input variables
- Verify conditional logic (if statements)
- Review generated case JSON for debugging

## Future Enhancements

Planned features:
- Template inheritance/composition
- Custom transformation functions
- Multi-collection population
- Template validation CLI tool
- Template testing framework
- Visual template editor
