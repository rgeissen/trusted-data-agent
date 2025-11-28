# Marketplace Testing Guide

## Quick Start Test

### Prerequisites
- Server running: `python -m trusted_data_agent.main --host 0.0.0.0 --port 5050`
- Two user accounts: `admin` and `test2`
- Fresh database with Default Collections created

### Test 1: Publish a Collection

**As admin user:**

1. **Login** as `admin`
2. Navigate to **Intelligence** panel (Knowledge Repositories)
3. Create a new collection:
   - Click "Create New Collection"
   - Name: "SQL Performance Tips"
   - Description: "Best practices for SQL optimization"
   - MCP Server: (select your MCP server)
   - Click "Create"

4. **Publish to Marketplace**:
   - Find "SQL Performance Tips" in your collections
   - Click the **⋮** (three dots) menu
   - Select "Publish to Marketplace"
   - Set visibility: **Public**
   - Category: "Analytics"
   - Tags: ["sql", "performance", "optimization"]
   - Long description: "Curated collection of SQL query optimization patterns"
   - Click "Publish"

5. **Verify Publication**:
   - You should see a 🌐 (globe) badge on the collection card
   - The badge indicates it's published to marketplace

### Test 2: Browse Marketplace

**As test2 user:**

1. **Login** as `test2`
2. Navigate to **Marketplace** panel (shopping bag icon in sidebar)
3. You should see two tabs:
   - "Browse Marketplace" (active)
   - "My Collections"

4. **Browse Published Collections**:
   - You should see "SQL Performance Tips" collection
   - Collection card shows:
     - Name and description
     - Owner: admin
     - Subscriber count: 0
     - Tags and category
   - You should NOT see admin's Default Collection (private)

5. **Search and Filter**:
   - Try searching for "SQL"
   - Try changing visibility filter
   - Pagination should work if > 50 collections

### Test 3: Subscribe to Collection

**Still as test2:**

1. **Subscribe**:
   - Find "SQL Performance Tips" in marketplace
   - Click "Subscribe" button
   - You should see success notification
   - Button changes to "Subscribed"

2. **Verify Subscription**:
   - Switch to "My Collections" tab
   - "SQL Performance Tips" should appear
   - It should have a 📌 (pin) badge indicating subscription
   - Subscriber count should be 1

3. **Check Intelligence Panel**:
   - Navigate to **Intelligence** panel
   - "SQL Performance Tips" should appear in your list
   - It should have 📌 Subscribed badge
   - Click "Inspect" - should work even though you don't own it

### Test 4: Use Subscribed Collection in RAG

**Still as test2:**

1. **Add a case to the collection** (as admin first):
   - Switch back to admin user
   - Add some RAG cases to "SQL Performance Tips"
   - Use the MCP workflow to generate some cases

2. **Query as subscriber** (as test2):
   - Login as test2
   - Ask a question related to SQL performance
   - The RAG retriever should find examples from:
     - Your Default Collection (owned)
     - SQL Performance Tips (subscribed)

3. **Verify Retrieval**:
   - Check server logs for RAG retrieval
   - Should see: "Retrieved RAG cases from collections: [0, 1]"
   - Collection 0 = test2's Default Collection
   - Collection 1 = SQL Performance Tips (subscribed)

### Test 5: Unsubscribe

**As test2:**

1. **Unsubscribe**:
   - Go to Marketplace → "My Collections" tab
   - Find "SQL Performance Tips"
   - Click "Unsubscribe" button
   - Confirm action

2. **Verify Unsubscription**:
   - Collection disappears from "My Collections"
   - Intelligence panel no longer shows it
   - Subscriber count decrements to 0
   - No longer used in RAG retrieval

### Test 6: Fork a Collection (Optional)

**As test2:**

1. **Fork**:
   - Browse marketplace
   - Find "SQL Performance Tips"
   - Click "Fork" button
   - Name: "My SQL Tips"
   - Description: "Customized version"
   - Click "Fork"

2. **Verify Fork**:
   - New collection "My SQL Tips" appears in your Intelligence panel
   - Has 👤 Owner badge (you own it)
   - Contains same cases as original
   - Completely independent - changes don't sync

---

## Expected Behavior

### Collection Visibility Rules

| Collection State | Owner Sees | Subscribers See | Marketplace |
|-----------------|------------|-----------------|-------------|
| Private | ✅ Yes | ❌ No | ❌ Hidden |
| Public (not listed) | ✅ Yes | ❌ No | ❌ Hidden |
| Public (listed) | ✅ Yes | ✅ Yes (if subscribed) | ✅ Visible |
| Unlisted (listed) | ✅ Yes | ✅ Yes (if subscribed) | ✅ Visible (with link) |

### Badge Indicators

- **👤 Owner**: You created this collection
- **📌 Subscribed**: You're subscribed (reference-only, no copy)
- **🌐 Public**: Published and listed in marketplace
- **🔗 Unlisted**: Published but only accessible via direct link

### RAG Retrieval Scope

User sees cases from:
1. ✅ Collections they own (owner_user_id matches)
2. ✅ Collections they subscribe to (active subscription)
3. ✅ Admin collections (owner_user_id is NULL)
4. ❌ Other users' private collections

---

## Troubleshooting

### Issue: "Marketplace is empty"

**Possible causes:**
- No collections published to marketplace
- All collections are private
- Collections not marked as `is_marketplace_listed = true`

**Fix:**
```bash
# Check database
sqlite3 tda_auth.db "SELECT id, name, visibility, is_marketplace_listed FROM collections;"

# Ensure at least one collection has:
# - visibility = 'public'
# - is_marketplace_listed = 1
```

### Issue: "Subscribe button doesn't work"

**Check:**
1. Are you logged in? (JWT token in localStorage)
2. Do you already own the collection?
3. Are you already subscribed?
4. Check browser console for errors
5. Check server logs for error messages

### Issue: "Subscribed collection not appearing in Intelligence"

**Check:**
1. Is the subscription `enabled = true` in database?
2. Restart the application (collections loaded on startup)
3. Check server logs for collection loading

### Issue: "RAG doesn't use subscribed collections"

**Check:**
1. Is the collection loaded in ChromaDB?
2. Does it have any cases?
3. Check `retrieve_examples()` log output
4. Verify collection is in `self.collections` dict

---

## Database Queries for Debugging

```bash
# List all collections
sqlite3 tda_auth.db "SELECT id, name, owner_user_id, visibility, is_marketplace_listed, subscriber_count FROM collections;"

# List all subscriptions
sqlite3 tda_auth.db "SELECT * FROM collection_subscriptions;"

# Check specific user's subscriptions
sqlite3 tda_auth.db "SELECT cs.*, c.name FROM collection_subscriptions cs JOIN collections c ON cs.source_collection_id = c.id WHERE cs.user_id = 'USER_UUID_HERE';"

# Count subscribers per collection
sqlite3 tda_auth.db "SELECT source_collection_id, COUNT(*) as subscribers FROM collection_subscriptions WHERE enabled = 1 GROUP BY source_collection_id;"
```

---

## API Testing with curl

```bash
# Get JWT token (save from login)
TOKEN="your-jwt-token-here"

# Browse marketplace
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5050/api/v1/marketplace/collections?limit=10"

# Subscribe to collection ID 1
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5050/api/v1/marketplace/collections/1/subscribe"

# Unsubscribe (use subscription_id from response)
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5050/api/v1/marketplace/subscriptions/SUBSCRIPTION_UUID"

# Publish collection ID 1
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "public", "marketplace_metadata": {"category": "analytics", "tags": ["sql"], "long_description": "Test"}}' \
  "http://localhost:5050/api/v1/rag/collections/1/publish"
```

---

## Success Criteria

✅ **Phase 1 Complete** if:
- Admin can publish collections to marketplace
- test2 can browse marketplace and see admin's published collections
- test2 can subscribe/unsubscribe
- Subscribed collections appear in Intelligence panel with 📌 badge
- RAG retrieval uses both owned and subscribed collections
- Subscriber counts update correctly
- Collections filtered by user properly (isolation working)

---

**Last Updated:** 2025-11-28  
**Version:** Phase 1 - Core Marketplace  
**Status:** Ready for Testing
