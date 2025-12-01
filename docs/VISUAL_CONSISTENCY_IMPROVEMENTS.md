# Visual Consistency Between Planner and Knowledge Repository Cards

## Overview

This document describes the improvements made to ensure visual consistency between Planner and Knowledge repository cards in the RAG Maintenance view.

## Problem Statement

Planner and Knowledge repository cards had slight visual inconsistencies:
- Different element ordering
- Inconsistent description field handling
- Knowledge cards lacked document/chunk count display
- Knowledge cards missing Upload button in main RAG view

## Solution

Both `createCollectionCard()` (Planner) and `createKnowledgeRepositoryCard()` (Knowledge) functions now follow identical structure and styling.

## Consistent Card Structure

Both card types now follow this exact structure:

```
┌─────────────────────────────────────────────────────────────┐
│ Card Container (glass-panel)                                │
├─────────────────────────────────────────────────────────────┤
│ HEADER                                                       │
│   ├─ Title Section                                          │
│   │   ├─ Repository Name (text-lg font-semibold)           │
│   │   └─ Collection ID (text-xs text-gray-500)             │
│   └─ Badges Container (flex-col items-end)                 │
│       ├─ Status Badge (Active/Disabled)                     │
│       └─ Indicators Row                                     │
│           ├─ Owner (if owned)                               │
│           ├─ Subscribed (if subscribed)                     │
│           └─ Published (if marketplace listed)              │
├─────────────────────────────────────────────────────────────┤
│ DESCRIPTION (if exists)                                     │
│   └─ Description text (text-xs text-gray-400)              │
├─────────────────────────────────────────────────────────────┤
│ MCP SERVER INFO                                             │
│   └─ MCP Server: {name} (text-sm text-gray-300)            │
├─────────────────────────────────────────────────────────────┤
│ METADATA                                                     │
│   └─ ChromaDB: {name} | {strategy} (text-xs text-gray-500) │
├─────────────────────────────────────────────────────────────┤
│ COUNTS (Knowledge only)                                     │
│   └─ X documents • Y chunks (text-xs text-gray-400)        │
├─────────────────────────────────────────────────────────────┤
│ ACTIONS                                                      │
│   └─ [Enable/Disable] [Refresh] [Inspect] [Edit]           │
│       [Upload (Knowledge only)] [Delete]                    │
└─────────────────────────────────────────────────────────────┘
```

## Key Consistency Improvements

### 1. Element Ordering

**Before:**
- Planner: header → description → mcpInfo → meta → actions
- Knowledge: header → (conditional description placement) → mcpInfo → meta → actions

**After (Both):**
```javascript
card.appendChild(header);
if (desc) card.appendChild(desc);  // Consistent conditional
card.appendChild(mcpInfo);
card.appendChild(meta);
if (countsInfo) card.appendChild(countsInfo);  // Knowledge only
card.appendChild(actions);
```

### 2. Description Field Handling

**Before:**
- Planner: Used if-statement, appended description separately
- Knowledge: Used if-else to conditionally append header

**After (Both):**
```javascript
const desc = col.description ? (() => {
    const d = document.createElement('p');
    d.className = 'text-xs text-gray-400';
    d.textContent = col.description;
    return d;
})() : null;

// Later...
if (desc) card.appendChild(desc);
```

### 3. Knowledge Repository Enhancements

#### Document/Chunk Counts
Added clear display of both metrics:

```javascript
const countsInfo = document.createElement('p');
countsInfo.className = 'text-xs text-gray-400';
const docCount = col.document_count || '?';
const chunkCount = col.count || col.example_count || 0;
countsInfo.textContent = `${docCount} documents • ${chunkCount} chunks`;
```

#### Upload Button
Added Upload button to Knowledge cards (matching functionality in Knowledge Repository Handler):

```javascript
const uploadBtn = document.createElement('button');
uploadBtn.type = 'button';
uploadBtn.className = 'px-3 py-1 rounded-md bg-purple-600 hover:bg-purple-500 text-sm text-white';
uploadBtn.innerHTML = '<span style="font-size: 14px;">+</span> Upload';
uploadBtn.addEventListener('click', () => {
    if (window.knowledgeRepositoryHandler && window.knowledgeRepositoryHandler.openUploadDocumentsModal) {
        window.knowledgeRepositoryHandler.openUploadDocumentsModal(col.id, col.name, col);
    }
});
```

## Styling Consistency

### Card Container
Both use identical styling:
```css
glass-panel rounded-xl p-4 flex flex-col gap-3 border border-white/10 hover:border-teradata-orange transition-colors
```

### Typography
- **Repository Name**: `text-lg font-semibold text-white`
- **Collection ID**: `text-xs text-gray-500`
- **Description**: `text-xs text-gray-400`
- **MCP Server**: `text-sm text-gray-300` (label: `text-gray-500`)
- **Metadata**: `text-xs text-gray-500`
- **Counts**: `text-xs text-gray-400`

### Badge Colors
Both card types use identical badge styling:

| Badge Type | Background | Text | Icon |
|------------|-----------|------|------|
| Active | `bg-green-500/20` | `text-green-400` | - |
| Disabled | `bg-gray-500/20` | `text-gray-400` | - |
| Owner | `bg-blue-500/20` | `text-blue-400` | 👤 |
| Subscribed | `bg-purple-500/20` | `text-purple-400` | 📌 |
| Public | `bg-orange-500/20` | `text-orange-400` | 🌐 |
| Unlisted | `bg-orange-500/20` | `text-orange-400` | 🔗 |

### Button Colors
Both card types use identical button styling:

| Button | Background | Hover | Text |
|--------|-----------|-------|------|
| Enable | `bg-green-600` | `bg-green-500` | `text-white` |
| Disable | `bg-yellow-600` | `bg-yellow-500` | `text-white` |
| Refresh | `bg-gray-700` | `bg-gray-600` | `text-gray-200` |
| Inspect | `bg-[#F15F22]` | `bg-[#D9501A]` | `text-white` |
| Edit | `bg-blue-600` | `bg-blue-500` | `text-white` |
| Upload | `bg-purple-600` | `bg-purple-500` | `text-white` |
| Delete | `bg-red-600` | `bg-red-500` | `text-white` |

## Function Exports

### Updated Exports

#### `knowledgeRepositoryHandler.js`
```javascript
export function openUploadDocumentsModal(collectionId, collectionName, repoData) {
    // ... implementation
}
```

#### `ragCollectionManagement.js`
```javascript
const { openUploadDocumentsModal } = await import('./knowledgeRepositoryHandler.js');

window.knowledgeRepositoryHandler = {
    loadKnowledgeRepositories,
    deleteKnowledgeRepository,
    openUploadDocumentsModal  // New export
};
```

## Visual Comparison

### Planner Repository Card
```
┌─────────────────────────────────────────────────────────┐
│ Default Collection                      [Active] [Owner] │
│ Collection ID: 1                                         │
│ Your default collection for RAG cases                    │
│ MCP Server: Teradata MCP                                │
│ ChromaDB: default_collection_ad169837                   │
│ [Disable] [Refresh] [Inspect] [Edit] [Delete]          │
└─────────────────────────────────────────────────────────┘
```

### Knowledge Repository Card
```
┌─────────────────────────────────────────────────────────┐
│ TestDBTandTeradata                      [Active] [Owner] │
│ Collection ID: 2                                         │
│ Knowledge repository                                     │
│ MCP Server: None                                         │
│ ChromaDB: tda_rag_coll_2_6c28d2 | semantic chunking     │
│ 1 documents • 47 chunks                                  │
│ [Disable] [Refresh] [Inspect] [Edit] [Upload] [Delete] │
└─────────────────────────────────────────────────────────┘
```

## Key Differences (Intentional)

The only intentional differences between card types:

1. **Metadata Line**
   - Planner: Shows only ChromaDB name
   - Knowledge: Shows ChromaDB name + chunking strategy

2. **Counts Display**
   - Planner: Not applicable (no chunking)
   - Knowledge: Shows document count and chunk count

3. **Upload Button**
   - Planner: Not shown (not applicable)
   - Knowledge: Purple Upload button for adding documents

## Files Modified

1. **`/static/js/ui.js`**
   - Updated `createKnowledgeRepositoryCard()` function
   - Updated `createCollectionCard()` function
   - Ensured identical structure and styling
   - Added Upload button to Knowledge cards
   - Added document/chunk counts to Knowledge cards

2. **`/static/js/handlers/knowledgeRepositoryHandler.js`**
   - Exported `openUploadDocumentsModal()` function

3. **`/static/js/handlers/ragCollectionManagement.js`**
   - Added `openUploadDocumentsModal` to window.knowledgeRepositoryHandler exports

## Testing Checklist

- [ ] Both card types display with identical spacing and layout
- [ ] Description appears in same position for both card types
- [ ] Badges align consistently on the right side
- [ ] MCP Server info displays consistently
- [ ] ChromaDB metadata displays consistently
- [ ] Button styling is identical across both card types
- [ ] Hover effects work consistently
- [ ] Upload button appears only on Knowledge cards
- [ ] Upload button opens modal correctly
- [ ] Document/chunk counts display correctly on Knowledge cards
- [ ] Cards have identical hover border color (Teradata orange)

## Benefits

1. **Consistent User Experience**: Users see the same visual pattern for both repository types
2. **Reduced Cognitive Load**: Similar layouts make navigation intuitive
3. **Maintainability**: Identical structure makes future updates easier
4. **Professional Appearance**: Unified design language throughout the application
5. **Functional Parity**: Both card types support all applicable operations with consistent UI

## Future Considerations

- Consider creating a shared card component to reduce code duplication
- Add tooltips to explain the difference between Planner and Knowledge repositories
- Consider adding repository type badge to make distinction clearer
- Explore responsive design improvements for smaller screens
