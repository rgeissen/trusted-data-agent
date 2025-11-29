/**
 * Knowledge Repository Handler
 * Manages Knowledge repository creation, document upload, and metadata management
 */

import { state } from '../state.js';

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
    
    // Chunking strategy change handler with auto-preview
    const chunkingSelect = document.getElementById('knowledge-repo-chunking');
    if (chunkingSelect) {
        chunkingSelect.addEventListener('change', (e) => {
            handleChunkingStrategyChange(e);
            triggerAutoPreview();
        });
    }
    
    // Chunk parameter change handlers with auto-preview
    const chunkSizeInput = document.getElementById('knowledge-repo-chunk-size');
    const chunkOverlapInput = document.getElementById('knowledge-repo-chunk-overlap');
    
    if (chunkSizeInput) {
        chunkSizeInput.addEventListener('change', triggerAutoPreview);
    }
    
    if (chunkOverlapInput) {
        chunkOverlapInput.addEventListener('change', triggerAutoPreview);
    }
    
    // File upload handlers
    initializeFileUpload();
    
    // Preview button handler
    const previewBtn = document.getElementById('knowledge-repo-preview-btn');
    if (previewBtn) {
        previewBtn.addEventListener('click', handlePreviewChunking);
    }
    
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
    
    // Reset preview state
    const previewEmpty = document.getElementById('knowledge-repo-preview-empty');
    const previewResults = document.getElementById('knowledge-repo-preview-results');
    const preview = document.getElementById('knowledge-repo-preview');
    if (previewEmpty) previewEmpty.classList.remove('hidden');
    if (previewResults) previewResults.classList.add('hidden');
    if (preview) preview.classList.add('hidden');
    
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
        const maxSize = 50 * 1024 * 1024; // 50MB
        
        if (!validExts.includes(ext)) {
            console.error(`[Knowledge] File ${file.name} has invalid format. Supported: PDF, TXT, DOCX, MD`);
            alert(`File ${file.name} has invalid format. Supported: PDF, TXT, DOCX, MD`);
            return false;
        }
        
        if (file.size > maxSize) {
            console.error(`[Knowledge] File ${file.name} exceeds 50MB limit`);
            alert(`File ${file.name} exceeds 50MB limit`);
            return false;
        }
        
        return true;
    });
    
    if (validFiles.length === 0) return;
    
    // Add to selected files
    selectedFiles = [...selectedFiles, ...validFiles];
    
    // Update UI
    displayFileList();
    
    // Show metadata and preview sections
    const metadata = document.getElementById('knowledge-repo-metadata');
    const preview = document.getElementById('knowledge-repo-preview');
    if (metadata) metadata.classList.remove('hidden');
    if (preview) preview.classList.remove('hidden');
    
    // Auto-generate preview
    setTimeout(() => triggerAutoPreview(), 100);
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
        // Get form values
        const nameInput = document.getElementById('knowledge-repo-name');
        const descInput = document.getElementById('knowledge-repo-description');
        const chunkingInput = document.getElementById('knowledge-repo-chunking');
        const embeddingInput = document.getElementById('knowledge-repo-embedding');
        
        if (!nameInput) {
            console.error('[Knowledge] Name input field not found');
            alert('Form error: Name field not found');
            return;
        }
        
        const name = nameInput.value.trim();
        const description = descInput?.value.trim() || '';
        const chunkingStrategy = chunkingInput?.value || 'semantic';
        const embeddingModel = embeddingInput?.value || 'default';
        
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
            console.error('[Knowledge] Repository name is required');
            alert('Repository name is required');
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
        const token = localStorage.getItem('tda_auth_token');
        const createResponse = await fetch('/api/v1/rag/collections', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                name: name,
                description: description || 'Knowledge repository',
                repository_type: 'knowledge',
                chunking_strategy: chunkingStrategy,
                chunk_size: chunkSize,
                chunk_overlap: chunkOverlap
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
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });
                
                if (!uploadResponse.ok) {
                    const error = await uploadResponse.json();
                    console.warn(`Failed to upload ${file.name}:`, error.message);
                    console.warn(`[Knowledge] Warning: Failed to upload ${file.name}`);
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
        console.log(`[Knowledge] Repository "${name}" created successfully!`);
        alert(`Knowledge repository "${name}" created successfully!`);
        
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
        alert(error.message || 'Failed to create Knowledge repository');
        
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
        const token = localStorage.getItem('tda_auth_token');
        const response = await fetch('/api/v1/rag/collections', {
            headers: {
                'Authorization': `Bearer ${token}`
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

/**
 * Render more chunks (for infinite scroll)
 */
function renderMoreChunks(count = 5) {
    const previewChunks = document.getElementById('knowledge-repo-preview-chunks');
    if (!previewChunks || !window.previewChunksData) return;
    
    const chunks = window.previewChunksData;
    const startIdx = window.previewChunksDisplayed || 0;
    const endIdx = Math.min(startIdx + count, chunks.length);
    
    // Remove "load more" indicator if it exists
    const loadMoreIndicator = previewChunks.querySelector('.load-more-indicator');
    if (loadMoreIndicator) loadMoreIndicator.remove();
    
    // Render chunks
    for (let idx = startIdx; idx < endIdx; idx++) {
        const chunk = chunks[idx];
        const chunkEl = document.createElement('div');
        chunkEl.className = 'bg-gray-700/50 rounded-lg p-4 border border-gray-600 hover:border-purple-500/50 transition-colors';
        
        const isTruncated = chunk.text.length > 500;
        const chunkId = `chunk-preview-${idx}`;
        
        chunkEl.innerHTML = `
            <div class="flex items-center justify-between mb-3">
                <span class="text-sm font-semibold text-purple-300">Chunk ${idx + 1}</span>
                <span class="text-xs px-2 py-1 rounded-full bg-gray-600 text-gray-300">${chunk.text.length} chars</span>
            </div>
            <div id="${chunkId}-text" class="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">
                ${isTruncated ? chunk.text.substring(0, 500) + '...' : chunk.text}
            </div>
            ${isTruncated ? `
                <button id="${chunkId}-toggle" class="mt-3 text-xs text-purple-400 hover:text-purple-300 underline transition-colors">
                    Show full chunk
                </button>
            ` : ''}
        `;
        
        // Add toggle functionality if truncated
        if (isTruncated) {
            const toggleBtn = chunkEl.querySelector(`#${chunkId}-toggle`);
            const textDiv = chunkEl.querySelector(`#${chunkId}-text`);
            let isExpanded = false;
            
            toggleBtn.addEventListener('click', () => {
                isExpanded = !isExpanded;
                textDiv.textContent = isExpanded ? chunk.text : chunk.text.substring(0, 500) + '...';
                toggleBtn.textContent = isExpanded ? 'Show less' : 'Show full chunk';
            });
        }
        
        previewChunks.appendChild(chunkEl);
    }
    
    window.previewChunksDisplayed = endIdx;
    
    // Add "scroll for more" indicator if there are more chunks
    if (endIdx < chunks.length) {
        const moreEl = document.createElement('div');
        moreEl.className = 'load-more-indicator text-center py-3 text-sm text-gray-400 flex items-center justify-center gap-2';
        moreEl.innerHTML = `
            <svg class="animate-bounce w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path>
            </svg>
            <span>Scroll down to load ${Math.min(5, chunks.length - endIdx)} more chunks (${chunks.length - endIdx} remaining)</span>
        `;
        previewChunks.appendChild(moreEl);
    }
}

/**
 * Setup infinite scroll for preview chunks
 */
function setupInfiniteScroll() {
    const previewChunks = document.getElementById('knowledge-repo-preview-chunks');
    if (!previewChunks) return;
    
    // Find the scrollable parent container (has overflow-y-auto class)
    const scrollContainer = previewChunks.parentElement;
    if (!scrollContainer) return;
    
    // Remove existing listener if any
    if (window.previewScrollListener) {
        scrollContainer.removeEventListener('scroll', window.previewScrollListener);
    }
    
    // Create scroll listener
    window.previewScrollListener = () => {
        const scrollTop = scrollContainer.scrollTop;
        const scrollHeight = scrollContainer.scrollHeight;
        const clientHeight = scrollContainer.clientHeight;
        
        // Load more when scrolled to bottom (with 100px threshold)
        if (scrollTop + clientHeight >= scrollHeight - 100) {
            if (window.previewChunksData && window.previewChunksDisplayed < window.previewChunksData.length) {
                renderMoreChunks(5);
            }
        }
    };
    
    scrollContainer.addEventListener('scroll', window.previewScrollListener);
}

/**
 * Trigger auto-preview when files or settings change
 */
function triggerAutoPreview() {
    // Only auto-preview if files are selected
    if (!selectedFiles || selectedFiles.length === 0) {
        return;
    }
    
    // Debounce to avoid rapid consecutive calls
    if (window.previewTimeout) {
        clearTimeout(window.previewTimeout);
    }
    
    window.previewTimeout = setTimeout(() => {
        handlePreviewChunking(true); // Pass true to indicate auto-preview
    }, 300);
}

/**
 * Handle chunking preview
 */
async function handlePreviewChunking(isAutoPreview = false) {
    if (selectedFiles.length === 0) {
        if (!isAutoPreview) {
            alert('Please select at least one document to preview chunking');
        }
        return;
    }
    
    const previewBtn = document.getElementById('knowledge-repo-preview-btn');
    const previewResults = document.getElementById('knowledge-repo-preview-results');
    const previewStats = document.getElementById('knowledge-repo-preview-stats');
    const previewChunks = document.getElementById('knowledge-repo-preview-chunks');
    
    if (!previewBtn || !previewResults || !previewStats || !previewChunks) return;
    
    // Get chunking configuration
    const chunkingStrategy = document.getElementById('knowledge-repo-chunking')?.value || 'semantic';
    let chunkSize = 1000;
    let chunkOverlap = 200;
    
    if (chunkingStrategy === 'fixed_size') {
        chunkSize = parseInt(document.getElementById('knowledge-repo-chunk-size')?.value || '1000');
        chunkOverlap = parseInt(document.getElementById('knowledge-repo-chunk-overlap')?.value || '200');
    }
    
    // Disable button and show loading
    previewBtn.disabled = true;
    previewBtn.textContent = 'Generating Preview...';
    previewResults.classList.remove('hidden');
    previewChunks.innerHTML = '<p class="text-sm text-gray-400 text-center py-4">Processing...</p>';
    
    try {
        // For now, we'll use the first file for preview
        const file = selectedFiles[0];
        
        // Create FormData to send file
        const formData = new FormData();
        formData.append('file', file);
        formData.append('chunking_strategy', chunkingStrategy);
        formData.append('chunk_size', chunkSize);
        formData.append('chunk_overlap', chunkOverlap);
        
        // Call preview API endpoint (we'll need to create this)
        const token = localStorage.getItem('tda_auth_token');
        const response = await fetch('/api/v1/knowledge/preview-chunking', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to generate preview');
        }
        
        const data = await response.json();
        const chunks = data.chunks || [];
        
        // Update stats
        const totalChars = data.total_characters || chunks.reduce((sum, chunk) => sum + chunk.text.length, 0);
        const isTruncated = data.is_preview_truncated;
        const fullDocChars = data.full_document_characters;
        const previewNote = data.preview_note;
        
        let statsText = `${chunks.length} chunks • ${totalChars.toLocaleString()} chars`;
        if (isTruncated && previewNote) {
            statsText += ` • ${previewNote}`;
        } else if (isTruncated) {
            statsText += ` • Preview (full doc: ${fullDocChars.toLocaleString()} chars)`;
        } else {
            statsText += ` • Avg ${Math.round(totalChars / chunks.length)} chars/chunk`;
        }
        previewStats.textContent = statsText;
        
        // Hide empty state, show results
        const previewEmpty = document.getElementById('knowledge-repo-preview-empty');
        if (previewEmpty) previewEmpty.classList.add('hidden');
        
        // Store chunks for infinite scroll
        window.previewChunksData = chunks;
        window.previewChunksDisplayed = 0;
        
        // Clear and setup infinite scroll
        previewChunks.innerHTML = '';
        renderMoreChunks(5); // Initial load: 5 chunks
        
        // Setup infinite scroll listener
        setupInfiniteScroll();
        
    } catch (error) {
        console.error('[Knowledge] Preview error:', error);
        previewChunks.innerHTML = `<p class="text-sm text-red-400 text-center py-4">Failed to generate preview: ${error.message}</p>`;
    } finally {
        previewBtn.disabled = false;
        previewBtn.textContent = 'Preview Segmentation';
    }
}
