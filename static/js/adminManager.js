/**
 * Administration Module
 * Handles user management and feature configuration UI
 */

const AdminManager = {
    currentUsers: [],
    currentFeatures: [],
    featureChanges: {},

    /**
     * Show notification message
     */
    showNotification(message, type = 'info') {
        // Simple notification fallback
        const color = type === 'success' ? 'bg-green-600' : type === 'error' ? 'bg-red-600' : 'bg-blue-600';
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 ${color} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity`;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    },

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
                this.showNotification(data.message || 'Failed to load users', 'error');
            }
        } catch (error) {
            console.error('[AdminManager] Error loading users:', error);
            this.showNotification('Failed to load users', 'error');
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
                this.showNotification(`User tier updated to ${newTier}`, 'success');
                await this.loadUsers(); // Reload to get updated feature counts
            } else {
                this.showNotification(data.message || 'Failed to update user tier', 'error');
                await this.loadUsers(); // Reload to reset select
            }
        } catch (error) {
            console.error('[AdminManager] Error changing user tier:', error);
            this.showNotification('Failed to update user tier', 'error');
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
                this.showNotification(data.message || 'Failed to load features', 'error');
            }
        } catch (error) {
            console.error('[AdminManager] Error loading features:', error);
            this.showNotification('Failed to load features', 'error');
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
            this.showNotification('No changes to save', 'info');
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
                this.showNotification(`Updated ${successCount} feature(s)`, 'success');
            }
            if (errorCount > 0) {
                this.showNotification(`Failed to update ${errorCount} feature(s)`, 'error');
            }

            // Reload features to get fresh data
            await this.loadFeatures();

        } catch (error) {
            console.error('[AdminManager] Error saving feature changes:', error);
            this.showNotification('Failed to save changes', 'error');
        }
    },

    /**
     * Reset features to defaults
     */
    async resetFeatures() {
        if (!confirm('Are you sure you want to reset all feature tiers to their default values?')) {
            return;
        }

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
                this.showNotification(data.message || 'Features reset to defaults', 'success');
                await this.loadFeatures();
            } else {
                this.showNotification(data.message || 'Failed to reset features', 'error');
            }
        } catch (error) {
            console.error('[AdminManager] Error resetting features:', error);
            this.showNotification('Failed to reset features', 'error');
        }
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
            
            const response = await fetch(url, {
                method,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showNotification(isEdit ? 'User updated successfully' : 'User created successfully', 'success');
                this.hideUserModal();
                await this.loadUsers();
            } else {
                this.showNotification(data.message || 'Failed to save user', 'error');
            }
        } catch (error) {
            console.error('[AdminManager] Error saving user:', error);
            this.showNotification('Failed to save user', 'error');
        }
    },
    
    /**
     * Delete user
     */
    async deleteUser(userId) {
        const user = this.currentUsers.find(u => u.id === userId);
        if (!user) return;
        
        if (!confirm(`Are you sure you want to delete user "${user.username}"?`)) {
            return;
        }
        
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
                this.showNotification('User deleted successfully', 'success');
                await this.loadUsers();
            } else {
                this.showNotification(data.message || 'Failed to delete user', 'error');
            }
        } catch (error) {
            console.error('[AdminManager] Error deleting user:', error);
            this.showNotification('Failed to delete user', 'error');
        }
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
                this.showNotification('Not authenticated', 'error');
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
                this.showNotification(data.message || 'Failed to load panes', 'error');
            }
        } catch (error) {
            console.error('[AdminManager] Error loading panes:', error);
            this.showNotification('Failed to load panes', 'error');
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
                                class="pane-visibility-checkbox sr-only peer" 
                                data-pane-id="${pane.pane_id}" 
                                data-tier="user"
                                ${pane.visible_to_user ? 'checked' : ''}>
                            <div class="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                        </label>
                    </td>
                    <td class="px-6 py-4 text-center">
                        <label class="inline-flex items-center cursor-pointer">
                            <input type="checkbox" 
                                class="pane-visibility-checkbox sr-only peer" 
                                data-pane-id="${pane.pane_id}" 
                                data-tier="developer"
                                ${pane.visible_to_developer ? 'checked' : ''}>
                            <div class="relative w-11 h-6 bg-gray-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600"></div>
                        </label>
                    </td>
                    <td class="px-6 py-4 text-center">
                        <label class="inline-flex items-center cursor-pointer">
                            <input type="checkbox" 
                                class="pane-visibility-checkbox sr-only peer" 
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
                this.showNotification('Not authenticated', 'error');
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
                this.showNotification(`Pane visibility updated for ${tier} tier`, 'success');
                
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
                this.showNotification(data.message || 'Failed to update pane visibility', 'error');
                // Reload to reset UI
                await this.loadPanes();
            }
        } catch (error) {
            console.error('[AdminManager] Error updating pane visibility:', error);
            this.showNotification('Failed to update pane visibility', 'error');
            // Reload to reset UI
            await this.loadPanes();
        }
    },

    /**
     * Reset all pane visibility to defaults
     */
    async resetPanes() {
        if (!confirm('Reset all pane visibility to default configuration? This will override all custom settings.')) {
            return;
        }

        try {
            const token = localStorage.getItem('tda_auth_token');
            if (!token) {
                this.showNotification('Not authenticated', 'error');
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
                this.showNotification('Pane visibility reset to defaults', 'success');
                this.currentPanes = data.panes || [];
                this.renderPanes();
                
                // Trigger pane visibility refresh for current user
                if (typeof window.updatePaneVisibility === 'function') {
                    window.updatePaneVisibility();
                }
            } else {
                this.showNotification(data.message || 'Failed to reset panes', 'error');
            }
        } catch (error) {
            console.error('[AdminManager] Error resetting panes:', error);
            this.showNotification('Failed to reset panes', 'error');
        }
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AdminManager.init());
} else {
    AdminManager.init();
}
