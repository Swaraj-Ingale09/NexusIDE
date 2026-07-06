/**
 * Monaco Editor Setup for NexusIDE
 * Proper initialization with responsive layout support
 */

let editor = null;
let isEditorReady = false;

// Configure Monaco paths
require.config({ 
    paths: { 
        'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' 
    } 
});

/**
 * Initialize Monaco Editor
 */
require(['vs/editor/editor.main'], function() {
    const editorContainer = document.getElementById('editor-container');
    
    if (!editorContainer) {
        console.error('Editor container not found');
        return;
    }

    // Load saved code or use default
    const savedCode = localStorage.getItem('nexusIDE-code') || 
        `# Welcome to NexusIDE
# Start coding or use AI assistance to get suggestions

print("Hello, NexusIDE!")`;

    // Define NexusIDE Dark Theme FIRST — before editor creation
    defineEditorTheme();

    // Create editor instance
    editor = monaco.editor.create(editorContainer, {
        value: savedCode,
        language: 'python',
        theme: 'nexuside-dark',
        fontSize: 14,
        fontFamily: '"Fira Code", "Courier New", monospace',
        automaticLayout: false, // We manage layout manually for smoother resizing
        minimap: { enabled: true, size: 'proportional' },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        formatOnPaste: true,
        formatOnType: true,
        suggestOnTriggerCharacters: true,
        lineNumbers: 'on',
        glyphMargin: true,
        folding: true,
        lineDecorationsWidth: 10,
        padding: { top: 16, bottom: 16 },
        renderLineHighlight: 'all',
        smoothScrolling: true,
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: true,
        tabSize: 4,
        insertSpaces: true,
        roundedSelection: false,
        readOnly: false,
        scrollbar: {
            vertical: 'auto',
            horizontal: 'auto',
            useShadows: true,
            verticalSliderSize: 12,
            horizontalSliderSize: 12,
        }
    });

    // Register Python completions
    registerPythonCompletions();

    // Keyboard shortcuts
    setupKeyboardShortcuts();

    // Mark as ready
    isEditorReady = true;
    window.dispatchEvent(new Event('monacoReady'));
    console.log('✓ Monaco editor initialized');
});

/**
 * Define custom NexusIDE Dark Theme
 * NOTE: Monaco theme colors only accept 6-digit hex strings (no alpha, no rgba).
 *       Glassmorphism for current-line and scrollbar is handled via CSS overrides
 *       in editor.css with !important — this just sets the base palette.
 */
function defineEditorTheme() {
    monaco.editor.defineTheme('nexuside-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [
            { token: 'comment',  foreground: '6b7280', fontStyle: 'italic' },
            { token: 'string',   foreground: '10b981' },
            { token: 'number',   foreground: 'f59e0b' },
            { token: 'builtin',  foreground: '06b6d4' },
            { token: 'keyword',  foreground: '7c3aed' },
            { token: 'variable', foreground: 'e2e8f0' },
            { token: 'type',     foreground: 'f59e0b' },
        ],
        colors: {
            'editor.background':                    '#0b0f1a',
            'editor.foreground':                    '#f1f5f9',

            /* Current-line: keep fully transparent so CSS backdrop-filter shows */
            'editor.lineHighlightBackground':       '#0b0f1a00',
            'editor.lineHighlightBorder':           '#00000000',

            'editor.selectionBackground':           '#22d3ee22',
            'editor.selectionHighlightBackground':  '#7c3aed18',
            'editor.inactiveSelectionBackground':   '#22d3ee14',
            'editor.hoverHighlightBackground':      '#22d3ee10',
            'editor.rangeHighlightBackground':      '#22d3ee0c',

            'editorCursor.foreground':              '#22d3ee',
            'editorLineNumber.foreground':          '#64748b',
            'editorLineNumber.activeForeground':    '#22d3ee',

            'editorBracketMatch.background':        '#22d3ee22',
            'editorBracketMatch.border':            '#22d3ee88',

            'editorWhitespace.foreground':          '#ffffff10',
            'editorIndentGuide.background':         '#ffffff08',
            'editorIndentGuide.activeBackground':   '#22d3ee22',

            /* Scrollbar: set near-transparent so CSS override takes full effect */
            'scrollbar.shadow':                     '#00000000',
            'scrollbarSlider.background':           '#7c3aed20',
            'scrollbarSlider.hoverBackground':      '#22d3ee25',
            'scrollbarSlider.activeBackground':     '#22d3ee55',
        }
    });

    monaco.editor.setTheme('nexuside-dark');
}

/**
 * Register Python language completions and snippets
 */
function registerPythonCompletions() {
    monaco.languages.registerCompletionItemProvider('python', {
        triggerCharacters: ['.'],
        provideCompletionItems: function(model, position) {
            const suggestions = [
                // Built-in functions
                {
                    label: 'print()',
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'print(${1:"Hello"})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'Print to stdout'
                },
                {
                    label: 'len()',
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'len(${1:object})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'Return length'
                },
                {
                    label: 'range()',
                    kind: monaco.languages.CompletionItemKind.Function,
                    insertText: 'range(${1:10})',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'Create range'
                },
                // Common snippets
                {
                    label: 'for loop',
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'for ${1:i} in range(${2:10}):\n\t${3:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'For loop'
                },
                {
                    label: 'if statement',
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'if ${1:condition}:\n\t${2:pass}\nelse:\n\t${3:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'If-else block'
                },
                {
                    label: 'while loop',
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'while ${1:True}:\n\t${2:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'While loop'
                },
                {
                    label: 'try-except',
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'try:\n\t${1:pass}\nexcept ${2:Exception}:\n\t${3:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'Try-except block'
                },
                {
                    label: 'def function',
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'def ${1:func_name}(${2:args}):\n\t"""${3:docstring}"""\n\t${4:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'Function definition'
                },
                {
                    label: 'class definition',
                    kind: monaco.languages.CompletionItemKind.Snippet,
                    insertText: 'class ${1:ClassName}:\n\t"""${2:docstring}"""\n\tdef __init__(self${3:, args}):\n\t\t${4:pass}',
                    insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                    detail: 'Class definition'
                }
            ];
            return { suggestions: suggestions };
        }
    });
}

/**
 * Setup custom keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    if (!editor) return;

    // Ctrl+Enter / Cmd+Enter to run code
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
        const executeBtn = document.getElementById('execute-btn');
        if (executeBtn) executeBtn.click();
    });

    // Ctrl+Shift+F to format (if formatter is available)
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyF, () => {
        if (typeof window.formatCode === 'function') {
            window.formatCode();
        } else {
            console.log('Formatter not available');
        }
    });
}

/**
 * Get current editor code
 */
function getEditorCode() {
    return editor ? editor.getValue() : '';
}

/**
 * Set editor code
 */
function setEditorCode(code) {
    if (editor) {
        editor.setValue(code);
    }
}

/**
 * Manual layout trigger (called by layout manager during resizing)
 */
function triggerEditorLayout() {
    if (editor && typeof editor.layout === 'function') {
        try {
            editor.layout();
        } catch (e) {
            console.error('Layout error:', e);
        }
    }
}

/**
 * Format code (hook for formatter)
 */
window.formatCode = function() {
    console.log('Code formatting requested');
    // Will be implemented with the formatter endpoint
};

/**
 * Add marker/diagnostics
 */
window.setEditorMarkers = function(markers) {
    if (editor) {
        monaco.editor.setModelMarkers(editor.getModel(), 'nexuside', markers || []);
    }
};

// Make editor accessible globally
window.getEditorCode = getEditorCode;
window.setEditorCode = setEditorCode;
window.triggerEditorLayout = triggerEditorLayout;

console.log('✓ Monaco setup loaded');
