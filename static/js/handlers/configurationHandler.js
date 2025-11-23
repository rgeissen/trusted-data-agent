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

// Make showNotification globally available for use throughout the application
window.showNotification = showNotification;

function generateId() {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Load credentials from localStorage for a given provider
 * @param {string} provider - The LLM provider name
 * @returns {object} - The credentials object
 */
function loadCredentialsFromLocalStorage(provider) {
    const storageKey = `${provider.toLowerCase()}ApiKey`;
    
    // Special case for Ollama
    if (provider === 'Ollama') {
        const host = localStorage.getItem('ollamaHost');
        return host ? { ollama_host: host } : {};
    }
    
    const stored = localStorage.getItem(storageKey);
    if (!stored) return {};
    
    try {
        // Try parsing as JSON (for multi-field providers)
        return JSON.parse(stored);
    } catch {
        // If not JSON, assume it's a simple apiKey string
        return { apiKey: stored };
    }
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
// MCP CLASSIFICATION SETTING
// ============================================================================

/**
 * Load the MCP classification setting from the backend
 */
async function loadClassificationSetting() {
    try {
        const response = await fetch('/api/v1/config/classification', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            const result = await response.json();
            const checkbox = document.getElementById('enable-mcp-classification');
            if (checkbox) {
                checkbox.checked = result.enable_mcp_classification;
            }
        }
    } catch (error) {
        console.error('Failed to load classification setting:', error);
    }
}

/**
 * Save the MCP classification setting to the backend
 */
async function saveClassificationSetting(enabled) {
    try {
        const response = await fetch('/api/v1/config/classification', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enable_mcp_classification: enabled })
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification('success', result.message);
        } else {
            const error = await response.json();
            showNotification('error', error.message || 'Failed to save classification setting');
        }
    } catch (error) {
        console.error('Failed to save classification setting:', error);
        showNotification('error', 'Failed to save classification setting');
    }
}

// ============================================================================
// STATE MANAGEMENT
// ============================================================================
class ConfigurationState {
    constructor() {
        this.mcpServers = [];
        this.llmConfigurations = [];
        this.activeLLM = null;
        this.profiles = [];
        this.activeProfileId = null;
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return;
        await this.loadMCPServers();
        await this.loadLLMConfigurations();
        await this.migrateLegacyLLMProviders();
        await this.loadProfiles();
        this.initialized = true;
    }

    /**
     * Migrate legacy localStorage LLM providers to backend configurations
     */
    async migrateLegacyLLMProviders() {
        try {
            // Check if there are any legacy providers in localStorage
            const legacyProvidersJSON = safeGetItem(STORAGE_KEYS.LLM_PROVIDERS);
            if (!legacyProvidersJSON) return; // Nothing to migrate

            const legacyProviders = JSON.parse(legacyProvidersJSON);
            const providerKeys = Object.keys(legacyProviders);
            
            if (providerKeys.length === 0) {
                // Clean up empty legacy data
                localStorage.removeItem(STORAGE_KEYS.LLM_PROVIDERS);
                localStorage.removeItem(STORAGE_KEYS.ACTIVE_LLM);
                return;
            }

            console.log('Migrating legacy LLM providers:', providerKeys);

            // Track migration results
            const migrationResults = [];

            // Migrate each provider to a new configuration
            for (const providerKey of providerKeys) {
                const legacyConfig = legacyProviders[providerKey];
                if (!legacyConfig || !legacyConfig.model) continue; // Skip incomplete configs

                const configData = {
                    name: `${providerKey} (Migrated)`,
                    provider: providerKey,
                    model: legacyConfig.model,
                    credentials: legacyConfig.credentials || {}
                };

                // Add listingMethod for Amazon if it exists
                if (providerKey === 'Amazon' && legacyConfig.listingMethod) {
                    configData.credentials.listingMethod = legacyConfig.listingMethod;
                }

                try {
                    const result = await this.addLLMConfiguration(configData);
                    if (result) {
                        migrationResults.push({ provider: providerKey, success: true, id: result.id });
                        console.log(`Migrated ${providerKey} configuration:`, result);
                    }
                } catch (error) {
                    console.error(`Failed to migrate ${providerKey}:`, error);
                    migrationResults.push({ provider: providerKey, success: false, error: error.message });
                }
            }

            // Note: We don't set an active LLM anymore since active state is now
            // determined by profiles. Users will need to update their profiles to
            // use the migrated configurations.

            // Clean up localStorage after successful migration
            localStorage.removeItem(STORAGE_KEYS.LLM_PROVIDERS);
            localStorage.removeItem(STORAGE_KEYS.ACTIVE_LLM);

            const successCount = migrationResults.filter(r => r.success).length;
            if (successCount > 0) {
                showNotification('success', `Migrated ${successCount} LLM configuration(s) to new system`);
            }
        } catch (error) {
            console.error('Error during LLM provider migration:', error);
            // Don't fail initialization if migration fails
        }
    }

    async loadProfiles() {
        try {
            const { profiles, default_profile_id, active_for_consumption_profile_ids } = await API.getProfiles();
            this.profiles = profiles || [];
            this.defaultProfileId = default_profile_id;
            this.activeForConsumptionProfileIds = active_for_consumption_profile_ids || [];
            
            // Initialize session header with default profile
            if (this.defaultProfileId && typeof window.updateSessionHeaderProfile === 'function') {
                const defaultProfile = this.profiles.find(p => p.id === this.defaultProfileId);
                if (defaultProfile) {
                    window.updateSessionHeaderProfile(defaultProfile, null);
                }
            }
            
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

    async copyProfile(profileId) {
        const profile = this.profiles.find(p => p.id === profileId);
        if (!profile) return null;
        
        // Create a copy with a new ID and modified name
        const newProfile = {
            ...profile,
            id: generateId(),
            name: `${profile.name} (Copy)`,
            tag: '' // Clear tag so user can generate/enter a new one
        };
        
        // Add the copied profile
        const response = await fetch('/api/v1/profiles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newProfile)
        });
        
        if (response.ok) {
            await this.loadProfiles();
            return newProfile;
        }
        return null;
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

    async loadLLMConfigurations() {
        try {
            const response = await fetch('/api/v1/llm/configurations');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.llmConfigurations = result.configurations || [];
                this.activeLLM = result.active_configuration_id;
                return this.llmConfigurations;
            }
        } catch (error) {
            console.error('Failed to load LLM configurations:', error);
            this.llmConfigurations = [];
        }
        return this.llmConfigurations;
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

    async setActiveLLM(configId) {
        try {
            const response = await fetch(`/api/v1/llm/configurations/${configId}/activate`, {
                method: 'POST'
            });
            
            if (response.ok) {
                this.activeLLM = configId;
                updateReconnectButton();
            }
        } catch (error) {
            console.error('Failed to set active LLM configuration:', error);
        }
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

    async addLLMConfiguration(configuration) {
        configuration.id = configuration.id || generateId();
        
        try {
            const headers = { 'Content-Type': 'application/json' };
            const authToken = localStorage.getItem('tda_auth_token');
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }
            
            const response = await fetch('/api/v1/llm/configurations', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(configuration)
            });
            
            if (response.ok) {
                const result = await response.json();
                await this.loadLLMConfigurations();
                return result.configuration; // Return the full configuration object with ID
            } else {
                const errorData = await response.json();
                console.error('Failed to add LLM configuration:', errorData);
                throw new Error(errorData.message || 'Failed to add LLM configuration');
            }
        } catch (error) {
            console.error('Failed to add LLM configuration:', error);
            throw error;
        }
    }

    async removeLLMConfiguration(configId) {
        try {
            const response = await fetch(`/api/v1/llm/configurations/${configId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.llmConfigurations = this.llmConfigurations.filter(c => c.id !== configId);
                if (this.activeLLM === configId) {
                    this.activeLLM = null;
                }
                return { success: true };
            } else {
                const errorData = await response.json();
                return { 
                    success: false, 
                    error: errorData.message || 'Failed to remove LLM configuration' 
                };
            }
        } catch (error) {
            console.error('Failed to remove LLM configuration:', error);
            return { 
                success: false, 
                error: error.message || 'Failed to remove LLM configuration' 
            };
        }
    }

    async updateLLMConfiguration(configId, updates) {
        try {
            const headers = { 'Content-Type': 'application/json' };
            const authToken = localStorage.getItem('tda_auth_token');
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }
            
            const response = await fetch(`/api/v1/llm/configurations/${configId}`, {
                method: 'PUT',
                headers: headers,
                body: JSON.stringify(updates)
            });
            
            if (response.ok) {
                await this.loadLLMConfigurations();
                return true;
            }
        } catch (error) {
            console.error('Failed to update LLM configuration:', error);
        }
        return false;
    }

    getActiveMCPServer() {
        return this.mcpServers.find(s => s.id === this.activeMCP);
    }

    getActiveLLMConfiguration() {
        return this.llmConfigurations.find(c => c.id === this.activeLLM);
    }

    canReconnect() {
        const mcpServer = this.getActiveMCPServer();
        const llmConfig = this.getActiveLLMConfiguration();
        return !!(mcpServer && llmConfig && llmConfig.model);
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

    // Determine which servers are used by profiles
    const defaultProfile = configState.profiles.find(p => p.id === configState.defaultProfileId);
    const activeProfiles = configState.profiles.filter(p => 
        configState.activeForConsumptionProfileIds.includes(p.id)
    );

    container.innerHTML = configState.mcpServers.map(server => {
        // Check if this server is used by default profile
        const isDefault = defaultProfile?.mcpServerId === server.id;
        
        // Check if this server is used by any active profile
        const isActive = activeProfiles.some(p => p.mcpServerId === server.id);
        
        // Build status badges
        let statusBadges = '';
        if (isDefault) {
            statusBadges += '<span class="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-blue-500 text-white rounded-full">Default</span>';
        }
        if (isActive) {
            statusBadges += '<span class="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-green-500 text-white rounded-full ml-2">Active</span>';
        }

        return `
            <div class="bg-gradient-to-br from-white/10 to-white/5 border-2 border-white/10 rounded-xl p-4 hover:border-white/20 transition-all duration-200" data-mcp-id="${server.id}">
                <div class="flex items-center justify-between gap-4">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            <h4 class="text-base font-bold text-white truncate">${escapeHtml(server.name)}</h4>
                            ${statusBadges}
                        </div>
                        <div class="text-sm text-gray-400">
                            <span class="font-medium text-gray-300">Host:</span> ${escapeHtml(server.host)}:${escapeHtml(server.port)} 
                            <span class="mx-2">•</span> 
                            <span class="font-medium text-gray-300">Path:</span> ${escapeHtml(server.path)}
                        </div>
                        ${server.testStatus ? `
                            <div class="mt-2 text-sm ${server.testStatus === 'success' ? 'text-green-400' : 'text-red-400'}">
                                ${escapeHtml(server.testMessage || '')}
                            </div>
                        ` : ''}
                    </div>
                    <div class="flex items-center gap-2 flex-shrink-0">
                        <button type="button" data-action="test-mcp" data-server-id="${server.id}" 
                            class="px-3 py-1.5 text-sm font-medium bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors text-white">
                            Test
                        </button>
                        <button type="button" data-action="edit-mcp" data-server-id="${server.id}" 
                            class="px-3 py-1.5 text-sm font-medium bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-white">
                            Edit
                        </button>
                        <button type="button" data-action="delete-mcp" data-server-id="${server.id}" 
                            class="px-3 py-1.5 text-sm font-medium bg-gray-700 hover:bg-red-600 rounded-lg transition-colors text-red-400 hover:text-white">
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    attachMCPEventListeners();
}

function attachMCPEventListeners() {

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
// UI RENDERING - LLM CONFIGURATIONS
// ============================================================================
export function renderLLMProviders() {
    const container = document.getElementById('llm-providers-container');
    if (!container) return;

    if (configState.llmConfigurations.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center text-gray-400 py-8">
                <p>No LLM configurations found. Click "Add Configuration" to get started.</p>
            </div>
        `;
        return;
    }

    // Determine which configurations are used by profiles
    const defaultProfile = configState.profiles.find(p => p.id === configState.defaultProfileId);
    const activeProfiles = configState.profiles.filter(p => 
        configState.activeForConsumptionProfileIds.includes(p.id)
    );

    container.innerHTML = configState.llmConfigurations.map(config => {
        // Check if this configuration is used by default profile
        const isDefault = defaultProfile?.llmConfigurationId === config.id;
        
        // Check if this configuration is used by any active profile
        const isActive = activeProfiles.some(p => p.llmConfigurationId === config.id);
        
        // Build status badges
        let statusBadges = '';
        if (isDefault) {
            statusBadges += '<span class="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-blue-500 text-white rounded-full">Default</span>';
        }
        if (isActive) {
            statusBadges += '<span class="inline-flex items-center px-2.5 py-0.5 text-xs font-medium bg-green-500 text-white rounded-full ml-2">Active</span>';
        }

        return `
            <div class="bg-gradient-to-br from-white/10 to-white/5 border-2 border-white/10 rounded-xl p-5 hover:border-white/20 transition-all duration-200" data-llm-config-id="${config.id}">
                <div class="flex flex-col gap-4">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-3">
                                <h4 class="text-lg font-bold text-white">${escapeHtml(config.name)}</h4>
                                ${statusBadges}
                            </div>
                            <div class="space-y-2">
                                <div class="flex items-center gap-2 text-sm">
                                    <span class="font-semibold text-gray-300">Provider:</span>
                                    <span class="text-gray-400">${escapeHtml(config.provider)}</span>
                                </div>
                                <div class="flex items-center gap-2 text-sm">
                                    <span class="font-semibold text-gray-300">Model:</span>
                                    <span class="text-gray-400">${escapeHtml(config.model)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 pt-2 border-t border-white/10">
                        <button type="button" data-action="edit-llm" data-config-id="${config.id}" 
                            class="flex-1 px-4 py-2 text-sm font-medium bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-white">
                            Edit
                        </button>
                        <button type="button" data-action="delete-llm" data-config-id="${config.id}" 
                            class="flex-1 px-4 py-2 text-sm font-medium bg-gray-700 hover:bg-red-600 rounded-lg transition-colors text-red-400 hover:text-white">
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    attachLLMEventListeners();
}

function attachLLMEventListeners() {
    // Edit LLM button
    document.querySelectorAll('[data-action="edit-llm"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const configId = e.target.dataset.configId;
            showLLMConfigurationModal(configId);
        });
    });

    // Delete LLM button
    document.querySelectorAll('[data-action="delete-llm"]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const configId = e.target.dataset.configId;
            const config = configState.llmConfigurations.find(c => c.id === configId);
            
            if (config && confirm(`Are you sure you want to delete "${config.name}"?`)) {
                const result = await configState.removeLLMConfiguration(configId);
                if (result.success) {
                    showNotification('success', 'LLM configuration deleted successfully');
                    renderLLMProviders();
                    updateReconnectButton();
                } else {
                    showNotification('error', result.error);
                }
            }
        });
    });
}

// Placeholder for LLM configuration modal (to be implemented)
export function showLLMConfigurationModal(configId = null) {
    const config = configId ? configState.llmConfigurations.find(c => c.id === configId) : null;
    const isEdit = !!config;
    const selectedProvider = config?.provider || 'Google';

    // Build provider options
    const providerOptions = Object.keys(LLM_PROVIDER_TEMPLATES)
        .map(key => `<option value="${key}" ${key === selectedProvider ? 'selected' : ''}>${LLM_PROVIDER_TEMPLATES[key].name}</option>`)
        .join('');

    const modalHTML = `
        <div id="llm-config-modal" class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
            <div class="glass-panel rounded-xl p-6 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
                <h3 class="text-xl font-bold text-white mb-4">${isEdit ? 'Edit' : 'Add'} LLM Configuration</h3>
                <div class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">Configuration Name</label>
                        <input type="text" id="llm-modal-name" value="${config ? escapeHtml(config.name) : ''}" 
                            placeholder="e.g., Production GPT-4" 
                            class="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-300 mb-1">Provider</label>
                        <select id="llm-modal-provider" class="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none" ${isEdit ? 'disabled' : ''}>
                            ${providerOptions}
                        </select>
                        ${isEdit ? '<p class="text-xs text-gray-400 mt-1">Provider cannot be changed after creation</p>' : ''}
                    </div>
                    <div id="llm-modal-credentials-container">
                        <!-- Credentials fields will be inserted here -->
                    </div>
                    <div id="llm-modal-model-container">
                        <label class="block text-sm font-medium text-gray-300 mb-1">Model</label>
                        <div class="flex items-center gap-2">
                            <select id="llm-modal-model" class="flex-1 min-w-0 p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
                                <option value="">-- Select a model --</option>
                                ${config?.model ? `<option value="${escapeHtml(config.model)}" selected>${escapeHtml(config.model)}</option>` : ''}
                            </select>
                            <button type="button" id="llm-modal-refresh-models" 
                                class="flex-shrink-0 p-2 bg-gray-600 hover:bg-gray-500 rounded-md transition-colors">
                                <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0011.667 0l3.181-3.183m-4.991-2.691L7.985 5.356m0 0v4.992m0 0h4.992m0 0l3.181-3.183a8.25 8.25 0 0111.667 0l3.181 3.183" />
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="flex gap-3 pt-4">
                        <button id="llm-modal-cancel" class="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-md transition-colors text-white">
                            Cancel
                        </button>
                        <button id="llm-modal-save" class="flex-1 px-4 py-2 bg-[#F15F22] hover:bg-[#D9501A] rounded-md transition-colors text-white font-medium">
                            ${isEdit ? 'Update' : 'Add'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);

    const modal = document.getElementById('llm-config-modal');
    const providerSelect = modal.querySelector('#llm-modal-provider');
    const credentialsContainer = modal.querySelector('#llm-modal-credentials-container');
    const refreshBtn = modal.querySelector('#llm-modal-refresh-models');
    const modelSelect = modal.querySelector('#llm-modal-model');

    // Function to render credential fields based on selected provider
    function renderCredentialFields(provider) {
        const template = LLM_PROVIDER_TEMPLATES[provider];
        if (!template) return;

        let html = '';

        // Render regular credential fields
        template.fields.forEach(field => {
            let value = '';
            
            // First, try to get value from localStorage (always preferred for credentials)
            const storedCredentials = loadCredentialsFromLocalStorage(provider);
            value = storedCredentials[field.id] || '';
            
            // If still no value, try to get from config (backend) as fallback
            // This handles the case where credentials were saved to backend (when persistence was on)
            if (!value && config?.credentials) {
                value = config.credentials[field.id] || '';
            }
            
            html += `
                <div>
                    <label class="block text-sm font-medium text-gray-300 mb-1">${escapeHtml(field.label)}</label>
                    <input type="${field.type}" 
                        data-credential="${field.id}" 
                        value="${escapeHtml(value)}" 
                        placeholder="${escapeHtml(field.placeholder)}" 
                        ${field.required ? 'required' : ''}
                        class="w-full p-2 bg-gray-700 border border-gray-600 rounded-md focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none">
                </div>
            `;
        });

        // Render extra fields (like AWS listing method)
        if (template.extra?.listingMethod) {
            html += '<div><label class="block text-sm font-medium text-gray-300 mb-2">Model Listing Method</label><div class="flex items-center gap-6">';
            template.extra.listingMethod.forEach(option => {
                const checked = config?.listingMethod === option.value || (option.default && !config?.listingMethod);
                html += `
                    <div class="flex items-center">
                        <input id="listing-${option.id}" name="listing_method" type="radio" value="${option.value}" 
                            ${checked ? 'checked' : ''} 
                            data-credential="listingMethod"
                            class="h-4 w-4 border-gray-300 text-[#F15F22] focus:ring-[#F15F22]">
                        <label for="listing-${option.id}" class="ml-2 text-sm text-gray-300">${escapeHtml(option.label)}</label>
                    </div>
                `;
            });
            html += '</div></div>';
        }

        credentialsContainer.innerHTML = html;
    }

    // Function to refresh models
    async function refreshModels() {
        const provider = providerSelect.value;
        const credentials = {};
        
        // Collect credentials
        credentialsContainer.querySelectorAll('[data-credential]').forEach(input => {
            const field = input.dataset.credential;
            if (input.type === 'radio') {
                if (input.checked) {
                    credentials[field] = input.value;
                }
            } else {
                credentials[field] = input.value;
            }
        });

        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<svg class="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';

        try {
            const response = await fetch('/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, ...credentials })
            });

            const data = await response.json();

            if (data.models && data.models.length > 0) {
                const certifiedModels = data.models.filter(model => {
                    return typeof model === 'string' || model.certified !== false;
                });
                const firstCertifiedModel = certifiedModels.length > 0 
                    ? (typeof certifiedModels[0] === 'string' ? certifiedModels[0] : certifiedModels[0].name)
                    : null;
                
                // Clear and rebuild options without affecting select element styling
                modelSelect.innerHTML = '';
                
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = '-- Select a model --';
                modelSelect.appendChild(defaultOption);
                
                data.models.forEach(model => {
                    const modelName = typeof model === 'string' ? model : model.name;
                    const certified = typeof model === 'object' ? model.certified : true;
                    const label = certified ? modelName : `${modelName} (support evaluated)`;
                    const selected = modelName === firstCertifiedModel;
                    
                    const option = document.createElement('option');
                    option.value = modelName;
                    option.textContent = label;
                    if (!certified) option.disabled = true;
                    if (selected) option.selected = true;
                    
                    modelSelect.appendChild(option);
                });
                
                showNotification('success', `Found ${data.models.length} models${firstCertifiedModel ? ` - selected ${firstCertifiedModel}` : ''}`);
            } else {
                showNotification('warning', 'No models found');
            }
        } catch (error) {
            showNotification('error', `Failed to fetch models: ${error.message}`);
        } finally {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0011.667 0l3.181-3.183m-4.991-2.691L7.985 5.356m0 0v4.992m0 0h4.992m0 0l3.181-3.183a8.25 8.25 0 0111.667 0l3.181 3.183" /></svg>';
        }
    }

    // Initial render of credential fields
    renderCredentialFields(selectedProvider);

    // Provider change handler (only for new configs)
    if (!isEdit) {
        providerSelect.addEventListener('change', () => {
            renderCredentialFields(providerSelect.value);
            // Clear model selection when provider changes
            modelSelect.innerHTML = '<option value="">-- Select a model --</option>';
        });
    }

    // Refresh models button
    refreshBtn.addEventListener('click', refreshModels);

    // Cancel button
    modal.querySelector('#llm-modal-cancel').addEventListener('click', () => modal.remove());

    // Save button
    modal.querySelector('#llm-modal-save').addEventListener('click', async () => {
        const name = modal.querySelector('#llm-modal-name').value.trim();
        const provider = providerSelect.value;
        const model = modelSelect.value;
        
        if (!name) {
            showNotification('error', 'Configuration name is required');
            return;
        }

        if (!model) {
            showNotification('error', 'Please select a model');
            return;
        }

        // Collect credentials
        const credentials = {};
        credentialsContainer.querySelectorAll('[data-credential]').forEach(input => {
            const field = input.dataset.credential;
            if (input.type === 'radio') {
                if (input.checked) {
                    credentials[field] = input.value;
                }
            } else {
                credentials[field] = input.value;
            }
        });

        // Validate required fields
        const template = LLM_PROVIDER_TEMPLATES[provider];
        const missingFields = template.fields.filter(f => f.required && !credentials[f.id]);
        if (missingFields.length > 0) {
            showNotification('error', `Missing required fields: ${missingFields.map(f => f.label).join(', ')}`);
            return;
        }

        const configData = {
            name,
            provider,
            model,
            credentials
        };

        try {
            let success;
            if (isEdit) {
                success = await configState.updateLLMConfiguration(configId, configData);
            } else {
                const result = await configState.addLLMConfiguration(configData);
                success = result !== null && result !== undefined;
            }

            if (success) {
                // Save credentials to localStorage for future use
                const storageKey = `${provider.toLowerCase()}ApiKey`;
                try {
                    // For providers with multiple fields, store as JSON object
                    if (Object.keys(credentials).length > 1) {
                        localStorage.setItem(storageKey, JSON.stringify(credentials));
                    } else if (credentials.apiKey) {
                        // For simple apiKey, store as plain string
                        localStorage.setItem(storageKey, credentials.apiKey);
                    } else if (credentials.ollama_host) {
                        // For Ollama, store host separately for backward compatibility
                        localStorage.setItem('ollamaHost', credentials.ollama_host);
                    } else {
                        // Store the whole credentials object
                        localStorage.setItem(storageKey, JSON.stringify(credentials));
                    }
                } catch (e) {
                    console.error('Failed to save credentials to localStorage:', e);
                }
                
                renderLLMProviders();
                modal.remove();
                showNotification('success', `LLM configuration ${isEdit ? 'updated' : 'added'} successfully`);
            }
        } catch (error) {
            showNotification('error', `Failed to ${isEdit ? 'update' : 'add'} configuration: ${error.message}`);
        }
    });
}

// Old LLM provider form functions removed - now using LLM configurations
// renderLLMProviderForm, refreshModels, saveLLMProvider are deprecated

// ============================================================================
// ACTION HANDLERS - MCP SERVERS
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

// ============================================================================
// UI UPDATE HELPERS
// ============================================================================
function updateProfilesTab() {
    const profilesTab = document.querySelector('.config-tab[data-tab="profiles-tab"]');
    if (!profilesTab) return;

    const mcpConfigured = configState.mcpServers.length > 0;
    const llmConfigured = configState.llmConfigurations.length > 0;

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
    btn.classList.toggle('opacity-50', !canReconnect);
    btn.classList.toggle('cursor-not-allowed', !canReconnect);
}

export async function reconnectAndLoad() {
    const defaultProfile = configState.profiles.find(p => p.id === configState.defaultProfileId);

    if (!defaultProfile) {
        showNotification('error', 'Please set a default profile before connecting.');
        return;
    }

    // Set the active MCP and LLM based on the default profile
    await configState.setActiveMCP(defaultProfile.mcpServerId);
    await configState.setActiveLLM(defaultProfile.llmConfigurationId);

    const mcpServer = configState.getActiveMCPServer();
    const llmConfig = configState.getActiveLLMConfiguration();

    // Validate that both MCP server and LLM configuration are configured
    if (!mcpServer) {
        showNotification('error', 'Please configure and select an MCP Server first (go to MCP Servers tab)');
        return;
    }

    if (!llmConfig) {
        showNotification('error', 'Please configure and select an LLM Configuration first (go to LLM Providers tab)');
        return;
    }

    // Additional validation for required fields
    if (!mcpServer.host || !mcpServer.port) {
        showNotification('error', 'MCP Server configuration is incomplete (missing host or port)');
        return;
    }

    // Load credentials from localStorage and merge with config
    // Since credentials are never stored in tda_config.json, we need to get them from browser storage
    const credentialsFromStorage = loadCredentialsFromLocalStorage(llmConfig.provider);
    if (!credentialsFromStorage || Object.keys(credentialsFromStorage).length === 0) {
        showNotification('error', 'LLM Configuration credentials are missing. Please edit the configuration and enter your credentials.');
        return;
    }
    
    // Merge credentials from localStorage into llmConfig
    llmConfig.credentials = credentialsFromStorage;

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
            provider: llmConfig.provider,
            model: llmConfig.model,
            credentials: llmConfig.credentials,
            server_name: mcpServer.name,
            server_id: mcpServer.id,
            mcp_server: {
                id: mcpServer.id,
                name: mcpServer.name,
                host: mcpServer.host,
                port: mcpServer.port,
                path: mcpServer.path
            },
            listing_method: llmConfig.listingMethod || 'foundation_models',
            tts_credentials_json: document.getElementById('tts-credentials-json')?.value || '',
            charting_intensity: document.getElementById('charting-intensity')?.value || 'none'
        };


        const headers = { 'Content-Type': 'application/json' };
        
        // Add authentication token if available
        const authToken = localStorage.getItem('tda_auth_token');
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }
        
        // Add User UUID header (for backwards compatibility)
        if (state.userUUID) {
            headers['X-TDA-User-UUID'] = state.userUUID;
        }
        
        const response = await fetch('/configure', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(configData)
        });

        const result = await response.json();

        if (result.status === 'success') {
            statusDiv.innerHTML = '<span class="text-green-400">✓ ' + escapeHtml(result.message) + '</span>';
            showNotification('success', result.message);
            
            // Don't override active profiles - they are already loaded from backend configuration
            // The active_for_consumption_profile_ids should persist from the saved config
            
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
                        <div class="flex items-center gap-2 mb-1">
                            <h4 class="font-semibold text-white">${escapeHtml(profile.name || profile.tag)}</h4>
                            ${profile.color ? `
                            <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-semibold border" 
                                  style="background: linear-gradient(135deg, ${profile.color}30, ${profile.color}15); border-color: ${profile.color}50; color: ${profile.color};">
                                <span class="w-2 h-2 rounded-full" style="background: ${profile.color};"></span>
                                @${escapeHtml(profile.tag)}
                            </span>
                            ` : `
                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-semibold bg-[#F15F22]/20 text-[#F15F22] border border-[#F15F22]/30">
                                @${escapeHtml(profile.tag)}
                            </span>
                            `}
                        </div>
                        <p class="text-sm text-gray-400 mb-3">${escapeHtml(profile.description)}</p>
                        <div class="text-sm text-gray-400 space-y-1">
                            <p><span class="font-medium">LLM:</span> ${(() => {
                                const llmConfig = configState.llmConfigurations.find(c => c.id === profile.llmConfigurationId);
                                if (llmConfig) {
                                    const providerDisplay = profile.providerName || llmConfig.provider;
                                    return `<span style="color: ${profile.color || '#9ca3af'};">${escapeHtml(providerDisplay)}</span> / ${escapeHtml(llmConfig.model)}`;
                                }
                                return 'N/A';
                            })()}</p>
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
                    <button type="button" data-action="copy-profile" data-profile-id="${profile.id}" 
                        class="px-3 py-1 text-sm bg-green-600 hover:bg-green-700 rounded transition-colors text-white">
                        Copy
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
            
            // Auto-activate the default profile if it's not already active
            if (!configState.activeForConsumptionProfileIds.includes(profileId)) {
                const activeIds = [...configState.activeForConsumptionProfileIds, profileId];
                await configState.setActiveForConsumptionProfiles(activeIds);
            }
            
            renderProfiles();
            renderLLMProviders(); // Re-render to update default/active badges
            renderMCPServers(); // Re-render to update default/active badges
            updateReconnectButton(); // Update Reconnect & Load button state
            
            showNotification('success', 'Default profile updated. Click "Reconnect & Load" to apply changes.');
        });
    });

    // Toggle Active for Consumption checkbox
    document.querySelectorAll('[data-action="toggle-active-consumption"]').forEach(checkbox => {
        checkbox.addEventListener('change', async (e) => {
            const profileId = e.target.dataset.profileId;
            const isChecked = e.target.checked;
            
            // Prevent deactivating the default profile
            if (!isChecked && profileId === configState.defaultProfileId) {
                e.target.checked = true; // Revert the checkbox
                showNotification('error', 'Cannot deactivate the default profile. Set a different profile as default first.');
                return;
            }
            
            let activeIds = configState.activeForConsumptionProfileIds;

            if (isChecked) {
                // Test the profile before activating
                const resultsContainer = document.getElementById(`test-results-${profileId}`);
                if (resultsContainer) {
                    resultsContainer.innerHTML = `<span class="text-yellow-400">Testing before activation...</span>`;
                }
                
                try {
                    const result = await API.testProfile(profileId);
                    const allSuccessful = Object.values(result.results).every(r => r.status === 'success');
                    
                    let testResultsHTML = '';
                    for (const [key, value] of Object.entries(result.results)) {
                        const statusClass = value.status === 'success' ? 'text-green-400' : 'text-red-400';
                        testResultsHTML += `<p class="${statusClass}">${value.message}</p>`;
                    }
                    
                    if (allSuccessful) {
                        // Tests passed - activate the profile
                        if (!activeIds.includes(profileId)) {
                            activeIds.push(profileId);
                        }
                        await configState.setActiveForConsumptionProfiles(activeIds);
                        renderProfiles();
                        renderLLMProviders(); // Re-render to update default/active badges
                        renderMCPServers(); // Re-render to update default/active badges
                        showNotification('success', 'Profile tested successfully and activated');
                        
                        // Re-apply test results after render
                        const newResultsContainer = document.getElementById(`test-results-${profileId}`);
                        if (newResultsContainer) {
                            newResultsContainer.innerHTML = testResultsHTML;
                        }
                    } else {
                        // Tests failed - revert checkbox and show results
                        e.target.checked = false;
                        if (resultsContainer) {
                            resultsContainer.innerHTML = testResultsHTML;
                        }
                        showNotification('error', 'Profile tests failed. Cannot activate profile.');
                    }
                } catch (error) {
                    // Test error - revert checkbox
                    e.target.checked = false;
                    if (resultsContainer) {
                        resultsContainer.innerHTML = `<span class="text-red-400">Test failed: ${error.message}</span>`;
                    }
                    showNotification('error', `Failed to test profile: ${error.message}`);
                }
            } else {
                // Deactivating - no test needed
                activeIds = activeIds.filter(id => id !== profileId);
                await configState.setActiveForConsumptionProfiles(activeIds);
                renderProfiles();
                renderLLMProviders(); // Re-render to update default/active badges
                renderMCPServers(); // Re-render to update default/active badges
            }
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

    // Copy Profile button
    document.querySelectorAll('[data-action="copy-profile"]').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const profileId = e.target.dataset.profileId;
            const profile = configState.profiles.find(p => p.id === profileId);
            const profileName = profile ? profile.name : 'this profile';
            
            const copiedProfile = await configState.copyProfile(profileId);
            if (copiedProfile) {
                renderProfiles();
                renderLLMProviders(); // Re-render to update default/active badges
                renderMCPServers(); // Re-render to update default/active badges
                showNotification('success', `Profile "${profileName}" copied successfully. Please edit to set a unique tag.`);
            } else {
                showNotification('error', 'Failed to copy profile');
            }
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
                renderLLMProviders(); // Re-render to update default/active badges
                renderMCPServers(); // Re-render to update default/active badges
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

    // Populate LLM configurations
    const llmSelect = modal.querySelector('#profile-modal-llm-provider');
    const activeLLMId = configState.activeLLM || configState.llmConfigurations[0]?.id;
    llmSelect.innerHTML = configState.llmConfigurations
        .map(config => {
            const isSelected = profile ? 
                (profile.llmConfigurationId === config.id) : 
                (config.id === activeLLMId);
            return `<option value="${config.id}" ${isSelected ? 'selected' : ''}>${escapeHtml(config.name)}</option>`;
        })
        .join('');

    // Populate MCP servers
    const mcpSelect = modal.querySelector('#profile-modal-mcp-server');
    const activeMCPId = configState.activeMCP || configState.mcpServers[0]?.id;
    mcpSelect.innerHTML = configState.mcpServers
        .map(server => {
            const isSelected = profile ? 
                (profile.mcpServerId === server.id) : 
                (server.id === activeMCPId);
            return `<option value="${server.id}" ${isSelected ? 'selected' : ''}>${escapeHtml(server.name)}</option>`;
        })
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

    // Set profile name, tag and description
    const profileNameInput = modal.querySelector('#profile-modal-name');
    const profileTagInput = modal.querySelector('#profile-modal-tag');
    const profileDescInput = modal.querySelector('#profile-modal-description');
    
    profileNameInput.value = profile ? (profile.name || '') : '';
    profileTagInput.value = profile ? (profile.tag || '').replace('@', '') : '';
    profileDescInput.value = profile ? profile.description : '';

    // Tag generation function
    function generateTag() {
        const llmConfig = configState.llmConfigurations.find(c => c.id === llmSelect.value);
        const mcpServer = configState.mcpServers.find(s => s.id === mcpSelect.value);
        
        if (!llmConfig || !mcpServer) {
            return '';
        }
        
        // Extract characters from provider, model, and server
        const providerPart = (llmConfig.provider || '').substring(0, 2).toUpperCase();
        const modelPart = (llmConfig.model || '').substring(0, 2).toUpperCase();
        const serverPart = (mcpServer.name || '').substring(0, 1).toUpperCase();
        
        let tag = (providerPart + modelPart + serverPart).substring(0, 5);
        
        // Ensure uniqueness
        let suffix = '';
        let counter = 1;
        while (configState.profiles.some(p => p.id !== profileId && p.tag === tag + suffix)) {
            suffix = counter.toString();
            counter++;
        }
        
        return tag + suffix;
    }

    // Auto-generate tag when LLM/MCP changes (only for new profiles)
    if (!isEdit) {
        // Auto-generate when LLM or MCP changes (only if tag is empty)
        const autoGenerate = () => {
            if (!profileTagInput.value.trim()) {
                profileTagInput.value = generateTag();
            }
        };
        llmSelect.addEventListener('change', autoGenerate);
        mcpSelect.addEventListener('change', autoGenerate);
    }

    // Manual tag generation button
    const generateTagBtn = modal.querySelector('#profile-modal-generate-tag');
    if (generateTagBtn) {
        generateTagBtn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            profileTagInput.value = generateTag();
        };
    }

    // Force uppercase on tag input
    profileTagInput.addEventListener('input', (e) => {
        e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').substring(0, 5);
    });

    // Show the modal
    modal.classList.remove('hidden');

    // Attach event listeners for uncheck all buttons
    const toolsUncheckBtn = modal.querySelector('#profile-modal-tools-uncheck-all');
    const promptsUncheckBtn = modal.querySelector('#profile-modal-prompts-uncheck-all');
    
    if (toolsUncheckBtn) {
        toolsUncheckBtn.onclick = () => {
            toolsContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        };
    }
    
    if (promptsUncheckBtn) {
        promptsUncheckBtn.onclick = () => {
            promptsContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
        };
    }

    // Attach event listeners for save/cancel
    modal.querySelector('#profile-modal-cancel').onclick = () => modal.classList.add('hidden');
    modal.querySelector('#profile-modal-save').onclick = async () => {
        const name = modal.querySelector('#profile-modal-name').value.trim();
        const tag = modal.querySelector('#profile-modal-tag').value.trim().toUpperCase();
        const description = modal.querySelector('#profile-modal-description').value.trim();

        if (!name) {
            showNotification('error', 'Profile name is required');
            return;
        }

        if (!tag) {
            showNotification('error', 'Profile tag is required');
            return;
        }

        // Validate tag uniqueness
        if (configState.profiles.some(p => p.id !== profileId && p.tag === tag)) {
            showNotification('error', `Tag "${tag}" is already in use. Please choose a different tag.`);
            return;
        }
        
        const selectedTools = Array.from(toolsContainer.querySelectorAll('input:checked')).map(cb => cb.value);
        const selectedPrompts = Array.from(promptsContainer.querySelectorAll('input:checked')).map(cb => cb.value);
        const selectedRag = Array.from(ragContainer.querySelectorAll('input:checked')).map(cb => parseInt(cb.value));
        const selectedAutocomplete = Array.from(autocompleteContainer.querySelectorAll('input:checked')).map(cb => parseInt(cb.value));

        const profileData = {
            id: profile ? profile.id : `profile-${generateId()}`,
            name,
            tag,
            description,
            llmConfigurationId: llmSelect.value,
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
            renderLLMProviders(); // Re-render to update default/active badges
            renderMCPServers(); // Re-render to update default/active badges
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
    
    // Load MCP classification setting
    await loadClassificationSetting();

    // Add MCP server button
    const addMCPBtn = document.getElementById('add-mcp-server-btn');
    if (addMCPBtn) {
        addMCPBtn.addEventListener('click', () => showMCPServerModal());
    }

    // Add LLM configuration button
    const addLLMConfigBtn = document.getElementById('add-llm-config-btn');
    if (addLLMConfigBtn) {
        addLLMConfigBtn.addEventListener('click', () => showLLMConfigurationModal());
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
    
    // MCP Classification toggle
    const classificationCheckbox = document.getElementById('enable-mcp-classification');
    if (classificationCheckbox) {
        classificationCheckbox.addEventListener('change', async (e) => {
            await saveClassificationSetting(e.target.checked);
        });
    }

}
