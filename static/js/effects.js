// Advanced Effects and Animations
class VisualEffects {
    constructor() {
        this.particleCount = Math.min(30, Math.max(15, Math.floor(window.innerWidth / 120)));
        this.init();
    }

    throttle(func, limit) {
        let inThrottle = false;
        return (...args) => {
            if (!inThrottle) {
                func(...args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    init() {
        this.createParticleBackground();
        this.setupAnimations();
        this.setupInteractiveEffects();
    }

    createParticleBackground() {
        const container = document.querySelector('.editor-layout');
        if (!container) return;

        const canvas = document.createElement('canvas');
        canvas.className = 'particle-canvas';
        canvas.id = 'nexuside-particle-canvas';
        canvas.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            opacity: 0.25;
        `;

        const parent = container.parentElement;
        parent.insertBefore(canvas, container);

        const ctx = canvas.getContext('2d');
        const resizeCanvas = () => {
            const dpr = window.devicePixelRatio || 1;
            canvas.width = window.innerWidth * dpr;
            canvas.height = window.innerHeight * dpr;
            canvas.style.width = `${window.innerWidth}px`;
            canvas.style.height = `${window.innerHeight}px`;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };

        resizeCanvas();

        const particles = [];

        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.vx = (Math.random() - 0.5) * 0.5;
                this.vy = (Math.random() - 0.5) * 0.5;
                this.size = Math.random() * 2 + 1;
                this.color = `rgba(0, 217, 255, ${Math.random() * 0.5 + 0.3})`;
            }

            update() {
                this.x += this.vx;
                this.y += this.vy;

                if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
                if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
            }

            draw() {
                ctx.fillStyle = this.color;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        for (let i = 0; i < this.particleCount; i++) {
            particles.push(new Particle());
        }

        let animationFrameId = null;
        const animate = () => {
            if (document.hidden) {
                animationFrameId = requestAnimationFrame(animate);
                return;
            }

            ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

            particles.forEach(p => {
                p.update();
                p.draw();
            });

            // Draw connections
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < 75) {
                        ctx.strokeStyle = `rgba(0, 217, 255, ${0.18 * (1 - distance / 75)})`;
                        ctx.lineWidth = 1;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }

            animationFrameId = requestAnimationFrame(animate);
        };

        animate();

        window.addEventListener('resize', this.throttle(() => {
            resizeCanvas();
        }, 200));

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !animationFrameId) {
                animate();
            }
        });
    }

    setupAnimations() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes glow {
                0%, 100% { box-shadow: 0 0 10px rgba(0, 217, 255, 0.5); }
                50% { box-shadow: 0 0 20px rgba(0, 217, 255, 0.8); }
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }

            @keyframes slideIn {
                from { transform: translateX(-100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @keyframes typewriter {
                from { width: 0; }
                to { width: 100%; }
            }

            @keyframes floating {
                0%, 100% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
            }

            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes fadeInScale {
                from {
                    opacity: 0;
                    transform: scale(0.95);
                }
                to {
                    opacity: 1;
                    transform: scale(1);
                }
            }

            @keyframes shimmer {
                0% {
                    background-position: -1000px 0;
                }
                100% {
                    background-position: 1000px 0;
                }
            }

            @keyframes glow-pulse {
                0%, 100% {
                    box-shadow: 0 0 10px rgba(0, 217, 255, 0.4), 0 0 20px rgba(0, 217, 255, 0.2);
                }
                50% {
                    box-shadow: 0 0 20px rgba(0, 217, 255, 0.8), 0 0 40px rgba(0, 217, 255, 0.4);
                }
            }

            .toolbar-btn:hover {
                animation: glow 1.5s ease-in-out infinite;
            }

            .toolbar-btn:focus {
                animation: fadeInScale 0.3s ease;
            }

            .ai-message {
                animation: fadeInUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .ai-response {
                animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .status-indicator {
                animation: pulse 2s ease-in-out infinite;
            }

            .status-indicator.executing {
                animation: glow-pulse 1.5s ease-in-out infinite;
            }

            .loading-spinner {
                animation: floating 2s ease-in-out infinite;
            }

            .notification {
                animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            }

            .notification-exit {
                animation: slideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1) reverse;
            }
        `;
        document.head.appendChild(style);
    }

    setupInteractiveEffects() {
        // Glow effect on hover using event delegation
        document.body.addEventListener('pointerover', (event) => {
            const btn = event.target.closest('.toolbar-btn, .ai-suggestion-btn');
            if (!btn) return;
            btn.style.boxShadow = '0 0 15px rgba(0, 217, 255, 0.5)';
        });

        document.body.addEventListener('pointerout', (event) => {
            const btn = event.target.closest('.toolbar-btn, .ai-suggestion-btn');
            if (!btn) return;
            btn.style.boxShadow = 'none';
        });

        // Ripple effect on buttons with event delegation
        document.body.addEventListener('click', (event) => {
            const btn = event.target.closest('button');
            if (!btn) return;

            const ripple = document.createElement('span');
            ripple.style.cssText = `
                position: absolute;
                pointer-events: none;
                background: rgba(255, 255, 255, 0.35);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s ease-out;
            `;
            btn.style.position = btn.style.position || 'relative';
            btn.style.overflow = 'hidden';
            btn.appendChild(ripple);

            const rect = btn.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            ripple.style.width = ripple.style.height = `${size}px`;
            ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
            ripple.style.top = `${event.clientY - rect.top - size / 2}px`;

            window.setTimeout(() => ripple.remove(), 600);
        });
    }

    createNotification(message, type = 'info') {
        const notif = document.createElement('div');
        notif.className = `notification notification-${type}`;
        notif.textContent = message;
        notif.style.cssText = `
            position: fixed;
            top: 100px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
            z-index: 9999;
            animation: slideInRight 0.3s ease;
        `;

        document.body.appendChild(notif);
        setTimeout(() => {
            notif.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => notif.remove(), 300);
        }, 3000);
    }
}

// Enable/disable heavy effects from templates for better smoothness.
const ENABLE_EFFECTS = (window.NEXUSIDE_ENABLE_EFFECTS === true);

if (ENABLE_EFFECTS) {
    const visualEffects = new VisualEffects();
}

// Ripple animation (lightweight)
if (!document.getElementById('nexuside-ripple-style')) {
    const style = document.createElement('style');
    style.id = 'nexuside-ripple-style';
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}


