/**
 * Realistic Activity Tracker
 * Logs REAL user activities - no padding, actual metrics only
 */

class RealisticActivityTracker {
    constructor() {
        this.heartbeatInterval = 60000; // 1 minute
        this.lastPage = window.location.pathname;
        this.isActive = true;
        this.init();
    }

    init() {
        // Send heartbeat every minute unless a dedicated heartbeat manager is already active
        if (!window.userHeartbeatActive) {
            setInterval(() => this.sendHeartbeat(), this.heartbeatInterval);
            // Initial heartbeat
            this.sendHeartbeat();
        } else {
            console.debug('RealisticActivityTracker: heartbeat suppressed because dedicated heartbeat manager is active');
        }
        
        // Track page changes
        window.addEventListener('hashchange', () => this.trackPageView());
        
        // Track visibility
        document.addEventListener('visibilitychange', () => {
            this.isActive = !document.hidden;
        });
    }

    /**
     * Send heartbeat to server
     */
    sendHeartbeat() {
        if (!this.isActive) return;

        const data = {
            page: window.location.pathname + window.location.hash,
        };

        fetch('/api/heartbeat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify(data)
        }).catch(err => console.debug('Heartbeat error:', err));
    }

    /**
     * Track page view
     */
    trackPageView() {
        const page = window.location.pathname + window.location.hash;
        if (page === this.lastPage) return;

        this.lastPage = page;
        this.logActivity('page_view', `Viewed ${page}`);
    }

    /**
     * Track code execution - called by compiler
     * @param {string} language - Programming language
     * @param {number} time - Execution time in seconds
     * @param {string} status - 'success' or 'error'
     * @param {string} error - Error message if failed
     */
    trackCodeExecution(language, time, status, error = '') {
        const data = {
            language: language,
            execution_time: time,
            status: status,
            error: error,
        };

        fetch('/api/track/execution/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify(data)
        })
        .then(r => r.json())
        .then(data => console.debug('Execution tracked:', data))
        .catch(err => console.debug('Tracking error:', err));
    }

    /**
     * Track AI usage - called by AI service
     * @param {string} action - AI action type (chat, analysis, etc)
     * @param {number} tokens - Tokens used
     * @param {number} time - Response time in seconds
     * @param {string} provider - AI provider (openai, claude, etc)
     */
    trackAIUsage(action, tokens, time, provider = 'unknown') {
        const data = {
            action: action,
            tokens: tokens,
            response_time: time,
            provider: provider,
        };

        fetch('/api/track/ai-usage/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify(data)
        })
        .then(r => r.json())
        .then(data => console.debug('AI usage tracked:', data))
        .catch(err => console.debug('Tracking error:', err));
    }

    /**
     * Track snippet creation
     * @param {string} language - Programming language
     * @param {number} lines - Number of lines
     */
    trackSnippetCreation(language, lines) {
        const data = {
            language: language,
            lines: lines,
        };

        fetch('/api/activity/log/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify(data)
        })
        .catch(err => console.debug('Tracking error:', err));
    }

    /**
     * Log a generic activity
     * @param {string} type - Activity type
     * @param {string} description - Description
     */
    logActivity(type, description) {
        const data = {
            activity_type: type,
            description: description,
        };

        fetch('/api/activity/log/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken(),
            },
            body: JSON.stringify(data)
        })
        .catch(err => console.debug('Activity logging error:', err));
    }

    /**
     * Get CSRF token from DOM
     */
    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    /**
     * Get user stats - shows REAL data
     */
    async getUserStats(days = 30) {
        try {
            const response = await fetch(`/api/user/stats/?days=${days}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            return data;
        } catch (err) {
            console.error('Error fetching stats:', err);
            return null;
        }
    }

    /**
     * Get admin dashboard stats - admin only
     */
    async getDashboardStats(days = 30) {
        try {
            const response = await fetch(`/api/admin/dashboard/realistic/?days=${days}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            return data;
        } catch (err) {
            console.error('Error fetching dashboard:', err);
            return null;
        }
    }
}

// Initialize tracker when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.activityTracker = new RealisticActivityTracker();
    });
} else {
    window.activityTracker = new RealisticActivityTracker();
}
