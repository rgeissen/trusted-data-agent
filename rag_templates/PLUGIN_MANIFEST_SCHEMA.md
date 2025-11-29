# Template Plugin Manifest Schema

## Overview

The `manifest.json` file describes metadata, dependencies, and configuration for a template plugin. This enables modular distribution, versioning, and community-developed templates.

> **Note:** Template files themselves are validated using JSON schemas in `schemas/` directory:
> - `schemas/planner-schema.json` - For execution strategy templates (sql_query, api_request, etc.)
> - `schemas/knowledge-template-schema.json` - For document storage templates
> 
> See `schemas/README.md` for template validation details and `TYPE_TAXONOMY.md` for understanding type concepts.

## Template Structure Overview

Templates consist of two main files:

1. **`manifest.json`** (this schema) - Plugin metadata and configuration
2. **`template.json`** - Template definition, validated by JSON schemas:
   - **Planner templates**: Validated against `schemas/planner-schema.json`
   - **Knowledge templates**: Validated against `schemas/knowledge-template-schema.json`

### Template Type Determination
```python
# The template_type field determines which schema validates the template
if template_data.get("template_type") == "knowledge_repository":
    # Use schemas/knowledge-template-schema.json
    schema_type = "knowledge"
else:
    # Use schemas/planner-schema.json for all execution strategies
    schema_type = "planner"
```

See `schemas/README.md` for complete template validation rules.

---

## Manifest Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["name", "version", "template_id", "display_name", "author"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z0-9-]+$",
      "description": "Package name (lowercase, hyphens only)"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version (e.g., 1.0.0)"
    },
    "template_id": {
      "type": "string",
      "pattern": "^[a-z0-9_]+_v\\d+$",
      "description": "Unique template identifier (e.g., sql_query_v1)"
    },
    "display_name": {
      "type": "string",
      "description": "Human-readable template name"
    },
    "description": {
      "type": "string",
      "description": "Brief description of template functionality"
    },
    "author": {
      "type": "string",
      "description": "Author name or organization"
    },
    "license": {
      "type": "string",
      "description": "SPDX license identifier (e.g., MIT, Apache-2.0)"
    },
    "homepage": {
      "type": "string",
      "format": "uri",
      "description": "Project homepage URL"
    },
    "repository": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["git", "svn", "hg"]
        },
        "url": {
          "type": "string",
          "format": "uri"
        }
      }
    },
    "keywords": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Search keywords for marketplace"
    },
    "compatibility": {
      "type": "object",
      "properties": {
        "min_app_version": {
          "type": "string",
          "description": "Minimum TDA version required"
        },
        "max_app_version": {
          "type": "string",
          "description": "Maximum TDA version supported"
        }
      }
    },
    "dependencies": {
      "type": "object",
      "properties": {
        "templates": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Required template dependencies"
        },
        "python_packages": {
          "type": "array",
          "items": {
            "type": "string"
          },
          "description": "Required Python packages (pip format)"
        }
      }
    },
    "files": {
      "type": "object",
      "required": ["template"],
      "properties": {
        "template": {
          "type": "string",
          "description": "Path to template.json (relative to manifest)"
        },
        "ui_config": {
          "type": "string",
          "description": "Path to custom UI config panel HTML"
        },
        "ui_script": {
          "type": "string",
          "description": "Path to custom UI JavaScript"
        },
        "validator": {
          "type": "string",
          "description": "Path to custom Python validator"
        },
        "icon": {
          "type": "string",
          "description": "Path to template icon (SVG, PNG)"
        }
      }
    },
    "permissions": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["database_access", "mcp_tools", "file_system", "network"]
      },
      "description": "Required permissions for template execution"
    },
    "ui_components": {
      "type": "object",
      "properties": {
        "config_panel": {
          "type": "boolean",
          "description": "Has custom configuration panel"
        },
        "preview_renderer": {
          "type": "boolean",
          "description": "Has custom preview renderer"
        },
        "file_upload": {
          "type": "boolean",
          "description": "Supports file upload (e.g., PDFs for context)"
        }
      }
    },
    "population_modes": {
      "type": "object",
      "description": "Supported methods for populating RAG collections with this template",
      "properties": {
        "manual": {
          "type": "object",
          "properties": {
            "supported": {
              "type": "boolean",
              "description": "Whether manual entry mode is supported"
            },
            "description": {
              "type": "string",
              "description": "Description of manual entry workflow"
            },
            "required_fields": {
              "type": "array",
              "items": {
                "type": "string"
              },
              "description": "Required template variables for manual entry"
            }
          }
        },
        "auto_generate": {
          "type": "object",
          "properties": {
            "supported": {
              "type": "boolean",
              "description": "Whether LLM auto-generation is supported"
            },
            "requires_llm": {
              "type": "boolean",
              "description": "Whether LLM configuration is required"
            },
            "requires_pdf": {
              "type": "boolean",
              "description": "Whether PDF processing capabilities are required"
            },
            "description": {
              "type": "string",
              "description": "Description of auto-generation workflow"
            },
            "input_variables": {
              "type": "object",
              "description": "Input variables required for auto-generation",
              "additionalProperties": {
                "type": "object",
                "properties": {
                  "required": {
                    "type": "boolean"
                  },
                  "type": {
                    "type": "string",
                    "enum": ["string", "integer", "boolean", "file"]
                  },
                  "default": {},
                  "min": {
                    "type": "number"
                  },
                  "max": {
                    "type": "number"
                  },
                  "description": {
                    "type": "string"
                  },
                  "example": {
                    "type": "string"
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

## Example: SQL Query Constructor - Database Context Manifest

```json
{
  "name": "sql-query-basic",
  "version": "1.0.0",
  "template_id": "sql_query_v1",
  "display_name": "SQL Query Constructor - Database Context",
  "description": "Two-phase strategy: Execute SQL statement and generate final report",
  "author": "TDA Core Team",
  "license": "AGPL-3.0",
  "homepage": "https://github.com/rgeissen/trusted-data-agent",
  "repository": {
    "type": "git",
    "url": "https://github.com/rgeissen/trusted-data-agent"
  },
  "keywords": ["sql", "database", "query", "teradata", "postgresql"],
  "compatibility": {
    "min_app_version": "1.0.0",
    "max_app_version": "2.x.x"
  },
  "dependencies": {
    "templates": [],
    "python_packages": []
  },
  "files": {
    "template": "sql_query_v1.json",
    "icon": "sql_icon.svg"
  },
  "permissions": [
    "database_access",
    "mcp_tools"
  ],
  "ui_components": {
    "config_panel": false,
    "preview_renderer": false
  },
  "population_modes": {
    "manual": {
      "supported": true,
      "description": "User manually enters question/SQL pairs through the template interface",
      "required_fields": ["user_query", "sql_statement"]
    },
    "auto_generate": {
      "supported": true,
      "requires_llm": true,
      "description": "LLM generates question/SQL pairs from business context",
      "input_variables": {
        "context_topic": {
          "required": true,
          "description": "Business domain or subject area",
          "example": "customer analytics, sales reporting"
        },
        "document_content": {
          "required": false,
          "description": "Optional business documentation for context",
          "example": "Business requirements, user stories"
        },
        "database_name": {
          "required": false,
          "description": "Target database name",
          "example": "production_db"
        },
        "num_examples": {
          "required": true,
          "type": "integer",
          "default": 5,
          "min": 1,
          "max": 20,
          "description": "Number of question/SQL pairs to generate"
        }
      }
    }
  }
}
```

## Example: Advanced Template with Custom UI

```json
{
  "name": "api-rest-advanced",
  "version": "2.1.0",
  "template_id": "api_rest_v2",
  "display_name": "Advanced REST API Template",
  "description": "Multi-step REST API workflow with authentication and retry logic",
  "author": "community-developer",
  "license": "MIT",
  "homepage": "https://github.com/community-dev/api-rest-template",
  "repository": {
    "type": "git",
    "url": "https://github.com/community-dev/api-rest-template"
  },
  "keywords": ["api", "rest", "http", "authentication", "oauth"],
  "compatibility": {
    "min_app_version": "1.5.0",
    "max_app_version": "2.x.x"
  },
  "dependencies": {
    "templates": [],
    "python_packages": ["requests>=2.28.0", "oauthlib>=3.2.0"]
  },
  "files": {
    "template": "api_rest_v2.json",
    "ui_config": "ui/config-panel.html",
    "ui_script": "ui/config-panel.js",
    "validator": "validators/api_validator.py",
    "icon": "api_icon.svg"
  },
  "permissions": [
    "network",
    "mcp_tools"
  ],
  "ui_components": {
    "config_panel": true,
    "preview_renderer": true
  }
}
```

## Directory Structure

```
template-plugin-name/
├── manifest.json              # This file - plugin metadata
├── template.json              # Template definition (required)
├── README.md                  # Documentation
├── LICENSE                    # License file
├── icon.svg                   # Template icon (optional)
├── ui/                        # Custom UI components (optional)
│   ├── config-panel.html      # Custom configuration UI
│   └── config-panel.js        # UI logic
└── validators/                # Custom validators (optional)
    └── validator.py           # Input validation logic
```

## Usage

### For Template Developers

1. Create `manifest.json` in your template directory
2. Ensure all paths in `files` section are correct
3. Test locally before distribution
4. Package as `.tar.gz` or publish to git repository

### For End Users

Templates with manifests can be:
- Installed from marketplace (future feature)
- Installed from git URL
- Installed from local directory
- Hot-reloaded without app restart

## Population Modes

Templates can support two modes for populating RAG collections:

### 1. Manual Entry Mode
User manually enters question/answer pairs through the template interface.
- **Use case**: Precision control, custom examples, small datasets
- **Workflow**: User fills in template variables for each example
- **Required**: List of required template fields in `required_fields`

### 2. Auto-generate Mode
LLM automatically generates question/answer pairs from provided context.
- **Use case**: Rapid prototyping, large datasets, documentation-driven
- **Workflow**: User provides context (topic, documents, etc.) → LLM generates examples
- **Required**: LLM configuration, `input_variables` specification

### Population Flow (UI)
```
Add RAG Collection
  ├─ Step 1: Collection Details (name, description, MCP server)
  ├─ Step 2: Population Decision
  │    ├─ Option A: No Population (empty collection)
  │    └─ Option B: Populate with Template
  │         ├─ Select Template Type
  │         └─ Step 3: Population Method
  │              ├─ Manual Entry → Fill template fields
  │              └─ Auto-generate → Provide context + LLM generates
  └─ Create Collection
```

### Example: SQL Template with Both Modes

**Manual Mode:**
- User enters: `user_query`, `sql_statement`, `database_name`
- Creates individual RAG cases one by one
- Good for: Verified examples, edge cases, compliance-critical queries

**Auto-generate Mode:**
- User enters: `context_topic` (e.g., "customer analytics"), `document_content` (optional)
- LLM generates: 5-20 question/SQL pairs based on context
- Good for: Training data, documentation coverage, initial seeding

## Validation

### Manifest Validation
The application validates manifests on load:
- Required fields present
- Version format valid
- File paths exist
- Dependencies resolvable
- Permissions declared
- Population modes configuration valid

### Template File Validation
Template files referenced in manifests are validated using JSON schemas:

**For Planner Templates** (sql_query, api_request, etc.):
```python
# Validated against: schemas/planner-schema.json
from rag_templates.exceptions import SchemaValidationError

try:
    manager.get_template("sql_query_v1")
except SchemaValidationError as e:
    print(f"Schema errors: {e.schema_errors}")
    # Example errors:
    # - 'input_variables' is a required property
    # - 'template_id' does not match '^[a-z0-9_]+_v\d+$'
```

**For Knowledge Templates** (knowledge_repository):
```python
# Validated against: schemas/knowledge-template-schema.json
try:
    manager.get_template("knowledge_repo_v1")
except SchemaValidationError as e:
    print(f"Schema errors: {e.schema_errors}")
```

### Type Taxonomy Validation
Templates must correctly use three type concepts:

1. **template_type** (Strategy) - How template executes
   - Planner types: `sql_query`, `api_request`, `custom_workflow`
   - Knowledge type: `knowledge_repository`

2. **repository_type** (Storage) - How data is stored (derived from template_type)
   - `planner` - For execution strategy templates
   - `knowledge` - For document storage templates

3. **category** (UI Grouping) - How templates are organized
   - Examples: `Database`, `Knowledge Management`, `API Integration`

See `TYPE_TAXONOMY.md` for detailed explanation of these concepts.

## Error Handling

Templates use standardized exception hierarchy for consistent error reporting:

```python
from rag_templates.exceptions import (
    TemplateError,              # Base exception
    TemplateNotFoundError,      # Template doesn't exist
    TemplateValidationError,    # Validation failed
    SchemaValidationError,      # JSON schema validation failed
    ToolValidationError,        # Invalid MCP tool references
    TemplateRegistryError,      # Registry issues
    TemplateLoadError          # File loading failed
)

# Example: Handle missing template
try:
    template = manager.get_template("missing_v1")
except TemplateNotFoundError as e:
    print(f"Template {e.template_id} not found")

# Example: Handle validation errors
try:
    manager._validate_template(template_data)
except SchemaValidationError as e:
    print(f"Template: {e.template_id}")
    print(f"Errors: {e.schema_errors}")
except ToolValidationError as e:
    print(f"Invalid tools: {e.invalid_tools}")
```

All exceptions include rich context (template_id, details, original_error) for debugging.

## Security Considerations

- Custom validators run in restricted environment
- File system access limited to template directory
- Network access requires explicit permission
- Code scanning for malicious patterns
- Optional cryptographic signature verification
- MCP tool names validated against whitelist and live server capabilities

## Current Implementation Status

### ✅ Implemented
- **JSON Schema Validation** - Templates validated at load time (schemas/planner-schema.json, knowledge-template-schema.json)
- **Type Taxonomy** - Clear separation of template_type, repository_type, category
- **Error Handling** - Custom exception hierarchy with rich context
- **Tool Validation** - MCP tool names validated against TDA core tools and live server
- **Template Registry** - Central registry with metadata and status
- **Hot Reload** - Templates reload without app restart

### 🚧 Partially Implemented
- **Population Modes** - Manual and auto-generate modes defined in manifest
- **Category System** - Categories defined in registry, UI integration pending
- **Permission System** - Defined in manifest, enforcement pending

### 📋 Planned
- Digital signatures for verified publishers
- Dependency version constraints
- Backward compatibility declarations
- Update channels (stable, beta, nightly)
- Analytics hooks (opt-in)
- Template marketplace
- Version migration tools

## Related Documentation

- **`TYPE_TAXONOMY.md`** - Understanding template_type, repository_type, and category
- **`schemas/README.md`** - JSON schema validation details
- **`schemas/planner-schema.json`** - Schema for execution strategy templates
- **`schemas/knowledge-template-schema.json`** - Schema for document storage templates
- **`exceptions.py`** - Custom exception classes for error handling
- **`IMPROVEMENTS_LOG.md`** - History of system improvements and current health score
