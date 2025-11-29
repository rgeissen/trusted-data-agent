# Planner Repository Constructor Library

This directory contains the constructor library for building **Planner Repositories** - specialized RAG collections that store execution strategies and planning patterns. These constructors enable automatic generation of proven execution traces that guide the agent's decision-making process.

**Repository Types:**
- **Planner Repositories** (built by these constructors): Execution patterns and strategies
- **Knowledge Repositories** (separate system): General documents and reference materials

## Structure

```
rag_templates/
├── README.md                      # This file
├── template_registry.json         # Template registry and metadata
└── templates/                     # Individual template definitions
    ├── sql_query_v1.json         # SQL Query Constructor - Database Context
    ├── api_request_v1.json       # (Future) API Request Template
    └── custom_workflow_v1.json   # (Future) Custom Workflow Template
```

## Template Registry

The `template_registry.json` file contains metadata about all available templates:

- **template_id**: Unique identifier for the template
- **template_file**: JSON file containing the template definition
- **status**: Template status (`active`, `beta`, `deprecated`, `draft`)
- **display_order**: Order in which templates appear in the UI

Only templates with `status: "active"` are loaded at startup.

## Template Definition Format

Each template JSON file contains:

### Required Sections

1. **Metadata**
   - `template_id`: Unique identifier
   - `template_name`: Display name
   - `template_type`: Type identifier (sql_query, api_request, etc.)
   - `description`: Brief description
   - `status`: Template status
   - `version`: Template version

2. **Input Variables**
   - User-provided parameters (e.g., user_query, sql_statement)
   - Each variable specifies: type, required, description, placeholder, validation rules
   
3. **Output Configuration**
   - Auto-generated values (session_id, tokens, feedback, etc.)
   - Marks which values are editable at runtime
   
4. **Strategy Template**
   - Phase definitions and goal templates
   - Tool mappings and argument configurations
   
5. **Metadata Mapping**
   - How input variables map to case metadata
   
6. **Validation Rules**
   - Input validation logic

## Template Usage

Templates are loaded automatically at application startup:

1. **Template Manager** loads `template_registry.json`
2. Loads all active template definitions from `templates/` directory
3. Validates template structure
4. Makes templates available via `get_template_manager()`

### Accessing Templates

```python
from trusted_data_agent.agent.rag_template_manager import get_template_manager

# Get template manager
manager = get_template_manager()

# List all templates
templates = manager.list_templates()

# Get specific template
sql_template = manager.get_template("sql_query_v1")

# Get editable configuration
config = manager.get_template_config("sql_query_v1")

# Update configuration (runtime only)
manager.update_template_config("sql_query_v1", {
    "default_mcp_tool": "custom_sql_executor",
    "estimated_input_tokens": 200,
    "estimated_output_tokens": 250
})
```

### Creating New Templates

1. Create a new JSON file in `templates/` directory
2. Follow the structure of `sql_query_v1.json`
3. Add entry to `template_registry.json`
4. Set status to `"active"` to enable
5. Restart application to load new template

## Configuration Persistence

Template configurations can be edited at runtime via the UI:

- Editable values are marked with `"editable": true` in the template
- Changes are stored in memory during the session
- To persist changes permanently, modify the template JSON file

## Best Practices

1. **Version Templates**: Use semantic versioning (v1.0.0, v1.1.0, v2.0.0)
2. **Maintain Backwards Compatibility**: Create new versions rather than breaking existing templates
3. **Validate Thoroughly**: Ensure all required fields are present
4. **Document Examples**: Include usage examples in the template
5. **Test Before Activating**: Use `"status": "beta"` for testing, then promote to `"active"`

## Example: SQL Query Constructor - Database Context

See `templates/sql_query_v1.json` for a complete example of a production-ready template.

Key features:
- Clear input variable definitions with validation
- Editable output configuration
- Dynamic phase goal generation
- Conditional argument inclusion
- Token estimation defaults
