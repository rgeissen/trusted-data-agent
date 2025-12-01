# Marketplace Repository Type Separation

## Overview

The marketplace now clearly separates **Planner Repositories** and **Knowledge Repositories** through a dedicated tab interface, providing users with a clear understanding of the two different types of collections available.

**Implementation Date:** December 1, 2025  
**Status:** ✅ Complete

---

## Changes Summary

### Visual Separation

#### Before
- Single view showing all collections mixed together
- No clear distinction between Planner and Knowledge repositories
- Users had to check metadata to understand repository type

#### After
- **Dual-tab interface** separating Planner and Knowledge repositories
- **Visual badges** on each collection card indicating type
- **Contextual descriptions** explaining each repository type
- **Filtered browsing** showing only selected type

---

## User Interface Changes

### 1. Repository Type Toggle Tabs

Added a prominent toggle between Planner and Knowledge repositories:

```
┌─────────────────────────────────────────────────┐
│  ┌──────────────────┐ ┌──────────────────────┐ │
│  │ 📋 Planner      │ │ 📄 Knowledge        │ │
│  │ Repositories    │ │ Repositories        │ │
│  └──────────────────┘ └──────────────────────┘ │
│                                                 │
│  Description: Execution patterns and strategies │
│               for proven task completion        │
└─────────────────────────────────────────────────┘
```

**Features:**
- Toggle-style tabs with icon + label
- Active tab highlighted in orange (#F15F22)
- Inactive tab in gray with hover effects
- Dynamic description text changes with selection

### 2. Collection Card Badges

Each collection card now displays its repository type:

**Planner Badge:**
```
┌─────────────────┐
│ 📋 Planner     │  (Blue badge)
└─────────────────┘
```

**Knowledge Badge:**
```
┌─────────────────┐
│ 📄 Knowledge   │  (Purple badge)
└─────────────────┘
```

### 3. Updated Page Header

Changed from:
- ❌ "Planner Repository Marketplace"

To:
- ✅ "Intelligence Marketplace"

More inclusive title encompassing both types.

---

## Technical Implementation

### Frontend Changes

#### File: `templates/index.html`

**Added Repository Type Tabs:**
```html
<!-- Repository Type Tabs (Planner / Knowledge) -->
<div class="mb-6">
    <div class="flex gap-2 bg-white/5 rounded-lg p-1">
        <button id="marketplace-repo-type-planner" class="...">
            <svg>...</svg>
            <span>Planner Repositories</span>
        </button>
        <button id="marketplace-repo-type-knowledge" class="...">
            <svg>...</svg>
            <span>Knowledge Repositories</span>
        </button>
    </div>
    <div class="mt-3 px-2">
        <p id="marketplace-repo-type-description">
            <span id="planner-description">...</span>
            <span id="knowledge-description" class="hidden">...</span>
        </p>
    </div>
</div>
```

#### File: `static/js/handlers/marketplaceHandler.js`

**Added State Variable:**
```javascript
let currentRepositoryType = 'planner'; // 'planner' or 'knowledge'
```

**Added Event Handlers:**
```javascript
// Repository type tab handlers
const plannerTypeTab = document.getElementById('marketplace-repo-type-planner');
const knowledgeTypeTab = document.getElementById('marketplace-repo-type-knowledge');

plannerTypeTab.addEventListener('click', () => {
    switchRepositoryType('planner');
});

knowledgeTypeTab.addEventListener('click', () => {
    switchRepositoryType('knowledge');
});
```

**Added Switch Function:**
```javascript
function switchRepositoryType(type) {
    currentRepositoryType = type;
    currentPage = 1;
    
    // Update tab styling
    // Update description text
    
    loadMarketplaceCollections();
}
```

**Updated API Calls:**
```javascript
// Added repository_type to API params
const params = new URLSearchParams({
    page: currentPage,
    per_page: 10,
    visibility: currentVisibility,
    repository_type: currentRepositoryType  // NEW
});
```

**Updated Collection Filtering:**
```javascript
// Filter my-collections by repository type
collections = collections
    .filter(c => c.id !== 0 && c.repository_type === currentRepositoryType)
    .map(c => ({ ...c, is_owner: true }));
```

**Added Repository Type Badge:**
```javascript
const repoTypeBadge = repositoryType === 'knowledge' 
    ? '<span class="...">📄 Knowledge</span>'
    : '<span class="...">📋 Planner</span>';
```

### Backend Changes

#### File: `src/trusted_data_agent/api/rest_routes.py`

**Updated API Documentation:**
```python
"""
Query parameters:
- visibility: Filter by visibility (public, unlisted)
- search: Search in name and description
- repository_type: Filter by repository type (planner, knowledge)  # NEW
- limit: Max results (default: 50)
- offset: Pagination offset (default: 0)
"""
```

**Added Query Parameter:**
```python
repository_type_filter = request.args.get("repository_type", None)
```

**Added Filtering Logic:**
```python
# Repository type filter (if provided)
if repository_type_filter:
    coll_repo_type = coll.get("repository_type", "planner")
    if coll_repo_type != repository_type_filter:
        continue
```

---

## User Experience

### Workflow: Browsing Planner Repositories

1. User clicks on "Marketplace" in sidebar
2. **Planner Repositories tab is selected by default**
3. Description shows: "Execution patterns and strategies for proven task completion"
4. Only Planner collections are displayed
5. Each card shows blue "📋 Planner" badge

### Workflow: Browsing Knowledge Repositories

1. User clicks **"Knowledge Repositories"** tab
2. Tab highlights in orange, Planner tab grays out
3. Description changes to: "Reference documents and domain knowledge for planning context"
4. Collections refresh to show only Knowledge repositories
5. Each card shows purple "📄 Knowledge" badge

### Workflow: My Collections

The same filtering applies:
- "My Collections" tab shows only user's owned collections
- Repository type toggle still applies
- Can view owned Planner collections separately from owned Knowledge collections

---

## Design Decisions

### Why Tab-Based Separation?

1. **Consistent Pattern:** Reuses the Intelligence view's tab pattern (Planner/Knowledge tabs)
2. **Clear Mental Model:** Users understand they're browsing one type at a time
3. **Reduced Cognitive Load:** No need to scan mixed results
4. **Scalability:** Easy to add filters/features specific to each type

### Why Visual Badges?

1. **Quick Identification:** At-a-glance understanding of repository type
2. **Redundancy:** Even within filtered view, reinforces what user is viewing
3. **Color Coding:**
   - Blue = Planner (matches execution/strategy theme)
   - Purple = Knowledge (matches documentation theme)

### Why Two-Level Tab System?

**Level 1: Browse / My Collections**
- Controls data source (marketplace vs. owned)

**Level 2: Planner / Knowledge**
- Controls repository type filter

This creates a clear hierarchy:
```
Browse Marketplace → Filter by Type → View Collections
     OR
My Collections → Filter by Type → View Collections
```

---

## Benefits

### For Users

✅ **Clarity:** Immediate understanding of collection purpose  
✅ **Efficiency:** No need to filter through mixed results  
✅ **Discoverability:** Easier to find relevant collections  
✅ **Context:** Clear descriptions for each type  

### For Platform

✅ **Scalability:** Easy to add type-specific features  
✅ **Consistency:** Matches Intelligence view pattern  
✅ **Analytics:** Can track type-specific usage  
✅ **Future-Proof:** Ready for additional repository types  

---

## Testing Checklist

### Frontend Tests

- [ ] Planner tab selected by default on load
- [ ] Clicking Knowledge tab switches view and updates styling
- [ ] Description text changes based on selected tab
- [ ] Collection cards show correct badge (blue Planner / purple Knowledge)
- [ ] Search works within filtered repository type
- [ ] Pagination works within filtered repository type
- [ ] My Collections respects repository type filter

### Backend Tests

- [ ] API returns only Planner collections when `repository_type=planner`
- [ ] API returns only Knowledge collections when `repository_type=knowledge`
- [ ] API returns all types when `repository_type` not specified (backwards compatibility)
- [ ] Repository type filter works with visibility filter
- [ ] Repository type filter works with search query

### Integration Tests

- [ ] Switching tabs triggers API call with correct parameter
- [ ] Collections refresh correctly when switching types
- [ ] Empty state shows when no collections of selected type
- [ ] Owned collections filtered by type in My Collections tab

---

## Backwards Compatibility

✅ **API:** `repository_type` parameter is optional
- If not provided, API returns all types (existing behavior)
- Existing API clients continue to work

✅ **Frontend:** Graceful degradation
- If `repository_type` field missing from collection, defaults to "planner"
- Badge displays correctly for legacy data

---

## Future Enhancements

### Short-Term
- [ ] Type-specific sorting options (e.g., Knowledge sorted by document count)
- [ ] Type-specific metadata display (e.g., chunking strategy for Knowledge)
- [ ] Type-specific search filters

### Medium-Term
- [ ] Category/tag filtering within each type
- [ ] Type-specific empty states with creation prompts
- [ ] Type-specific publishing guidelines

### Long-Term
- [ ] Additional repository types (if needed)
- [ ] Cross-type recommendations ("Users who liked this Planner collection also used this Knowledge collection")

---

## Files Modified

### Frontend
- `templates/index.html` (+30 lines)
- `static/js/handlers/marketplaceHandler.js` (+60 lines)

### Backend
- `src/trusted_data_agent/api/rest_routes.py` (+8 lines)

### Documentation
- `docs/Marketplace/REPOSITORY_TYPE_SEPARATION.md` (new, this file)

---

## Conclusion

The marketplace now provides **clear visual and functional separation** between Planner and Knowledge repositories, improving user experience and laying the groundwork for type-specific features. The implementation follows existing UI patterns, maintains backwards compatibility, and requires minimal code changes.

**Status:** ✅ Ready for testing and deployment

---

**Document Version:** 1.0  
**Author:** Development Team  
**Date:** December 1, 2025
