# Feedback Consistency Implementation Plan

## Executive Summary

The system has a **data synchronization issue** between ChromaDB (used for fast table queries) and the filesystem (source of truth). When users provide feedback, the filesystem is updated correctly, but ChromaDB metadata isn't always synchronized, causing:

- Table shows "-" (dash) for feedback that exists in details panel
- Inconsistent display across the same data

**Recommended Solution**: Implement a two-phase fix using filesystem-as-truth with in-memory cache layer.

**Timeline**: 4-5 days for complete implementation with testing

---

## Immediate Fix (Day 1 - Quick Win)

### Problem
Currently, when rendering the overview table, feedback comes from ChromaDB metadata which may be stale.

### Solution
Add a new backend endpoint that loads feedback directly from case files for authoritative data.

### Implementation

**File**: `/src/trusted_data_agent/api/routes.py`

Add after line 835:
```python
@api_bp.route("/rag/collections/<int:collection_id>/rows/authoritative", methods=["GET"])
async def get_collection_rows_authoritative(collection_id):
    """
    Returns collection rows with feedback loaded from authoritative source (filesystem case files).
    This bypasses ChromaDB metadata and reads directly from case files to ensure accuracy.
    
    This endpoint is used by the UI table to display correct feedback values while
    we implement the full caching solution.
    """
    # Same parameters as get_collection_rows
    limit = request.args.get('limit', default=25, type=int)
    limit = max(1, min(limit, 100))
    query_text = request.args.get('q', default=None, type=str)
    light = request.args.get('light', default='true').lower() == 'true'
    
    try:
        # First, get the rows from ChromaDB (for search/sampling logic)
        # This gives us the IDs and basic metadata
        resp = await get_collection_rows(collection_id)
        data = json.loads(resp.data)
        
        if 'error' in data:
            return jsonify(data), 400
        
        rows = data.get('rows', [])
        
        # Now, for each row, load the case file to get authoritative feedback
        project_root = Path(__file__).resolve().parents[3]
        cases_dir = project_root / 'rag' / 'tda_rag_cases'
        
        for row in rows:
            case_id = row.get('id')
            if case_id:
                # Search for case file
                file_stem = case_id if case_id.startswith('case_') else f'case_{case_id}'
                case_path = None
                
                # Check in collection subdirectories
                for collection_dir in cases_dir.glob("collection_*"):
                    if collection_dir.is_dir():
                        potential_path = collection_dir / f"{file_stem}.json"
                        if potential_path.exists():
                            case_path = potential_path
                            break
                
                # Load feedback from case file
                if case_path:
                    try:
                        with open(case_path, 'r', encoding='utf-8') as f:
                            case_data = json.load(f)
                        authoritative_feedback = case_data.get('metadata', {}).get('user_feedback_score', 0)
                        row['user_feedback_score'] = authoritative_feedback
                        app_logger.debug(f"Loaded authoritative feedback for {case_id}: {authoritative_feedback}")
                    except Exception as e:
                        app_logger.warning(f"Could not load case file for {case_id}: {e}")
                        # Keep whatever was in row already
        
        return jsonify({
            "rows": rows,
            "total": data.get('total', 0),
            "query": query_text,
            "collection_id": collection_id,
            "collection_name": data.get('collection_name', ''),
            "source": "authoritative"  # Indicate data source
        })
        
    except Exception as e:
        app_logger.error(f"Error getting authoritative collection rows: {e}", exc_info=True)
        return jsonify({"error": "Failed to get collection rows"}), 500
```

**File**: `/static/js/ui.js`

Update `fetchAndRenderCollectionRows()` function (around line 2252):

Change:
```javascript
const res = await fetch(`/rag/collections/${collectionId}/rows?${params.toString()}`);
```

To:
```javascript
// Use authoritative endpoint if available for accurate feedback display
const endpoint = `/rag/collections/${collectionId}/rows/authoritative?${params.toString()}`;
const fallbackEndpoint = `/rag/collections/${collectionId}/rows?${params.toString()}`;

let res = await fetch(endpoint);
if (!res.ok && res.status === 404) {
    // Fallback to standard endpoint if authoritative not available yet
    console.log('Authoritative endpoint not available, using standard endpoint');
    res = await fetch(fallbackEndpoint);
}
```

### Testing
```bash
# Test the new endpoint
curl http://localhost:8080/rag/collections/1/rows/authoritative

# Verify feedback is populated
```

---

## Phase 1: In-Memory Cache Layer (Day 2-3)

### Problem
Even with the authoritative endpoint, file I/O on every table render is slow.

### Solution
Cache feedback scores in memory, updated atomically with changes.

### Implementation

**File**: `/src/trusted_data_agent/agent/rag_retriever.py`

Add at class initialization (line ~50):

```python
# Add to __init__ method after other initializations
self.feedback_cache = {}  # Maps case_id -> feedback_score
self._load_feedback_cache()
```

Add new methods (after line 550):

```python
def _load_feedback_cache(self):
    """Load all feedback scores from case files into memory cache."""
    try:
        cases_dir = self.cases_base_dir
        self.feedback_cache = {}
        
        for collection_id in self.collections.keys():
            collection_dir = self._get_collection_dir(collection_id)
            if not collection_dir.exists():
                continue
            
            for case_file in collection_dir.glob('case_*.json'):
                try:
                    with open(case_file, 'r', encoding='utf-8') as f:
                        case_data = json.load(f)
                    case_id = case_data.get('case_id', case_file.stem.replace('case_', ''))
                    feedback = case_data.get('metadata', {}).get('user_feedback_score', 0)
                    self.feedback_cache[case_id] = feedback
                except Exception as e:
                    logger.debug(f"Error loading cache for {case_file}: {e}")
        
        logger.info(f"Loaded feedback cache with {len(self.feedback_cache)} entries")
    except Exception as e:
        logger.error(f"Error loading feedback cache: {e}")

def get_feedback_score(self, case_id: str) -> int:
    """Get feedback score from cache."""
    return self.feedback_cache.get(case_id, 0)

async def _invalidate_feedback_cache(self):
    """Reload feedback cache - call after updates."""
    self._load_feedback_cache()
```

Update `update_case_feedback()` method (line 463):

```python
async def update_case_feedback(self, case_id: str, feedback_score: int) -> bool:
    """
    Update user feedback for a RAG case.
    Updates both filesystem and ChromaDB atomically.
    """
    import json
    
    # ... existing code ...
    
    try:
        # Update case study JSON in filesystem
        with open(case_file, 'r', encoding='utf-8') as f:
            case_study = json.load(f)
        
        old_feedback = case_study["metadata"].get("user_feedback_score", 0)
        case_study["metadata"]["user_feedback_score"] = feedback_score
        
        # Save updated case study
        with open(case_file, 'w', encoding='utf-8') as f:
            json.dump(case_study, f, indent=2)
        
        logger.info(f"Updated case {case_id} feedback: {old_feedback} -> {feedback_score}")
        
        # Update in-memory cache immediately
        self.feedback_cache[case_id] = feedback_score
        
        # Update ChromaDB metadata in all collections that contain this case
        for collection_id, collection in self.collections.items():
            try:
                # ... existing ChromaDB update code ...
            except Exception as e:
                logger.error(f"Error updating case {case_id} in collection {collection_id}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating case feedback: {e}", exc_info=True)
        return False
```

**File**: `/src/trusted_data_agent/api/routes.py`

Update `get_collection_rows()` to use cache (line 653):

```python
@api_bp.route("/rag/collections/<int:collection_id>/rows", methods=["GET"])
async def get_collection_rows(collection_id):
    """Returns a sample or search results of rows from a ChromaDB collection."""
    try:
        # ... existing code up to row building ...
        
        for row in rows:
            # Override feedback from cache if available
            retriever = APP_STATE.get('rag_retriever_instance')
            if retriever and hasattr(retriever, 'get_feedback_score'):
                case_id = row.get('id')
                if case_id:
                    row['user_feedback_score'] = retriever.get_feedback_score(case_id)
        
        return jsonify({
            "rows": rows,
            # ... rest of response ...
        })
```

### Testing
```python
# Unit test for cache
def test_feedback_cache():
    retriever = RAGRetriever(...)
    assert retriever.get_feedback_score('case_xyz') == 0  # Initial
    
    await retriever.update_case_feedback('case_xyz', 1)
    assert retriever.get_feedback_score('case_xyz') == 1  # Updated
```

---

## Phase 2: Synchronization & Validation (Day 3-4)

### Problem
Over time, ChromaDB and filesystem might drift if updates fail.

### Solution
Add background validation and auto-sync.

### Implementation

**File**: `/src/trusted_data_agent/core/session_manager.py`

Add background sync task (after line 50 in initialization):

```python
# Add to SessionManager.__init__
self._feedback_sync_task = None
self._start_feedback_sync()

def _start_feedback_sync(self):
    """Start background task to sync feedback between sources."""
    try:
        loop = asyncio.get_event_loop()
        self._feedback_sync_task = loop.create_task(self._feedback_sync_loop())
    except RuntimeError:
        logger.warning("No event loop for feedback sync task")

async def _feedback_sync_loop(self):
    """Background task that periodically validates feedback consistency."""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            await self._validate_feedback_consistency()
        except Exception as e:
            logger.error(f"Feedback sync error: {e}")

async def _validate_feedback_consistency(self):
    """Check for and fix feedback inconsistencies."""
    try:
        retriever = APP_STATE.get('rag_retriever_instance')
        if not retriever:
            return
        
        project_root = Path(__file__).resolve().parents[3]
        cases_dir = project_root / 'rag' / 'tda_rag_cases'
        
        inconsistencies = []
        
        for collection_id in retriever.collections.keys():
            collection_dir = cases_dir / f"collection_{collection_id}"
            if not collection_dir.exists():
                continue
            
            for case_file in collection_dir.glob('case_*.json'):
                try:
                    with open(case_file, 'r') as f:
                        case_data = json.load(f)
                    
                    case_id = case_data.get('case_id')
                    filesystem_feedback = case_data.get('metadata', {}).get('user_feedback_score', 0)
                    chroma_feedback = retriever.feedback_cache.get(case_id, 0)
                    
                    if filesystem_feedback != chroma_feedback:
                        inconsistencies.append({
                            'case_id': case_id,
                            'filesystem': filesystem_feedback,
                            'cache': chroma_feedback
                        })
                        
                        # Auto-fix by updating cache to match filesystem
                        retriever.feedback_cache[case_id] = filesystem_feedback
                        
                except Exception as e:
                    logger.debug(f"Error validating {case_file}: {e}")
        
        if inconsistencies:
            logger.warning(f"Found and fixed {len(inconsistencies)} feedback inconsistencies")
            
    except Exception as e:
        logger.error(f"Error in feedback consistency validation: {e}")
```

### Testing
```python
# Test consistency check
def test_feedback_consistency():
    # Manually corrupt a feedback score
    # Run background sync
    # Verify it was fixed
```

---

## Phase 3: Frontend Update (Day 4-5)

### Update Event Handler

**File**: `/static/js/eventHandlers.js`

Update feedback button handler (around line 1678):

```javascript
// After successful feedback update, refresh table row
if (state.currentInspectedCollectionId !== undefined && state.currentInspectedCollectionId !== null) {
    console.log('[CaseFeedback] Refreshing table data after feedback change for case', caseId);
    
    // Import and call the table update function
    const { updateTableRowFeedback } = await import('./ui.js');
    
    // Update the feedback score in the table immediately
    updateTableRowFeedback(caseId, newVote === 'up' ? 1 : newVote === 'down' ? -1 : 0);
    
    // Optionally refresh the entire table for consistency check
    const { fetchAndRenderCollectionRows } = await import('./ui.js');
    await fetchAndRenderCollectionRows({ 
        collectionId: state.currentInspectedCollectionId, 
        query: state.ragCollectionSearchTerm || '',
        refresh: true  // Force refresh
    });
}
```

### Frontend Unit Tests

**File**: Create `/static/js/__tests__/ui.test.js`

```javascript
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('Feedback Display Consistency', () => {
    beforeEach(() => {
        // Setup DOM
        document.body.innerHTML = `
            <table id="rag-collection-table">
                <tbody id="rag-collection-table-body">
                    <tr data-case-id="case_123">
                        <td>case_123</td>
                        <td>query</td>
                        <td>strategy</td>
                        <td>Yes</td>
                        <td class="feedback-cell">—</td>
                        <td>100</td>
                        <td>2025-01-01</td>
                    </tr>
                </tbody>
            </table>
            <div id="rag-selected-case-metadata"></div>
        `;
    });
    
    it('should display feedback in table that matches details panel', async () => {
        // Test implementation
    });
    
    it('should update feedback in table immediately after button click', async () => {
        // Test implementation
    });
    
    it('should show correct feedback after page refresh', async () => {
        // Test implementation
    });
});
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] All code reviewed
- [ ] Unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] Manual testing completed
- [ ] Performance benchmarks acceptable
- [ ] Database backup created
- [ ] Rollback plan documented

### Deployment
- [ ] Deploy Phase 1 (authoritative endpoint) - Low risk
- [ ] Monitor logs for errors
- [ ] Deploy Phase 2 (cache layer) - Low-medium risk
- [ ] Monitor performance
- [ ] Deploy Phase 3 (frontend) - Low risk

### Post-Deployment
- [ ] Monitor error logs for 24 hours
- [ ] User acceptance testing
- [ ] Performance monitoring
- [ ] Feedback collection from users

---

## Monitoring & Metrics

### Key Metrics to Track
```
1. Feedback Display Accuracy
   - % of cases where table feedback matches details panel
   - Target: 100%

2. Performance
   - Table load time
   - Target: <200ms for initial load, <100ms for refresh

3. Cache Hit Rate
   - % of requests served from cache
   - Target: >95%

4. Consistency Issues
   - Number of filesystem/ChromaDB inconsistencies detected per hour
   - Target: 0 after Phase 2
```

### Logging Points
```python
# Add to key functions:
logger.info(f"[FEEDBACK] Case {case_id}: Updated to {feedback_score}")
logger.info(f"[FEEDBACK_CACHE] Hit for {case_id}: {feedback_score}")
logger.warning(f"[FEEDBACK_INCONSISTENCY] {case_id}: filesystem={fs_feedback}, cache={cache_feedback}")
```

---

## Rollback Plan

If issues occur:

1. **Minor Issue (Phase 1/3)**: Revert frontend changes, use standard endpoint
2. **Medium Issue (Phase 2)**: Disable cache, reload from files
3. **Major Issue**: Full rollback to previous commit

---

## Success Criteria

✅ Table feedback displays correctly in 100% of cases
✅ Details panel feedback matches table feedback always
✅ No "-" shown for feedback that exists
✅ Performance meets targets (<200ms table load)
✅ Cache consistency >99.9%
✅ Zero data loss events
✅ User feedback positive in UAT

---

## Timeline Summary

| Phase | Days | Risk | Status |
|-------|------|------|--------|
| Immediate Fix | 1 | Low | Ready |
| Phase 1 Cache | 1 | Low | Ready |
| Phase 2 Sync | 1 | Medium | Ready |
| Phase 3 Frontend | 1 | Low | Ready |
| Testing & QA | 1 | Low | Ready |
| **Total** | **4-5** | | |

