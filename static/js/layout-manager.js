/**
 * NexusIDE Layout Manager
 * Smooth, responsive resizable panes with Monaco editor integration
 */

class LayoutManager {
    constructor() {
        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.startEditorSize = 0;
        this.layout = document.querySelector('.editor-layout');
        this.editorContainer = document.querySelector('.editor-container');
        this.divider = document.querySelector('[data-divider]');
        this.outputContainer = document.querySelector('.output-container');
        
        this.isHorizontal = false; // Will detect based on layout direction
        this.minSize = 15; // Minimum % for each pane
        this.maxSize = 85; // Maximum % for each pane
        
        this.layouts = {
            'vertical':      { editor: '62%', output: '38%' },
            'horizontal':    { editor: '50%', output: '50%' },
            'editor-focus':  { editor: '75%', output: '25%' },
            'output-focus':  { editor: '25%', output: '75%' }
        };
        
        this.init();
    }

    init() {
        if (!this.layout || !this.divider || !this.editorContainer || !this.outputContainer) {
            console.warn('LayoutManager: Required DOM elements not found');
            return;
        }

        this.detectOrientation();
        this.setupDividerListeners();
        this.setupLayoutButtons();
        this.loadSavedLayout();
        this.setupWindowResize();
    }

    detectOrientation() {
        // Check if layout is horizontal or vertical based on flex-direction
        const flexDirection = window.getComputedStyle(this.layout).flexDirection;
        this.isHorizontal = flexDirection === 'column';
    }

    setupDividerListeners() {
        if (!this.divider) return;

        // Mouse events
        this.divider.addEventListener('mousedown', (e) => this.onDragStart(e));
        document.addEventListener('mousemove', (e) => this.onDragMove(e));
        document.addEventListener('mouseup', (e) => this.onDragEnd(e));

        // Touch events
        this.divider.addEventListener('touchstart', (e) => this.onDragStart(e));
        document.addEventListener('touchmove', (e) => this.onDragMove(e), { passive: false });
        document.addEventListener('touchend', (e) => this.onDragEnd(e));

        // Visual feedback
        this.divider.style.cursor = this.isHorizontal ? 'row-resize' : 'col-resize';
    }

    onDragStart(e) {
        e.preventDefault();
        this.isDragging = true;

        if (e.touches) {
            this.dragStartX = e.touches[0].clientX;
            this.dragStartY = e.touches[0].clientY;
        } else {
            this.dragStartX = e.clientX;
            this.dragStartY = e.clientY;
        }

        // Get initial size
        if (this.isHorizontal) {
            this.startEditorSize = this.editorContainer.offsetHeight;
        } else {
            this.startEditorSize = this.editorContainer.offsetWidth;
        }

        // Visual feedback
        document.body.style.userSelect = 'none';
        document.body.style.WebkitUserSelect = 'none';
        document.body.style.cursor = this.isHorizontal ? 'row-resize' : 'col-resize';
        this.divider.classList.add('active');
    }

    onDragMove(e) {
        if (!this.isDragging) return;
        e.preventDefault();

        let currentX = e.clientX;
        let currentY = e.clientY;

        if (e.touches) {
            currentX = e.touches[0].clientX;
            currentY = e.touches[0].clientY;
        }

        let delta = 0;
        let totalSize = 0;

        if (this.isHorizontal) {
            delta = currentY - this.dragStartY;
            // Subtract padding (top+bottom = 20px) and divider height (22px)
            totalSize = this.layout.offsetHeight - 20 - 22;
        } else {
            delta = currentX - this.dragStartX;
            // Subtract padding (left+right = 24px) and divider width (22px)
            totalSize = this.layout.offsetWidth - 24 - 22;
        }

        // Calculate new size
        const newEditorSize = this.startEditorSize + delta;
        const editorPercent = (newEditorSize / totalSize) * 100;
        const outputPercent = 100 - editorPercent;

        // Apply size constraints
        if (editorPercent >= this.minSize && editorPercent <= this.maxSize &&
            outputPercent >= this.minSize && outputPercent <= this.maxSize) {
            
            this.editorContainer.style.flex = `0 0 ${editorPercent}%`;
            this.outputContainer.style.flex = `0 0 ${outputPercent}%`;

            // Relayout Monaco editor
            this.relayoutMonaco();
        }
    }

    onDragEnd(e) {
        if (!this.isDragging) return;

        this.isDragging = false;
        document.body.style.userSelect = 'auto';
        document.body.style.WebkitUserSelect = 'auto';
        document.body.style.cursor = 'default';
        this.divider.classList.remove('active');

        // Save layout
        this.saveLayout();

        // Final Monaco relayout
        this.relayoutMonaco();
    }

    relayoutMonaco() {
        // Trigger Monaco editor resize
        if (window.editor && typeof window.editor.layout === 'function') {
            setTimeout(() => {
                try {
                    window.editor.layout();
                } catch (e) {
                    console.error('Monaco layout error:', e);
                }
            }, 0);
        }
    }

    setupLayoutButtons() {
        const buttons = document.querySelectorAll('[data-layout-btn]');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const layoutType = btn.dataset.layoutBtn;
                this.applyLayout(layoutType);
            });
        });
    }

    updateLayoutButtonState(type) {
        document.querySelectorAll('[data-layout-btn]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.layoutBtn === type);
        });
    }

    applyLayout(type) {
        if (!this.layouts[type]) return;

        const layout = this.layouts[type];
        
        // Smooth transition
        this.editorContainer.style.transition = 'flex 0.4s cubic-bezier(0.4, 0, 0.2, 1)';
        this.outputContainer.style.transition = 'flex 0.4s cubic-bezier(0.4, 0, 0.2, 1)';

        this.editorContainer.style.flex = `0 0 ${layout.editor}`;
        this.outputContainer.style.flex = `0 0 ${layout.output}`;

        // Remove transition after animation completes
        setTimeout(() => {
            this.editorContainer.style.transition = '';
            this.outputContainer.style.transition = '';
            this.relayoutMonaco();
        }, 400);

        // Save
        localStorage.setItem('nexuside-layout-preset', type);
        this.updateLayoutButtonState(type);
    }

    saveLayout() {
        if (!this.editorContainer) return;
        const flex = this.editorContainer.style.flex;
        if (flex) {
            localStorage.setItem('nexuside-layout-flex', flex);
        }
    }

    loadSavedLayout() {
        const savedPreset = localStorage.getItem('nexuside-layout-preset');
        const savedFlex = localStorage.getItem('nexuside-layout-flex');

        if (savedPreset && this.layouts[savedPreset]) {
            const layout = this.layouts[savedPreset];
            this.editorContainer.style.flex = `0 0 ${layout.editor}`;
            this.outputContainer.style.flex = `0 0 ${layout.output}`;
            this.updateLayoutButtonState(savedPreset);
        } else if (savedFlex) {
            this.editorContainer.style.flex = savedFlex;
            const percent = parseFloat(savedFlex);
            this.outputContainer.style.flex = `0 0 ${100 - percent}%`;
            this.updateLayoutButtonState(null);
        }

        setTimeout(() => this.relayoutMonaco(), 100);
    }

    setupWindowResize() {
        window.addEventListener('resize', () => {
            this.relayoutMonaco();
        });
    }
}

const initLayoutManager = () => {
    if (!window.layoutManager) {
        window.layoutManager = new LayoutManager();
        console.log('✓ Layout manager initialized');
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initLayoutManager);
} else {
    initLayoutManager();
}
