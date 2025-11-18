# Quick Start Guide: TDA Persistent Configuration

## What's New?

TDA now saves RAG collection metadata to a persistent configuration file (`tda_config.json`) that survives application restarts. No more manual re-configuration!

## Location

The configuration file is automatically created at:
```
<project-root>/tda_config.json
```

## Automatic Operation

The configuration system works automatically. You don't need to do anything special:

1. **On First Startup**: 
   - `tda_config.json` is created with the default RAG collection
   
2. **When You Add a Collection**:
   - Collection metadata is saved to `tda_config.json`
   - Collection is created in ChromaDB
   
3. **On Application Restart**:
   - All collections are loaded from `tda_config.json`
   - Collections are recreated in ChromaDB
   - Everything works as before!

## Using the API

### Create a Collection
```bash
curl -X POST http://localhost:5050/v1/rag/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Collection",
    "description": "Collection for specific use cases",
    "mcp_server_id": "teradata_mcp_server"
  }'
```

### Update Collection Metadata
```bash
curl -X PUT http://localhost:5050/v1/rag/collections/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "description": "Updated description"
  }'
```

### Delete a Collection
```bash
curl -X DELETE http://localhost:5050/v1/rag/collections/1
```

### Toggle Collection (Enable/Disable)
```bash
curl -X POST http://localhost:5050/v1/rag/collections/1/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

## Manual Configuration (Advanced)

You can manually edit `tda_config.json` if needed:

```json
{
  "schema_version": "1.0",
  "created_at": "2025-11-18T10:30:00+00:00",
  "last_modified": "2025-11-18T10:30:00+00:00",
  "rag_collections": [
    {
      "id": 0,
      "name": "Default TDA RAG Cases",
      "collection_name": "tda_rag_cases_collection",
      "mcp_server_id": null,
      "enabled": true,
      "created_at": "2025-11-18T10:30:00+00:00",
      "description": "Default collection for TDA RAG cases"
    }
  ]
}
```

**Important**: 
- Restart the application after manual edits
- Keep valid JSON format
- Don't delete the default collection (ID 0)
- Collection IDs must be unique integers

## Backup and Recovery

### Automatic Backup
If `tda_config.json` becomes corrupted, TDA will:
1. Back it up to `tda_config.json.backup`
2. Create a fresh config with defaults
3. Log the issue for investigation

### Manual Backup
```bash
# Create a backup before making changes
cp tda_config.json tda_config.json.backup

# Restore from backup
cp tda_config.json.backup tda_config.json
```

## Troubleshooting

### Config File Not Created
- Check file permissions in the project directory
- Look for errors in the application logs
- Ensure the application has write access

### Collections Not Loading
- Verify `tda_config.json` has valid JSON syntax
- Check that `RAG_ENABLED = True` in config.py
- Review application startup logs

### Lost Collections After Restart
- Check if `tda_config.json` exists and contains your collections
- Look for backup file (`tda_config.json.backup`)
- Review logs for any errors during save operations

## Migration from Previous Versions

If you're upgrading from a version without persistent config:
1. Start the application - `tda_config.json` will be created
2. Add your collections via the UI or API
3. Collections will now persist automatically

## Future Enhancements

The configuration system is designed to be extended. Future versions may include:
- User preferences and settings
- Custom prompt templates  
- Saved workflows
- MCP server configurations

All will be stored in the same `tda_config.json` file.

## More Information

See the full documentation:
- [docs/tda_config.md](../docs/tda_config.md) - Configuration file format
- [docs/IMPLEMENTATION_CONFIG_PERSISTENCE.md](../docs/IMPLEMENTATION_CONFIG_PERSISTENCE.md) - Implementation details
