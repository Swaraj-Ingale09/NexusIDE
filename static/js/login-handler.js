// Enhanced Login Handler with Persistent Session
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    const rememberMeCheckbox = document.getElementById('remember-me');

    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const rememberMe = rememberMeCheckbox ? rememberMeCheckbox.checked : true;

            try {
                const response = await fetch('/api/auth/login/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: username,
                        password: password
                    })
                });

                const data = await response.json();

                if (data.success && data.access) {
                    // Save tokens using auth manager
                    authManager.saveSession(
                        data.access,
                        data.refresh,
                        data.user,
                        7 * 24 * 60 * 60 // 7 days
                    );

                    // Show success message
                    showNotification('✅ Login successful! Redirecting...', 'success');

                    // Redirect to dashboard or home after 1.5 seconds
                    setTimeout(() => {
                        window.location.href = '/compiler/';
                    }, 1500);
                } else {
                    showNotification('❌ ' + (data.error || 'Login failed'), 'error');
                }
            } catch (error) {
                showNotification('❌ Connection error: ' + error.message, 'error');
            }
        });
    }

    // Handle logout
    const logoutBtn = document.querySelector('a[href="/logout/"]');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            authManager.logout();
        });
    }
});

// Global notification function
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        border-radius: 8px;
        animation: slideInRight 0.3s ease;
    `;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);
