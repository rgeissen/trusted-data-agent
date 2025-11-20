# Quick Reference: RAG Template Population

## 🚀 Quick Start

### 1. Get Available Templates
```bash
curl http://localhost:5050/api/v1/rag/templates
```

### 2. Populate Collection
```bash
curl -X POST http://localhost:5050/api/v1/rag/collections/1/populate \
  -H "Content-Type: application/json" \
  -d '{
    "template_type": "sql_query",
    "examples": [
      {
        "user_query": "Show all users",
        "sql_statement": "SELECT * FROM users"
      },
      {
        "user_query": "Count orders",
        "sql_statement": "SELECT COUNT(*) FROM orders"
      }
    ],
    "database_name": "mydb"
  }'
```

### 3. Using the Example Script
```bash
cd docs/RAG
./example_template_population.py --collection-id 1 --database mydb
```

## 📁 Directory Structure

```
rag/tda_rag_cases/
├── collection_0/       # Default collection
│   ├── case_xxx.json
│   └── case_yyy.json
├── collection_1/       # MCP server 1
│   └── case_aaa.json
└── collection_2/       # MCP server 2
    └── case_bbb.json
```

## 🔧 Template Types

### SQL Query Template
**Use for:** Database queries that need SQL execution + report generation

**Required fields:**
- `user_query`: Natural language question
- `sql_statement`: SQL to execute

**Optional fields:**
- `database_name`: Context (stored in metadata)
- `mcp_tool_name`: Tool name (default: `base_executeRawSQLStatement`)

## ✅ Validation Rules

- User query cannot be empty
- SQL statement cannot be empty  
- SQL must contain keywords: SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER
- Collection must exist in APP_STATE

## 📊 Response Format

```json
{
  "status": "success",
  "message": "Successfully populated 3 cases",
  "results": {
    "collection_id": 1,
    "collection_name": "MySQL DB",
    "total_examples": 3,
    "successful": 3,
    "failed": 0,
    "case_ids": ["uuid1", "uuid2", "uuid3"],
    "errors": []
  }
}
```

## 🎯 Best Practices

1. **Start Small**: Test with 2-3 examples first
2. **Diverse Queries**: Cover different query patterns
3. **Clear Questions**: Make user_query natural and specific
4. **Test Retrieval**: Query after population to verify
5. **Monitor Feedback**: Track which templates work best

## 🔍 Verification Commands

```bash
# Check collection contents
curl http://localhost:5050/api/v1/rag/collections/1/rows

# Check file system
ls -la rag/tda_rag_cases/collection_1/

# Test retrieval (query the agent)
curl -X POST http://localhost:5050/api/v1/sessions/{session_id}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show all users"}'
```

## ⚠️ Important Notes

- Template cases start with `is_most_efficient: true`
- They compete with organic cases based on feedback
- Downvoting demotes them like any other case
- Migration is automatic on first startup
- Original cases moved to `collection_0/`

## 🐛 Troubleshooting

**"Collection ID does not exist"**
→ Create collection first: `POST /api/v1/rag/collections`

**"Validation failed"**
→ Check examples have both user_query and sql_statement
→ Ensure SQL contains valid keywords

**"RAG retriever not initialized"**
→ Check RAG_ENABLED in config
→ Verify application started successfully

**Cases not retrieved**
→ Enable collection: `POST /api/v1/rag/collections/{id}/toggle`
→ Check similarity score (must be > 0.7)
→ Verify MCP server ID matches collection
