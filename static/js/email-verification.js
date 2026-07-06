/**
 * Email Verification System
 * Handles all email verification flows and UI
 */

class EmailVerificationManager {
  constructor() {
    this.isVerified = false;
    this.userEmail = null;
    this.verificationType = 'send'; // 'send' or 'verify'
    this.loading = false;
    this.init();
  }

  async init() {
    /**
     * Initialize email verification system
     * Check current verification status
     */
    await this.checkVerificationStatus();
    this.setupEventListeners();
  }

  async checkVerificationStatus() {
    /**
     * Fetch current email verification status from API
     */
    try {
      const response = await fetch('/api/email-verification/check/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        this.isVerified = data.email_verified;
        this.userEmail = data.email;
        this.updateUI();
      }
    } catch (err) {
      console.error('Failed to check verification status:', err);
    }
  }

  setupEventListeners() {
    /**
     * Setup event listeners for verification buttons and forms
     */
    // Note: Actual event listeners are set up in Alpine.js context
    // This is a utility method for manual setup if needed
  }

  async sendVerificationCode() {
    /**
     * Send verification code to user's email
     * Code will appear in server console (development)
     */
    if (this.loading) return;

    this.loading = true;
    try {
      const response = await fetch('/api/email-verification/send/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
        },
        body: JSON.stringify({})
      });

      const data = await response.json();

      if (response.ok) {
        return {
          success: true,
          message: data.message,
          email: this.userEmail
        };
      } else {
        return {
          success: false,
          error: data.error || 'Failed to send verification code'
        };
      }
    } catch (err) {
      return {
        success: false,
        error: 'Network error: ' + err.message
      };
    } finally {
      this.loading = false;
    }
  }

  async verifyCode(code) {
    /**
     * Verify email with 6-digit code
     * @param {string} code - 6-digit verification code
     */
    if (this.loading) return;

    if (!code || code.length !== 6 || !/^\d+$/.test(code)) {
      return {
        success: false,
        error: 'Please enter a valid 6-digit code'
      };
    }

    this.loading = true;
    try {
      const response = await fetch('/api/email-verification/verify/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`
        },
        body: JSON.stringify({ token: code })
      });

      const data = await response.json();

      if (response.ok) {
        this.isVerified = true;
        this.updateUI();
        return {
          success: true,
          message: data.message
        };
      } else {
        return {
          success: false,
          error: data.error || 'Verification failed'
        };
      }
    } catch (err) {
      return {
        success: false,
        error: 'Network error: ' + err.message
      };
    } finally {
      this.loading = false;
    }
  }

  updateUI() {
    /**
     * Update UI to reflect verification status
     */
    const statusElement = document.getElementById('emailVerificationStatus');
    if (statusElement) {
      if (this.isVerified) {
        statusElement.innerHTML = `
          <div class="alert alert-success" role="alert">
            <i class="fas fa-check-circle me-2"></i>
            <strong>Email Verified!</strong> Your email address has been verified.
          </div>
        `;
        statusElement.className = 'verified';
      } else {
        statusElement.innerHTML = `
          <div class="alert alert-warning" role="alert">
            <i class="fas fa-exclamation-circle me-2"></i>
            <strong>Email Not Verified</strong> Please verify your email address to access all features.
          </div>
        `;
        statusElement.className = 'unverified';
      }
    }

    // Dispatch custom event for other components to listen to
    window.dispatchEvent(new CustomEvent('emailVerificationStatusChanged', {
      detail: { verified: this.isVerified, email: this.userEmail }
    }));
  }

  getVerificationBadge() {
    /**
     * Get HTML badge showing verification status
     */
    if (this.isVerified) {
      return '<span class="badge bg-success"><i class="fas fa-check"></i> Verified</span>';
    } else {
      return '<span class="badge bg-warning"><i class="fas fa-exclamation"></i> Pending</span>';
    }
  }

  isEmailVerified() {
    return this.isVerified;
  }

  getEmail() {
    return this.userEmail;
  }
}

// Create global instance
window.emailVerificationManager = new EmailVerificationManager();

/**
 * Alpine.js helper function for email verification modal
 */
function emailVerificationApp() {
  return {
    step: 1, // 1: Send, 2: Verify
    code: '',
    loading: false,
    errorMessage: '',
    successMessage: '',
    email: '',

    async init() {
      this.email = window.emailVerificationManager.userEmail;
    },

    async sendCode() {
      this.loading = true;
      this.errorMessage = '';
      this.successMessage = '';

      const result = await window.emailVerificationManager.sendVerificationCode();

      if (result.success) {
        this.successMessage = result.message;
        this.step = 2;
        // Auto-focus the code input
        setTimeout(() => {
          const codeInput = document.getElementById('verificationCodeInput');
          if (codeInput) codeInput.focus();
        }, 100);
      } else {
        this.errorMessage = result.error;
      }

      this.loading = false;
    },

    async verifyCode() {
      if (!this.code || this.code.length !== 6) {
        this.errorMessage = 'Please enter a valid 6-digit code';
        return;
      }

      this.loading = true;
      this.errorMessage = '';
      this.successMessage = '';

      const result = await window.emailVerificationManager.verifyCode(this.code);

      if (result.success) {
        this.successMessage = result.message;
        // Auto-close modal after 2 seconds
        setTimeout(() => {
          this.closeModal();
        }, 2000);
      } else {
        this.errorMessage = result.error;
      }

      this.loading = false;
    },

    closeModal() {
      this.step = 1;
      this.code = '';
      this.errorMessage = '';
      this.successMessage = '';
      const modal = document.getElementById('emailVerificationModal');
      if (modal) {
        modal.style.display = 'none';
      }
    },

    openModal() {
      const modal = document.getElementById('emailVerificationModal');
      if (modal) {
        modal.style.display = 'flex';
        this.step = 1;
        this.code = '';
        this.errorMessage = '';
        this.successMessage = '';
      }
    },

    handleCodeInput(event) {
      // Only allow digits
      this.code = event.target.value.replace(/[^\d]/g, '').slice(0, 6);
      // Auto-submit when 6 digits entered
      if (this.code.length === 6) {
        setTimeout(() => this.verifyCode(), 100);
      }
    }
  };
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', function() {
  // Check if already authenticated
  const token = localStorage.getItem('access_token');
  if (token) {
    // Verify verification status periodically
    setInterval(() => {
      window.emailVerificationManager.checkVerificationStatus();
    }, 60000); // Check every minute
  }
});

/**
 * Utility function to display verification status in navbar/header
 */
function updateVerificationBadge() {
  const badge = document.getElementById('emailVerificationBadge');
  if (badge && window.emailVerificationManager) {
    badge.innerHTML = window.emailVerificationManager.getVerificationBadge();
  }
}

// Update badge whenever status changes
window.addEventListener('emailVerificationStatusChanged', updateVerificationBadge);
