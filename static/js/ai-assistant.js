// AI Assistant Integration with Enhanced Features
class AIAssistant {
    constructor() {
        this.isOpen = false;
        this.messages = [];
        this.isLoading = false;
        // Initialize when DOM is ready so the container exists
        console.info('AIAssistant: constructor called, readyState=', document.readyState);
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    init() {
        // Ensure container exists, then build UI and listeners
        this.ensurePanelExists();
        this.setupUI();
        this.setupEventListeners();
        this.createDebugHandle();

        // Restore previous open state
        try {
            const wasOpen = localStorage.getItem('ai-panel-open') === 'true';
            if (wasOpen) {
                const p = document.querySelector('.ai-chat-container');
                if (p) p.classList.remove('collapsed');
                const btn = document.getElementById('ai-toggle');
                if (btn) btn.classList.add('active');
                this.isOpen = true;
            }
        } catch (e) { /* noop */ }
    }

    ensurePanelExists() {
        let panel = document.querySelector('.ai-chat-container');
        if (!panel) {
            console.warn('AIAssistant: creating missing .ai-chat-container element');
            panel = document.createElement('div');
            panel.className = 'ai-chat-container collapsed';
            document.body.appendChild(panel);
        }
        panel.style.zIndex = '';
        return panel;
    }

    createDebugHandle() {
        // Debug handle removed — use the toolbar "Ask AI" button instead
    }

    setupUI() {
        const chat = document.querySelector('.ai-chat-container');
        if (!chat) {
            console.warn('AIAssistant: .ai-chat-container not found in DOM');
            return;
        }
        console.info('AIAssistant: setting up UI inside .ai-chat-container');

        chat.innerHTML = `
            <!-- Header -->
            <div class="ai-header">
                <div class="ai-header-brand">
                    <div class="ai-brand-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="ai-brand-info">
                        <span class="ai-brand-name">NexusAI</span>
                        <span class="ai-status-badge" id="ai-status-badge">
                            <span class="ai-status-dot" id="ai-status-dot"></span>
                            <span id="ai-status-label">Checking…</span>
                        </span>
                    </div>
                </div>
                <button class="ai-close-btn" onclick="aiAssistant.togglePanel()" title="Close">
                    <i class="fas fa-xmark"></i>
                </button>
            </div>

            <!-- Messages area -->
            <div class="ai-messages" id="ai-messages">
                <!-- Empty state -->
                <div class="ai-empty-state" id="ai-empty-state">
                    <div class="ai-empty-glow"></div>
                    <div class="ai-empty-icon">
                        <i class="fas fa-robot"></i>
                    </div>
                    <p class="ai-empty-title">How can I help?</p>
                    <p class="ai-empty-sub">Pick an action below or type a question about your code.</p>
                </div>
            </div>

            <!-- Quick actions -->
            <div class="ai-actions">
                <button class="ai-action-chip" onclick="aiAssistant.fixCode()">
                    <i class="fas fa-wrench"></i><span>Fix</span>
                </button>
                <button class="ai-action-chip" onclick="aiAssistant.explainCode()">
                    <i class="fas fa-lightbulb"></i><span>Explain</span>
                </button>
                <button class="ai-action-chip" onclick="aiAssistant.optimizeCode()">
                    <i class="fas fa-bolt"></i><span>Optimize</span>
                </button>
                <button class="ai-action-chip" onclick="aiAssistant.formatCode()">
                    <i class="fas fa-align-left"></i><span>Format</span>
                </button>
                <button class="ai-action-chip" onclick="aiAssistant.generateTests()">
                    <i class="fas fa-flask"></i><span>Tests</span>
                </button>
            </div>

            <!-- Input bar -->
            <div class="ai-input-bar">
                <textarea id="ai-input" placeholder="Ask anything about your code…" rows="1"></textarea>
                <button onclick="aiAssistant.sendMessage()" class="ai-send-btn" title="Send (Ctrl+Enter)">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        `;

        this.messagesContainer = document.getElementById('ai-messages');

        // Check AI availability after building UI
        this.checkStatus();
    }

    checkStatus() {
        const dot   = document.getElementById('ai-status-dot');
        const label = document.getElementById('ai-status-label');
        if (!dot || !label) return;

        // Checking state
        dot.className   = 'ai-status-dot checking';
        label.textContent = 'Checking…';

        fetch('/api/ai/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            },
            body: JSON.stringify({ action: 'ping', code: ' ' })
        })
        .then(res => {
            // Any non-network response means the service is reachable
            if (res.ok || res.status === 400) {
                dot.className     = 'ai-status-dot online';
                label.textContent = 'Available';
            } else {
                dot.className     = 'ai-status-dot offline';
                label.textContent = 'Unavailable';
            }
        })
        .catch(() => {
            dot.className     = 'ai-status-dot offline';
            label.textContent = 'Unavailable';
        });
    }

    setupEventListeners() {
        const input = document.getElementById('ai-input');
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                    this.sendMessage();
                }
            });
        }
        
        // Ask AI button from output toolbar
        const askAIOutputBtn = document.getElementById('ask-ai-output-btn');
        if (askAIOutputBtn) {
            askAIOutputBtn.addEventListener('click', () => {
                this.togglePanel();
                this.askAboutOutput();
            });
        }
    }
    
    askAboutOutput() {
        /**Ask AI about the current output*/
        const outputText = document.getElementById('output')?.value || '';
        const code = getEditorCode();
        
        if (!outputText.trim()) {
            this.addMessage('No output to analyze. Run your code first!', true);
            return;
        }
        
        this.addMessage('🔍 Analyzing your output...', true);
        
        // Send to AI for analysis
        this.callAIAPI('analyze', code, `Please analyze this output and explain what's happening:\n\n${outputText}`);
    }

    addMessage(text, isAI = true) {
        // Hide empty state once we have messages
        const emptyState = document.getElementById('ai-empty-state');
        if (emptyState) emptyState.style.display = 'none';

        const msgDiv = document.createElement('div');
        msgDiv.className = `ai-message ${isAI ? 'ai-response' : 'user-message'}`;
        msgDiv.innerHTML = `
            <div class="ai-message-avatar">
                <i class="fas ${isAI ? 'fa-robot' : 'fa-user'}"></i>
            </div>
            <div class="ai-message-content">
                <div class="ai-message-text">${this.escapeHTML(text)}</div>
                ${isAI ? '<div class="ai-message-time">just now</div>' : ''}
            </div>
        `;
        this.messagesContainer.appendChild(msgDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

        if (isAI) this.animateMessage(msgDiv);
    }

    escapeHTML(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    animateMessage(element) {
        element.style.opacity = '0';
        element.style.transform = 'translateY(10px)';
        setTimeout(() => {
            element.style.transition = 'all 0.3s ease';
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, 10);
    }

    fixCode() {
        const code = getEditorCode();
        const error = document.getElementById('error')?.value || '';
        
        if (!code.trim()) {
            this.addMessage('Please write some code first!', true);
            return;
        }

        if (!error.trim()) {
            this.addMessage('No errors detected. Run your code first to identify issues!', true);
            return;
        }

        this.addMessage('🔧 Analyzing and fixing your code...', true);
        this.callAIAPI('fix', code, error);
    }

    explainCode() {
        const code = getEditorCode();
        if (!code.trim()) {
            this.addMessage('Write some code first, and I\'ll explain it!', true);
            return;
        }

        this.addMessage('📖 Explaining your code...', true);
        this.callAIAPI('explain', code);
    }

    optimizeCode() {
        const code = getEditorCode();
        if (!code.trim()) {
            this.addMessage('Write some code first to optimize!', true);
            return;
        }

        this.addMessage('⚡ Analyzing for optimizations...', true);
        this.callAIAPI('optimize', code);
    }

    formatCode() {
        const code = getEditorCode();
        if (!code.trim()) {
            this.addMessage('Write some code first to format!', true);
            return;
        }

        this.addMessage('✨ Formatting your code...', true);
        this.callAIAPI('format', code);
    }

    generateTests() {
        const code = getEditorCode();
        if (!code.trim()) {
            this.addMessage('Write some code first to generate tests!', true);
            return;
        }

        this.addMessage('🧪 Generating unit tests...', true);
        this.callAIAPI('test', code);
    }

    sendMessage() {
        const input = document.getElementById('ai-input');
        const message = input.value.trim();
        if (!message || this.isLoading) return;

        this.addMessage(message, false);
        input.value = '';

        this.addMessage('💭 Thinking...', true);
        this.callAIAPI('chat', getEditorCode(), message);
    }

    callAIAPI(action, code, context = '') {
        if (this.isLoading) return;
        this.isLoading = true;

        // Show busy state in status badge
        const dot   = document.getElementById('ai-status-dot');
        const label = document.getElementById('ai-status-label');
        if (dot)   dot.className   = 'ai-status-dot checking';
        if (label) label.textContent = 'Thinking…';

        // Create the streaming message bubble immediately
        const emptyState = document.getElementById('ai-empty-state');
        if (emptyState) emptyState.style.display = 'none';

        const msgDiv = document.createElement('div');
        msgDiv.className = 'ai-message ai-response';
        msgDiv.innerHTML = `
            <div class="ai-message-avatar"><i class="fas fa-robot"></i></div>
            <div class="ai-message-content">
                <div class="ai-message-text"><span class="ai-cursor">▍</span></div>
                <div class="ai-message-time">just now</div>
            </div>`;
        this.messagesContainer.appendChild(msgDiv);
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

        const targetEl = msgDiv.querySelector('.ai-message-text');
        let fullText = '';

        fetch('/api/ai/v2/stream/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, code, context })
        })
        .then(response => {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            const read = () => {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        // Stream finished

                        // Remove cursor
                        targetEl.innerHTML = this.escapeHTML(fullText).replace(/\\n/g, '\n');
                        this.finishStream(action, fullText, dot, label);
                        return;
                    }

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // keep incomplete line

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            targetEl.innerHTML = this.escapeHTML(fullText).replace(/\\n/g, '\n');
                            this.finishStream(action, fullText, dot, label);
                            return;
                        }
                        if (data.startsWith('[ERROR]')) {
                            targetEl.textContent = data;
                            this.finishStream(action, '', dot, label);
                            return;
                        }
                        // Unescape newlines encoded by the server
                        fullText += data.replace(/\\n/g, '\n');
                        targetEl.textContent = fullText + '▍';
                        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
                    }

                    read(); // continue reading
                }).catch(err => {
                    targetEl.textContent = '❌ Stream error: ' + err.message;
                    this.finishStream(action, '', dot, label);
                });
            };

            read();
        })
        .catch(err => {
            targetEl.textContent = '❌ ' + err.message;
            this.finishStream(action, '', dot, label);
        });
    }

    finishStream(action, fullText, dot, label) {
        this.isLoading = false;
        if (dot)   { dot.className = 'ai-status-dot online'; }
        if (label) { label.textContent = 'Available'; }

        // Apply code to editor for fix/optimize/format actions
        if (['fix', 'optimize', 'format'].includes(action) && fullText && typeof setEditorCode === 'function') {
            const fence = fullText.match(/```(?:\w+)?\s*([\s\S]*?)```/);
            const newCode = fence ? fence[1].trim() : fullText.trim();
            if (newCode) {
                setEditorCode(newCode);
                if (typeof editor !== 'undefined' && editor && typeof editor.layout === 'function') {
                    try { editor.layout(); } catch(e) {}
                }
            }
        }
    }

    togglePanel() {
        let panel = document.querySelector('.ai-chat-container');
        if (!panel) {
            console.warn('AIAssistant: togglePanel called but .ai-chat-container missing, creating one');
            panel = this.ensurePanelExists();
        }

        // If UI wasn't initialized (messagesContainer missing), try to initialize now
        if (!this.messagesContainer) {
            console.info('AIAssistant: messagesContainer missing, attempting setupUI before toggling');
            this.setupUI();
        }

        const wasCollapsed = panel.classList.contains('collapsed');
        const btn = document.getElementById('ai-toggle');
        
        if (wasCollapsed) {
            panel.classList.remove('collapsed');
            panel.style.transform = '';
            panel.style.opacity = '';
            if (btn) btn.classList.add('active');
            console.info('AIAssistant: panel opened');
            this.isOpen = true;
            this.checkStatus();
        } else {
            panel.classList.add('collapsed');
            if (btn) btn.classList.remove('active');
            console.info('AIAssistant: panel collapsed');
            this.isOpen = false;
        }

        try { localStorage.setItem('ai-panel-open', this.isOpen); } catch (e) {}
    }
}

// Expose on window so inline `onclick="aiAssistant.*"` handlers work
window.aiAssistant = new AIAssistant();