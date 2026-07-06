// Persistent Login Management for NexusIDE
class PersistentAuthManager {
    constructor() {
        // Server-issued tokens (used across the app)
        this.tokenKey = 'access_token';
        this.refreshTokenKey = 'refresh_token';
        this.userKey = 'nexuside_user';
        this.expiresAtKey = 'nexuside_token_expires_at';
        this.init();
    }


    init() {
        // Check if user is already logged in on page load
        this.checkAndRestoreSession();
        
        // Set up token refresh scheduling
        this.refreshTimer = null;
        this.setupTokenRefresh();
        
        // Clear tokens on logout (listen for logout events)
        window.addEventListener('logout', () => this.clearSession());
    }

    /**
     * Save tokens and user info to localStorage (persistent across refreshes)
     */
    saveSession(accessToken, refreshToken, user, expiresIn = 604800) {
        const expiresAt = Date.now() + (expiresIn * 1000);
        
        localStorage.setItem(this.tokenKey, accessToken);
        localStorage.setItem(this.refreshTokenKey, refreshToken);
        localStorage.setItem(this.userKey, JSON.stringify(user));
        localStorage.setItem(this.expiresAtKey, expiresAt);

        
        // Also set in sessionStorage for current tab
        sessionStorage.setItem(this.tokenKey, accessToken);
        sessionStorage.setItem(this.userKey, JSON.stringify(user));
        
        console.log('✅ Session saved - User will stay logged in');
        
        // Emit auth status change event
        window.dispatchEvent(new Event('authStatusChanged'));
    }

    /**
     * Restore session from localStorage on page load
     */
    checkAndRestoreSession() {
        const accessToken = localStorage.getItem(this.tokenKey);
        const refreshToken = localStorage.getItem(this.refreshTokenKey);
        const user = localStorage.getItem(this.userKey);
        const expiresAt = localStorage.getItem(this.expiresAtKey);

        // If we have tokens, but user/expiresAt isn't stored (current login/register pages only store access/refresh),
        // still consider the user logged in for UI purposes.
        if (accessToken && refreshToken) {
            sessionStorage.setItem(this.tokenKey, accessToken);
            if (user) sessionStorage.setItem(this.userKey, user);
            if (expiresAt) {
                // If we know expiry, keep strict validation.
                if (Date.now() >= parseInt(expiresAt)) {
                    this.refreshAccessToken(refreshToken);
                }
            }
            console.log('✅ Session restored from access/refresh tokens');
            return true;
        }

        if (accessToken && user && expiresAt) {
            const now = Date.now();
            
            // Token still valid
            if (now < parseInt(expiresAt)) {
                sessionStorage.setItem(this.tokenKey, accessToken);
                sessionStorage.setItem(this.userKey, user);
                console.log('✅ Session restored from storage');
                return true;
            }

            
            // Token expired but refresh token available
            if (refreshToken) {
                console.log('🔄 Token expired, attempting to refresh...');
                this.refreshAccessToken(refreshToken);
                return true;
            }
            
            // Both tokens expired, clear session
            this.clearSession();
            return false;
        }
        
        return false;
    }

    /**
     * Refresh access token using refresh token
     */
    async refreshAccessToken(refreshToken) {
        try {
            const response = await fetch('/api/auth/token/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    refresh: refreshToken
                })
            });

            if (response.ok) {
                const data = await response.json();
                const expiresAt = Date.now() + (7 * 24 * 60 * 60 * 1000); // 7 days
                
                localStorage.setItem(this.tokenKey, data.access);
                localStorage.setItem(this.expiresAtKey, expiresAt);
                sessionStorage.setItem(this.tokenKey, data.access);
                
                this.scheduleNextRefresh();
                console.log('✅ Access token refreshed');
                return true;
            } else {
                // Refresh token invalid, clear session
                this.clearSession();
                window.location.href = '/login/';
                return false;
            }
        } catch (error) {
            console.error('Error refreshing token:', error);
            return false;
        }
    }

    /**
     * Set up token refresh timer based on expiry time.
     */
    setupTokenRefresh() {
        this.scheduleNextRefresh();
    }

    scheduleNextRefresh() {
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
            this.refreshTimer = null;
        }

        const expiresAt = localStorage.getItem(this.expiresAtKey);
        if (!expiresAt) return;

        const now = Date.now();
        const expiryTime = parseInt(expiresAt, 10);
        const oneHourInMs = 60 * 60 * 1000;
        const refreshTime = expiryTime - oneHourInMs;
        const delay = Math.max(refreshTime - now, 0);

        if (delay <= 0) {
            const refreshToken = localStorage.getItem(this.refreshTokenKey);
            if (refreshToken) {
                this.refreshAccessToken(refreshToken);
            }
            return;
        }

        this.refreshTimer = setTimeout(() => {
            const refreshToken = localStorage.getItem(this.refreshTokenKey);
            if (refreshToken) {
                this.refreshAccessToken(refreshToken);
            }
        }, delay);
    }

    /**
     * Get current access token
     */
    getAccessToken() {
        return sessionStorage.getItem(this.tokenKey) || localStorage.getItem(this.tokenKey);
    }

    /**
     * Get current user info
     */
    getCurrentUser() {
        const user = sessionStorage.getItem(this.userKey) || localStorage.getItem(this.userKey);
        return user ? JSON.parse(user) : null;
    }

    /**
     * Check if user is logged in
     */
    isLoggedIn() {
        const token = this.getAccessToken();
        if (!token) return false;
        
        // If we have a token but no expiry stored (e.g. raw login/register),
        // treat as logged in (the token itself is the authority).
        const expiresAt = localStorage.getItem(this.expiresAtKey);
        if (!expiresAt) return true;
        
        // Check if token is still within its lifetime
        return Date.now() < parseInt(expiresAt);
    }

    /**
     * Clear session and log out user
     */
    clearSession() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.refreshTokenKey);
        localStorage.removeItem(this.userKey);
        localStorage.removeItem(this.expiresAtKey);
        
        sessionStorage.removeItem(this.tokenKey);
        sessionStorage.removeItem(this.userKey);
        
        console.log('🔓 Session cleared - User logged out');
        
        // Emit auth status change event
        window.dispatchEvent(new Event('authStatusChanged'));
    }

    /**
     * Logout user and clear everything
     */
    logout() {
        this.clearSession();
        window.dispatchEvent(new Event('logout'));
        window.location.href = '/';
    }
}

// Initialize auth manager globally
const authManager = new PersistentAuthManager();

// Debug: expose auth state helpers for logo-manager.js
// (helps ensure isLoggedIn()/getCurrentUser() are available after refresh)
window.authManager = authManager;

