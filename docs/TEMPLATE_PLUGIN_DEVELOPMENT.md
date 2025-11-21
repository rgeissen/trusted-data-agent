# Template Plugin Development Guide

## Overview

This guide explains how to create, test, and distribute modular template plugins for the Trusted Data Agent (TDA). The plugin system allows community developers to create and share custom templates that can be installed on-demand.

## Quick Start

### Creating Your First Template Plugin

```bash
# 1. Create plugin directory
mkdir my-custom-template
cd my-custom-template

# 2. Create manifest.json
cat > manifest.json << 'EOF'
{
  "name": "my-custom-template",
  "version": "1.0.0",
  "template_id": "my_custom_v1",
  "display_name": "My Custom Template",
  "description": "A custom template for specific use cases",
  "author": "Your Name",
  "license": "MIT",
  "keywords": ["custom", "example"],
  "files": {
    "template": "template.json"
  },
  "permissions": ["mcp_tools"]
}
EOF

# 3. Create template.json (see Template Structure below)

# 4. Test locally
python -m trusted_data_agent.tools.validate_template .

# 5. Package for distribution
tar -czf my-custom-template-1.0.0.tar.gz .
```

## Directory Structure

```
my-custom-template/
├── manifest.json              # Required: Plugin metadata
├── template.json              # Required: Template definition
├── README.md                  # Recommended: Documentation
├── LICENSE                    # Recommended: License file
├── icon.svg                   # Optional: Template icon
├── ui/                        # Optional: Custom UI components
│   ├── config-panel.html
│   └── config-panel.js
└── validators/                # Optional: Custom validators
    └── validator.py
```

## Manifest File (`manifest.json`)

### Required Fields

```json
{
  "name": "template-package-name",
  "version": "1.0.0",
  "template_id": "template_id_v1",
  "display_name": "Human Readable Name",
  "author": "Your Name or Organization"
}
```

### Complete Example

```json
{
  "name": "advanced-api-template",
  "version": "2.0.0",
  "template_id": "api_advanced_v2",
  "display_name": "Advanced API Request Template",
  "description": "Multi-step API workflow with authentication, retry logic, and error handling",
  "author": "community-developer",
  "license": "MIT",
  "homepage": "https://github.com/dev/advanced-api-template",
  "repository": {
    "type": "git",
    "url": "https://github.com/dev/advanced-api-template"
  },
  "keywords": ["api", "rest", "http", "oauth", "authentication"],
  "compatibility": {
    "min_app_version": "1.5.0",
    "max_app_version": "2.x.x"
  },
  "dependencies": {
    "templates": [],
    "python_packages": ["requests>=2.28.0"]
  },
  "files": {
    "template": "template.json",
    "ui_config": "ui/config-panel.html",
    "ui_script": "ui/config-panel.js",
    "icon": "icon.svg"
  },
  "permissions": ["network", "mcp_tools"],
  "ui_components": {
    "config_panel": true,
    "preview_renderer": false
  }
}
```

## Template File (`template.json`)

### Required Structure

```json
{
  "template_id": "my_custom_v1",
  "template_name": "My Custom Template",
  "template_version": "1.0.0",
  "template_type": "custom_workflow",
  "description": "Detailed description of what this template does",
  "status": "active",
  "input_variables": {
    "user_query": {
      "type": "string",
      "required": true,
      "description": "The user's question"
    },
    "custom_param": {
      "type": "string",
      "required": false,
      "description": "Optional parameter",
      "default": "default_value"
    }
  },
  "output_configuration": {
    "session_id": {
      "type": "constant",
      "value": "00000000-0000-0000-0000-000000000000"
    },
    "llm_config": {
      "provider": {"type": "constant", "value": "Template"},
      "model": {"type": "constant", "value": "my_custom_v1"}
    }
  },
  "strategy_template": {
    "phase_count": 2,
    "phases": [
      {
        "phase": 1,
        "goal_template": "Execute custom action: {custom_param}",
        "relevant_tools": ["mcp_tool_name"],
        "arguments": {
          "param1": {"source": "custom_param"}
        }
      },
      {
        "phase": 2,
        "goal": "Generate final report",
        "relevant_tools": ["TDA_FinalReport"],
        "arguments": {}
      }
    ]
  }
}
```

## Testing Your Template

### 1. Local Validation

```bash
# Validate manifest and template structure
python -c "
from trusted_data_agent.agent.template_plugin_validator import validate_plugin_package
from pathlib import Path

is_valid, errors, warnings = validate_plugin_package(Path('.'))
print(f'Valid: {is_valid}')
if errors:
    print('Errors:', errors)
if warnings:
    print('Warnings:', warnings)
"
```

### 2. Install Locally

```bash
# Copy to user plugin directory
mkdir -p ~/.tda/templates/my-custom-template
cp -r ./* ~/.tda/templates/my-custom-template/

# Reload templates via API
curl -X POST http://localhost:8080/api/v1/rag/templates/reload
```

### 3. Test via API

```bash
# List all templates (should include yours)
curl http://localhost:8080/api/v1/rag/templates/list

# Get your template info
curl http://localhost:8080/api/v1/rag/templates/my_custom_v1/plugin-info

# Test population
curl -X POST http://localhost:8080/api/v1/rag/collections/1/populate \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "custom_workflow",
    "examples": [{
      "user_query": "Test question",
      "custom_param": "test_value"
    }]
  }'
```

## Distribution

### Option 1: GitHub Repository

```bash
# 1. Create GitHub repo
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourusername/template-name
git push -u origin main

# 2. Create release
git tag -a v1.0.0 -m "Version 1.0.0"
git push origin v1.0.0

# 3. Users can install via:
# (Future feature)
tda-template install https://github.com/yourusername/template-name
```

### Option 2: Package Archive

```bash
# Create distributable archive
tar -czf my-template-1.0.0.tar.gz \
  manifest.json \
  template.json \
  README.md \
  LICENSE \
  icon.svg

# Users can install via:
# (Future feature)
tda-template install my-template-1.0.0.tar.gz
```

### Option 3: Template Marketplace

(Coming soon - submit to central marketplace)

## Advanced Features

### Custom UI Components

Create custom configuration panels for your template:

**ui/config-panel.html:**
```html
<div class="custom-template-config">
    <label>Custom Setting</label>
    <input type="text" id="custom-setting" />
    <button onclick="saveCustomConfig()">Save</button>
</div>
```

**ui/config-panel.js:**
```javascript
function saveCustomConfig() {
    const value = document.getElementById('custom-setting').value;
    fetch(`/api/v1/rag/templates/my_custom_v1/config`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({custom_setting: value})
    });
}
```

### Custom Validators

Create Python validators for input validation:

**validators/validator.py:**
```python
def validate_input(input_data):
    """
    Validate template input data.
    
    Args:
        input_data: Dictionary of input values
        
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    if 'custom_param' in input_data:
        value = input_data['custom_param']
        if len(value) > 100:
            errors.append("custom_param must be <= 100 characters")
    
    return len(errors) == 0, errors
```

## Security Considerations

### Permissions

Declare all required permissions in manifest:
- `database_access`: Query databases
- `mcp_tools`: Use MCP tools
- `file_system`: Read/write files
- `network`: Make HTTP requests

### Code Scanning

Templates are automatically scanned for:
- Use of `eval()`, `exec()`
- File write operations
- Subprocess execution
- Unsafe JavaScript patterns

### Best Practices

1. ✅ **Minimize permissions**: Only request what you need
2. ✅ **Validate inputs**: Use custom validators
3. ✅ **Document clearly**: README with examples
4. ✅ **Version properly**: Follow semantic versioning
5. ✅ **Test thoroughly**: Include test cases
6. ❌ **Never** include hardcoded credentials
7. ❌ **Avoid** arbitrary code execution
8. ❌ **Don't** access files outside plugin directory

## API Reference

### Discover Plugins
```bash
GET /api/v1/rag/templates/discover
```

Returns all discovered plugins including unloaded ones.

### Get Plugin Info
```bash
GET /api/v1/rag/templates/{template_id}/plugin-info
```

Returns manifest.json content for a template.

### Reload Templates
```bash
POST /api/v1/rag/templates/reload
```

Hot-reload all templates without restart.

### Validate Plugin
```bash
POST /api/v1/rag/templates/validate
Body: {"plugin_path": "/path/to/plugin"}
```

Validate plugin before installation.

## Examples

See the `examples/` directory for complete template examples:
- `examples/sql-query-basic/` - Simple SQL template
- `examples/api-rest-advanced/` - API with authentication
- `examples/custom-workflow/` - Multi-step workflow

## Troubleshooting

### Template Not Loading

1. Check manifest.json syntax:
   ```bash
   python -m json.tool manifest.json
   ```

2. Validate template structure:
   ```bash
   curl -X POST http://localhost:8080/api/v1/rag/templates/validate \
     -d '{"plugin_path": "/path/to/template"}'
   ```

3. Check application logs:
   ```bash
   tail -f logs/app.log | grep template
   ```

### Validation Errors

Common issues:
- Missing required manifest fields
- Invalid version format (must be X.Y.Z)
- Invalid template_id format (must be lowercase_v1)
- Template file not found
- Security scan warnings

## Contributing

To contribute templates to the official collection:

1. Follow this development guide
2. Ensure all validations pass
3. Include comprehensive README
4. Add test cases
5. Submit pull request to main repository

## Support

- Documentation: https://github.com/rgeissen/trusted-data-agent/docs
- Issues: https://github.com/rgeissen/trusted-data-agent/issues
- Discussions: https://github.com/rgeissen/trusted-data-agent/discussions

## License

Template plugins can use any OSI-approved license. Common choices:
- MIT - Permissive
- Apache-2.0 - Permissive with patent protection
- GPL-3.0 - Copyleft
- AGPL-3.0 - Strong copyleft (matches TDA core)
