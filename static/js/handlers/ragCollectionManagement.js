/**
 * RAG Collection Management Handler
 * Manages the Add RAG Collection modal and collection operations
 */

/**
 * Show notification helper
 */
function showNotification(type, message) {
    const colors = {
        success: 'bg-green-600',
        error: 'bg-red-600',
        warning: 'bg-yellow-600',
        info: 'bg-blue-600'
    };

    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 ${colors[type] || colors.info} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity duration-300`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Modal Elements
const addRagCollectionBtn = document.getElementById('add-rag-collection-btn');
const addRagCollectionModalOverlay = document.getElementById('add-rag-collection-modal-overlay');
const addRagCollectionModalContent = document.getElementById('add-rag-collection-modal-content');
const addRagCollectionModalClose = document.getElementById('add-rag-collection-modal-close');
const addRagCollectionCancel = document.getElementById('add-rag-collection-cancel');
const addRagCollectionForm = document.getElementById('add-rag-collection-form');
const addRagCollectionSubmit = document.getElementById('add-rag-collection-submit');

// Form Fields
const ragCollectionNameInput = document.getElementById('rag-collection-name');
const ragCollectionMcpServerSelect = document.getElementById('rag-collection-mcp-server');
const ragCollectionDescriptionInput = document.getElementById('rag-collection-description');

/**
 * Open the Add RAG Collection modal
 */
function openAddRagCollectionModal() {
    // Populate MCP server dropdown
    populateMcpServerDropdown();
    
    // Show modal with animation
    addRagCollectionModalOverlay.classList.remove('hidden');
    
    // Trigger animation after a frame
    requestAnimationFrame(() => {
        addRagCollectionModalOverlay.classList.remove('opacity-0');
        addRagCollectionModalContent.classList.remove('scale-95', 'opacity-0');
        addRagCollectionModalContent.classList.add('scale-100', 'opacity-100');
    });
}

/**
 * Close the Add RAG Collection modal
 */
function closeAddRagCollectionModal() {
    // Animate out
    addRagCollectionModalOverlay.classList.add('opacity-0');
    addRagCollectionModalContent.classList.remove('scale-100', 'opacity-100');
    addRagCollectionModalContent.classList.add('scale-95', 'opacity-0');
    
    // Hide after animation
    setTimeout(() => {
        addRagCollectionModalOverlay.classList.add('hidden');
        // Reset form
        addRagCollectionForm.reset();
    }, 200);
}

/**
 * Populate MCP Server dropdown from current state
 */
function populateMcpServerDropdown() {
    // Clear existing options except the placeholder
    ragCollectionMcpServerSelect.innerHTML = '<option value="">Select an MCP Server...</option>';
    
    // Get MCP servers from state
    if (state && state.server_configs && Array.isArray(state.server_configs)) {
        state.server_configs.forEach(server => {
            const option = document.createElement('option');
            option.value = server.name;
            option.textContent = server.name;
            ragCollectionMcpServerSelect.appendChild(option);
        });
    }
    
    // If no servers available, show message
    if (ragCollectionMcpServerSelect.options.length === 1) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No MCP servers configured';
        option.disabled = true;
        ragCollectionMcpServerSelect.appendChild(option);
    }
}

/**
 * Handle Add RAG Collection form submission
 */
async function handleAddRagCollection(event) {
    event.preventDefault();
    
    // Get form values
    const name = ragCollectionNameInput.value.trim();
    const mcpServerName = ragCollectionMcpServerSelect.value;
    const description = ragCollectionDescriptionInput.value.trim();
    
    // Validate
    if (!name) {
        showNotification('error', 'Collection name is required');
        return;
    }
    
    if (!mcpServerName) {
        showNotification('error', 'Please select an MCP server');
        return;
    }
    
    // Disable submit button
    addRagCollectionSubmit.disabled = true;
    addRagCollectionSubmit.textContent = 'Creating...';
    
    try {
        // Call API
        const response = await fetch('/api/v1/rag/collections', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                mcp_server_name: mcpServerName,
                description: description || ''
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('success', `Collection "${name}" created successfully (ID: ${data.id})`);
            
            // Close modal
            closeAddRagCollectionModal();
            
            // Refresh RAG collections list (if a refresh function exists)
            if (typeof loadRagCollections === 'function') {
                await loadRagCollections();
            }
        } else {
            showNotification('error', `Failed to create collection: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error creating RAG collection:', error);
        showNotification('error', 'Failed to create collection. Check console for details.');
    } finally {
        // Re-enable submit button
        addRagCollectionSubmit.disabled = false;
        addRagCollectionSubmit.textContent = 'Create Collection';
    }
}

/**
 * Toggle a RAG collection's enabled state
 */
async function toggleRagCollection(collectionId, currentState) {
    try {
        const response = await fetch(`/api/v1/rag/collections/${collectionId}/toggle`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const newState = data.enabled ? 'enabled' : 'disabled';
            showNotification('success', `Collection ${newState} successfully`);
            
            // Refresh collections list
            if (typeof loadRagCollections === 'function') {
                await loadRagCollections();
            }
        } else {
            showNotification('error', `Failed to toggle collection: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error toggling RAG collection:', error);
        showNotification('error', 'Failed to toggle collection. Check console for details.');
    }
}

/**
 * Delete a RAG collection
 */
async function deleteRagCollection(collectionId, collectionName) {
    // Confirm deletion
    if (!confirm(`Are you sure you want to delete the collection "${collectionName}"?\n\nThis will remove all RAG cases associated with this collection.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/rag/collections/${collectionId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('success', `Collection "${collectionName}" deleted successfully`);
            
            // Refresh collections list
            if (typeof loadRagCollections === 'function') {
                await loadRagCollections();
            }
        } else {
            showNotification('error', `Failed to delete collection: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error deleting RAG collection:', error);
        showNotification('error', 'Failed to delete collection. Check console for details.');
    }
}

/**
 * Refresh a RAG collection's vector store
 */
async function refreshRagCollection(collectionId, collectionName) {
    try {
        showNotification('info', `Refreshing collection "${collectionName}"...`);
        
        const response = await fetch(`/api/v1/rag/collections/${collectionId}/refresh`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('success', `Collection "${collectionName}" refreshed successfully`);
        } else {
            showNotification('error', `Failed to refresh collection: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error refreshing RAG collection:', error);
        showNotification('error', 'Failed to refresh collection. Check console for details.');
    }
}

// Event Listeners
if (addRagCollectionBtn) {
    addRagCollectionBtn.addEventListener('click', openAddRagCollectionModal);
}

if (addRagCollectionModalClose) {
    addRagCollectionModalClose.addEventListener('click', closeAddRagCollectionModal);
}

if (addRagCollectionCancel) {
    addRagCollectionCancel.addEventListener('click', closeAddRagCollectionModal);
}

if (addRagCollectionModalOverlay) {
    addRagCollectionModalOverlay.addEventListener('click', (e) => {
        // Close if clicking on overlay background (not content)
        if (e.target === addRagCollectionModalOverlay) {
            closeAddRagCollectionModal();
        }
    });
}

if (addRagCollectionForm) {
    addRagCollectionForm.addEventListener('submit', handleAddRagCollection);
}

// Export functions for use in other modules
window.ragCollectionManagement = {
    toggleRagCollection,
    deleteRagCollection,
    refreshRagCollection
};
