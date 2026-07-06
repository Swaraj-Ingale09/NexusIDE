// NexusIDE - Main JavaScript
console.log('NexusIDE loaded');

// Auth helpers
const Auth = {
    getToken() {
        return localStorage.getItem('access_token');
    },
    
    setToken(access, refresh) {
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
    },
    
    clearToken() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    },
    
    isAuthenticated() {
        return !!this.getToken();
    },
    
    logout() {
        this.clearToken();
        window.location.href = '/';
    }
};

// API helpers
const API = {
    baseURL: '/api',
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const token = Auth.getToken();
        const timeout = options.timeout || 15000;
        const controller = new AbortController();
        const signal = options.signal || controller.signal;
        const timer = setTimeout(() => controller.abort(), timeout);

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers,
                signal
            });
            
            if (response.status === 401) {
                Auth.logout();
                return null;
            }
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`API Error ${response.status}: ${errorText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        } finally {
            clearTimeout(timer);
        }
    },
    
    get(endpoint) {
        if (window.apiCache && typeof window.apiCache.fetch === 'function') {
            return window.apiCache.fetch(`${this.baseURL}${endpoint}`);
        }
        return this.request(endpoint);
    },
    
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
};

// UI helpers
const UI = {
    showLoading(element) {
        element.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';
    },
    
    showError(element, message) {
        element.innerHTML = `<div class="alert alert-danger">${message}</div>`;
    },
    
    showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        document.body.insertBefore(alert, document.body.firstChild);
    }
};

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    if (!Auth.isAuthenticated() && window.location.pathname.startsWith('/dashboard')) {
        window.location.href = '/login/';
    }
});
