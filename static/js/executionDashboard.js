/**
 * Execution Dashboard Controller
 * Manages the three-tier execution intelligence dashboard
 */

class ExecutionDashboard {
    constructor() {
        this.currentSessionId = null;
        this.sessionsData = [];
        this.analyticsData = null;
        this.velocityChart = null;
    }

    /**
     * Get headers for API requests including User UUID
     */
    _getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        // Get userUUID from localStorage (same as main app)
        const userUUID = localStorage.getItem('tdaUserUUID');
        if (userUUID) {
            headers['X-TDA-User-UUID'] = userUUID;
        } else {
            console.warn('User UUID not found in localStorage for dashboard API calls');
        }
        
        return headers;
    }

    /**
     * Initialize the dashboard
     */
    async initialize() {
        console.log('Initializing Execution Dashboard...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Load initial data
        await this.refreshDashboard();
    }

    /**
     * Set up all event listeners
     */
    setupEventListeners() {
        // Refresh button
        document.getElementById('refresh-dashboard-btn')?.addEventListener('click', () => {
            this.refreshDashboard();
        });

        // Search input
        document.getElementById('session-search')?.addEventListener('input', (e) => {
            this.filterAndRenderSessions();
        });

        // Filter and sort controls
        document.getElementById('session-filter-status')?.addEventListener('change', () => {
            this.filterAndRenderSessions();
        });

        document.getElementById('session-sort')?.addEventListener('change', () => {
            this.filterAndRenderSessions();
        });

        // Inspector close button
        document.getElementById('close-inspector-btn')?.addEventListener('click', () => {
            this.closeInspector();
        });

        // Export buttons
        document.getElementById('export-json-btn')?.addEventListener('click', () => {
            this.exportSessionAsJSON();
        });

        document.getElementById('export-report-btn')?.addEventListener('click', () => {
            this.exportSessionAsReport();
        });
    }

    /**
     * Refresh all dashboard data
     */
    async refreshDashboard() {
        console.log('Refreshing dashboard data...');
        
        try {
            // Show loading state
            this.showLoadingState();
            
            // Load analytics and sessions in parallel
            const headers = this._getHeaders();
            const [analyticsResponse, sessionsResponse] = await Promise.all([
                fetch('/api/v1/sessions/analytics', { headers }),
                fetch('/api/v1/sessions?limit=100', { headers })
            ]);

            if (!analyticsResponse.ok || !sessionsResponse.ok) {
                throw new Error('Failed to fetch dashboard data');
            }

            this.analyticsData = await analyticsResponse.json();
            const sessionsData = await sessionsResponse.json();
            this.sessionsData = sessionsData.sessions || [];

            // Render all sections
            this.renderAnalytics();
            this.filterAndRenderSessions();

            console.log('Dashboard refreshed successfully');
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            this.showErrorState(error.message);
        }
    }

    /**
     * Render analytics section (Tier 1)
     */
    renderAnalytics() {
        if (!this.analyticsData) return;

        const data = this.analyticsData;

        // Update metric cards
        document.getElementById('metric-total-sessions').textContent = data.total_sessions.toLocaleString();
        document.getElementById('metric-total-tokens').textContent = data.total_tokens.total.toLocaleString();
        document.getElementById('metric-input-tokens').textContent = data.total_tokens.input.toLocaleString();
        document.getElementById('metric-output-tokens').textContent = data.total_tokens.output.toLocaleString();
        document.getElementById('metric-success-rate').textContent = `${data.success_rate}%`;
        document.getElementById('metric-estimated-cost').textContent = `$${data.estimated_cost.toFixed(2)}`;

        // Render velocity sparkline
        this.renderVelocitySparkline(data.velocity_data);

        // Render model distribution
        this.renderModelDistribution(data.model_distribution);

        // Render top champions
        this.renderTopChampions(data.top_champions);
    }

    /**
     * Render velocity sparkline chart
     */
    renderVelocitySparkline(velocityData) {
        const canvas = document.getElementById('velocity-sparkline');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.offsetWidth;
        const height = 32;
        canvas.width = width;
        canvas.height = height;

        if (!velocityData || velocityData.length === 0) {
            // Draw empty state
            ctx.fillStyle = '#374151';
            ctx.fillText('No velocity data', width / 2 - 40, height / 2);
            return;
        }

        // Extract counts
        const counts = velocityData.map(d => d.count);
        const maxCount = Math.max(...counts, 1);

        // Draw sparkline
        ctx.clearRect(0, 0, width, height);
        ctx.beginPath();
        ctx.strokeStyle = '#f97316'; // Orange
        ctx.lineWidth = 2;

        const stepX = width / (counts.length - 1 || 1);
        counts.forEach((count, i) => {
            const x = i * stepX;
            const y = height - (count / maxCount) * height * 0.8;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();

        // Fill area under line
        ctx.lineTo(width, height);
        ctx.lineTo(0, height);
        ctx.closePath();
        ctx.fillStyle = 'rgba(249, 115, 22, 0.2)';
        ctx.fill();
    }

    /**
     * Render model distribution bars
     */
    renderModelDistribution(modelDist) {
        const container = document.getElementById('model-distribution-list');
        if (!container) return;

        if (!modelDist || Object.keys(modelDist).length === 0) {
            container.innerHTML = '<p class="text-gray-400 text-sm">No model data available</p>';
            return;
        }

        const html = Object.entries(modelDist)
            .sort((a, b) => b[1] - a[1])
            .map(([model, percentage]) => `
                <div class="flex items-center gap-2">
                    <div class="flex-1 flex items-center gap-2">
                        <span class="text-sm text-white truncate" title="${model}">${model}</span>
                        <div class="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div class="h-full bg-blue-500 rounded-full" style="width: ${percentage}%"></div>
                        </div>
                    </div>
                    <span class="text-sm text-gray-400 w-12 text-right">${percentage}%</span>
                </div>
            `).join('');

        container.innerHTML = html;
    }

    /**
     * Render top efficiency champions
     */
    renderTopChampions(champions) {
        const container = document.getElementById('top-champions-list');
        if (!container) return;

        if (!champions || champions.length === 0) {
            container.innerHTML = '<p class="text-gray-400 text-sm">No efficiency data available</p>';
            return;
        }

        const html = champions.map((champion, index) => `
            <div class="flex items-center gap-3 p-2 bg-white/5 rounded-lg hover:bg-white/10 transition-colors">
                <div class="flex-shrink-0 w-6 h-6 bg-yellow-500/20 rounded-full flex items-center justify-center">
                    <span class="text-xs font-bold text-yellow-400">${index + 1}</span>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm text-white truncate" title="${champion.query}">${champion.query}</p>
                </div>
                <div class="flex-shrink-0 text-xs text-gray-400">${champion.tokens.toLocaleString()} tokens</div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    /**
     * Filter and render session cards (Tier 2)
     */
    filterAndRenderSessions() {
        const searchQuery = document.getElementById('session-search')?.value.toLowerCase() || '';
        const filterStatus = document.getElementById('session-filter-status')?.value || 'all';
        const sortBy = document.getElementById('session-sort')?.value || 'recent';

        // Filter sessions
        let filteredSessions = this.sessionsData.filter(session => {
            const matchesSearch = session.name.toLowerCase().includes(searchQuery);
            const matchesStatus = filterStatus === 'all' || session.status === filterStatus;
            return matchesSearch && matchesStatus;
        });

        // Sort sessions
        filteredSessions.sort((a, b) => {
            switch (sortBy) {
                case 'recent':
                    return (b.last_updated || '').localeCompare(a.last_updated || '');
                case 'oldest':
                    return (a.created_at || '').localeCompare(b.created_at || '');
                case 'tokens':
                    return b.total_tokens - a.total_tokens;
                case 'turns':
                    return b.turn_count - a.turn_count;
                default:
                    return 0;
            }
        });

        // Render session cards
        this.renderSessionCards(filteredSessions);
    }

    /**
     * Render session cards in the gallery
     */
    renderSessionCards(sessions) {
        const container = document.getElementById('session-cards-grid');
        if (!container) return;

        if (sessions.length === 0) {
            container.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <p class="text-gray-400">No sessions found</p>
                </div>
            `;
            return;
        }

        const html = sessions.map(session => this.createSessionCard(session)).join('');
        container.innerHTML = html;

        // Add click listeners to cards
        sessions.forEach(session => {
            const card = document.getElementById(`session-card-${session.id}`);
            if (card) {
                card.addEventListener('click', () => this.openInspector(session.id));
            }
        });
    }

    /**
     * Create HTML for a single session card
     */
    createSessionCard(session) {
        const statusColors = {
            success: 'bg-green-500/20 text-green-400 border-green-500/50',
            partial: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
            failed: 'bg-red-500/20 text-red-400 border-red-500/50',
            empty: 'bg-gray-500/20 text-gray-400 border-gray-500/50'
        };

        const statusColor = statusColors[session.status] || statusColors.empty;
        const date = session.created_at ? new Date(session.created_at).toLocaleString() : 'Unknown';

        return `
            <div id="session-card-${session.id}" class="bg-white/5 backdrop-blur-sm rounded-xl p-4 border border-white/10 hover:border-teradata-orange/50 transition-all cursor-pointer group">
                <div class="flex items-start justify-between mb-3">
                    <h3 class="text-white font-semibold truncate flex-1 group-hover:text-teradata-orange transition-colors" title="${session.name}">
                        ${session.name}
                    </h3>
                    <span class="px-2 py-1 text-xs font-semibold rounded border ${statusColor} flex-shrink-0 ml-2">
                        ${session.status}
                    </span>
                </div>
                
                <div class="space-y-2 text-sm">
                    <div class="flex items-center justify-between text-gray-400">
                        <span>Model:</span>
                        <span class="text-white font-medium">${session.provider}/${session.model}</span>
                    </div>
                    <div class="flex items-center justify-between text-gray-400">
                        <span>Turns:</span>
                        <span class="text-white font-medium">${session.turn_count}</span>
                    </div>
                    <div class="flex items-center justify-between text-gray-400">
                        <span>Tokens:</span>
                        <span class="text-white font-medium">${session.total_tokens.toLocaleString()}</span>
                    </div>
                    <div class="flex items-center justify-between text-gray-400">
                        <span>Created:</span>
                        <span class="text-white text-xs">${date}</span>
                    </div>
                </div>
                
                ${session.has_rag ? `
                    <div class="mt-3 pt-3 border-t border-white/10 flex items-center gap-2 text-xs text-green-400">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                        </svg>
                        RAG Enhanced
                    </div>
                ` : ''}
            </div>
        `;
    }

    /**
     * Open the deep dive inspector (Tier 3)
     */
    async openInspector(sessionId) {
        console.log('Opening inspector for session:', sessionId);
        this.currentSessionId = sessionId;

        // Show inspector modal
        const inspector = document.getElementById('deep-dive-inspector');
        if (inspector) {
            inspector.classList.remove('hidden');
        }

        // Load session details
        try {
            const headers = this._getHeaders();
            const response = await fetch(`/api/v1/sessions/${sessionId}/details`, { headers });
            if (!response.ok) {
                throw new Error('Failed to fetch session details');
            }

            const sessionData = await response.json();
            this.renderInspector(sessionData);
        } catch (error) {
            console.error('Error loading session details:', error);
            alert('Failed to load session details: ' + error.message);
            this.closeInspector();
        }
    }

    /**
     * Render inspector content
     */
    renderInspector(sessionData) {
        // Update header
        document.getElementById('inspector-session-name').textContent = sessionData.name || 'Unnamed Session';
        document.getElementById('inspector-session-meta').textContent = 
            `Created: ${new Date(sessionData.created_at).toLocaleString()} • ID: ${sessionData.id}`;

        // Update stats
        const workflow = sessionData.last_turn_data?.workflow_history || [];
        const turnCount = workflow.filter(t => t.isValid !== false).length;
        
        document.getElementById('inspector-turn-count').textContent = turnCount;
        document.getElementById('inspector-total-tokens').textContent = 
            (sessionData.input_tokens + sessionData.output_tokens).toLocaleString();
        document.getElementById('inspector-model').textContent = `${sessionData.provider}/${sessionData.model}`;
        
        const ragCases = sessionData.rag_cases || [];
        document.getElementById('inspector-rag-count').textContent = ragCases.length;

        // Render timeline
        this.renderTimeline(workflow);

        // Render RAG cases if any
        if (ragCases.length > 0) {
            document.getElementById('inspector-rag-section').classList.remove('hidden');
            this.renderRAGCases(ragCases);
        } else {
            document.getElementById('inspector-rag-section').classList.add('hidden');
        }
    }

    /**
     * Render execution timeline
     */
    renderTimeline(workflow) {
        const container = document.getElementById('inspector-timeline');
        if (!container) return;

        if (!workflow || workflow.length === 0) {
            container.innerHTML = '<p class="text-gray-400">No timeline data available</p>';
            return;
        }

        const html = workflow.map((turn, index) => {
            if (turn.isValid === false) return '';

            const hasError = turn.execution_trace?.some(entry => 
                entry.result?.status === 'error'
            );

            return `
                <div class="flex gap-4">
                    <div class="flex flex-col items-center">
                        <div class="w-8 h-8 rounded-full ${hasError ? 'bg-red-500/20' : 'bg-blue-500/20'} flex items-center justify-center">
                            <span class="text-sm font-bold ${hasError ? 'text-red-400' : 'text-blue-400'}">${turn.turn_number || index + 1}</span>
                        </div>
                        ${index < workflow.length - 1 ? '<div class="w-0.5 h-12 bg-white/10"></div>' : ''}
                    </div>
                    <div class="flex-1 pb-8">
                        <div class="bg-white/5 rounded-lg p-4 border border-white/10">
                            <p class="text-white font-semibold mb-2">${turn.user_query || 'Query ' + (index + 1)}</p>
                            <p class="text-gray-400 text-sm mb-2">${turn.final_summary || 'No summary available'}</p>
                            <div class="flex items-center gap-4 text-xs text-gray-500">
                                <span>Tokens: ${(turn.turn_input_tokens || 0) + (turn.turn_output_tokens || 0)}</span>
                                <span>Time: ${turn.timestamp ? new Date(turn.timestamp).toLocaleTimeString() : 'Unknown'}</span>
                                ${turn.task_id ? `<span>Task: ${turn.task_id.substring(0, 8)}...</span>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        container.innerHTML = html;
    }

    /**
     * Render RAG efficiency cases
     */
    renderRAGCases(ragCases) {
        const container = document.getElementById('inspector-rag-cases');
        if (!container) return;

        const html = ragCases.map(ragCase => `
            <div class="bg-white/5 rounded-lg p-4 border border-white/10">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-white font-semibold">Case ${ragCase.case_id.substring(0, 8)}</span>
                    ${ragCase.is_most_efficient ? `
                        <span class="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs font-semibold rounded border border-yellow-500/50">
                            Most Efficient
                        </span>
                    ` : ''}
                </div>
                <div class="text-sm space-y-1">
                    <p class="text-gray-400">Turn: ${ragCase.turn_id || 'Unknown'}</p>
                    <p class="text-gray-400">Tokens: ${ragCase.output_tokens || 0}</p>
                    <p class="text-gray-400">Collection: ${ragCase.collection_id || 0}</p>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }

    /**
     * Close the inspector
     */
    closeInspector() {
        const inspector = document.getElementById('deep-dive-inspector');
        if (inspector) {
            inspector.classList.add('hidden');
        }
        this.currentSessionId = null;
    }

    /**
     * Export current session as JSON
     */
    async exportSessionAsJSON() {
        if (!this.currentSessionId) return;

        try {
            const headers = this._getHeaders();
            const response = await fetch(`/api/v1/sessions/${this.currentSessionId}/details`, { headers });
            const sessionData = await response.json();

            const dataStr = JSON.stringify(sessionData, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `session_${this.currentSessionId}.json`;
            link.click();
            
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Export failed:', error);
            alert('Failed to export session: ' + error.message);
        }
    }

    /**
     * Export current session as formatted report
     */
    async exportSessionAsReport() {
        if (!this.currentSessionId) return;

        try {
            const headers = this._getHeaders();
            const response = await fetch(`/api/v1/sessions/${this.currentSessionId}/details`, { headers });
            const sessionData = await response.json();

            const workflow = sessionData.last_turn_data?.workflow_history || [];
            const ragCases = sessionData.rag_cases || [];

            const report = `
EXECUTION REPORT
================

Session: ${sessionData.name}
ID: ${sessionData.id}
Created: ${new Date(sessionData.created_at).toLocaleString()}
Model: ${sessionData.provider}/${sessionData.model}

STATISTICS
----------
Total Turns: ${workflow.filter(t => t.isValid !== false).length}
Total Tokens: ${sessionData.input_tokens + sessionData.output_tokens}
  - Input: ${sessionData.input_tokens}
  - Output: ${sessionData.output_tokens}
RAG Cases: ${ragCases.length}

EXECUTION TIMELINE
------------------
${workflow.map((turn, i) => {
    if (turn.isValid === false) return '';
    return `
Turn ${turn.turn_number || i + 1}:
Query: ${turn.user_query || 'N/A'}
Summary: ${turn.final_summary || 'N/A'}
Tokens: ${(turn.turn_input_tokens || 0) + (turn.turn_output_tokens || 0)}
Time: ${turn.timestamp ? new Date(turn.timestamp).toLocaleString() : 'Unknown'}
`;
}).join('\n')}

${ragCases.length > 0 ? `
RAG EFFICIENCY CASES
--------------------
${ragCases.map(c => `
Case ID: ${c.case_id}
Turn: ${c.turn_id}
Most Efficient: ${c.is_most_efficient ? 'Yes' : 'No'}
Tokens: ${c.output_tokens || 0}
`).join('\n')}
` : ''}
            `.trim();

            const blob = new Blob([report], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `session_report_${this.currentSessionId}.txt`;
            link.click();
            
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Export failed:', error);
            alert('Failed to export report: ' + error.message);
        }
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        const grid = document.getElementById('session-cards-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <p class="text-gray-400">Loading sessions...</p>
                </div>
            `;
        }
    }

    /**
     * Show error state
     */
    showErrorState(message) {
        const grid = document.getElementById('session-cards-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="col-span-full text-center py-12">
                    <p class="text-red-400">Error loading dashboard: ${message}</p>
                </div>
            `;
        }
    }
}

// Export for use in main.js
window.ExecutionDashboard = ExecutionDashboard;
