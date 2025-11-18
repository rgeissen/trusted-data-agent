/**
 * RAG Collection Management Handler
 * Manages the Add RAG Collection modal and collection operations
 */

import { state } from '../state.js';
import { loadRagCollections } from '../ui.js';
// Note: configState is accessed via window.configState to avoid circular imports

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
    
    // Get MCP servers from window.configState
    if (window.configState && window.configState.mcpServers && Array.isArray(window.configState.mcpServers)) {
        window.configState.mcpServers.forEach(server => {
            const option = document.createElement('option');
            option.value = server.id;  // Use server ID instead of name
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
    const mcpServerId = ragCollectionMcpServerSelect.value;  // This is now the server ID
    const description = ragCollectionDescriptionInput.value.trim();
    
    // Validate
    if (!name) {
        showNotification('error', 'Collection name is required');
        return;
    }
    
    if (!mcpServerId) {
        showNotification('error', 'Please select an MCP server');
        return;
    }
    
    // Disable submit button
    addRagCollectionSubmit.disabled = true;
    addRagCollectionSubmit.textContent = 'Creating...';
    
    try {
        // Call API with mcp_server_id
        const response = await fetch('/api/v1/rag/collections', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                mcp_server_id: mcpServerId,  // Send ID instead of name
                description: description || ''
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('success', `Collection "${name}" created successfully (ID: ${data.collection_id})`);
            
            // Close modal
            closeAddRagCollectionModal();
            
            // Refresh RAG collections list
            await loadRagCollections();
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
        // Toggle the state: if currently enabled, disable it; if disabled, enable it
        const newState = !currentState;
        
        const response = await fetch(`/api/v1/rag/collections/${collectionId}/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                enabled: newState
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const newState = data.enabled ? 'enabled' : 'disabled';
            showNotification('success', `Collection ${newState} successfully`);
            
            // Refresh collections list
            await loadRagCollections();
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
            await loadRagCollections();
        } else {
            showNotification('error', `Failed to delete collection: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error deleting RAG collection:', error);
        showNotification('error', 'Failed to delete collection. Check console for details.');
    }
}

/**
 * Open Edit RAG Collection modal
 */
function openEditCollectionModal(collection) {
    // Get edit modal elements
    const editModalOverlay = document.getElementById('edit-rag-collection-modal-overlay');
    const editModalContent = document.getElementById('edit-rag-collection-modal-content');
    const editCollectionIdInput = document.getElementById('edit-rag-collection-id');
    const editCollectionNameInput = document.getElementById('edit-rag-collection-name');
    const editCollectionMcpServerSelect = document.getElementById('edit-rag-collection-mcp-server');
    const editCollectionDescriptionInput = document.getElementById('edit-rag-collection-description');
    
    // Populate MCP server dropdown for edit modal
    editCollectionMcpServerSelect.innerHTML = '<option value="">Select an MCP Server...</option>';
    if (window.configState && window.configState.mcpServers && Array.isArray(window.configState.mcpServers)) {
        window.configState.mcpServers.forEach(server => {
            const option = document.createElement('option');
            option.value = server.id;
            option.textContent = server.name;
            // Check if this server is the one assigned to the collection
            if (server.id === collection.mcp_server_id) {
                option.selected = true;
            }
            editCollectionMcpServerSelect.appendChild(option);
        });
    }
    
    // Populate form with collection data
    editCollectionIdInput.value = collection.id;
    editCollectionNameInput.value = collection.name;
    editCollectionDescriptionInput.value = collection.description || '';
    
    // Show modal with animation
    editModalOverlay.classList.remove('hidden');
    requestAnimationFrame(() => {
        editModalOverlay.classList.remove('opacity-0');
        editModalContent.classList.remove('scale-95', 'opacity-0');
        editModalContent.classList.add('scale-100', 'opacity-100');
    });
}

/**
 * Close Edit RAG Collection modal
 */
function closeEditCollectionModal() {
    const editModalOverlay = document.getElementById('edit-rag-collection-modal-overlay');
    const editModalContent = document.getElementById('edit-rag-collection-modal-content');
    const editForm = document.getElementById('edit-rag-collection-form');
    
    // Animate out
    editModalOverlay.classList.add('opacity-0');
    editModalContent.classList.remove('scale-100', 'opacity-100');
    editModalContent.classList.add('scale-95', 'opacity-0');
    
    // Hide after animation
    setTimeout(() => {
        editModalOverlay.classList.add('hidden');
        editForm.reset();
    }, 200);
}

/**
 * Handle Edit RAG Collection form submission
 */
async function handleEditRagCollection(event) {
    event.preventDefault();
    
    const editCollectionIdInput = document.getElementById('edit-rag-collection-id');
    const editCollectionNameInput = document.getElementById('edit-rag-collection-name');
    const editCollectionMcpServerSelect = document.getElementById('edit-rag-collection-mcp-server');
    const editCollectionDescriptionInput = document.getElementById('edit-rag-collection-description');
    const editSubmitBtn = document.getElementById('edit-rag-collection-submit');
    
    // Get form values
    const collectionId = parseInt(editCollectionIdInput.value);
    const name = editCollectionNameInput.value.trim();
    const mcpServerId = editCollectionMcpServerSelect.value;  // This is now the server ID
    const description = editCollectionDescriptionInput.value.trim();
    
    // Validate
    if (!name) {
        showNotification('error', 'Collection name is required');
        return;
    }
    
    if (!mcpServerId) {
        showNotification('error', 'Please select an MCP server');
        return;
    }
    
    // Disable submit button
    editSubmitBtn.disabled = true;
    editSubmitBtn.textContent = 'Saving...';
    
    try {
        // Call API with mcp_server_id
        const response = await fetch(`/api/v1/rag/collections/${collectionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                mcp_server_id: mcpServerId,  // Send ID instead of name
                description: description || ''
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('success', `Collection "${name}" updated successfully`);
            
            // Close modal
            closeEditCollectionModal();
            
            // Refresh RAG collections list
            await loadRagCollections();
        } else {
            showNotification('error', `Failed to update collection: ${data.error || data.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error updating RAG collection:', error);
        showNotification('error', 'Failed to update collection. Check console for details.');
    } finally {
        // Re-enable submit button
        editSubmitBtn.disabled = false;
        editSubmitBtn.textContent = 'Save Changes';
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

// Edit Modal Event Listeners
const editRagCollectionModalClose = document.getElementById('edit-rag-collection-modal-close');
const editRagCollectionCancel = document.getElementById('edit-rag-collection-cancel');
const editRagCollectionModalOverlay = document.getElementById('edit-rag-collection-modal-overlay');
const editRagCollectionForm = document.getElementById('edit-rag-collection-form');

if (editRagCollectionModalClose) {
    editRagCollectionModalClose.addEventListener('click', closeEditCollectionModal);
}

if (editRagCollectionCancel) {
    editRagCollectionCancel.addEventListener('click', closeEditCollectionModal);
}

if (editRagCollectionModalOverlay) {
    editRagCollectionModalOverlay.addEventListener('click', (e) => {
        // Close if clicking on overlay background (not content)
        if (e.target === editRagCollectionModalOverlay) {
            closeEditCollectionModal();
        }
    });
}

if (editRagCollectionForm) {
    editRagCollectionForm.addEventListener('submit', handleEditRagCollection);
}

// Export functions for use in other modules
window.ragCollectionManagement = {
    toggleRagCollection,
    deleteRagCollection,
    refreshRagCollection,
    openEditCollectionModal
};
