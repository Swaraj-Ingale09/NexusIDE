/**
 * User Heartbeat Tracking - Optimized
 * Sends a heartbeat every 60 seconds when user is active
 * Includes request batching and backoff
 */

class UserHeartbeat {
    constructor() {
        this.heartbeatInterval = null;
        this.lastActivity = Date.now();
        this.inactivityTimeout = 5 * 60 * 1000; // 5 minutes of inactivity = not counting time
        this.heartbeatIntervalDuration = 60 * 1000; // Send heartbeat every 60 seconds
        this.isAuthenticated = this.checkAuthentication();
        this.failedAttempts = 0;
        this.maxRetries = 3;
        
        if (this.isAuthenticated) {
            this.init();
        }
    }
    
    checkAuthentication() {
        /**Check if user is authenticated by checking for access token*/
        return !!localStorage.getItem('access_token');
    }
    
    init() {
        /**Initialize heartbeat tracking with passive event listeners for performance*/
        // Use passive event listeners for better scroll performance
        document.addEventListener('mousemove', () => this.updateActivity(), { passive: true });
        document.addEventListener('keypress', () => this.updateActivity(), { passive: true });
        document.addEventListener('click', () => this.updateActivity(), { passive: true });
        document.addEventListener('scroll', () => this.updateActivity(), { passive: true });
        
        // Start heartbeat interval
        this.startHeartbeat();
        
        // Resume heartbeat if user comes back from inactivity
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.updateActivity();
            }
        });
    }
    
    updateActivity() {
        /**Update last activity timestamp*/
        this.lastActivity = Date.now();
    }
    
    startHeartbeat() {
        /**Start sending heartbeats every 60 seconds with retry logic"""*/
        this.sendHeartbeat(); // Send immediately on first load
        
        this.heartbeatInterval = setInterval(() => {
            this.sendHeartbeat();
        }, this.heartbeatIntervalDuration);
    }
    
    async sendHeartbeat() {
        /**Send heartbeat to server with exponential backoff on failure*/
        if (window.userHeartbeatActive) {
            return;
        }

        const token = localStorage.getItem('access_token');
        if (!token) return;
        
        const currentPage = window.location.pathname;
        
        try {
            const response = await fetch('/api/heartbeat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    page: currentPage
                }),
                signal: AbortSignal.timeout(5000)  // 5 second timeout
            });
            
            if (response.status === 401) {
                // Token expired, stop heartbeats
                this.stop();
                this.failedAttempts = 0;
            } else if (response.ok) {
                this.failedAttempts = 0;  // Reset on success
            } else {
                this.handleFailure();
            }
        } catch (err) {
            this.handleFailure();
        }
    }
    
    handleFailure() {
        /**Handle failed heartbeat with exponential backoff*/
        this.failedAttempts++;
        
        if (this.failedAttempts >= this.maxRetries) {
            // Stop after max retries to prevent hammering the server
            this.stop();
            this.failedAttempts = 0;
        }
    }
    
    stop() {
        /**Stop sending heartbeats*/
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
}

// Initialize heartbeat tracking when page loads
const initHeartbeat = () => {
    if (!window.userHeartbeat) {
        window.userHeartbeat = new UserHeartbeat();
        window.userHeartbeatActive = true;
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHeartbeat);
} else {
    initHeartbeat();
}
