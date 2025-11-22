// static/js/handlers/configurationHandler.js
// Manages the new modular configuration system with MCP servers, LLM providers, and localStorage

import { handleViewSwitch } from '../ui.js';
import { handleStartNewSession, handleLoadSession } from './sessionManagement.js';
import { handleLoadResources } from '../eventHandlers.js';
import * as API from '../api.js';
import * as UI from '../ui.js';
import * as DOM from '../domElements.js';
import { state } from '../state.js';
import { safeSetItem, safeGetItem } from '../storageUtils.js';

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Shows a toast notification in the header status area
 * @param {string} type - 'success', 'error', 'warning', 'info'
 * @param {string} message - The message to display
 */
function showNotification(type, message) {
    const colors = {
        success: 'bg-green-600/90',
        error: 'bg-red-600/90',
        warning: 'bg-yellow-600/90',
        info: 'bg-blue-600/90'
    };

    const statusElement = document.getElementById('header-status-message');
    if (!statusElement) {
        return;
    }
    
    // Clear any existing timeout
    if (statusElement.hideTimeout) {
        clearTimeout(statusElement.hideTimeout);
    }
    
    // Set the message and style
    statusElement.textContent = message;
    statusElement.className = `text-sm px-3 py-1 rounded-md transition-all duration-300 ${colors[type] || colors.info} text-white`;
    statusElement.style.opacity = '1';
    
    // Auto-hide after 5 seconds
    statusElement.hideTimeout = setTimeout(() => {
        statusElement.style.opacity = '0';
        setTimeout(() => {
            statusElement.textContent = '';
            statusElement.className = 'text-sm px-3 py-1 rounded-md transition-all duration-300 opacity-0';
        }, 300);
    }, 5000);
}

function generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// STORAGE KEYS
// ============================================================================
const STORAGE_KEYS = {
    MCP_SERVERS: 'tda_mcp_servers',
    LLM_PROVIDERS: 'tda_llm_providers',
    ACTIVE_MCP: 'tda_active_mcp',
    ACTIVE_LLM: 'tda_active_llm',
};

// ============================================================================
// LLM PROVIDER TEMPLATES
// ============================================================================
const LLM_PROVIDER_TEMPLATES = {
    Google: {
        name: 'Google',
        fields: [
            { id: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Enter your Google API Key', required: true }
        ]
    },
    Anthropic: {
        name: 'Anthropic',
        fields: [
            { id: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Enter your Anthropic API Key', required: true }
        ]
    },
    OpenAI: {
        name: 'OpenAI',
        fields: [
            { id: 'apiKey', label: 'API Key', type: 'password', placeholder: 'Enter your OpenAI API Key', required: true }
        ]
    },
    Azure: {
        name: 'Microsoft Azure',
        fields: [
            { id: 'azure_api_key', label: 'Azure API Key', type: 'password', placeholder: 'Enter your Azure API Key', required: true },
            { id: 'azure_endpoint', label: 'Azure Endpoint', type: 'text', placeholder: 'e.g., https://your-resource.openai.azure.com/', required: true },
            { id: 'azure_deployment_name', label: 'Deployment Name', type: 'text', placeholder: 'Your model deployment name', required: true },
            { id: 'azure_api_version', label: 'API Version', type: 'text', placeholder: 'e.g., 2024-02-01', required: true }
        ]
    },
    Friendli: {
        name: 'Friendli.ai',
        fields: [
            { id: 'friendli_token', label: 'Personal Access Token', type: 'password', placeholder: 'Enter your Friendli PAT', required: true },
            { id: 'friendli_endpoint_url', label: 'Dedicated Endpoint URL (Optional)', type: 'text', placeholder: 'e.g., https://your-endpoint.friendli.ai', required: false }
        ]
    },
    Amazon: {
        name: 'Amazon',
        fields: [
            { id: 'aws_access_key_id', label: 'AWS Access Key ID', type: 'password', placeholder: 'Enter your AWS Access Key ID', required: true },
            { id: 'aws_secret_access_key', label: 'AWS Secret Access Key', type: 'password', placeholder: 'Enter your AWS Secret Access Key', required: true },
            { id: 'aws_region', label: 'AWS Region', type: 'text', placeholder: 'e.g., us-east-1', required: true }
        ],
        extra: {
            listingMethod: [
                { id: 'foundation_models', label: 'Foundation Models', value: 'foundation_models', default: true },
                { id: 'inference_profiles', label: 'Inference Profiles', value: 'inference_profiles', default: false }
            ]
        }
    },
    Ollama: {
        name: 'Ollama (Local)',
        fields: [
            { id: 'ollama_host', label: 'Ollama Host', type: 'text', placeholder: 'e.g., http://localhost:11434', required: true }
        ]
    }
};

// ============================================================================
// STATE MANAGEMENT
// ============================================================================
class ConfigurationState {
    constructor() {
        this.mcpServers = [];
        this.llmProviders = this.loadLLMProviders();
        this.activeMCP = null;
        this.activeLLM = localStorage.getItem(STORAGE_KEYS.ACTIVE_LLM);
        this.profiles = [];
        this.activeProfileId = null;
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return;
        await this.loadMCPServers();
        await this.loadProfiles();
        this.initialized = true;
    }

    async loadProfiles() {
        try {
            const { profiles, default_profile_id, active_for_consumption_profile_ids } = await API.getProfiles();
            this.profiles = profiles || [];
            this.defaultProfileId = default_profile_id;
            this.activeForConsumptionProfileIds = active_for_consumption_profile_ids || [];
            return this.profiles;
        } catch (error) {
            console.error('Failed to load profiles:', error);
            this.profiles = [];
        }
        return this.profiles;
    }
    
    async addProfile(profile) {
        const newProfile = await API.addProfile(profile);
        this.profiles.push(newProfile.profile);
        return newProfile.profile;
    }

    async updateProfile(profileId, updates) {
        const updatedProfile = await API.updateProfile(profileId, updates);
        const index = this.profiles.findIndex(p => p.id === profileId);
        if (index !== -1) {
            this.profiles[index] = { ...this.profiles[index], ...updates };
        }
        return updatedProfile;
    }

    async removeProfile(profileId) {
        await API.deleteProfile(profileId);
        this.profiles = this.profiles.filter(p => p.id !== profileId);
        if (this.defaultProfileId === profileId) {
            this.defaultProfileId = null;
        }
        this.activeForConsumptionProfileIds = this.activeForConsumptionProfileIds.filter(id => id !== profileId);
    }

    async setDefaultProfile(profileId) {
        await API.setDefaultProfile(profileId);
        this.defaultProfileId = profileId;
    }

    async setActiveForConsumptionProfiles(profileIds) {
        await API.setActiveForConsumptionProfiles(profileIds);
        this.activeForConsumptionProfileIds = profileIds;
    }

    async loadMCPServers() {
        try {
            const response = await fetch('/api/v1/mcp/servers');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.mcpServers = result.servers || [];
                this.activeMCP = result.active_server_id;
                return this.mcpServers;
            }
        } catch (error) {
            console.error('Failed to load MCP servers:', error);
            this.mcpServers = [];
        }
        return this.mcpServers;
    }

    async saveMCPServers() {
        // No-op: servers are saved individually via API
        // Kept for compatibility
    }

    loadLLMProviders() {
        const stored = localStorage.getItem(STORAGE_KEYS.LLM_PROVIDERS);
        if (stored) {
            return JSON.parse(stored);
        }
        // Initialize with default empty configs for each provider
        const providers = {};
        Object.keys(LLM_PROVIDER_TEMPLATES).forEach(key => {
            providers[key] = { provider: key, configured: false, model: null, credentials: {} };
        });
        return providers;
    }

    saveLLMProviders() {
        safeSetItem(STORAGE_KEYS.LLM_PROVIDERS, JSON.stringify(this.llmProviders));
    }

    async setActiveMCP(serverId) {
        try {
            const response = await fetch(`/api/v1/mcp/servers/${serverId}/activate`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.activeMCP = serverId;
                updateReconnectButton();
            }
        } catch (error) {
            console.error('Failed to set active MCP server:', error);
        }
    }

    setActiveLLM(provider) {
        this.activeLLM = provider;
        safeSetItem(STORAGE_KEYS.ACTIVE_LLM, provider);
        updateReconnectButton();
    }

    async addMCPServer(server) {
        server.id = server.id || generateId();
        
        try {
            const response = await fetch('/api/v1/mcp/servers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(server)
            });
            
            if (response.ok) {
                // Reload servers from backend to get the updated list
                await this.loadMCPServers();
                return server.id;
            } else {
                const errorData = await response.json();
                console.error('Failed to add MCP server:', errorData);
                throw new Error(errorData.message || 'Failed to add MCP server');
            }
        } catch (error) {
            console.error('Failed to add MCP server:', error);
            throw error;
        }
    }

    async removeMCPServer(serverId) {
        try {
            const response = await fetch(`/api/v1/mcp/servers/${serverId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.mcpServers = this.mcpServers.filter(s => s.id !== serverId);
                if (this.activeMCP === serverId) {
                    this.activeMCP = null;
                }
                return { success: true };
            } else {
                const errorData = await response.json();
                return { 
                    success: false, 
                    error: errorData.message || 'Failed to remove MCP server' 
                };
            }
        } catch (error) {
            console.error('Failed to remove MCP server:', error);
            return { 
                success: false, 
                error: error.message || 'Failed to remove MCP server' 
            };
        }
    }

    async updateMCPServer(serverId, updates) {
        try {
            const response = await fetch(`/api/v1/mcp/servers/${serverId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });
            
            if (response.ok) {
                // Reload servers from backend to get the updated list
                await this.loadMCPServers();
                return true;
            }
        } catch (error) {
            console.error('Failed to update MCP server:', error);
        }
        return false;
    }

    updateLLMProvider(provider, data) {
        this.llmProviders[provider] = { ...this.llmProviders[provider], ...data, configured: true };
        this.saveLLMProviders();
    }

    getActiveMCPServer() {
        return this.mcpServers.find(s => s.id === this.activeMCP);
    }

    getActiveLLMProvider() {
        return this.activeLLM ? this.llmProviders[this.activeLLM] : null;
    }

    canReconnect() {
        const mcpServer = this.getActiveMCPServer();
        const llmProvider = this.getActiveLLMProvider();
        return !!(mcpServer && llmProvider && llmProvider.configured && llmProvider.model);
    }
}

// Global state instance
export const configState = new ConfigurationState();

// Also expose to window to avoid circular imports
window.configState = configState;

// ============================================================================
// UI RENDERING - MCP SERVERS
// ============================================================================
export function renderMCPServers() {
    const container = document.getElementById('mcp-servers-container');
    if (!container) return;

    if (configState.mcpServers.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-8">
                <p>No MCP servers configured. Click "Add Server" to get started.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = configState.mcpServers.map(server => `
        <div class="bg-white/5 border ${server.id === configState.activeMCP ? 'border-[#F15F22]' : 'border-white/10'} rounded-lg p-4" data-mcp-id="${server.id}">
            <div class="flex items-start justify-between">
                <div class="flex items-start gap-3 flex-1">
                    <input type="radio" name="active-mcp" value="${server.id}" ${server.id === configState.activeMCP ? 'checked' : ''} 
                        class="mt-1 h-4 w-4 border-gray-300 text-[#F15F22] focus:ring-[#F15F22]" data-action="select-mcp">
                    <div class="flex-1">
                        <h4 class="font-semibold text-white mb-2">${escapeHtml(server.name)}</h4>
                        <div class="text-sm text-gray-400 space-y-1">
                            <p><span class="font-medium">Host:</span> ${escapeHtml(server.host)}:${escapeHtml(server.port)}</p>
                            <p><span class="font-medium">Path:</span> ${escapeHtml(server.path)}</p>
                        </div>
                        ${server.testStatus ? `
                            <div class="mt-2 text-sm ${server.testStatus === 'success' ? 'text-green-400' : 'text-red-400'}">
                                ${escapeHtml(server.testMessage || '')}
                            </div>
                        ` : ''}
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <button type="button" data-action="test-mcp" data-server-id="${server.id}" 
                        class="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 rounded transition-colors text-white">
                        Test
                    </button>
                    <button type="button" data-action="edit-mcp" data-server-id="${server.id}" 
                        class="px-3 py-1 text-sm bg-gray-600 hover:bg-gray-700 rounded transition-colors text-white">
                        Edit
                    </button>
                    <button type="button" data-action="delete-mcp" data-server-id="${server.id}" 
                        class="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 rounded transition-colors text-white">
                        Delete
                    </button>
                </div>
            </div>
        </div>
    `).join('');

    attachMCPEventListeners();
}

function attachMCPEventListeners() {
    // Select MCP radio buttons
    document.querySelectorAll('[data-action="select-mcp"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.checked) {
                configState.setActiveMCP(e.target.value);
                renderMCPServers(); // Re-render to update active state
            }
        });
    });

    // Test MCP button
    document.querySelectorAll('[data-action="test-mcp"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const serverId = e.target.dataset.serverId;
            testMCPConnection(serverId);
        });
    });

    // Edit MCP button
    document.querySelectorAll('[data-action="edit-mcp"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const serverId = e.target.dataset.serverId;
            showMCPServerModal(serverId);
        });
    });

    // Delete MCP button
    document.querySelectorAll('[data-action="delete-mcp"]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const serverId = e.target.dataset.serverId;
            const server = configState.mcpServers.find(s => s.id === serverId);
            const serverName = server ? server.name : 'this server';
            
            if (confirm(`Are you sure you want to delete MCP server "${serverName}"?`)) {
                const result = await configState.removeMCPServer(serverId);
                if (result.success) {
                    renderMCPServers();
                    showNotification('success', 'MCP server deleted successfully');
                } else {
                    showNotification('error', result.error);
                }
            }
        });
    });
}

// ============================================================================
// UI RENDERING - LLM PROVIDERS
// ============================================================================
export function renderLLMProviders() {
    const container = document.getElementById('llm-providers-container');
    if (!container) return;

    container.innerHTML = Object.entries(LLM_PROVIDER_TEMPLATES).map(([key, template]) => {
        const providerData = configState.llmProviders[key];
        const isActive = configState.activeLLM === key;
        const isConfigured = providerData && providerData.configured;
        const modelName = providerData && providerData.model ? providerData.model : 'Not configured';

        return `
            <div class="bg-white/5 border ${isActive ? 'border-[#F15F22]' : 'border-white/10'} rounded-lg overflow-hidden" data-llm-provider="${key}">
                <div class="p-4 cursor-pointer hover:bg-white/5 transition-colors" data-action="toggle-llm-details">
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center gap-3">
                            <input type="radio" name="active-llm" value="${key}" ${isActive ? 'checked' : ''} 
                                class="h-4 w-4 border-gray-300 text-[#F15F22] focus:ring-[#F15F22]" data-action="select-llm">
                            <h4 class="font-semibold text-white">${escapeHtml(template.name)}</h4>
                        </div>
                        <div class="w-5 h-5 text-gray-400 transition-transform" data-chevron>
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                            </svg>
                        </div>
                    </div>
                    <div class="text-sm text-gray-400">
                        <span class="font-medium">Model:</span> ${escapeHtml(modelName)}
                    </div>
                    ${isConfigured ? '<div class="mt-2 text-xs text-green-400">✓ Configured</div>' : '<div class="mt-2 text-xs text-gray-500">Not configured</div>'}
                </div>
                <div class="llm-provider-details hidden bg-black/20 p-4 border-t border-white/10">
                    <div id="llm-${key}-form-container"></div>
                </div>
            </div>
        `;
    }).join('');

    attachLLMEventListeners();
}

function attachLLMEventListeners() {
    // Select LLM radio buttons
    document.querySelectorAll('[data-action="select-llm"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.checked) {
                configState.setActiveLLM(e.target.value);
                renderLLMProviders(); // Re-render to update active state
            }
        });
        // Prevent event bubbling to toggle
        radio.addEventListener('click', (e) => e.stopPropagation());
    });

    // Toggle LLM provider details
    document.querySelectorAll('[data-action="toggle-llm-details"]').forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            // Don't toggle if clicking radio button
            if (e.target.closest('[data-action="select-llm"]')) return;
            
            const card = toggle.closest('[data-llm-provider]');
            const provider = card.dataset.llmProvider;
            const details = card.querySelector('.llm-provider-details');
            const chevron = card.querySelector('[data-chevron]');
            
            if (details.classList.contains('hidden')) {
                details.classList.remove('hidden');
                chevron.style.transform = 'rotate(180deg)';
                renderLLMProviderForm(provider);
            } else {
                details.classList.add('hidden');
                chevron.style.transform = 'rotate(0deg)';
            }
        });
    });
}

function renderLLMProviderForm(provider) {
    const container = document.getElementById(`llm-${provider}-form-container`);
    if (!container) return;

    const template = LLM_PROVIDER_TEMPLATES[provider];
    const providerData = configState.llmProviders[provider] || {};

    let formHTML = '<div class="space-y-4">';

    // Render fields
    template.fields.forEach(field => {
        const value = providerData.credentials?.[field.id] || '';
        formHTML += `
            <div>
                <label class="block text-sm font-medium text-gray-300 mb-1">${escapeHtml(field.label)}</label>
                <input type="${field.type}" 
                    data-field="${field.id}" 
                    value="${escapeHtml(value)}" 
                    placeholder="${escapeHtml(field.placeholder)}" 
                    ${field.required ? 'required' : ''}
                    class="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
            </div>
        `;
    });

    // Extra fields (like AWS listing method)
    if (template.extra?.listingMethod) {
        formHTML += '<div><label class="block text-sm font-medium text-gray-300 mb-2">Model Listing Method</label><div class="flex items-center gap-6">';
        template.extra.listingMethod.forEach(option => {
            const checked = providerData.listingMethod === option.value || (option.default && !providerData.listingMethod);
            formHTML += `
                <div class="flex items-center">
                    <input id="listing-${option.id}" name="listing_method_${provider}" type="radio" value="${option.value}" 
                        ${checked ? 'checked' : ''} 
                        data-field="listingMethod"
                        class="h-4 w-4 border-gray-300 text-[#F15F22] focus:ring-[#F15F22]">
                    <label for="listing-${option.id}" class="ml-2 text-sm text-gray-300">${escapeHtml(option.label)}</label>
                </div>
            `;
        });
        formHTML += '</div></div>';
    }

    // Model selection
    formHTML += `
        <div>
            <label class="block text-sm font-medium text-gray-300 mb-1">Model</label>
            <div class="flex items-center gap-2">
                <select data-field="model" class="flex-1 p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
                    <option value="">-- Select a model --</option>
                    ${providerData.model ? `<option value="${escapeHtml(providerData.model)}" selected>${escapeHtml(providerData.model)}</option>` : ''}
                </select>
                <button type="button" data-action="refresh-models" data-provider="${provider}" 
                    class="p-2 bg-gray-600 hover:bg-gray-500 rounded-md transition-colors">
                    <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0011.667 0l3.181-3.183m-4.991-2.691L7.985 5.356m0 0v4.992m0 0h4.992m0 0l3.181-3.183a8.25 8.25 0 0111.667 0l3.181 3.183" />
                    </svg>
                </button>
            </div>
        </div>
    `;

    // Save button
    formHTML += `
        <button type="button" data-action="save-llm-provider" data-provider="${provider}" 
            class="w-full px-4 py-2 bg-[#F15F22] hover:bg-[#D9501A] rounded-md transition-colors text-white font-medium">
            Save Configuration
        </button>
    `;

    formHTML += '</div>';
    container.innerHTML = formHTML;

    // Attach event listeners
    container.querySelector('[data-action="refresh-models"]').addEventListener('click', () => refreshModels(provider));
    container.querySelector('[data-action="save-llm-provider"]').addEventListener('click', () => saveLLMProvider(provider));
}

// ============================================================================
// ACTION HANDLERS
// ============================================================================
export function showMCPServerModal(serverId = null) {
    const server = serverId ? configState.mcpServers.find(s => s.id === serverId) : null;
    const isEdit = !!server;

    const modalHTML = `
        <div id="mcp-server-modal" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div class="glass-panel rounded-xl p-6 max-w-md w-full mx-4">
                <h3 class="text-xl font-bold text-white mb-4">${isEdit ? 'Edit' : 'Add'} MCP Server</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">Server Name</label>
                        <input type="text" id="mcp-modal-name" value="${server ? escapeHtml(server.name) : ''}" 
                            placeholder="e.g., Production DB Server" 
                            class="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">Host</label>
                        <input type="text" id="mcp-modal-host" value="${server ? escapeHtml(server.host) : ''}" 
                            placeholder="e.g., localhost" 
                            class="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">Port</label>
                        <input type="text" id="mcp-modal-port" value="${server ? escapeHtml(server.port) : ''}" 
                            placeholder="e.g., 8000" 
                            class="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">Path</label>
                        <input type="text" id="mcp-modal-path" value="${server ? escapeHtml(server.path) : ''}" 
                            placeholder="e.g., /sse" 
                            class="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
                    </div>
                    <div class="flex gap-3 pt-4">
                        <button id="mcp-modal-cancel" class="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-md transition-colors text-white">
                            Cancel
                        </button>
                        <button id="mcp-modal-save" class="flex-1 px-4 py-2 bg-[#F15F22] hover:bg-[#D9501A] rounded-md transition-colors text-white font-medium">
                            ${isEdit ? 'Update' : 'Add'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    const modal = document.getElementById('mcp-server-modal');
    modal.querySelector('#mcp-modal-cancel').addEventListener('click', () => modal.remove());
    modal.querySelector('#mcp-modal-save').addEventListener('click', async () => {
        const data = {
            name: modal.querySelector('#mcp-modal-name').value.trim(),
            host: modal.querySelector('#mcp-modal-host').value.trim(),
            port: modal.querySelector('#mcp-modal-port').value.trim(),
            path: modal.querySelector('#mcp-modal-path').value.trim(),
        };

        if (!data.name || !data.host || !data.port || !data.path) {
            showNotification('error', 'All fields are required');
            return;
        }

        try {
            let success;
            if (isEdit) {
                success = await configState.updateMCPServer(serverId, data);
            } else {
                const result = await configState.addMCPServer(data);
                success = result !== null && result !== undefined;
            }

            if (success) {
                renderMCPServers();
                modal.remove();
                showNotification('success', `MCP server ${isEdit ? 'updated' : 'added'} successfully`);
            }
        } catch (error) {
            showNotification('error', `Failed to ${isEdit ? 'update' : 'add'} MCP server: ${error.message}`);
        }
    });
}

async function testMCPConnection(serverId) {
    const server = configState.mcpServers.find(s => s.id === serverId);
    if (!server) return;

    const btn = document.querySelector(`[data-action="test-mcp"][data-server-id="${serverId}"]`);
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Testing...';
    }

    try {
        const response = await fetch('/test-mcp-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: server.name,
                host: server.host,
                port: server.port,
                path: server.path
            })
        });

        const result = await response.json();

        server.testStatus = result.status;
        server.testMessage = result.message;
        configState.saveMCPServers();
        renderMCPServers();

        showNotification(result.status, result.message);
    } catch (error) {
        showNotification('error', `Test failed: ${error.message}`);
        server.testStatus = 'error';
        server.testMessage = error.message;
        configState.saveMCPServers();
        renderMCPServers();
    }
}

async function refreshModels(provider) {
    const container = document.getElementById(`llm-${provider}-form-container`);
    if (!container) return;

    const btn = container.querySelector('[data-action="refresh-models"]');
    const select = container.querySelector('[data-field="model"]');
    
    // Collect current form data
    const credentials = {};
    container.querySelectorAll('[data-field]').forEach(input => {
        const field = input.dataset.field;
        if (field && field !== 'model') {
            credentials[field] = input.value;
        }
    });

    btn.disabled = true;
    btn.innerHTML = '<svg class="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';

    try {
        const response = await fetch('/models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, ...credentials })
        });

        const data = await response.json();

        if (data.models && data.models.length > 0) {
            // Find first certified model for auto-selection
            const certifiedModels = data.models.filter(model => {
                return typeof model === 'string' || model.certified !== false;
            });
            const firstCertifiedModel = certifiedModels.length > 0 
                ? (typeof certifiedModels[0] === 'string' ? certifiedModels[0] : certifiedModels[0].name)
                : null;
            
            select.innerHTML = '<option value="">-- Select a model --</option>' + 
                data.models.map(model => {
                    const modelName = typeof model === 'string' ? model : model.name;
                    const certified = typeof model === 'object' ? model.certified : true;
                    const label = certified ? modelName : `${modelName} (support evaluated)`;
                    const selected = modelName === firstCertifiedModel ? 'selected' : '';
                    return `<option value="${escapeHtml(modelName)}" ${!certified ? 'disabled' : ''} ${selected}>${escapeHtml(label)}</option>`;
                }).join('');
            
            // Update the provider's model in state if auto-selected
            if (firstCertifiedModel) {
                const currentProvider = configState.llmProviders[provider] || {};
                currentProvider.model = firstCertifiedModel;
            }
            
            showNotification('success', `Found ${data.models.length} models${firstCertifiedModel ? ` - selected ${firstCertifiedModel}` : ''}`);
        } else {
            showNotification('warning', 'No models found');
        }
    } catch (error) {
        showNotification('error', `Failed to fetch models: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0011.667 0l3.181-3.183m-4.991-2.691L7.985 5.356m0 0v4.992m0 0h4.992m0 0l3.181-3.183a8.25 8.25 0 0111.667 0l3.181 3.183" /></svg>';
    }
}

function saveLLMProvider(provider) {
    const container = document.getElementById(`llm-${provider}-form-container`);
    if (!container) return;

    const credentials = {};
    let model = null;
    let listingMethod = null;

    container.querySelectorAll('[data-field]').forEach(input => {
        const field = input.dataset.field;
        if (field === 'model') {
            model = input.value;
        } else if (field === 'listingMethod' && input.checked) {
            listingMethod = input.value;
        } else if (field) {
            credentials[field] = input.value;
        }
    });

    if (!model) {
        showNotification('error', 'Please select a model');
        return;
    }

    configState.updateLLMProvider(provider, { credentials, model, listingMethod });
    renderLLMProviders();
    updateReconnectButton(); // Update button state after saving
    showNotification('success', `${LLM_PROVIDER_TEMPLATES[provider].name} configuration saved`);
}

function updateProfilesTab() {
    const profilesTab = document.querySelector('.config-tab[data-tab="profiles-tab"]');
    if (!profilesTab) return;

    const mcpConfigured = configState.mcpServers.length > 0;
    const llmConfigured = Object.values(configState.llmProviders).some(p => p.configured);

    if (mcpConfigured && llmConfigured) {
        profilesTab.disabled = false;
        profilesTab.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        profilesTab.disabled = true;
        profilesTab.classList.add('opacity-50', 'cursor-not-allowed');
    }
}

export function updateReconnectButton() {
    const btn = document.getElementById('reconnect-and-load-btn');
    if (!btn) return;

    const canReconnect = configState.canReconnect();
    btn.disabled = !canReconnect;
    updateProfilesTab();
}

export async function reconnectAndLoad() {
    const defaultProfile = configState.profiles.find(p => p.id === configState.defaultProfileId);

    if (!defaultProfile) {
        showNotification('error', 'Please set a default profile before connecting.');
        return;
    }

    // Set the active MCP and LLM based on the default profile
    await configState.setActiveMCP(defaultProfile.mcpServerId);
    configState.setActiveLLM(defaultProfile.llmProvider);

    const mcpServer = configState.getActiveMCPServer();
    const llmProvider = configState.getActiveLLMProvider();

    // ... rest of the function
    
    // Validate that both MCP server and LLM provider are configured
    if (!mcpServer) {
        showNotification('error', 'Please configure and select an MCP Server first (go to MCP Servers tab)');
        return;
    }

    if (!llmProvider) {
        showNotification('error', 'Please configure and select an LLM Provider first (go to LLM Providers tab)');
        return;
    }

    // Additional validation for required fields
    if (!mcpServer.host || !mcpServer.port) {
        showNotification('error', 'MCP Server configuration is incomplete (missing host or port)');
        return;
    }

    if (!llmProvider.credentials || Object.keys(llmProvider.credentials).length === 0) {
        showNotification('error', 'LLM Provider credentials are missing or incomplete');
        return;
    }

    const btn = document.getElementById('reconnect-and-load-btn');
    const btnText = document.getElementById('reconnect-button-text');
    const spinner = document.getElementById('reconnect-loading-spinner');
    const statusDiv = document.getElementById('reconnect-status');

    btn.disabled = true;
    btnText.textContent = 'Connecting...';
    spinner.classList.remove('hidden');
    spinner.classList.add('animate-spin');
    statusDiv.innerHTML = '<span class="text-gray-400">Initializing connection...</span>';

    try {
        const configData = {
            provider: llmProvider.provider,
            model: llmProvider.model,
            credentials: llmProvider.credentials,
            server_name: mcpServer.name,
            server_id: mcpServer.id, // Add unique server ID
            host: mcpServer.host,
            port: mcpServer.port,
            path: mcpServer.path,
            listing_method: llmProvider.listingMethod || 'foundation_models',
            tts_credentials_json: document.getElementById('tts-credentials-json')?.value || '',
            charting_intensity: document.getElementById('charting-intensity')?.value || 'none'
        };


        const response = await fetch('/configure', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });

        const result = await response.json();

        if (result.status === 'success') {
            statusDiv.innerHTML = '<span class="text-green-400">✓ ' + escapeHtml(result.message) + '</span>';
            showNotification('success', result.message);
            
            // Update status indicators
            DOM.mcpStatusDot.classList.remove('disconnected');
            DOM.mcpStatusDot.classList.add('connected');
            DOM.llmStatusDot.classList.remove('disconnected', 'busy');
            DOM.llmStatusDot.classList.add('idle');
            DOM.contextStatusDot.classList.remove('disconnected');
            DOM.contextStatusDot.classList.add('idle');
            
            // Update RAG indicator - check if RAG is active after configuration
            if (DOM.ragStatusDot) {
                const status = await API.checkServerStatus();
                if (status.rag_active) {
                    DOM.ragStatusDot.classList.remove('disconnected');
                    DOM.ragStatusDot.classList.add('connected');
                } else {
                    DOM.ragStatusDot.classList.remove('connected');
                    DOM.ragStatusDot.classList.add('disconnected');
                }
            }
            
            // Update state with current provider/model
            state.currentProvider = configData.provider;
            state.currentModel = configData.model;
            safeSetItem('lastSelectedProvider', configData.provider);
            
            // Update status bar with provider and model info
            UI.updateStatusPromptName(configData.provider, configData.model);
            
            // Enable panel toggle buttons after configuration
            if (DOM.toggleHistoryButton) {
                DOM.toggleHistoryButton.classList.remove('btn-disabled');
                DOM.toggleHistoryButton.style.opacity = '1';
                DOM.toggleHistoryButton.style.cursor = 'pointer';
                DOM.toggleHistoryButton.style.pointerEvents = 'auto';
                if (DOM.historyExpandIcon) DOM.historyExpandIcon.classList.remove('hidden');
                if (DOM.historyCollapseIcon) DOM.historyCollapseIcon.classList.add('hidden');
            }
            if (DOM.toggleStatusButton) {
                DOM.toggleStatusButton.classList.remove('btn-disabled');
                DOM.toggleStatusButton.style.opacity = '1';
                DOM.toggleStatusButton.style.cursor = 'pointer';
                DOM.toggleStatusButton.style.pointerEvents = 'auto';
                if (DOM.statusExpandIcon) DOM.statusExpandIcon.classList.remove('hidden');
                if (DOM.statusCollapseIcon) DOM.statusCollapseIcon.classList.add('hidden');
            }
            if (DOM.toggleHeaderButton) {
                DOM.toggleHeaderButton.classList.remove('btn-disabled');
                DOM.toggleHeaderButton.style.opacity = '1';
                DOM.toggleHeaderButton.style.cursor = 'pointer';
                DOM.toggleHeaderButton.style.pointerEvents = 'auto';
                if (DOM.headerExpandIcon) DOM.headerExpandIcon.classList.remove('hidden');
                if (DOM.headerCollapseIcon) DOM.headerCollapseIcon.classList.add('hidden');
            }
            
            // Show conversation header after successful configuration
            const conversationHeader = document.getElementById('conversation-header');
            if (conversationHeader) {
                conversationHeader.classList.remove('hidden');
            } else {
                console.error('[DEBUG] reconnectAndLoad - Conversation header element not found!');
            }
            
            // Show panel toggle buttons after configuration
            const topButtonsContainer = document.getElementById('top-buttons-container');
            if (topButtonsContainer) {
                topButtonsContainer.classList.remove('hidden');
            }
            
            // Load MCP resources (tools, prompts, resources)
            await Promise.all([
                handleLoadResources('tools'),
                handleLoadResources('prompts'),
                handleLoadResources('resources')
            ]);
            
            // Enable chat input
            DOM.chatModalButton.disabled = false;
            DOM.userInput.placeholder = "Ask about databases, tables, users...";
            UI.setExecutionState(false);
            
            // Load existing session or create new one, then switch to conversation view
            setTimeout(async () => {
                try {
                    const currentSessionId = state.currentSessionId;
                    const sessions = await API.loadAllSessions();
                    
                    // Populate session list UI
                    DOM.sessionList.innerHTML = '';
                    
                    if (sessions && Array.isArray(sessions) && sessions.length > 0) {
                        // Populate session list dropdown/sidebar
                        const sessionToLoad = sessions.find(s => s.id === currentSessionId) ? currentSessionId : sessions[0].id;
                        
                        sessions.forEach((session) => {
                            const isActive = session.id === sessionToLoad;
                            const sessionItem = UI.addSessionToList(session, isActive);
                            DOM.sessionList.appendChild(sessionItem);
                        });
                        
                        // Load the selected session
                        await handleLoadSession(sessionToLoad);
                    } else {
                        // No sessions exist, create a new one
                        await handleStartNewSession();
                    }
                    
                    // Hide welcome screen and show chat interface
                    if (window.hideWelcomeScreen) {
                        window.hideWelcomeScreen();
                    }
                    
                    handleViewSwitch('conversation-view');
                } catch (sessionError) {
                    console.error('Failed to load/create session:', sessionError);
                    showNotification('warning', 'Configuration successful, but failed to initialize session. Please create one manually.');
                    handleViewSwitch('conversation-view');
                }
            }, 1000); // Small delay to allow user to see success message
        } else {
            statusDiv.innerHTML = '<span class="text-red-400">✗ ' + escapeHtml(result.message) + '</span>';
            showNotification('error', result.message);
        }
    } catch (error) {
        statusDiv.innerHTML = '<span class="text-red-400">✗ Connection failed</span>';
        showNotification('error', `Connection failed: ${error.message}`);
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Save & Connect';
        spinner.classList.remove('animate-spin');
        spinner.classList.add('hidden');
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize configuration tabs
 */
function initializeConfigTabs() {
    const tabs = document.querySelectorAll('.config-tab');
    const tabContents = document.querySelectorAll('.config-tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTabId = tab.getAttribute('data-tab');
            
            // Update tab buttons
            tabs.forEach(t => {
                t.classList.remove('active', 'border-[#F15F22]', 'text-white');
                t.classList.add('text-gray-400', 'border-transparent');
            });
            tab.classList.add('active', 'border-[#F15F22]', 'text-white');
            tab.classList.remove('text-gray-400', 'border-transparent');
            
            // Update tab content
            tabContents.forEach(content => {
                if (content.id === targetTabId) {
                    content.classList.remove('hidden');
                    content.classList.add('active');
                } else {
                    content.classList.add('hidden');
                    content.classList.remove('active');
                }
            });
        });
    });
}

// ============================================================================
// UI RENDERING - PROFILES
// ============================================================================

function renderProfiles() {
    const container = document.getElementById('profiles-container');
    if (!container) return;

    if (configState.profiles.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-8">
                <p>No profiles configured. Click "Add Profile" to get started.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = configState.profiles.map(profile => {
        const isDefault = profile.id === configState.defaultProfileId;
        const isActiveForConsumption = configState.activeForConsumptionProfileIds.includes(profile.id);

        return `
        <div class="bg-white/5 border ${isDefault ? 'border-[#F15F22]' : 'border-white/10'} rounded-lg p-4" data-profile-id="${profile.id}">
            <div class="flex items-start justify-between">
                <div class="flex items-start gap-3 flex-1">
                    <div class="flex flex-col items-center gap-2">
                        <button title="Set as Default" data-action="set-default-profile" data-profile-id="${profile.id}" class="p-1 rounded-full ${isDefault ? 'text-yellow-400' : 'text-gray-500 hover:text-yellow-400'}">
                            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M10 15l-5.878 3.09 1.123-6.545L.489 6.91l6.572-.955L10 0l2.939 5.955 6.572.955-4.756 4.635 1.123 6.545z"/></svg>
                        </button>
                        <div class="flex items-center" title="Active for Consumption">
                           <label class="relative inline-flex items-center cursor-pointer">
                                <input type="checkbox" data-action="toggle-active-consumption" data-profile-id="${profile.id}" ${isActiveForConsumption ? 'checked' : ''} class="sr-only peer">
                                <div class="w-11 h-6 bg-gray-800/50 border border-gray-500 rounded-full peer peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-600 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teradata-orange"></div>
                            </label>
                        </div>
                    </div>
                    <div class="flex-1">
                        <h4 class="font-semibold text-white mb-1">@${escapeHtml(profile.tag)}</h4>
                        <p class="text-sm text-gray-400 mb-3">${escapeHtml(profile.description)}</p>
                        <div class="text-sm text-gray-400 space-y-1">
                            <p><span class="font-medium">LLM:</span> ${escapeHtml(profile.llmProvider)} / ${escapeHtml(configState.llmProviders[profile.llmProvider]?.model || 'N/A')}</p>
                            <p><span class="font-medium">MCP:</span> ${escapeHtml(configState.mcpServers.find(s => s.id === profile.mcpServerId)?.name || 'Unknown')}</p>
                        </div>
                        <div class="mt-2 text-xs" id="test-results-${profile.id}"></div>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <button type="button" data-action="test-profile" data-profile-id="${profile.id}" 
                        class="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 rounded transition-colors text-white">
                        Test
                    </button>
                    <button type="button" data-action="edit-profile" data-profile-id="${profile.id}" 
                        class="px-3 py-1 text-sm bg-gray-600 hover:bg-gray-700 rounded transition-colors text-white">
                        Edit
                    </button>
                    <button type="button" data-action="delete-profile" data-profile-id="${profile.id}" 
                        class="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 rounded transition-colors text-white">
                        Delete
                    </button>
                </div>
            </div>
        </div>
    `}).join('');

    attachProfileEventListeners();
}

function attachProfileEventListeners() {
    // Set Default Profile button
    document.querySelectorAll('[data-action="set-default-profile"]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const profileId = e.currentTarget.dataset.profileId;
            await configState.setDefaultProfile(profileId);
            renderProfiles();
        });
    });

    // Toggle Active for Consumption checkbox
    document.querySelectorAll('[data-action="toggle-active-consumption"]').forEach(checkbox => {
        checkbox.addEventListener('change', async (e) => {
            const profileId = e.target.dataset.profileId;
            const isChecked = e.target.checked;
            let activeIds = configState.activeForConsumptionProfileIds;

            if (isChecked) {
                if (!activeIds.includes(profileId)) {
                    activeIds.push(profileId);
                }
            } else {
                activeIds = activeIds.filter(id => id !== profileId);
            }
            await configState.setActiveForConsumptionProfiles(activeIds);
            renderProfiles();
        });
    });
    
    // Test Profile button
    document.querySelectorAll('[data-action="test-profile"]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const profileId = e.target.dataset.profileId;
            const resultsContainer = document.getElementById(`test-results-${profileId}`);
            resultsContainer.innerHTML = `<span class="text-yellow-400">Testing...</span>`;
            try {
                const result = await API.testProfile(profileId);
                let html = '';
                const all_successful = Object.values(result.results).every(r => r.status === 'success');
                
                for (const [key, value] of Object.entries(result.results)) {
                    const statusClass = value.status === 'success' ? 'text-green-400' : 'text-red-400';
                    html += `<p class="${statusClass}">${value.message}</p>`;
                }
                resultsContainer.innerHTML = html;

                // Update checkbox
                let activeIds = [...configState.activeForConsumptionProfileIds];
                if (all_successful) {
                    if (!activeIds.includes(profileId)) {
                        activeIds.push(profileId);
                    }
                } else {
                    activeIds = activeIds.filter(id => id !== profileId);
                }
                await configState.setActiveForConsumptionProfiles(activeIds);

                const checkbox = document.querySelector(`input[data-action="toggle-active-consumption"][data-profile-id="${profileId}"]`);
                if (checkbox) {
                    checkbox.checked = all_successful;
                }

            } catch (error) {
                resultsContainer.innerHTML = `<span class="text-red-400">${error.message}</span>`;
                // Also uncheck on API error
                let activeIds = configState.activeForConsumptionProfileIds.filter(id => id !== profileId);
                await configState.setActiveForConsumptionProfiles(activeIds);
                const checkbox = document.querySelector(`input[data-action="toggle-active-consumption"][data-profile-id="${profileId}"]`);
                if (checkbox) {
                    checkbox.checked = false;
                }
            }
        });
    });

    // Edit Profile button
    document.querySelectorAll('[data-action="edit-profile"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const profileId = e.target.dataset.profileId;
            showProfileModal(profileId);
        });
    });

    // Delete Profile button
    document.querySelectorAll('[data-action="delete-profile"]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const profileId = e.target.dataset.profileId;
            const profile = configState.profiles.find(p => p.id === profileId);
            const profileName = profile ? profile.name : 'this profile';
            
            if (confirm(`Are you sure you want to delete profile "${profileName}"?`)) {
                await configState.removeProfile(profileId);
                renderProfiles();
                showNotification('success', 'Profile deleted successfully');
            }
        });
    });
}

async function showProfileModal(profileId = null) {
    const profile = profileId ? configState.profiles.find(p => p.id === profileId) : null;
    const isEdit = !!profile;

    const modal = document.getElementById('profile-modal');
    if (!modal) return;

    modal.querySelector('#profile-modal-title').textContent = isEdit ? 'Edit Profile' : 'Add Profile';

    // Populate LLM providers
    const llmSelect = modal.querySelector('#profile-modal-llm-provider');
    llmSelect.innerHTML = Object.keys(configState.llmProviders)
        .filter(key => configState.llmProviders[key].configured)
        .map(key => `<option value="${key}" ${profile?.llmProvider === key ? 'selected' : ''}>${LLM_PROVIDER_TEMPLATES[key].name}</option>`)
        .join('');

    // Populate MCP servers
    const mcpSelect = modal.querySelector('#profile-modal-mcp-server');
    mcpSelect.innerHTML = configState.mcpServers
        .map(server => `<option value="${server.id}" ${profile?.mcpServerId === server.id ? 'selected' : ''}>${escapeHtml(server.name)}</option>`)
        .join('');

    const toolsContainer = modal.querySelector('#profile-modal-tools');
    const promptsContainer = modal.querySelector('#profile-modal-prompts');
    let allTools = [];
    let allPrompts = [];

    async function populateResources(mcpServerId) {
        const server = configState.mcpServers.find(s => s.id === mcpServerId);
        if (!server) {
            toolsContainer.innerHTML = '<span class="text-gray-400">Select an MCP server.</span>';
            promptsContainer.innerHTML = '<span class="text-gray-400">Select an MCP server.</span>';
            return;
        }

        toolsContainer.innerHTML = '<span class="text-gray-400">Loading...</span>';
        promptsContainer.innerHTML = '<span class="text-gray-400">Loading...</span>';

        try {
            const resources = await API.fetchResourcesForServer(server);
            allTools = Object.values(resources.tools || {}).flat().map(t => t.name);
            allPrompts = Object.values(resources.prompts || {}).flat().map(p => p.name);

            toolsContainer.innerHTML = allTools.map(tool => `
                <label class="flex items-center gap-2 text-sm text-gray-300">
                    <input type="checkbox" value="${escapeHtml(tool)}" ${profile?.tools?.includes(tool) || profile?.tools?.includes('*') || !profile ? 'checked' : ''}>
                    ${escapeHtml(tool)}
                </label>
            `).join('') || '<span class="text-gray-400">No tools found.</span>';

            promptsContainer.innerHTML = allPrompts.map(prompt => `
                <label class="flex items-center gap-2 text-sm text-gray-300">
                    <input type="checkbox" value="${escapeHtml(prompt)}" ${profile?.prompts?.includes(prompt) || profile?.prompts?.includes('*') || !profile ? 'checked' : ''}>
                    ${escapeHtml(prompt)}
                </label>
            `).join('') || '<span class="text-gray-400">No prompts found.</span>';
        } catch (error) {
            toolsContainer.innerHTML = `<span class="text-red-400">Error: ${error.message}</span>`;
            promptsContainer.innerHTML = `<span class="text-red-400">Error: ${error.message}</span>`;
        }
    }
    
    mcpSelect.onchange = () => populateResources(mcpSelect.value);

    // Initial population
    const initialMcpId = profile ? profile.mcpServerId : (configState.mcpServers[0]?.id || null);
    if (initialMcpId) {
        populateResources(initialMcpId);
    } else {
        toolsContainer.innerHTML = '<span class="text-gray-400">No MCP servers configured.</span>';
        promptsContainer.innerHTML = '<span class="text-gray-400">No MCP servers configured.</span>';
    }


    // Populate RAG collections
    const ragContainer = modal.querySelector('#profile-modal-rag-collections');
    const autocompleteContainer = modal.querySelector('#profile-modal-autocomplete-collections');
    
    const { collections: ragCollections } = await API.getRagCollections();
    
    ragContainer.innerHTML = ragCollections.map(coll => `
        <label class="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" value="${coll.id}" ${profile?.ragCollections?.includes(coll.id) || profile?.ragCollections?.includes('*') || !profile ? 'checked' : ''}>
            ${escapeHtml(coll.name)}
        </label>
    `).join('') || '<span class="text-gray-400">No RAG collections found.</span>';

    autocompleteContainer.innerHTML = ragCollections.map(coll => `
        <label class="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" value="${coll.id}" ${profile?.autocompleteCollections?.includes(coll.id) || profile?.autocompleteCollections?.includes('*') || !profile ? 'checked' : ''}>
            ${escapeHtml(coll.name)}
        </label>
    `).join('') || '<span class="text-gray-400">No RAG collections found.</span>';

    // Set profile tag and description
    modal.querySelector('#profile-modal-tag').value = profile ? profile.tag : '';
    modal.querySelector('#profile-modal-description').value = profile ? profile.description : '';

    // Show the modal
    modal.classList.remove('hidden');

    // Attach event listeners for save/cancel
    modal.querySelector('#profile-modal-cancel').onclick = () => modal.classList.add('hidden');
    modal.querySelector('#profile-modal-save').onclick = async () => {
        const tag = modal.querySelector('#profile-modal-tag').value.trim();
        const description = modal.querySelector('#profile-modal-description').value.trim();

        if (!tag) {
            showNotification('error', 'Profile tag is required');
            return;
        }
        
        const selectedTools = Array.from(toolsContainer.querySelectorAll('input:checked')).map(cb => cb.value);
        const selectedPrompts = Array.from(promptsContainer.querySelectorAll('input:checked')).map(cb => cb.value);
        const selectedRag = Array.from(ragContainer.querySelectorAll('input:checked')).map(cb => parseInt(cb.value));
        const selectedAutocomplete = Array.from(autocompleteContainer.querySelectorAll('input:checked')).map(cb => parseInt(cb.value));

        const profileData = {
            id: profile ? profile.id : `profile-${generateId()}`,
            tag,
            description,
            llmProvider: llmSelect.value,
            mcpServerId: mcpSelect.value,
            tools: selectedTools.length === allTools.length ? ['*'] : selectedTools,
            prompts: selectedPrompts.length === allPrompts.length ? ['*'] : selectedPrompts,
            ragCollections: selectedRag.length === ragCollections.length ? ['*'] : selectedRag,
            autocompleteCollections: selectedAutocomplete.length === ragCollections.length ? ['*'] : selectedAutocomplete,
        };

        try {
            if (isEdit) {
                await configState.updateProfile(profileId, profileData);
            } else {
                await configState.addProfile(profileData);
            }

            renderProfiles();
            modal.classList.add('hidden');
            showNotification('success', `Profile ${isEdit ? 'updated' : 'added'} successfully`);
        } catch (error) {
            showNotification('error', error.message);
        }
    };
}


export async function initializeConfigurationUI() {
    // Initialize tabs
    initializeConfigTabs();
    
    // Load MCP servers from backend first
    await configState.initialize();
    
    renderMCPServers();
    renderLLMProviders();
    renderProfiles();
    updateReconnectButton();

    // Add MCP server button
    const addMCPBtn = document.getElementById('add-mcp-server-btn');
    if (addMCPBtn) {
        addMCPBtn.addEventListener('click', () => showMCPServerModal());
    }

    // Add Profile button
    const addProfileBtn = document.getElementById('add-profile-btn');
    if (addProfileBtn) {
        addProfileBtn.addEventListener('click', () => showProfileModal());
    }

    // Test All Profiles button
    const testAllProfilesBtn = document.getElementById('test-all-profiles-btn');
    if (testAllProfilesBtn) {
        testAllProfilesBtn.addEventListener('click', async () => {
            let activeIds = [...configState.activeForConsumptionProfileIds];
            for (const profile of configState.profiles) {
                const profileId = profile.id;
                const resultsContainer = document.getElementById(`test-results-${profileId}`);
                if (resultsContainer) {
                    resultsContainer.innerHTML = `<span class="text-yellow-400">Testing...</span>`;
                    try {
                        const result = await API.testProfile(profileId);
                        let html = '';
                        const all_successful = Object.values(result.results).every(r => r.status === 'success');

                        for (const [key, value] of Object.entries(result.results)) {
                            const statusClass = value.status === 'success' ? 'text-green-400' : 'text-red-400';
                            html += `<p class="${statusClass}">${value.message}</p>`;
                        }
                        resultsContainer.innerHTML = html;

                        // Update activeIds list based on result
                        if (all_successful) {
                            if (!activeIds.includes(profileId)) {
                                activeIds.push(profileId);
                            }
                        } else {
                            activeIds = activeIds.filter(id => id !== profileId);
                        }
                        
                        // Manually update the toggle switch state
                        const checkbox = document.querySelector(`input[data-action="toggle-active-consumption"][data-profile-id="${profileId}"]`);
                        if (checkbox) {
                            checkbox.checked = all_successful;
                        }

                    } catch (error) {
                        resultsContainer.innerHTML = `<span class="text-red-400">${error.message}</span>`;
                        // Also uncheck on API error
                        activeIds = activeIds.filter(id => id !== profileId);
                        const checkbox = document.querySelector(`input[data-action="toggle-active-consumption"][data-profile-id="${profileId}"]`);
                        if (checkbox) {
                            checkbox.checked = false;
                        }
                    }
                }
            }
            // Save the final state of all active profiles once at the end
            await configState.setActiveForConsumptionProfiles(activeIds);
        });
    }

    // Reconnect button
    const reconnectBtn = document.getElementById('reconnect-and-load-btn');
    if (reconnectBtn) {
        reconnectBtn.addEventListener('click', reconnectAndLoad);
    }

}
