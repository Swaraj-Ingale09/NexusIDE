/**
 * Logo Manager - Dynamically show different logos based on login status
 * Shows admin/user badge when logged in, guest badge when logged out
 */

class LogoManager {
    constructor() {
        this.logoContainer = document.getElementById('logo-container');
        this.init();
    }

    init() {
        // Check initial auth status
        this.updateLogo();

        // Listen for auth changes
        window.addEventListener('authStatusChanged', () => {
            this.updateLogo();
        });

        // Update logo on page focus (in case logged out in another tab)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.updateLogo();
            }
        });

        // Update every 10 seconds for real-time sync across tabs
        setInterval(() => this.updateLogo(), 10000);
    }

    updateLogo() {
        if (!this.logoContainer) return;

        const isLoggedIn = authManager && authManager.isLoggedIn();
        const user = authManager && authManager.getCurrentUser();

        if (isLoggedIn && user) {
            this.showAuthenticatedLogo(user);
        } else {
            this.showGuestLogo();
        }
    }

    showAuthenticatedLogo(user) {
        const isAdmin = user.is_staff || user.is_superuser;
        
        this.logoContainer.innerHTML = `
            <div class="logo-authenticated" style="display: flex; align-items: center; gap: 12px;">
                <div class="logo-badge" style="position: relative; width: 40px; height: 40px;">
                    <svg viewBox="0 0 40 40" style="width: 100%; height: 100%;">
                        <!-- Badge background -->
                        <defs>
                            <linearGradient id="adminGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" style="stop-color: ${isAdmin ? '#00d9ff' : '#06b6d4'}; stop-opacity: 1" />
                                <stop offset="100%" style="stop-color: ${isAdmin ? '#0891b2' : '#0284c7'}; stop-opacity: 1" />
                            </linearGradient>
                            <filter id="adminGlow">
                                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                                <feMerge>
                                    <feMergeNode in="coloredBlur"/>
                                    <feMergeNode in="SourceGraphic"/>
                                </feMerge>
                            </filter>
                        </defs>
                        <!-- Circle background -->
                        <circle cx="20" cy="20" r="18" fill="url(#adminGradient)" filter="url(#adminGlow)"/>
                        <!-- Inner circle -->
                        <circle cx="20" cy="20" r="16" fill="rgba(255,255,255,0.05)"/>
                        <!-- User icon or crown -->
                        ${isAdmin ? this.getCrownSVG() : this.getUserSVG()}
                    </svg>
                </div>
                <div class="logo-info" style="display: flex; flex-direction: column; gap: 2px;">
                    <span style="font-size: 0.75rem; font-weight: 600; color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.5px;">
                        ${isAdmin ? '👑 Admin' : '👤 User'}
                    </span>
                    <span style="font-size: 0.85rem; font-weight: 500; color: #06b6d4;">
                        ${this.truncateName(user.username, 12)}
                    </span>
                </div>
            </div>
        `;

        // Add fade-in animation
        const element = this.logoContainer.querySelector('.logo-authenticated');
        if (element) {
            element.style.animation = 'fadeIn 0.5s ease-in';
        }
    }

    showGuestLogo() {
        this.logoContainer.innerHTML = `
            <div class="logo-guest" style="display: flex; align-items: center; gap: 10px;">
                <div class="logo-badge" style="position: relative; width: 40px; height: 40px;">
                    <svg viewBox="0 0 40 40" style="width: 100%; height: 100%;">
                        <!-- Badge background -->
                        <defs>
                            <linearGradient id="guestGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" style="stop-color: #64748b; stop-opacity: 1" />
                                <stop offset="100%" style="stop-color: #475569; stop-opacity: 1" />
                            </linearGradient>
                            <filter id="guestGlow">
                                <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
                                <feMerge>
                                    <feMergeNode in="coloredBlur"/>
                                    <feMergeNode in="SourceGraphic"/>
                                </feMerge>
                            </filter>
                        </defs>
                        <!-- Circle background -->
                        <circle cx="20" cy="20" r="18" fill="url(#guestGradient)" filter="url(#guestGlow)"/>
                        <!-- Inner circle -->
                        <circle cx="20" cy="20" r="16" fill="rgba(255,255,255,0.03)"/>
                        <!-- Guest icon -->
                        <circle cx="20" cy="12" r="4" fill="#cbd5e1"/>
                        <path d="M 12 22 Q 12 18 20 18 Q 28 18 28 22 L 28 28 Q 28 28 20 28 Q 12 28 12 22" fill="#cbd5e1"/>
                        <!-- Question mark -->
                        <text x="20" y="24" font-size="10" fill="#475569" text-anchor="middle" font-weight="bold">?</text>
                    </svg>
                </div>
                <div class="logo-info" style="display: flex; flex-direction: column; gap: 2px;">
                    <span style="font-size: 0.75rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px;">
                        👤 Guest
                    </span>
                    <span style="font-size: 0.85rem; font-weight: 500; color: #64748b;">
                        Not logged in
                    </span>
                </div>
            </div>
        `;

        // Add fade-in animation
        const element = this.logoContainer.querySelector('.logo-guest');
        if (element) {
            element.style.animation = 'fadeIn 0.5s ease-in';
        }
    }

    getCrownSVG() {
        return `
            <!-- Crown for admin -->
            <g transform="translate(20, 20)">
                <path d="M -6 2 L -3 -4 L 0 2 L 3 -4 L 6 2 Z" fill="#fff" opacity="0.9"/>
                <line x1="-6" y1="2" x2="6" y2="2" stroke="#fff" stroke-width="1" opacity="0.7"/>
            </g>
        `;
    }

    getUserSVG() {
        return `
            <!-- User icon -->
            <circle cx="20" cy="13" r="4" fill="#fff" opacity="0.9"/>
            <path d="M 12 24 Q 12 18 20 18 Q 28 18 28 24" fill="#fff" opacity="0.8"/>
        `;
    }

    truncateName(name, maxLength) {
        if (name.length > maxLength) {
            return name.substring(0, maxLength - 2) + '..';
        }
        return name;
    }
}

// Initialize when document is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        logoManager = new LogoManager();
    });
} else {
    logoManager = new LogoManager();
}
