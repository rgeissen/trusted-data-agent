# Knowledge Repository Card Improvements

## Summary of Changes

This document describes the improvements made to Knowledge Repository cards to address display issues and add upload functionality.

## Issues Addressed

### 1. Repository Name Display
**Problem:** Card was displaying ChromaDB collection name (`tda_rag_coll_2_6c28d2`) instead of user-friendly repository name (`TestDBTandTeradata`)

**Solution:** Updated `createKnowledgeRepositoryCard()` to use:
```javascript
const displayName = repo.name || repo.collection_name;
```
This ensures the display name (`repo.name`) is shown prominently, while the ChromaDB collection name is shown separately in the metadata section.

### 2. Active/Inactive Status Badge
**Problem:** No clear visual indicator of repository enabled status

**Solution:** Added status badge next to repository name:
- **Active** (green badge) - Repository is enabled
- **Inactive** (gray badge) - Repository is disabled

```html
<span class="px-2 py-0.5 text-xs rounded-full ${repo.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}">
    ${repo.enabled ? 'Active' : 'Inactive'}
</span>
```

### 3. Owner Badge
**Problem:** No indication of repository ownership

**Solution:** Added "Owner" badge with user icon (blue) to indicate the current user owns this repository:
```html
<span class="px-2 py-0.5 text-xs rounded-full bg-blue-500/20 text-blue-400 flex items-center gap-1">
    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
    </svg>
    Owner
</span>
```

### 4. Document Count vs Chunk Count
**Problem:** The card was showing chunk count (47) labeled as "documents"

**Solution:** Now displays both metrics separately:
- **Document count** - Fetched asynchronously from API (`/api/v1/knowledge/repositories/{id}/documents`)
- **Chunk count** - Displayed from repository metadata (`repo.count`)

```html
<div class="text-xs text-gray-500 mb-3 flex items-center gap-3">
    <span><span id="knowledge-doc-count-${repoId}" class="text-white font-medium">...</span> documents</span>
    <span>•</span>
    <span><span class="text-white font-medium">${chunkCount}</span> chunks</span>
</div>
```

### 5. Upload Documents Button
**Problem:** No way to add documents to existing repository

**Solution:** Added purple "Upload" button with + icon:
```html
<button class="upload-knowledge-docs-btn px-3 py-1 rounded-md bg-purple-600 hover:bg-purple-500 text-sm text-white flex items-center gap-1" 
        data-repo-id="${repoId}" 
        data-repo-name="${displayName}">
    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
    </svg>
    Upload
</button>
```

## New Functions Added

### `fetchKnowledgeDocumentCountForCard(collectionId)`
Asynchronously fetches the actual document count from the API and updates the card display.

```javascript
async function fetchKnowledgeDocumentCountForCard(collectionId) {
    try {
        const token = localStorage.getItem('tda_auth_token');
        const response = await fetch(`/api/v1/knowledge/repositories/${collectionId}/documents`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const countEl = document.getElementById(`knowledge-doc-count-${collectionId}`);
        if (!countEl) return;
        
        if (response.ok) {
            const data = await response.json();
            const count = data.documents ? data.documents.length : 0;
            countEl.textContent = count;
        } else {
            countEl.textContent = '?';
        }
    } catch (error) {
        console.error('[Knowledge] Failed to fetch document count for card:', error);
        const countEl = document.getElementById(`knowledge-doc-count-${collectionId}`);
        if (countEl) countEl.textContent = '?';
    }
}
```

### `openUploadDocumentsModal(collectionId, collectionName, repoData)`
Opens the Knowledge Repository modal in "upload mode" to add documents to existing repository.

**Features:**
- Reuses existing Knowledge Repository modal
- Pre-fills chunking parameters from existing repository
- Hides name/description fields (not needed for upload)
- Changes modal title to "Upload Documents to {repoName}"
- Changes submit button to "Upload Documents"
- Stores collection metadata in button dataset for form submission

```javascript
function openUploadDocumentsModal(collectionId, collectionName, repoData) {
    // Get chunking parameters from existing repo
    const chunkingStrategy = repoData?.chunking_strategy || 'semantic';
    const chunkSize = repoData?.chunk_size || 1000;
    const chunkOverlap = repoData?.chunk_overlap || 200;
    
    // Open modal and configure for upload mode
    // ... (see implementation for details)
    
    // Store metadata in submit button
    submitBtn.dataset.uploadMode = 'true';
    submitBtn.dataset.collectionId = collectionId;
    submitBtn.dataset.collectionName = collectionName;
}
```

## Updated Functions

### `handleKnowledgeRepositorySubmit(e)`
Enhanced to support both CREATE and UPLOAD modes.

**Changes:**
1. Detects upload mode from button dataset:
   ```javascript
   const uploadMode = submitBtn?.dataset.uploadMode === 'true';
   const existingCollectionId = submitBtn?.dataset.collectionId;
   ```

2. Skips collection creation in upload mode:
   ```javascript
   if (uploadMode && existingCollectionId) {
       collectionId = existingCollectionId;
       // Validate files selected...
   } else {
       // Create new collection...
   }
   ```

3. Shows appropriate success message:
   ```javascript
   const successMessage = uploadMode 
       ? `Documents uploaded to "${existingCollectionName}" successfully!`
       : `Knowledge repository created successfully!`;
   ```

4. Cleans up upload mode flags after completion:
   ```javascript
   delete submitBtn.dataset.uploadMode;
   delete submitBtn.dataset.collectionId;
   delete submitBtn.dataset.collectionName;
   ```

### `openKnowledgeRepositoryModal()`
Enhanced to properly reset modal to CREATE mode.

**Changes:**
1. Resets modal title to "Create Knowledge Repository"
2. Shows name/description fields
3. Clears upload mode flags from submit button
4. Resets button text to "Create Repository"

### `attachKnowledgeRepositoryCardHandlers(container, repositories)`
Added upload button click handler.

**Changes:**
```javascript
// Upload button handler
const uploadBtns = container.querySelectorAll('.upload-knowledge-docs-btn');
uploadBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const repoId = btn.dataset.repoId;
        const repoName = btn.dataset.repoName;
        const repo = repoMap.get(repoId);
        if (repo) {
            openUploadDocumentsModal(repoId, repoName, repo);
        }
    });
});
```

## Visual Improvements

### Card Layout
```
┌─────────────────────────────────────────────────────────┐
│ [📄] TestDBTandTeradata [Active] [Owner]                │
│      Collection ID: tda_rag_coll_2_6c28d2               │
│      ChromaDB: tda_rag_coll_2_6c28d2 | semantic chunking│
│      Description text here...                            │
│      3 documents • 47 chunks                             │
│      [Disable] [Refresh] [Inspect] [Edit] [Upload] [Delete]
└─────────────────────────────────────────────────────────┘
```

### Badge Colors
- **Active Badge**: Green (#10B981) - Indicates repository is enabled
- **Inactive Badge**: Gray (#6B7280) - Indicates repository is disabled  
- **Owner Badge**: Blue (#3B82F6) - Indicates user ownership

### Button Colors
- **Upload Button**: Purple (#9333EA) - Distinctive color for upload action
- **Enable/Disable**: Green/Yellow - Standard action colors
- **Refresh**: Gray - Secondary action
- **Inspect**: Orange (#F15F22) - Brand color
- **Edit**: Blue - Standard edit action
- **Delete**: Red - Destructive action

## API Endpoints Used

### Document Count
- **Endpoint**: `GET /api/v1/knowledge/repositories/{collection_id}/documents`
- **Purpose**: Fetch actual document count (not chunk count)
- **Returns**: `{ documents: [{ id, title, metadata, ... }] }`

### Document Upload
- **Endpoint**: `POST /api/v1/knowledge/repositories/{collection_id}/documents`
- **Purpose**: Upload new documents to existing repository
- **Body**: FormData with file, metadata, and chunking parameters

## Files Modified

### `/static/js/handlers/knowledgeRepositoryHandler.js`
- Added `fetchKnowledgeDocumentCountForCard()` function
- Added `openUploadDocumentsModal()` function
- Updated `createKnowledgeRepositoryCard()` function
- Updated `handleKnowledgeRepositorySubmit()` function
- Updated `openKnowledgeRepositoryModal()` function
- Updated `attachKnowledgeRepositoryCardHandlers()` function

## Testing Checklist

- [ ] Repository name displays correctly (user-friendly name, not collection ID)
- [ ] Active/Inactive badge shows correct status
- [ ] Owner badge displays for owned repositories
- [ ] Document count loads asynchronously and displays correctly
- [ ] Chunk count displays correctly
- [ ] Upload button opens modal with correct title
- [ ] Upload modal pre-fills chunking parameters from repository
- [ ] Upload modal hides name/description fields
- [ ] Upload succeeds and refreshes card with updated counts
- [ ] Create new repository still works correctly
- [ ] Modal resets properly when switching between create/upload modes

## Future Enhancements

1. **Conditional Owner Badge**: Only show "Owner" badge on repositories owned by current user (requires API to return owner information)

2. **Shared/Subscribed Badges**: Add badges for repositories that are:
   - Shared with user
   - Subscribed from marketplace
   - Forked from another user

3. **Permission Indicators**: Show what actions are available:
   - Read-only access
   - Edit access
   - Full ownership

4. **Document Preview**: Show recently added documents in card or on hover

5. **Upload Progress**: Real-time progress indicator for multi-document uploads

6. **Drag-and-Drop Upload**: Allow dragging files directly onto the Upload button

## Related Documentation

- [Repository Type Separation](./REPOSITORY_TYPE_SEPARATION.md)
- [Knowledge Repository Guide](./Knowledge_Repositories/)
- [RAG Architecture](./RAG/)
- [REST API Documentation](./RestAPI/)
