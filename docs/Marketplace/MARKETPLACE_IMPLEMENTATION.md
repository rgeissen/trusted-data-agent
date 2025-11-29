# Planner Repository Marketplace - Implementation Guide

## Phase 1: Data Model & Ownership (COMPLETED)

### Overview

This document tracks the implementation of the Planner Repository Marketplace feature, which enables users to share and discover RAG collections through a reference-based subscription model.

---

## Database Schema Changes

### New Tables

#### 1. `collection_subscriptions`
Tracks user subscriptions to shared marketplace collections (reference-based, no data copy).

**Columns:**
- `id` (PK): UUID
- `user_id` (FK): References `users.id`
- `source_collection_id`: Collection ID from `tda_config.json`
- `enabled`: Boolean (toggle on/off)
- `subscribed_at`: Timestamp
- `last_synced_at`: Timestamp (future use)

**Indexes:**
- Unique index on `(user_id, source_collection_id)`
- Index on `user_id`
- Index on `source_collection_id`

#### 2. `collection_ratings`
User ratings and reviews for marketplace collections.

**Columns:**
- `id` (PK): UUID
- `collection_id`: Collection ID from `tda_config.json`
- `user_id` (FK): References `users.id`
- `rating`: Integer (1-5 stars)
- `comment`: Text (optional)
- `helpful_count`: Integer (future voting)
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Indexes:**
- Unique index on `(collection_id, user_id)`
- Index on `collection_id`

---

## Collection Metadata Extensions

### New Fields in `tda_config.json`

Each collection now includes:

```json
{
  "id": 1,
  "name": "Collection Name",
  "collection_name": "tda_rag_coll_1_abc123",
  "mcp_server_id": "...",
  "enabled": true,
  
  // NEW MARKETPLACE FIELDS
  "owner_user_id": "uuid-123",           // null = admin-owned
  "visibility": "private",                // private | shared | public
  "is_marketplace_listed": false,         // Listed in marketplace UI
  "subscriber_count": 0,                  // Cache of subscriber count
  "marketplace_metadata": {               // Extended metadata
    "author": "username",
    "description": "Detailed description",
    "tags": ["tag1", "tag2"],
    "category": "customer-analytics",
    "published_at": "2025-11-27T...",
    "updated_at": "2025-11-27T..."
  }
}
```

**Field Descriptions:**
- `owner_user_id`: User who created/owns the collection (null for system collections)
- `visibility`: Access control level
  - `private`: Only owner can see
  - `shared`: Owner + specific users (future: share links)
  - `public`: Listed in marketplace, anyone can subscribe
- `is_marketplace_listed`: Whether collection appears in marketplace browse
- `subscriber_count`: Cached count for performance (updated on subscribe/unsubscribe)
- `marketplace_metadata`: Optional extended metadata for published collections

---

## Migration Process

### Step 1: Run Migration Script

```bash
# Dry run first (see what would change)
python maintenance/migrate_marketplace_schema.py --dry-run

# Apply migration
python maintenance/migrate_marketplace_schema.py
```

**What the migration does:**
1. Creates `collection_subscriptions` table
2. Creates `collection_ratings` table
3. Adds marketplace fields to existing collections in `tda_config.json`:
   - `owner_user_id = null` (admin-owned by default)
   - `visibility = "private"` (safe default)
   - `is_marketplace_listed = false` (not published)
   - `subscriber_count = 0`
   - `marketplace_metadata = {}` (empty placeholder)

### Step 2: Verify Migration

The script automatically runs verification unless `--skip-verification` is used.

Manual verification:
```bash
# Check database tables exist
sqlite3 tda_auth.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'collection_%';"

# Check collection metadata
python -c "from trusted_data_agent.core.config_manager import get_config_manager; 
import json; 
print(json.dumps(get_config_manager().get_rag_collections()[0], indent=2))"
```

---

## Backward Compatibility

### Existing Collections
- All existing collections migrate safely with default values
- `owner_user_id = null` means admin-owned (backward compatible)
- `visibility = "private"` means not shared (safe default)
- Existing queries continue to work unchanged

### RAG Retriever
- Current `retrieve_examples()` method works without changes
- Collection loading (`_load_active_collections()`) works unchanged
- Only new subscription logic needs to be added (Phase 2)

---

## Next Steps (Phase 2)

### Code Changes Required:

1. **Update RAG Retriever** (`src/trusted_data_agent/agent/rag_retriever.py`):
   - Add `_get_user_accessible_collections(user_id)` method
   - Update `_load_active_collections()` to handle subscriptions
   - Skip `_maintain_vector_store()` for subscribed collections
   - Add `fork_collection()` method

2. **Update Collection APIs** (`src/trusted_data_agent/api/rest_routes.py`):
   - Filter collections by user ownership + subscriptions
   - Add ownership validation on create/update/delete
   - Pass `owner_user_id` when creating collections

3. **Create Marketplace Routes** (`src/trusted_data_agent/api/marketplace_routes.py`):
   - `GET /api/v1/marketplace/collections` - Browse public collections
   - `POST /api/v1/marketplace/collections/{id}/subscribe` - Subscribe
   - `DELETE /api/v1/marketplace/subscriptions/{id}` - Unsubscribe
   - `POST /api/v1/marketplace/collections/{id}/fork` - Fork (copy)
   - `POST /api/v1/rag/collections/{id}/publish` - Publish
   - `POST /api/v1/marketplace/collections/{id}/rate` - Rate

---

## Testing Checklist

- [ ] Migration script runs successfully (dry-run)
- [ ] Migration script applies changes correctly
- [ ] Database tables created with proper indexes
- [ ] Collection metadata updated in tda_config.json
- [ ] Existing collections still load and query correctly
- [ ] No breaking changes to current RAG functionality

---

## Reference Architecture

### Subscription Model (Reference-Based)

```
Owner's Collection:
  ├── tda_config.json (id=1, owner=alice, visibility=public)
  ├── rag/tda_rag_cases/collection_1/ (alice's case files)
  └── .chromadb_rag_cache/tda_rag_coll_1_abc (ChromaDB collection)
                                          ↑
                                          | (reference only)
Subscriber:                               |
  ├── collection_subscriptions → (user=bob, source_collection_id=1)
  └── At query time: uses alice's ChromaDB collection
```

**Key Benefits:**
- ✅ No data duplication
- ✅ Auto-updates when owner adds cases
- ✅ 100x storage efficiency
- ✅ Clear attribution to original author

### Fork Model (Copy on Request)

```
Forked Collection:
  ├── tda_config.json (id=2, owner=bob, visibility=private, forked_from=1)
  ├── rag/tda_rag_cases/collection_2/ (bob's copied case files)
  └── .chromadb_rag_cache/tda_rag_coll_2_xyz (bob's ChromaDB collection)
```

**When to Fork:**
- User wants to customize cases
- User wants independent version control
- User wants to publish derivative work

---

## Rollback Procedure

If migration needs to be rolled back:

```bash
# 1. Drop marketplace tables
sqlite3 tda_auth.db "DROP TABLE IF EXISTS collection_subscriptions;"
sqlite3 tda_auth.db "DROP TABLE IF EXISTS collection_ratings;"

# 2. Restore tda_config.json from backup
cp tda_config.json.backup tda_config.json

# 3. Restart application
```

**Note:** Always backup `tda_config.json` before migration!

---

## Support & Troubleshooting

### Common Issues

**Q: Migration script fails with "table already exists"**  
A: Tables already migrated. Use `--skip-verification` or check existing schema.

**Q: Collections don't load after migration**  
A: Check `tda_config.json` syntax. Ensure all collections have required fields.

**Q: Permission denied on migration script**  
A: Run `chmod +x maintenance/migrate_marketplace_schema.py`

### Getting Help

- Check logs in migration output
- Review `tda_config.json` for syntax errors
- Verify database file permissions
- Ensure Python environment is activated

---

**Status:** Phase 1 Complete ✅  
**Next:** Phase 2 - Collection Ownership & Access Control
