/**
 * RAG Collection Management - Template System
 * 
 * Handles template loading, card rendering, and template field switching.
 */

import { showNotification } from './utils.js';

/**
 * Initialize template system on page load
 * @param {HTMLSelectElement} templateDropdown - Template type dropdown element
 * @param {Function} switchFieldsCallback - Callback to switch template fields
 */
export async function initializeTemplateSystem(templateDropdown, switchFieldsCallback) {
    console.log('[Template System] Starting initialization...');
    try {
        if (!window.templateManager) {
            console.error('[Template System] templateManager not available on window object');
            return;
        }
        
        // Initialize template manager
        await window.templateManager.initialize();
        console.log('[Template System] Template manager initialized successfully');
        
        // Populate template dropdown
        if (templateDropdown) {
            window.templateManager.populateTemplateDropdown(templateDropdown, {
                includeDeprecated: false,
                includeComingSoon: true,
                selectedTemplateId: 'sql_query_v1' // Default selection
            });
            console.log('[Template System] Template dropdown populated');
            
            // Trigger initial field rendering
            if (switchFieldsCallback) {
                await switchFieldsCallback();
                console.log('[Template System] Template fields switched');
            }
        }
        
        // Load template cards dynamically
        console.log('[Template System] Loading template cards...');
        await loadTemplateCards();
        console.log('[Template System] Template cards loaded');
    } catch (error) {
        console.error('[Template System] Failed to initialize:', error);
        console.error('[Template System] Error stack:', error.stack);
        showNotification('error', 'Failed to load templates: ' + error.message);
    }
}

/**
 * Load template cards dynamically from backend
 */
export async function loadTemplateCards() {
    const container = document.getElementById('rag-templates-container');
    if (!container) {
        console.warn('[Template Cards] Container not found');
        return;
    }
    
    try {
        if (!window.templateManager) {
            console.error('[Template Cards] templateManager not initialized');
            container.innerHTML = '<div class="col-span-full text-red-400 text-sm">Template manager not initialized</div>';
            return;
        }
        
        const templates = window.templateManager.getAllTemplates();
        console.log('[Template Cards] Retrieved templates:', templates);
        
        if (!templates || templates.length === 0) {
            container.innerHTML = '<div class="col-span-full text-gray-400 text-sm">No templates available</div>';
            return;
        }
        
        container.innerHTML = '';
        
        templates.forEach((template, index) => {
            try {
                const card = createTemplateCard(template, index);
                container.appendChild(card);
            } catch (cardError) {
                console.error(`[Template Cards] Failed to create card for template ${template.template_id}:`, cardError);
            }
        });
        
        console.log(`[Template Cards] Successfully loaded ${templates.length} template cards`);
    } catch (error) {
        console.error('[Template Cards] Failed to load:', error);
        container.innerHTML = '<div class="col-span-full text-red-400 text-sm">Failed to load templates: ' + error.message + '</div>';
    }
}

/**
 * Create a template card element
 * @param {object} template - Template metadata
 * @param {number} index - Template index for color rotation
 * @returns {HTMLElement} Template card element
 */
export function createTemplateCard(template, index) {
    const card = document.createElement('div');
    card.className = 'glass-panel rounded-xl p-6 hover:border-[#F15F22] transition-colors cursor-pointer';
    card.setAttribute('data-template-id', template.template_id);
    
    // Icon colors array
    const iconColors = ['blue', 'purple', 'green', 'orange', 'pink', 'indigo'];
    const colorIndex = index % iconColors.length;
    const color = iconColors[colorIndex];
    
    card.innerHTML = `
        <div class="flex items-start justify-between mb-4">
            <div class="w-12 h-12 bg-${color}-500/20 rounded-lg flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-${color}-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    ${getTemplateIcon(template.template_type)}
                </svg>
            </div>
            <div class="flex items-center gap-2">
                <span class="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-medium rounded">Ready</span>
            </div>
        </div>
        <h3 class="text-lg font-bold text-white mb-2">${template.display_name || template.template_name}</h3>
        <p class="text-sm text-gray-400 mb-4">${template.description || 'No description available'}</p>
        <div class="space-y-2 text-xs text-gray-500">
            <div class="flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <span>Template ID: ${template.template_id}</span>
            </div>
        </div>
        <div class="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
            <span class="text-xs text-gray-500">Click to populate</span>
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
        </div>
    `;
    
    // Add click handler
    card.addEventListener('click', () => {
        if (window.openSqlTemplatePopulator) {
            window.openSqlTemplatePopulator();
        }
    });
    
    return card;
}

/**
 * Get SVG path for template icon based on type
 * @param {string} templateType - Template type identifier
 * @returns {string} SVG path string
 */
export function getTemplateIcon(templateType) {
    const icons = {
        'sql_query': '<path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />',
        'api_request': '<path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />',
        'default': '<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />'
    };
    
    return icons[templateType] || icons['default'];
}

/**
 * Reload template configuration from server
 * @param {string} templateId - Template ID to reload
 * @returns {Promise<object|null>} Template configuration or null if failed
 */
export async function reloadTemplateConfiguration(templateId) {
    try {
        const id = templateId || 'sql_query_v1';
        // Add cache-busting parameter to force fresh load
        const response = await fetch(`/api/v1/rag/templates/${id}/config?_=${Date.now()}`);
        if (response.ok) {
            const configData = await response.json();
            console.log('[Template Config] Reloaded configuration:', configData);
            return configData;
        } else {
            console.warn('[Template Config] Failed to reload, status:', response.status);
            return null;
        }
    } catch (error) {
        console.error('[Template Config] Error reloading configuration:', error);
        return null;
    }
}
