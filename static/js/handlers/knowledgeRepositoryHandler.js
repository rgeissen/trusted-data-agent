/**
 * Knowledge Repository Handler
 * Manages Knowledge repository creation, document upload, and metadata management
 */

import { domElements, state } from '../state.js';
import { showStatusMessage } from '../uiUtils.js';

/**
 * Initialize Knowledge repository handlers
 */
export function initializeKnowledgeRepositoryHandlers() {
    console.log('[Knowledge] Initializing Knowledge repository handlers...');
    
    // Modal open/close handlers
    const addRepoBtn = document.getElementById('add-knowledge-repo-btn');
    const addConstructorBtn = document.getElementById('add-knowledge-constructor-btn');
    const modalOverlay = document.getElementById('add-knowledge-repository-modal-overlay');
    const modalClose = document.getElementById('add-knowledge-repository-modal-close');
    const modalCancel = document.getElementById('add-knowledge-repository-cancel');
    const modalForm = document.getElementById('add-knowledge-repository-form');
    
    if (addRepoBtn) {
        addRepoBtn.addEventListener('click', () => openKnowledgeRepositoryModal());
    }
    
    if (addConstructorBtn) {
        addConstructorBtn.addEventListener('click', () => openKnowledgeRepositoryModal());
    }
    
    if (modalClose) {
        modalClose.addEventListener('click', () => closeKnowledgeRepositoryModal());
    }
    
    if (modalCancel) {
        modalCancel.addEventListener('click', () => closeKnowledgeRepositoryModal());
    }
    
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                closeKnowledgeRepositoryModal();
            }
        });
    }
    
    // Form submission
    if (modalForm) {
        modalForm.addEventListener('submit', handleKnowledgeRepositorySubmit);
    }
    
    // Chunking strategy change handler
    const chunkingSelect = document.getElementById('knowledge-repo-chunking');
    if (chunkingSelect) {
        chunkingSelect.addEventListener('change', handleChunkingStrategyChange);
    }
    
    // File upload handlers
    initializeFileUpload();
    
    console.log('[Knowledge] Knowledge repository handlers initialized');
}

/**
 * Open the Knowledge repository modal
 */
function openKnowledgeRepositoryModal() {
    const modalOverlay = document.getElementById('add-knowledge-repository-modal-overlay');
    const modalContent = document.getElementById('add-knowledge-repository-modal-content');
    
    if (!modalOverlay || !modalContent) return;
    
    // Reset form
    const form = document.getElementById('add-knowledge-repository-form');
    if (form) form.reset();
    
    // Reset file list
    const fileList = document.getElementById('knowledge-repo-file-list');
    const filesContainer = document.getElementById('knowledge-repo-files-container');
    if (fileList) fileList.classList.add('hidden');
    if (filesContainer) filesContainer.innerHTML = '';
    
    // Hide metadata section
    const metadata = document.getElementById('knowledge-repo-metadata');
    if (metadata) metadata.classList.add('hidden');
    
    // Hide progress section
    const progress = document.getElementById('knowledge-repo-progress');
    if (progress) progress.classList.add('hidden');
    
    // Hide chunk params initially
    const chunkParams = document.getElementById('knowledge-repo-chunk-params');
    if (chunkParams) chunkParams.classList.add('hidden');
    
    // Show modal with animation
    modalOverlay.classList.remove('hidden');
    requestAnimationFrame(() => {
        modalOverlay.classList.remove('opacity-0');
        modalContent.classList.remove('scale-95', 'opacity-0');
    });
}

/**
 * Close the Knowledge repository modal
 */
function closeKnowledgeRepositoryModal() {
    const modalOverlay = document.getElementById('add-knowledge-repository-modal-overlay');
    const modalContent = document.getElementById('add-knowledge-repository-modal-content');
    
    if (!modalOverlay || !modalContent) return;
    
    // Hide with animation
    modalOverlay.classList.add('opacity-0');
    modalContent.classList.add('scale-95', 'opacity-0');
    
    setTimeout(() => {
        modalOverlay.classList.add('hidden');
    }, 300);
}

/**
 * Handle chunking strategy change
 */
function handleChunkingStrategyChange(e) {
    const strategy = e.target.value;
    const chunkParams = document.getElementById('knowledge-repo-chunk-params');
    
    // Show chunk size/overlap only for fixed_size strategy
    if (strategy === 'fixed_size') {
        chunkParams?.classList.remove('hidden');
    } else {
        chunkParams?.classList.add('hidden');
    }
}

/**
 * Initialize file upload handlers (drag & drop + click)
 */
function initializeFileUpload() {
    const dropzone = document.getElementById('knowledge-repo-dropzone');
    const fileInput = document.getElementById('knowledge-repo-file-input');
    
    if (!dropzone || !fileInput) return;
    
    // Click to browse
    dropzone.addEventListener('click', () => {
        fileInput.click();
    });
    
    // File selection
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    // Drag & drop
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('border-teradata-orange', 'bg-gray-700/20');
    });
    
    dropzone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropzone.classList.remove('border-teradata-orange', 'bg-gray-700/20');
    });
    
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('border-teradata-orange', 'bg-gray-700/20');
        handleFiles(e.dataTransfer.files);
    });
}

// Store selected files globally
let selectedFiles = [];

/**
 * Handle file selection
 */
function handleFiles(files) {
    const filesArray = Array.from(files);
    
    // Validate file types and sizes
    const validFiles = filesArray.filter(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        const validExts = ['pdf', 'txt', 'docx', 'md'];
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (!validExts.includes(ext)) {
            showStatusMessage(`File ${file.name} has invalid format. Supported: PDF, TXT, DOCX, MD`, 'error');
            return false;
        }
        
        if (file.size > maxSize) {
            showStatusMessage(`File ${file.name} exceeds 10MB limit`, 'error');
            return false;
        }
        
        return true;
    });
    
    if (validFiles.length === 0) return;
    
    // Add to selected files
    selectedFiles = [...selectedFiles, ...validFiles];
    
    // Update UI
    displayFileList();
    
    // Show metadata section
    const metadata = document.getElementById('knowledge-repo-metadata');
    if (metadata) metadata.classList.remove('hidden');
}

/**
 * Display file list
 */
function displayFileList() {
    const fileList = document.getElementById('knowledge-repo-file-list');
    const filesContainer = document.getElementById('knowledge-repo-files-container');
    
    if (!fileList || !filesContainer) return;
    
    fileList.classList.remove('hidden');
    filesContainer.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'flex items-center justify-between p-2 bg-gray-700 rounded-md';
        fileItem.innerHTML = `
            <div class="flex items-center gap-2">
                <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <span class="text-sm text-gray-300">${file.name}</span>
                <span class="text-xs text-gray-500">(${formatFileSize(file.size)})</span>
            </div>
            <button type="button" class="remove-file-btn p-1 text-red-400 hover:text-red-300 transition-colors" data-index="${index}">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        `;
        filesContainer.appendChild(fileItem);
    });
    
    // Add remove handlers
    filesContainer.querySelectorAll('.remove-file-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.currentTarget.dataset.index);
            selectedFiles.splice(index, 1);
            displayFileList();
            
            if (selectedFiles.length === 0) {
                fileList.classList.add('hidden');
                const metadata = document.getElementById('knowledge-repo-metadata');
                if (metadata) metadata.classList.add('hidden');
            }
        });
    });
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Handle form submission
 */
async function handleKnowledgeRepositorySubmit(e) {
    e.preventDefault();
    
    const submitBtn = document.getElementById('add-knowledge-repository-submit');
    const progressSection = document.getElementById('knowledge-repo-progress');
    const progressText = document.getElementById('knowledge-repo-progress-text');
    const progressBar = document.getElementById('knowledge-repo-progress-bar');
    
    try {
        // Get form data
        const name = document.getElementById('knowledge-repo-name').value.trim();
        const description = document.getElementById('knowledge-repo-description').value.trim();
        const chunkingStrategy = document.getElementById('knowledge-repo-chunking').value;
        const embeddingModel = document.getElementById('knowledge-repo-embedding').value;
        
        let chunkSize = 1000;
        let chunkOverlap = 200;
        
        if (chunkingStrategy === 'fixed_size') {
            chunkSize = parseInt(document.getElementById('knowledge-repo-chunk-size').value);
            chunkOverlap = parseInt(document.getElementById('knowledge-repo-chunk-overlap').value);
        }
        
        // Get metadata
        const category = document.getElementById('knowledge-repo-category')?.value.trim() || '';
        const author = document.getElementById('knowledge-repo-author')?.value.trim() || '';
        const tags = document.getElementById('knowledge-repo-tags')?.value.trim() || '';
        
        // Validate
        if (!name) {
            showStatusMessage('Repository name is required', 'error');
            return;
        }
        
        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';
        
        // Show progress
        if (progressSection) {
            progressSection.classList.remove('hidden');
            if (progressText) progressText.textContent = 'Creating repository...';
            if (progressBar) progressBar.style.width = '10%';
        }
        
        // Step 1: Create collection
        const createResponse = await fetch('/api/v1/rag/collection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`
            },
            body: JSON.stringify({
                collection_name: name,
                description: description || 'Knowledge repository',
                repository_type: 'knowledge',
                chunking_strategy: chunkingStrategy,
                chunk_size: chunkSize,
                chunk_overlap: chunkOverlap,
                embedding_model: embeddingModel
            })
        });
        
        if (!createResponse.ok) {
            const error = await createResponse.json();
            throw new Error(error.message || 'Failed to create repository');
        }
        
        const createData = await createResponse.json();
        const collectionId = createData.collection_id;
        
        if (progressBar) progressBar.style.width = '30%';
        
        // Step 2: Upload documents (if any)
        if (selectedFiles.length > 0) {
            if (progressText) progressText.textContent = `Uploading ${selectedFiles.length} documents...`;
            
            for (let i = 0; i < selectedFiles.length; i++) {
                const file = selectedFiles[i];
                
                if (progressText) {
                    progressText.textContent = `Processing ${file.name} (${i + 1}/${selectedFiles.length})...`;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                formData.append('title', file.name);
                formData.append('author', author);
                formData.append('category', category);
                formData.append('tags', tags);
                formData.append('chunking_strategy', chunkingStrategy);
                formData.append('chunk_size', chunkSize.toString());
                formData.append('chunk_overlap', chunkOverlap.toString());
                formData.append('embedding_model', embeddingModel);
                
                const uploadResponse = await fetch(`/api/v1/knowledge/repositories/${collectionId}/documents`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: formData
                });
                
                if (!uploadResponse.ok) {
                    const error = await uploadResponse.json();
                    console.warn(`Failed to upload ${file.name}:`, error.message);
                    showStatusMessage(`Warning: Failed to upload ${file.name}`, 'warning');
                } else {
                    console.log(`Successfully uploaded ${file.name}`);
                }
                
                // Update progress
                const progress = 30 + ((i + 1) / selectedFiles.length) * 70;
                if (progressBar) progressBar.style.width = `${progress}%`;
            }
        } else {
            if (progressBar) progressBar.style.width = '100%';
        }
        
        // Success
        if (progressText) progressText.textContent = 'Repository created successfully!';
        showStatusMessage(`Knowledge repository "${name}" created successfully!`, 'success');
        
        // Wait a moment then close modal
        setTimeout(() => {
            closeKnowledgeRepositoryModal();
            
            // Refresh Knowledge repositories list
            loadKnowledgeRepositories();
            
            // Reset form
            selectedFiles = [];
        }, 1500);
        
    } catch (error) {
        console.error('[Knowledge] Error creating repository:', error);
        showStatusMessage(error.message || 'Failed to create Knowledge repository', 'error');
        
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create Repository';
        }
        
        if (progressSection) {
            progressSection.classList.add('hidden');
        }
    }
}

/**
 * Load and display Knowledge repositories
 */
export async function loadKnowledgeRepositories() {
    const container = document.getElementById('knowledge-repositories-container');
    if (!container) return;
    
    try {
        const response = await fetch('/api/v1/rag/collections', {
            headers: {
                'Authorization': `Bearer ${state.token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load Knowledge repositories');
        }
        
        const data = await response.json();
        const knowledgeRepos = data.collections?.filter(c => c.repository_type === 'knowledge') || [];
        
        if (knowledgeRepos.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <svg class="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <p class="text-gray-400 text-sm">No Knowledge repositories yet. Create one to get started!</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = knowledgeRepos.map(repo => createKnowledgeRepositoryCard(repo)).join('');
        
    } catch (error) {
        console.error('[Knowledge] Error loading repositories:', error);
        container.innerHTML = `
            <div class="col-span-full text-center text-red-400 text-sm">
                Failed to load Knowledge repositories
            </div>
        `;
    }
}

/**
 * Create a Knowledge repository card HTML
 */
function createKnowledgeRepositoryCard(repo) {
    return `
        <div class="glass-panel p-6 rounded-lg hover:bg-white/5 transition-all cursor-pointer" data-repo-id="${repo.collection_id}">
            <div class="flex items-start justify-between mb-4">
                <div class="flex items-center gap-3">
                    <div class="p-2 bg-green-500/20 rounded-lg">
                        <svg class="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                    </div>
                    <div>
                        <h3 class="text-lg font-semibold text-white">${repo.collection_name}</h3>
                        <p class="text-xs text-gray-400">${repo.description || 'Knowledge repository'}</p>
                    </div>
                </div>
            </div>
            
            <div class="space-y-2">
                <div class="flex items-center gap-2 text-sm text-gray-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
                    </svg>
                    <span>${repo.example_count || 0} documents</span>
                </div>
                <div class="flex items-center gap-2 text-sm text-gray-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path>
                    </svg>
                    <span>${repo.chunking_strategy || 'semantic'} chunking</span>
                </div>
            </div>
            
            <div class="mt-4 pt-4 border-t border-gray-700 flex gap-2">
                <button class="view-knowledge-repo-btn flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm text-white transition-colors" data-repo-id="${repo.collection_id}">
                    View
                </button>
                <button class="delete-knowledge-repo-btn px-3 py-2 bg-red-600 hover:bg-red-700 rounded text-sm text-white transition-colors" data-repo-id="${repo.collection_id}">
                    Delete
                </button>
            </div>
        </div>
    `;
}
