/**
 * Administration Module
 * Handles user management and feature configuration UI
 */

const AdminManager = {
    currentUsers: [],
    currentFeatures: [],
    featureChanges: {},

    /**
     * Initialize the administration module
     */
    init() {
        console.log('[AdminManager] Initializing...');
        this.setupEventListeners();
    },

    /**
     * Setup event listeners for admin UI
     */
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.admin-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // User management
        const createUserBtn = document.getElementById('create-user-btn');
        if (createUserBtn) {
            createUserBtn.addEventListener('click', () => this.showCreateUserModal());
        }
        
        const refreshBtn = document.getElementById('refresh-users-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadUsers());
        }
        
        // User modal handlers
        const userModalClose = document.getElementById('user-modal-close');
        if (userModalClose) {
            userModalClose.addEventListener('click', () => this.hideUserModal());
        }
        
        const userFormCancel = document.getElementById('user-form-cancel');
        if (userFormCancel) {
            userFormCancel.addEventListener('click', () => this.hideUserModal());
        }
        
        const userForm = document.getElementById('user-form');
        if (userForm) {
            userForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const formData = {
                    id: document.getElementById('user-form-id').value,
                    username: document.getElementById('user-form-username').value,
                    email: document.getElementById('user-form-email').value,
                    displayName: document.getElementById('user-form-display-name').value,
                    password: document.getElementById('user-form-password').value,
                    tier: document.getElementById('user-form-tier').value
                };
                this.saveUser(formData);
            });
        }

        // Feature configuration
        const saveBtn = document.getElementById('save-features-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveFeatureChanges());
        }

        const resetBtn = document.getElementById('reset-features-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetFeatures());
        }

        // Feature search and filter
        const searchInput = document.getElementById('feature-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.filterFeatures(e.target.value));
        }

        const filterSelect = document.getElementById('feature-filter-tier');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => this.filterFeaturesByTier(e.target.value));
        }

        // Pane configuration
        const refreshPanesBtn = document.getElementById('refresh-panes-btn');
        if (refreshPanesBtn) {
            refreshPanesBtn.addEventListener('click', () => this.loadPanes());
        }

        const resetPanesBtn = document.getElementById('reset-panes-btn');
        if (resetPanesBtn) {
            resetPanesBtn.addEventListener('click', () => this.resetPanes());
        }

        // Application configuration
        const runMcpClassificationBtn = document.getElementById('run-mcp-classification-btn');
        if (runMcpClassificationBtn) {
            runMcpClassificationBtn.addEventListener('click', () => this.runMcpClassification());
        }

        // MCP Classification toggle is handled by configurationHandler.js

        // Expert Settings
        const saveExpertSettingsBtn = document.getElementById('save-expert-settings-btn');
        if (saveExpertSettingsBtn) {
            saveExpertSettingsBtn.addEventListener('click', () => this.saveExpertSettings());
        }

        const clearCacheBtn = document.getElementById('clear-cache-btn');
        if (clearCacheBtn) {
            clearCacheBtn.addEventListener('click', () => this.clearCache());
        }

        const resetStateBtn = document.getElementById('reset-state-btn');
        if (resetStateBtn) {
            resetStateBtn.addEventListener('click', () => this.resetState());
        }

        // System Prompts
        const systemPromptsTierSelector = document.getElementById('system-prompts-tier-selector');
        if (systemPromptsTierSelector) {
            systemPromptsTierSelector.addEventListener('change', (e) => this.loadSystemPromptForTier(e.target.value));
        }

        const loadSystemPromptBtn = document.getElementById('load-system-prompt-btn');
        if (loadSystemPromptBtn) {
            loadSystemPromptBtn.addEventListener('click', () => {
                const tier = document.getElementById('system-prompts-tier-selector').value;
                this.loadSystemPromptForTier(tier);
            });
        }

        const saveSystemPromptBtn = document.getElementById('save-system-prompt-btn');
        if (saveSystemPromptBtn) {
            saveSystemPromptBtn.addEventListener('click', () => this.saveSystemPrompt());
        }

        const resetSystemPromptBtn = document.getElementById('reset-system-prompt-btn');
        if (resetSystemPromptBtn) {
            resetSystemPromptBtn.addEventListener('click', () => this.resetSystemPromptToDefault());
        }

        const systemPromptTextarea = document.getElementById('system-prompt-editor-textarea');
        if (systemPromptTextarea) {
            systemPromptTextarea.addEventListener('input', () => this.updateCharCount());
        }

        // Application Configuration
        const saveAppConfigBtn = document.getElementById('save-app-config-btn');
        if (saveAppConfigBtn) {
            saveAppConfigBtn.addEventListener('click', () => this.saveAppConfig());
        }

        // Window defaults button
        const saveWindowDefaultsBtn = document.getElementById('save-window-defaults-btn');
        if (saveWindowDefaultsBtn) {
            saveWindowDefaultsBtn.addEventListener('click', () => this.saveWindowDefaults());
        }

        // Rate Limiting
        const rateLimitEnabledCheckbox = document.getElementById('rate-limit-enabled');
        if (rateLimitEnabledCheckbox) {
            rateLimitEnabledCheckbox.addEventListener('change', (e) => this.toggleRateLimitSettings(e.target.checked));
        }

        const saveRateLimitBtn = document.getElementById('save-rate-limit-btn');
        if (saveRateLimitBtn) {
            saveRateLimitBtn.addEventListener('click', () => this.saveRateLimitSettings());
        }
    },

    /**
     * Switch between admin tabs
     */
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.admin-tab').forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active', 'border-[#F15F22]', 'text-white');
                tab.classList.remove('text-gray-400', 'border-transparent');
            } else {
                tab.classList.remove('active', 'border-[#F15F22]', 'text-white');
                tab.classList.add('text-gray-400', 'border-transparent');
            }
        });

        // Update tab content
        document.querySelectorAll('.admin-tab-content').forEach(content => {
            if (content.id === tabName) {
                content.classList.remove('hidden');
                content.classList.add('active');
            } else {
                content.classList.add('hidden');
                content.classList.remove('active');
            }
        });

        // Load data for the active tab
        if (tabName === 'user-management-tab') {
            this.loadUsers();
        } else if (tabName === 'feature-config-tab') {
            this.loadFeatures();
        } else if (tabName === 'pane-config-tab') {
            this.loadPanes();
        } else if (tabName === 'app-config-tab') {
            this.loadAppConfig();
            this.loadRateLimitSettings();
            // Load document upload configurations
            if (typeof DocumentUploadConfigManager !== 'undefined' && DocumentUploadConfigManager.loadConfigurations) {
                DocumentUploadConfigManager.loadConfigurations();
            }
        } else if (tabName === 'expert-settings-tab') {
            this.loadExpertSettings();
        } else if (tabName === 'system-prompts-tab') {
            const tier = document.getElementById('system-prompts-tier-selector').value || 'user';
            this.loadSystemPromptForTier(tier);
        }
    },

    /**
     * Load all users from API
     */
    async loadUsers() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            const response = await fetch('/api/v1/admin/users', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.currentUsers = data.users;
                this.renderUsers();
                this.updateUserStats();
            } else {
                window.showNotification('error', data.message || 'Failed to load users');
                // Clear loading state even on error
                this.currentUsers = [];
                this.renderUsers();
                this.updateUserStats();
            }
        } catch (error) {
            console.error('[AdminManager] Error loading users:', error);
            window.showNotification('error', 'Failed to load users');
            // Clear loading state even on error
            this.currentUsers = [];
            this.renderUsers();
            this.updateUserStats();
        }
    },

    /**
     * Render users table
     */
    renderUsers() {
        const tbody = document.getElementById('users-table-body');
        if (!tbody) return;

        if (this.currentUsers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-8 text-center text-gray-400">
                        No users found
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.currentUsers.map(user => `
            <tr class="bg-gray-800/50 hover:bg-gray-700/50 transition-colors">
                <td class="px-6 py-4 font-medium text-white">${this.escapeHtml(user.username)}</td>
                <td class="px-6 py-4 text-gray-300">${this.escapeHtml(user.email || '')}</td>
                <td class="px-6 py-4">
                    <span class="px-3 py-1 rounded-full text-xs font-semibold ${this.getTierBadgeClass(user.profile_tier)}">
                        ${user.profile_tier.toUpperCase()}
                    </span>
                </td>
                <td class="px-6 py-4 text-gray-400 text-sm">
                    ${user.feature_count || 0} features
                </td>
                <td class="px-6 py-4">
                    <div class="flex gap-2">
                        <select 
                            class="tier-select p-2 bg-gray-700 border border-gray-600 rounded-md text-sm text-white focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none"
                            data-user-id="${user.id}"
                            ${user.is_current_user ? 'disabled' : ''}
                        >
                            <option value="user" ${user.profile_tier === 'user' ? 'selected' : ''}>User</option>
                            <option value="developer" ${user.profile_tier === 'developer' ? 'selected' : ''}>Developer</option>
                            <option value="admin" ${user.profile_tier === 'admin' ? 'selected' : ''}>Admin</option>
                        </select>
                        <button class="edit-user-btn p-2 text-blue-400 hover:text-blue-300 transition-colors" data-user-id="${user.id}" title="Edit User">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                        </button>
                        <button class="delete-user-btn p-2 text-red-400 hover:text-red-300 transition-colors" data-user-id="${user.id}" title="Delete User" ${user.is_current_user ? 'disabled' : ''}>
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // Attach change listeners
        tbody.querySelectorAll('.tier-select').forEach(select => {
            select.addEventListener('change', async (e) => {
                const userId = e.target.dataset.userId;
                const newTier = e.target.value;
                await this.changeUserTier(userId, newTier);
            });
        });
        
        // Attach edit listeners
        tbody.querySelectorAll('.edit-user-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const userId = e.currentTarget.dataset.userId;
                this.showEditUserModal(userId);
            });
        });
        
        // Attach delete listeners
        tbody.querySelectorAll('.delete-user-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const userId = e.currentTarget.dataset.userId;
                this.deleteUser(userId);
            });
        });
    },

    /**
     * Get badge class for tier
     */
    getTierBadgeClass(tier) {
        const classes = {
            'user': 'bg-blue-500/20 text-blue-400 border border-blue-400/30',
            'developer': 'bg-purple-500/20 text-purple-400 border border-purple-400/30',
            'admin': 'bg-red-500/20 text-red-400 border border-red-400/30'
        };
        return classes[tier] || classes['user'];
    },

    /**
     * Update user statistics
     */
    updateUserStats() {
        const tierCounts = {
            user: 0,
            developer: 0,
            admin: 0
        };

        this.currentUsers.forEach(user => {
            tierCounts[user.profile_tier] = (tierCounts[user.profile_tier] || 0) + 1;
        });

        document.getElementById('user-tier-count').textContent = tierCounts.user;
        document.getElementById('developer-tier-count').textContent = tierCounts.developer;
        document.getElementById('admin-tier-count').textContent = tierCounts.admin;
    },

    /**
     * Change user tier
     */
    async changeUserTier(userId, newTier) {
        try {
            const token = localStorage.getItem('tda_auth_token');
            const response = await fetch(`/api/v1/admin/users/${userId}/tier`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ profile_tier: newTier })
            });
            const data = await response.json();

            if (data.status === 'success') {
                window.showNotification('success', `User tier updated to ${newTier}`);
                await this.loadUsers(); // Reload to get updated feature counts
            } else {
                window.showNotification('error', data.message || 'Failed to update user tier');
                await this.loadUsers(); // Reload to reset select
            }
        } catch (error) {
            console.error('[AdminManager] Error changing user tier:', error);
            window.showNotification('error', 'Failed to update user tier');
            await this.loadUsers();
        }
    },

    /**
     * Load all features from API
     */
    async loadFeatures() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            const response = await fetch('/api/v1/admin/features', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                this.currentFeatures = data.features;
                this.featureChanges = {}; // Reset changes
                this.renderFeatures();
                this.updateFeatureStats(data.feature_count_by_tier);
            } else {
                window.showNotification('error', data.message || 'Failed to load features');
            }
        } catch (error) {
            console.error('[AdminManager] Error loading features:', error);
            window.showNotification('error', 'Failed to load features');
        }
    },

    /**
     * Render features table
     */
    renderFeatures() {
        const tbody = document.getElementById('features-table-body');
        if (!tbody) return;

        if (this.currentFeatures.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="px-6 py-8 text-center text-gray-400">
                        No features found
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.currentFeatures.map(feature => `
            <tr class="bg-gray-800/50 hover:bg-gray-700/50 transition-colors feature-row" data-feature="${feature.name}" data-tier="${feature.required_tier}" data-category="${feature.category}">
                <td class="px-6 py-4 font-medium text-white">${this.escapeHtml(feature.display_name)}</td>
                <td class="px-6 py-4 text-gray-400 text-sm">${this.escapeHtml(feature.description)}</td>
                <td class="px-6 py-4">
                    <select 
                        class="feature-tier-select p-2 bg-gray-700 border border-gray-600 rounded-md text-sm text-white focus:ring-2 focus:ring-[#F15F22] focus:border-[#F15F22] outline-none"
                        data-feature-name="${feature.name}"
                    >
                        <option value="user" ${feature.required_tier === 'user' ? 'selected' : ''}>User</option>
                        <option value="developer" ${feature.required_tier === 'developer' ? 'selected' : ''}>Developer</option>
                        <option value="admin" ${feature.required_tier === 'admin' ? 'selected' : ''}>Admin</option>
                    </select>
                </td>
                <td class="px-6 py-4 text-gray-400 text-sm">${this.escapeHtml(feature.category)}</td>
            </tr>
        `).join('');

        // Attach change listeners
        tbody.querySelectorAll('.feature-tier-select').forEach(select => {
            select.addEventListener('change', (e) => {
                const featureName = e.target.dataset.featureName;
                const newTier = e.target.value;
                this.featureChanges[featureName] = newTier;
                this.updateSaveButtonState();
            });
        });
    },

    /**
     * Update save button state
     */
    updateSaveButtonState() {
        const saveBtn = document.getElementById('save-features-btn');
        if (saveBtn) {
            const hasChanges = Object.keys(this.featureChanges).length > 0;
            if (hasChanges) {
                saveBtn.classList.add('ring-2', 'ring-yellow-400');
                saveBtn.textContent = `Save Changes (${Object.keys(this.featureChanges).length})`;
            } else {
                saveBtn.classList.remove('ring-2', 'ring-yellow-400');
                saveBtn.textContent = 'Save Changes';
            }
        }
    },

    /**
     * Filter features by search term
     */
    filterFeatures(searchTerm) {
        const term = searchTerm.toLowerCase();
        document.querySelectorAll('.feature-row').forEach(row => {
            const featureName = row.dataset.feature.toLowerCase();
            const description = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
            const matches = featureName.includes(term) || description.includes(term);
            row.style.display = matches ? '' : 'none';
        });
    },

    /**
     * Filter features by tier
     */
    filterFeaturesByTier(tier) {
        document.querySelectorAll('.feature-row').forEach(row => {
            if (!tier || row.dataset.tier === tier) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    },

    /**
     * Update feature statistics
     */
    updateFeatureStats(tierCounts) {
        if (tierCounts) {
            document.getElementById('user-features-count').textContent = tierCounts.user || 0;
            document.getElementById('developer-features-count').textContent = tierCounts.developer || 0;
            document.getElementById('admin-features-count').textContent = tierCounts.admin || 0;
        }
    },

    /**
     * Save feature changes
     */
    async saveFeatureChanges() {
        if (Object.keys(this.featureChanges).length === 0) {
            window.showNotification('info', 'No changes to save');
            return;
        }

        try {
            const changes = Object.entries(this.featureChanges);
            let successCount = 0;
            let errorCount = 0;

            for (const [featureName, newTier] of changes) {
                try {
                    const token = localStorage.getItem('tda_auth_token');
                    const response = await fetch(`/api/v1/admin/features/${featureName}/tier`, {
                        method: 'PATCH',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ required_tier: newTier })
                    });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        successCount++;
                    } else {
                        errorCount++;
                    }
                } catch (error) {
                    errorCount++;
                }
            }

            if (successCount > 0) {
                window.showNotification('success', `Updated ${successCount} feature(s)`);
            }
            if (errorCount > 0) {
                window.showNotification('error', `Failed to update ${errorCount} feature(s)`);
            }

            // Reload features to get fresh data
            await this.loadFeatures();

        } catch (error) {
            console.error('[AdminManager] Error saving feature changes:', error);
            window.showNotification('error', 'Failed to save changes');
        }
    },

    /**
     * Reset features to defaults
     */
    async resetFeatures() {
        if (!window.showConfirmation) {
            console.error('Confirmation system not available');
            return;
        }
        
        window.showConfirmation(
            'Reset Feature Tiers',
            'Are you sure you want to reset all feature tiers to their default values?',
            async () => {
                try {
                    const token = localStorage.getItem('tda_auth_token');
                    const response = await fetch('/api/v1/admin/features/reset', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        window.showNotification('success', data.message || 'Features reset to defaults');
                        await this.loadFeatures();
                    } else {
                        window.showNotification('error', data.message || 'Failed to reset features');
                    }
                } catch (error) {
                    console.error('[AdminManager] Error resetting features:', error);
                    window.showNotification('error', 'Failed to reset features');
                }
            }
        );
    },

    /**
     * Show create user modal
     */
    showCreateUserModal() {
        const modal = document.getElementById('user-modal-overlay');
        const form = document.getElementById('user-form');
        const title = document.getElementById('user-modal-title');
        const passwordContainer = document.getElementById('user-form-password-container');
        
        title.textContent = 'Create User';
        form.reset();
        document.getElementById('user-form-id').value = '';
        document.getElementById('user-form-password').required = true;
        document.getElementById('password-optional-text').style.display = 'none';
        passwordContainer.style.display = 'block';
        
        modal.classList.remove('hidden');
    },
    
    /**
     * Show edit user modal
     */
    showEditUserModal(userId) {
        const user = this.currentUsers.find(u => u.id === userId);
        if (!user) return;
        
        const modal = document.getElementById('user-modal-overlay');
        const form = document.getElementById('user-form');
        const title = document.getElementById('user-modal-title');
        const passwordContainer = document.getElementById('user-form-password-container');
        
        title.textContent = 'Edit User';
        document.getElementById('user-form-id').value = user.id;
        document.getElementById('user-form-username').value = user.username;
        document.getElementById('user-form-email').value = user.email || '';
        document.getElementById('user-form-display-name').value = user.display_name || '';
        document.getElementById('user-form-tier').value = user.profile_tier;
        document.getElementById('user-form-password').required = false;
        document.getElementById('user-form-password').value = '';
        document.getElementById('password-optional-text').style.display = 'inline';
        passwordContainer.style.display = 'block'; // Show password field for optional reset
        
        modal.classList.remove('hidden');
    },
    
    /**
     * Hide user modal
     */
    hideUserModal() {
        const modal = document.getElementById('user-modal-overlay');
        modal.classList.add('hidden');
    },
    
    /**
     * Save user (create or update)
     */
    async saveUser(formData) {
        try {
            const userId = formData.id;
            const token = localStorage.getItem('tda_auth_token');
            const isEdit = !!userId;
            
            // Validate required fields for new user
            if (!isEdit) {
                if (!formData.username || !formData.email || !formData.password) {
                    window.showNotification('error', 'Please fill in all required fields (username, email, password)');
                    return;
                }
            }
            
            const url = isEdit ? `/api/v1/admin/users/${userId}` : '/api/v1/admin/users';
            const method = isEdit ? 'PATCH' : 'POST';
            
            const payload = {
                username: formData.username,
                email: formData.email,
                display_name: formData.displayName,
                profile_tier: formData.tier
            };
            
            if (!isEdit || formData.password) {
                payload.password = formData.password;
            }
            
            console.log('[AdminManager] Saving user:', { method, url, payload: { ...payload, password: '***' } });
            
            const response = await fetch(url, {
                method,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            console.log('[AdminManager] Save user response:', data);
            
            if (data.status === 'success') {
                window.showNotification('success', isEdit ? 'User updated successfully' : 'User created successfully');
                this.hideUserModal();
                await this.loadUsers();
            } else {
                window.showNotification('error', data.message || 'Failed to save user');
            }
        } catch (error) {
            console.error('[AdminManager] Error saving user:', error);
            window.showNotification('error', 'Failed to save user');
        }
    },
    
    /**
     * Delete user
     */
    async deleteUser(userId) {
        const user = this.currentUsers.find(u => u.id === userId);
        if (!user) return;
        
        if (!window.showConfirmation) {
            console.error('Confirmation system not available');
            return;
        }
        
        window.showConfirmation(
            'Delete User',
            `Are you sure you want to delete user "${user.username}"?`,
            async () => {
                try {
                    const token = localStorage.getItem('tda_auth_token');
                    const response = await fetch(`/api/v1/admin/users/${userId}`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        window.showNotification('success', 'User deleted successfully');
                        await this.loadUsers();
                    } else {
                        window.showNotification('error', data.message || 'Failed to delete user');
                    }
                } catch (error) {
                    console.error('[AdminManager] Error deleting user:', error);
                    window.showNotification('error', 'Failed to delete user');
                }
            }
        );
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text ? String(text).replace(/[&<>"']/g, m => map[m]) : '';
    },

    // ==============================================================================
    // PANE VISIBILITY MANAGEMENT
    // ==============================================================================

    currentPanes: [],

    /**
     * Load pane visibility configuration
     */
    async loadPanes() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) {
                window.showNotification('error', 'Not authenticated');
                return;
            }

            const response = await fetch('/api/v1/admin/panes', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                this.currentPanes = data.panes || [];
                this.renderPanes();
            } else {
                window.showNotification('error', data.message || 'Failed to load panes');
            }
        } catch (error) {
            console.error('[AdminManager] Error loading panes:', error);
            window.showNotification('error', 'Failed to load panes');
        }
    },

    /**
     * Render panes table
     */
    renderPanes() {
        const tbody = document.getElementById('panes-table-body');
        if (!tbody) return;

        if (this.currentPanes.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-8 text-center text-gray-400">
                        No panes configured
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.currentPanes.map(pane => {
            const isAdminPane = pane.pane_id === 'admin';
            
            return `
                <tr class="hover:bg-white/5 transition-colors">
                    <td class="px-6 py-4">
                        <div class="flex items-center gap-2">
                            <span class="font-medium text-white">${this.escapeHtml(pane.pane_name)}</span>
                            ${isAdminPane ? '<span class="text-xs px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full">Protected</span>' : ''}
                        </div>
                    </td>
                    <td class="px-6 py-4">
                        <span class="text-sm text-gray-400">${this.escapeHtml(pane.description || '')}</span>
                    </td>
                    <td class="px-6 py-4 text-center">
                        <label class="inline-flex items-center cursor-pointer">
                            <input type="checkbox" 
                                class="sr-only peer" 
                                style="position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important; margin: -1px !important; overflow: hidden !important; clip: rect(0, 0, 0, 0) !important; white-space: nowrap !important; border-width: 0 !important;"
                                data-pane-id="${pane.pane_id}" 
                                data-tier="user"
                                ${pane.visible_to_user ? 'checked' : ''}>
                            <div class="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                    </td>
                    <td class="px-6 py-4 text-center">
                        <label class="inline-flex items-center cursor-pointer">
                            <input type="checkbox" 
                                class="sr-only peer" 
                                style="position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important; margin: -1px !important; overflow: hidden !important; clip: rect(0, 0, 0, 0) !important; white-space: nowrap !important; border-width: 0 !important;"
                                data-pane-id="${pane.pane_id}" 
                                data-tier="developer"
                                ${pane.visible_to_developer ? 'checked' : ''}>
                            <div class="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                        </label>
                    </td>
                    <td class="px-6 py-4 text-center">
                        <label class="inline-flex items-center cursor-pointer">
                            <input type="checkbox" 
                                class="sr-only peer" 
                                style="position: absolute !important; width: 1px !important; height: 1px !important; padding: 0 !important; margin: -1px !important; overflow: hidden !important; clip: rect(0, 0, 0, 0) !important; white-space: nowrap !important; border-width: 0 !important;"
                                data-pane-id="${pane.pane_id}" 
                                data-tier="admin"
                                ${pane.visible_to_admin ? 'checked' : ''}
                                ${isAdminPane ? 'disabled' : ''}>
                            <div class="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-red-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600 ${isAdminPane ? 'opacity-50 cursor-not-allowed' : ''}"></div>
                        </label>
                    </td>
                </tr>
            `;
        }).join('');

        // Add event listeners to checkboxes
        tbody.querySelectorAll('.pane-visibility-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const paneId = e.target.dataset.paneId;
                const tier = e.target.dataset.tier;
                const visible = e.target.checked;
                this.updatePaneVisibility(paneId, tier, visible);
            });
        });
    },

    /**
     * Update pane visibility for a specific tier
     */
    async updatePaneVisibility(paneId, tier, visible) {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) {
                window.showNotification('error', 'Not authenticated');
                return;
            }

            const updateData = {};
            updateData[`visible_to_${tier}`] = visible;

            const response = await fetch(`/api/v1/admin/panes/${paneId}/visibility`, {
                method: 'PATCH',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(updateData)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                window.showNotification('success', `Pane visibility updated for ${tier} tier`);
                
                // Update local state
                const paneIndex = this.currentPanes.findIndex(p => p.pane_id === paneId);
                if (paneIndex !== -1) {
                    this.currentPanes[paneIndex] = data.pane;
                }
                
                // Trigger pane visibility refresh for current user if needed
                if (typeof window.updatePaneVisibility === 'function') {
                    window.updatePaneVisibility();
                }
            } else {
                window.showNotification('error', data.message || 'Failed to update pane visibility');
                // Reload to reset UI
                await this.loadPanes();
            }
        } catch (error) {
            console.error('[AdminManager] Error updating pane visibility:', error);
            window.showNotification('error', 'Failed to update pane visibility');
            // Reload to reset UI
            await this.loadPanes();
        }
    },

    /**
     * Reset all pane visibility to defaults
     */
    async resetPanes() {
        if (!window.showConfirmation) {
            console.error('Confirmation system not available');
            return;
        }
        
        window.showConfirmation(
            'Reset Pane Visibility',
            'Reset all pane visibility to default configuration? This will override all custom settings.',
            async () => {
                try {
                    const token = localStorage.getItem('tda_auth_token');
                    if (!token) {
                        window.showNotification('error', 'Not authenticated');
                        return;
                    }

                    const response = await fetch('/api/v1/admin/panes/reset', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }

                    const data = await response.json();
            
            if (data.status === 'success') {
                window.showNotification('success', 'Pane visibility reset to defaults');
                this.currentPanes = data.panes || [];
                this.renderPanes();
                
                // Trigger pane visibility refresh for current user
                if (typeof window.updatePaneVisibility === 'function') {
                    window.updatePaneVisibility();
                }
            } else {
                window.showNotification('error', data.message || 'Failed to reset panes');
            }
        } catch (error) {
            console.error('[AdminManager] Error resetting panes:', error);
            window.showNotification('error', 'Failed to reset panes');
        }
            }
        );
    },

    /**
     * Run MCP Resource Classification
     */
    async runMcpClassification() {
        const statusEl = document.getElementById('mcp-classification-status');
        const detailsEl = document.getElementById('mcp-classification-details');
        const progressEl = document.getElementById('mcp-classification-progress');
        const button = document.getElementById('run-mcp-classification-btn');

        try {
            // Show progress
            if (progressEl) progressEl.classList.remove('hidden');
            if (button) button.disabled = true;
            if (statusEl) statusEl.textContent = 'Initializing services...';
            if (detailsEl) detailsEl.textContent = '';

            const token = localStorage.getItem('tda_auth_token');
            if (!token) {
                window.showNotification('error', 'Not authenticated');
                return;
            }

            const response = await fetch('/api/v1/admin/mcp-classification', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || `HTTP ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                window.showNotification('success', 'MCP classification completed successfully');
                if (statusEl) statusEl.textContent = 'Classification completed successfully';
                if (detailsEl) {
                    const details = [];
                    if (data.categories_count) details.push(`${data.categories_count} categories created`);
                    if (data.tools_count) details.push(`${data.tools_count} tools classified`);
                    if (data.prompts_count) details.push(`${data.prompts_count} prompts classified`);
                    if (data.resources_count) details.push(`${data.resources_count} resources classified`);
                    detailsEl.textContent = details.join(' • ');
                }
            } else {
                throw new Error(data.message || 'Classification failed');
            }
        } catch (error) {
            console.error('[AdminManager] Error running MCP classification:', error);
            
            // Show error in header banner
            const headerBanner = document.getElementById('header-status-message');
            if (headerBanner) {
                headerBanner.textContent = error.message;
                headerBanner.className = 'text-sm px-3 py-1 rounded-md bg-red-500/20 border border-red-400/40 text-red-200';
                headerBanner.style.opacity = '1';
                
                // Auto-hide after 10 seconds
                setTimeout(() => {
                    headerBanner.style.opacity = '0';
                    setTimeout(() => {
                        headerBanner.textContent = '';
                        headerBanner.className = 'text-sm px-3 py-1 rounded-md transition-all duration-300 opacity-0';
                    }, 300);
                }, 10000);
            }
            
            if (statusEl) statusEl.textContent = 'Ready to classify';
            if (detailsEl) detailsEl.textContent = '';
        } finally {
            // Hide progress
            if (progressEl) progressEl.classList.add('hidden');
            if (button) button.disabled = false;
        }
    },

    /**
     * Load application configuration settings
     */
    async loadAppConfig() {
        try {
            // Load MCP classification setting
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
            console.error('[AdminManager] Failed to load app configuration:', error);
        }
    },

    /**
     * Save the MCP classification setting
     */
    async saveClassificationSetting(enabled) {
        try {
            const response = await fetch('/api/v1/config/classification', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enable_mcp_classification: enabled })
            });
            
            if (response.ok) {
                const result = await response.json();
                window.showNotification('success', result.message || 'Classification setting updated');
            } else {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.message || 'Failed to update setting');
            }
        } catch (error) {
            console.error('[AdminManager] Failed to save classification setting:', error);
            window.showNotification('error', `Failed to save setting: ${error.message}`);
            
            // Revert checkbox on error
            const checkbox = document.getElementById('enable-mcp-classification');
            if (checkbox) {
                checkbox.checked = !enabled;
            }
        }
    },

    /**
     * Load expert settings from backend
     */
    async loadExpertSettings() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) return;

            const response = await fetch('/api/v1/admin/expert-settings', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success' && data.settings) {
                    const s = data.settings;
                    
                    // LLM Behavior
                    if (s.llm_behavior) {
                        this.setFieldValue('llm-max-retries', s.llm_behavior.max_retries);
                        this.setFieldValue('llm-base-delay', s.llm_behavior.base_delay);
                    }
                    
                    // Agent Configuration
                    if (s.agent_config) {
                        this.setFieldValue('max-execution-steps', s.agent_config.max_execution_steps);
                        this.setFieldValue('tool-call-timeout', s.agent_config.tool_call_timeout);
                    }
                    
                    // Performance & Context
                    if (s.performance) {
                        this.setFieldValue('context-max-rows', s.performance.context_max_rows);
                        this.setFieldValue('context-max-chars', s.performance.context_max_chars);
                        this.setFieldValue('description-threshold', s.performance.description_threshold);
                    }
                    
                    // Agent Behavior
                    if (s.agent_behavior) {
                        const allowSynthesis = document.getElementById('allow-synthesis');
                        const forceSubSummary = document.getElementById('force-sub-summary');
                        const condensePrompts = document.getElementById('condense-prompts');
                        if (allowSynthesis) allowSynthesis.checked = s.agent_behavior.allow_synthesis;
                        if (forceSubSummary) forceSubSummary.checked = s.agent_behavior.force_sub_summary;
                        if (condensePrompts) condensePrompts.checked = s.agent_behavior.condense_prompts;
                    }
                    
                    // Query Optimization
                    if (s.query_optimization) {
                        const sqlConsolidation = document.getElementById('enable-sql-consolidation');
                        if (sqlConsolidation) sqlConsolidation.checked = s.query_optimization.enable_sql_consolidation;
                    }
                    
                    // Security
                    if (s.security) {
                        this.setFieldValue('session-timeout', s.security.session_timeout);
                        this.setFieldValue('token-expiry', s.security.token_expiry);
                    }
                }
            }
        } catch (error) {
            console.error('[AdminManager] Error loading expert settings:', error);
        }
    },

    /**
     * Save expert settings to backend
     */
    async saveExpertSettings() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) {
                window.showNotification('error', 'Not authenticated');
                return;
            }

            const settings = {
                llm_behavior: {
                    max_retries: parseInt(this.getFieldValue('llm-max-retries')),
                    base_delay: parseFloat(this.getFieldValue('llm-base-delay'))
                },
                agent_config: {
                    max_execution_steps: parseInt(this.getFieldValue('max-execution-steps')),
                    tool_call_timeout: parseInt(this.getFieldValue('tool-call-timeout'))
                },
                performance: {
                    context_max_rows: parseInt(this.getFieldValue('context-max-rows')),
                    context_max_chars: parseInt(this.getFieldValue('context-max-chars')),
                    description_threshold: parseInt(this.getFieldValue('description-threshold'))
                },
                agent_behavior: {
                    allow_synthesis: document.getElementById('allow-synthesis')?.checked || false,
                    force_sub_summary: document.getElementById('force-sub-summary')?.checked || false,
                    condense_prompts: document.getElementById('condense-prompts')?.checked || false
                },
                query_optimization: {
                    enable_sql_consolidation: document.getElementById('enable-sql-consolidation')?.checked || false
                },
                security: {
                    session_timeout: parseInt(this.getFieldValue('session-timeout')),
                    token_expiry: parseInt(this.getFieldValue('token-expiry'))
                }
            };

            const response = await fetch('/api/v1/admin/expert-settings', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                // Use configurationHandler's notification system (positioned in header)
                if (window.showNotification) {
                    window.showNotification('success', 'Expert settings saved successfully');
                }
            } else {
                if (window.showNotification) {
                    window.showNotification('error', data.message || 'Failed to save settings');
                }
            }
        } catch (error) {
            console.error('[AdminManager] Error saving expert settings:', error);
            if (window.showNotification) {
                window.showNotification('error', error.message);
            }
        }
    },

    /**
     * Clear application cache
     */
    async clearCache() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) return;

            const response = await fetch('/api/v1/admin/clear-cache', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                window.showNotification('success', 'Cache cleared successfully');
            } else {
                throw new Error(data.message || 'Failed to clear cache');
            }
        } catch (error) {
            console.error('[AdminManager] Error clearing cache:', error);
            window.showNotification('error', error.message);
        }
    },

    /**
     * Reset application state
     */
    async resetState() {
        if (!window.showConfirmation) {
            console.error('Confirmation system not available');
            return;
        }
        
        window.showConfirmation(
            'Reset Application State',
            'This will reset all application state and require reconnection. Continue?',
            async () => {
                try {
                    const token = localStorage.getItem('tda_auth_token');
                    if (!token) return;

                    const response = await fetch('/api/v1/admin/reset-state', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });

                    const data = await response.json();
                    
                    if (response.ok && data.status === 'success') {
                        window.showNotification('success', data.message);
                    } else {
                        throw new Error(data.message || 'Failed to reset state');
                    }
                } catch (error) {
                    console.error('[AdminManager] Error resetting state:', error);
                    window.showNotification('error', error.message);
                }
            }
        );
    },

    /**
     * Load application configuration (feature toggles)
     */
    async loadAppConfig() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) return;

            const response = await fetch('/api/v1/admin/app-config', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                // Set checkbox values
                const ragCheckbox = document.getElementById('enable-rag-system');
                const voiceCheckbox = document.getElementById('enable-voice-system');
                const chartingCheckbox = document.getElementById('enable-charting-system');
                
                if (ragCheckbox) ragCheckbox.checked = data.config.rag_enabled || false;
                if (voiceCheckbox) voiceCheckbox.checked = data.config.voice_conversation_enabled || false;
                if (chartingCheckbox) chartingCheckbox.checked = data.config.charting_enabled || false;
                
                // Set RAG configuration values
                if (data.config.rag_config) {
                    const ragRefreshCheckbox = document.getElementById('rag-refresh-startup');
                    if (ragRefreshCheckbox) ragRefreshCheckbox.checked = data.config.rag_config.refresh_on_startup;
                    
                    this.setFieldValue('rag-num-examples', data.config.rag_config.num_examples);
                    this.setFieldValue('rag-embedding-model', data.config.rag_config.embedding_model);
                }
            }

            // Load window defaults
            await this.loadWindowDefaults();
        } catch (error) {
            console.error('[AdminManager] Error loading app config:', error);
        }
    },

    /**
     * Load window defaults from backend
     */
    async loadWindowDefaults() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) return;

            const response = await fetch('/api/v1/admin/window-defaults', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                const wd = data.window_defaults;
                
                // Session History Panel
                const sessionVisible = document.getElementById('session-history-visible');
                const sessionMode = document.getElementById('session-history-default-mode');
                const sessionToggle = document.getElementById('session-history-user-can-toggle');
                if (sessionVisible) sessionVisible.checked = wd.session_history_visible !== false;
                if (sessionMode) sessionMode.value = wd.session_history_default_mode || 'collapsed';
                if (sessionToggle) sessionToggle.checked = wd.session_history_user_can_toggle !== false;
                
                // Resources Panel
                const resourcesVisible = document.getElementById('resources-visible');
                const resourcesMode = document.getElementById('resources-default-mode');
                const resourcesToggle = document.getElementById('resources-user-can-toggle');
                if (resourcesVisible) resourcesVisible.checked = wd.resources_visible !== false;
                if (resourcesMode) resourcesMode.value = wd.resources_default_mode || 'collapsed';
                if (resourcesToggle) resourcesToggle.checked = wd.resources_user_can_toggle !== false;
                
                // Status Window
                const statusVisible = document.getElementById('status-visible');
                const statusMode = document.getElementById('status-default-mode');
                const statusToggle = document.getElementById('status-user-can-toggle');
                if (statusVisible) statusVisible.checked = wd.status_visible !== false;
                if (statusMode) statusMode.value = wd.status_default_mode || 'collapsed';
                if (statusToggle) statusToggle.checked = wd.status_user_can_toggle !== false;
                
                // Other settings
                const alwaysShowWelcomeCheckbox = document.getElementById('always-show-welcome-screen');
                const defaultThemeSelector = document.getElementById('default-theme-selector');
                if (alwaysShowWelcomeCheckbox) alwaysShowWelcomeCheckbox.checked = wd.always_show_welcome_screen || false;
                if (defaultThemeSelector) defaultThemeSelector.value = wd.default_theme || 'legacy';
            }
        } catch (error) {
            console.error('[AdminManager] Error loading window defaults:', error);
        }
    },

    /**
     * Save window defaults to backend
     */
    async saveWindowDefaults() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) return;

            // Session History Panel
            const sessionVisible = document.getElementById('session-history-visible');
            const sessionMode = document.getElementById('session-history-default-mode');
            const sessionToggle = document.getElementById('session-history-user-can-toggle');
            
            // Resources Panel
            const resourcesVisible = document.getElementById('resources-visible');
            const resourcesMode = document.getElementById('resources-default-mode');
            const resourcesToggle = document.getElementById('resources-user-can-toggle');
            
            // Status Window
            const statusVisible = document.getElementById('status-visible');
            const statusMode = document.getElementById('status-default-mode');
            const statusToggle = document.getElementById('status-user-can-toggle');
            
            // Other settings
            const alwaysShowWelcomeCheckbox = document.getElementById('always-show-welcome-screen');
            const defaultThemeSelector = document.getElementById('default-theme-selector');

            const windowDefaults = {
                // Session History Panel
                session_history_visible: sessionVisible ? sessionVisible.checked : true,
                session_history_default_mode: sessionMode ? sessionMode.value : 'collapsed',
                session_history_user_can_toggle: sessionToggle ? sessionToggle.checked : true,
                
                // Resources Panel
                resources_visible: resourcesVisible ? resourcesVisible.checked : true,
                resources_default_mode: resourcesMode ? resourcesMode.value : 'collapsed',
                resources_user_can_toggle: resourcesToggle ? resourcesToggle.checked : true,
                
                // Status Window
                status_visible: statusVisible ? statusVisible.checked : true,
                status_default_mode: statusMode ? statusMode.value : 'collapsed',
                status_user_can_toggle: statusToggle ? statusToggle.checked : true,
                
                // Other settings
                always_show_welcome_screen: alwaysShowWelcomeCheckbox ? alwaysShowWelcomeCheckbox.checked : false,
                default_theme: defaultThemeSelector ? defaultThemeSelector.value : 'legacy'
            };

            const response = await fetch('/api/v1/admin/window-defaults', {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(windowDefaults)
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                if (window.showNotification) {
                    window.showNotification('success', 'Startup settings saved successfully. Users will see these defaults on next load.');
                }
            } else {
                if (window.showNotification) {
                    window.showNotification('error', data.message || 'Failed to save window defaults');
                }
            }
        } catch (error) {
            console.error('[AdminManager] Error saving window defaults:', error);
            if (window.showNotification) {
                window.showNotification('error', 'Failed to save window defaults');
            }
        }
    },

    /**
     * Save application configuration (feature toggles)
     */
    async saveAppConfig() {
        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) return;

            const ragCheckbox = document.getElementById('enable-rag-system');
            const voiceCheckbox = document.getElementById('enable-voice-system');
            const chartingCheckbox = document.getElementById('enable-charting-system');
            const ragRefreshCheckbox = document.getElementById('rag-refresh-startup');

            const config = {
                rag_enabled: ragCheckbox ? ragCheckbox.checked : false,
                voice_conversation_enabled: voiceCheckbox ? voiceCheckbox.checked : false,
                charting_enabled: chartingCheckbox ? chartingCheckbox.checked : false,
                rag_config: {
                    refresh_on_startup: ragRefreshCheckbox ? ragRefreshCheckbox.checked : true,
                    num_examples: parseInt(this.getFieldValue('rag-num-examples')) || 3,
                    embedding_model: this.getFieldValue('rag-embedding-model') || 'all-MiniLM-L6-v2'
                }
            };

            const response = await fetch('/api/v1/admin/app-config', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                // Use configurationHandler's notification system (positioned in header)
                if (window.showNotification) {
                    window.showNotification('success', 'Feature settings saved successfully');
                }
            } else {
                if (window.showNotification) {
                    window.showNotification('error', data.message || 'Failed to save settings');
                }
            }
        } catch (error) {
            console.error('[AdminManager] Error saving app config:', error);
            if (window.showNotification) {
                window.showNotification('error', error.message);
            }
        }
    },

    /**
     * Helper to set field value
     */
    setFieldValue(id, value) {
        const field = document.getElementById(id);
        if (field) field.value = value;
    },

    /**
     * Helper to get field value
     */
    getFieldValue(id) {
        const field = document.getElementById(id);
        return field ? field.value : null;
    },

    // ========================================================================
    // SYSTEM PROMPTS MANAGEMENT
    // ========================================================================

    /**
     * Load system prompt for a specific prompt name
     */
    async loadSystemPromptForTier(promptName) {
        try {
            // Check license tier access (only "Prompt Engineer" and "Enterprise" license tiers can edit)
            const token = authClient ? authClient.getToken() : null;
            let canEdit = false;
            let licenseTier = 'Unknown';
            
            if (token) {
                try {
                    const response = await fetch('/api/v1/auth/me', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (response.ok) {
                        const userData = await response.json();
                        // Check license_info from APP_STATE (stored during license validation)
                        licenseTier = userData.user?.license_tier || 'Unknown';
                        canEdit = licenseTier === 'Prompt Engineer' || licenseTier === 'Enterprise';
                    }
                } catch (error) {
                    console.error('[AdminManager] Error checking license tier:', error);
                }
            }
            
            const notice = document.getElementById('system-prompts-tier-notice');
            const noticeText = notice?.querySelector('p.text-xs');
            const textarea = document.getElementById('system-prompt-editor-textarea');
            const saveBtn = document.getElementById('save-system-prompt-btn');
            const resetBtn = document.getElementById('reset-system-prompt-btn');
            
            // Show/hide notice and disable controls if not authorized
            if (notice) {
                notice.classList.toggle('hidden', canEdit);
                if (noticeText && !canEdit) {
                    noticeText.textContent = `System Prompt Editor requires "Prompt Engineer" or "Enterprise" license tier. Current tier: ${licenseTier}`;
                }
            }
            if (textarea) {
                textarea.disabled = !canEdit;
            }
            if (saveBtn) {
                saveBtn.disabled = !canEdit;
                saveBtn.classList.toggle('opacity-50', !canEdit);
                saveBtn.classList.toggle('cursor-not-allowed', !canEdit);
            }
            if (resetBtn) {
                resetBtn.disabled = !canEdit;
                resetBtn.classList.toggle('opacity-50', !canEdit);
                resetBtn.classList.toggle('cursor-not-allowed', !canEdit);
            }

            // Load the system prompt from the backend
            const overrideBadge = document.getElementById('system-prompt-override-badge');
            
            if (canEdit && token) {
                try {
                    const response = await fetch(`/api/v1/system-prompts/${promptName}`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        if (textarea) {
                            textarea.value = data.content || '';
                            this.updateCharCount();
                        }
                        // Show/hide override badge
                        if (overrideBadge) {
                            overrideBadge.classList.toggle('hidden', !data.is_override);
                        }
                    } else {
                        throw new Error('Failed to load system prompt');
                    }
                } catch (error) {
                    console.error('[AdminManager] Error loading system prompt:', error);
                    if (window.showNotification) {
                        window.showNotification('error', `Failed to load system prompt: ${error.message}`);
                    }
                }
            } else if (textarea) {
                textarea.value = '';
                this.updateCharCount();
                if (overrideBadge) {
                    overrideBadge.classList.add('hidden');
                }
            }

        } catch (error) {
            console.error('[AdminManager] Error loading system prompt:', error);
            if (window.showNotification) {
                window.showNotification('error', 'Failed to load system prompt');
            }
        }
    },

    /**
     * Save system prompt for current prompt name
     */
    async saveSystemPrompt() {
        try {
            const promptName = document.getElementById('system-prompts-tier-selector').value;
            const textarea = document.getElementById('system-prompt-editor-textarea');
            const content = textarea ? textarea.value : '';

            // Check license tier access
            const token = authClient ? authClient.getToken() : null;
            if (!token) {
                if (window.showNotification) {
                    window.showNotification('error', 'Authentication required');
                }
                return;
            }

            const response = await fetch('/api/v1/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (!response.ok) {
                if (window.showNotification) {
                    window.showNotification('error', 'Failed to verify license tier');
                }
                return;
            }

            const userData = await response.json();
            const licenseTier = userData.user?.license_tier || 'Unknown';
            
            if (licenseTier !== 'Prompt Engineer' && licenseTier !== 'Enterprise') {
                if (window.showNotification) {
                    window.showNotification('error', `System Prompt Editor requires "Prompt Engineer" or "Enterprise" license tier. Current tier: ${licenseTier}`);
                }
                return;
            }

            // Save the system prompt via backend API
            const saveResponse = await fetch(`/api/v1/system-prompts/${promptName}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content })
            });

            if (saveResponse.ok) {
                // Show override badge after saving
                const overrideBadge = document.getElementById('system-prompt-override-badge');
                if (overrideBadge) {
                    overrideBadge.classList.remove('hidden');
                }
                
                if (window.showNotification) {
                    window.showNotification('success', `System prompt "${promptName}" saved successfully`);
                }
            } else {
                const errorData = await saveResponse.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to save system prompt');
            }

        } catch (error) {
            console.error('[AdminManager] Error saving system prompt:', error);
            if (window.showNotification) {
                window.showNotification('error', `Failed to save system prompt: ${error.message}`);
            }
        }
    },

    /**
     * Reset system prompt to default for current prompt name
     */
    async resetSystemPromptToDefault() {
        const promptName = document.getElementById('system-prompts-tier-selector').value;
        const promptLabel = document.getElementById('system-prompts-tier-selector').selectedOptions[0]?.text || promptName;
        
        if (!window.showConfirmation) {
            console.error('Confirmation system not available');
            return;
        }
        
        window.showConfirmation(
            'Reset System Prompt',
            `Reset "${promptLabel}" to default?\n\nThis will remove any custom override and restore the encrypted default prompt.`,
            async () => {
                const token = authClient ? authClient.getToken() : null;
                if (!token) {
                    if (window.showNotification) {
                        window.showNotification('error', 'Authentication required');
                    }
                    return;
                }

                try {
                    const response = await fetch(`/api/v1/system-prompts/${promptName}`, {
                        method: 'DELETE',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });

                    if (response.ok) {
                        await this.loadSystemPromptForTier(promptName);
                        if (window.showNotification) {
                            window.showNotification('success', `System prompt "${promptLabel}" reset to default`);
                        }
                    } else {
                        throw new Error('Failed to reset system prompt');
                    }
                } catch (error) {
                    console.error('[AdminManager] Error resetting system prompt:', error);
                    if (window.showNotification) {
                        window.showNotification('error', `Failed to reset system prompt: ${error.message}`);
                    }
                }
            }
        );
    },

    /**
     * Update character count for system prompt
     */
    updateCharCount() {
        const textarea = document.getElementById('system-prompt-editor-textarea');
        const countElement = document.getElementById('system-prompt-char-count');
        
        if (textarea && countElement) {
            countElement.textContent = textarea.value.length.toLocaleString();
        }
    },

    /**
     * Load rate limiting settings from server
     */
    async loadRateLimitSettings() {
        const token = localStorage.getItem('tda_auth_token');
        if (!token) return;

        try {
            const response = await fetch('/api/v1/auth/admin/rate-limit-settings', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error('Failed to load rate limit settings');
            }

            const data = await response.json();
            const settings = data.settings || {};

            // Update checkbox
            const enabled = settings.rate_limit_enabled?.value === 'true';
            const checkbox = document.getElementById('rate-limit-enabled');
            if (checkbox) {
                checkbox.checked = enabled;
                this.toggleRateLimitSettings(enabled);
            }

            // Update input fields
            if (settings.rate_limit_user_prompts_per_hour) {
                const input = document.getElementById('rate-limit-user-prompts-per-hour');
                if (input) input.value = settings.rate_limit_user_prompts_per_hour.value;
            }
            if (settings.rate_limit_user_prompts_per_day) {
                const input = document.getElementById('rate-limit-user-prompts-per-day');
                if (input) input.value = settings.rate_limit_user_prompts_per_day.value;
            }
            if (settings.rate_limit_user_configs_per_hour) {
                const input = document.getElementById('rate-limit-user-configs-per-hour');
                if (input) input.value = settings.rate_limit_user_configs_per_hour.value;
            }
            if (settings.rate_limit_ip_login_per_minute) {
                const input = document.getElementById('rate-limit-ip-login-per-minute');
                if (input) input.value = settings.rate_limit_ip_login_per_minute.value;
            }
            if (settings.rate_limit_ip_register_per_hour) {
                const input = document.getElementById('rate-limit-ip-register-per-hour');
                if (input) input.value = settings.rate_limit_ip_register_per_hour.value;
            }
            if (settings.rate_limit_ip_api_per_minute) {
                const input = document.getElementById('rate-limit-ip-api-per-minute');
                if (input) input.value = settings.rate_limit_ip_api_per_minute.value;
            }

        } catch (error) {
            console.error('[AdminManager] Error loading rate limit settings:', error);
            window.showAppBanner('Failed to load rate limit settings', 'error', 5000);
        }
    },

    /**
     * Toggle rate limit settings visibility
     */
    toggleRateLimitSettings(enabled) {
        const settingsDiv = document.getElementById('rate-limit-settings');
        if (settingsDiv) {
            if (enabled) {
                settingsDiv.classList.remove('hidden');
            } else {
                settingsDiv.classList.add('hidden');
            }
        }
    },

    /**
     * Save rate limiting settings
     */
    async saveRateLimitSettings() {
        const token = localStorage.getItem('tda_auth_token');
        if (!token) {
            window.showAppBanner('Authentication required', 'error', 5000);
            return;
        }

        try {
            // Collect settings
            const settings = {
                rate_limit_enabled: document.getElementById('rate-limit-enabled')?.checked ? 'true' : 'false',
                rate_limit_user_prompts_per_hour: document.getElementById('rate-limit-user-prompts-per-hour')?.value || '100',
                rate_limit_user_prompts_per_day: document.getElementById('rate-limit-user-prompts-per-day')?.value || '1000',
                rate_limit_user_configs_per_hour: document.getElementById('rate-limit-user-configs-per-hour')?.value || '10',
                rate_limit_ip_login_per_minute: document.getElementById('rate-limit-ip-login-per-minute')?.value || '5',
                rate_limit_ip_register_per_hour: document.getElementById('rate-limit-ip-register-per-hour')?.value || '3',
                rate_limit_ip_api_per_minute: document.getElementById('rate-limit-ip-api-per-minute')?.value || '60'
            };

            const response = await fetch('/api/v1/auth/admin/rate-limit-settings', {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to save rate limit settings');
            }

            const data = await response.json();
            window.showAppBanner('Rate limit settings saved successfully', 'success', 5000);
            console.log('[AdminManager] Rate limit settings saved:', data);

        } catch (error) {
            console.error('[AdminManager] Error saving rate limit settings:', error);
            window.showAppBanner(`Failed to save rate limit settings: ${error.message}`, 'error', 5000);
        }
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AdminManager.init());
} else {
    AdminManager.init();
}
