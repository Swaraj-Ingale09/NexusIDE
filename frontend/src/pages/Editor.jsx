import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useLocation } from 'react-router-dom';
import api from '../utils/api';
import Editor from '@monaco-editor/react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play, Square, Save, Trash2, ChevronDown, Terminal,
  Sparkles, X, Send, Loader2, Copy, Check,
  Maximize2, Minimize2, FileCode2,
  MessageSquare, Zap, Bug, RefreshCw, GripVertical,
  Clock,
  WrapText, Map,
  Minus, Plus, Keyboard, Code, Braces,
  XCircle, CheckCircle2,
} from 'lucide-react';
import { useTabAutocomplete } from '../hooks/useTabAutocomplete';
import { useAIStreaming } from '../hooks/useAIStreaming';
import SQLPlayground from '../components/SQLPlayground';

const LANGUAGES = [
  { id: 'python', label: 'Python', icon: '🐍', defaultCode: '# Welcome to NexusIDE\nprint("Hello, World!")' },
  { id: 'c', label: 'C', icon: '⚙️', defaultCode: '#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}' },
  { id: 'cpp', label: 'C++', icon: '⚡', defaultCode: '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}' },
  { id: 'sql', label: 'SQL', icon: '🗄️', defaultCode: '-- Welcome to NexusIDE SQL Playground\n-- Try querying the pre-loaded tables:\nSELECT * FROM Customers;' },
];

const TEMPLATES = {
  python: [
    { name: 'Hello World', code: 'print("Hello, World!")' },
    { name: 'For Loop', code: 'for i in range(10):\n    print(i)' },
    { name: 'Function', code: 'def greet(name):\n    return f"Hello, {name}!"\n\nprint(greet("World"))' },
    { name: 'List Comprehension', code: 'squares = [x**2 for x in range(10)]\nprint(squares)' },
    { name: 'Class', code: 'class Person:\n    def __init__(self, name, age):\n        self.name = name\n        self.age = age\n\n    def __str__(self):\n        return f"{self.name}, {self.age}"\n\np = Person("Alice", 30)\nprint(p)' },
    { name: 'Try/Except', code: 'try:\n    result = 10 / 0\nexcept ZeroDivisionError as e:\n    print(f"Error: {e}")' },
    { name: 'File Read', code: 'with open("file.txt", "r") as f:\n    content = f.read()\n    print(content)' },
    { name: 'Matplotlib Plot', code: 'import matplotlib.pyplot as plt\n\nx = [1, 2, 3, 4, 5]\ny = [2, 4, 6, 8, 10]\n\nplt.plot(x, y)\nplt.xlabel("X")\nplt.ylabel("Y")\nplt.title("Simple Plot")\nplt.show()' },
  ],
  c: [
    { name: 'Hello World', code: '#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}' },
    { name: 'For Loop', code: '#include <stdio.h>\n\nint main() {\n    for (int i = 0; i < 10; i++) {\n        printf("%d\\n", i);\n    }\n    return 0;\n}' },
    { name: 'Function', code: '#include <stdio.h>\n\nint add(int a, int b) {\n    return a + b;\n}\n\nint main() {\n    printf("%d\\n", add(3, 4));\n    return 0;\n}' },
    { name: 'Array', code: '#include <stdio.h>\n\nint main() {\n    int arr[] = {1, 2, 3, 4, 5};\n    int n = sizeof(arr) / sizeof(arr[0]);\n    for (int i = 0; i < n; i++) {\n        printf("%d ", arr[i]);\n    }\n    return 0;\n}' },
    { name: 'Struct', code: '#include <stdio.h>\n#include <string.h>\n\nstruct Person {\n    char name[50];\n    int age;\n};\n\nint main() {\n    struct Person p = {"Alice", 30};\n    printf("%s, %d\\n", p.name, p.age);\n    return 0;\n}' },
  ],
  cpp: [
    { name: 'Hello World', code: '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}' },
    { name: 'Vector', code: '#include <iostream>\n#include <vector>\nusing namespace std;\n\nint main() {\n    vector<int> nums = {1, 2, 3, 4, 5};\n    for (int n : nums) {\n        cout << n << " ";\n    }\n    return 0;\n}' },
    { name: 'Class', code: '#include <iostream>\n#include <string>\nusing namespace std;\n\nclass Person {\npublic:\n    string name;\n    int age;\n    Person(string n, int a) : name(n), age(a) {}\n    void display() {\n        cout << name << ", " << age << endl;\n    }\n};\n\nint main() {\n    Person p("Alice", 30);\n    p.display();\n    return 0;\n}' },
    { name: 'Map', code: '#include <iostream>\n#include <map>\nusing namespace std;\n\nint main() {\n    map<string, int> ages;\n    ages["Alice"] = 30;\n    ages["Bob"] = 25;\n    for (auto& [name, age] : ages) {\n        cout << name << ": " << age << endl;\n    }\n    return 0;\n}' },
  ],
  sql: [
    { name: 'Select All Customers', code: 'SELECT * FROM Customers;' },
    { name: 'Select with Filter', code: 'SELECT CustomerName, City, Country\nFROM Customers\nWHERE Country = \'Germany\';' },
    { name: 'Join Query', code: 'SELECT c.CustomerName, p.ProductName, o.Quantity\nFROM Orders o\nJOIN Customers c ON o.CustomerID = c.CustomerID\nJOIN Products p ON o.ProductID = p.ProductID\nORDER BY o.Quantity DESC;' },
    { name: 'Aggregate', code: 'SELECT Country, COUNT(*) AS CustomerCount\nFROM Customers\nGROUP BY Country\nORDER BY CustomerCount DESC;' },
    { name: 'Products Above Average', code: 'SELECT ProductName, Price\nFROM Products\nWHERE Price > (SELECT AVG(Price) FROM Products)\nORDER BY Price DESC;' },
    { name: 'Insert', code: 'INSERT INTO Customers (CustomerName, ContactName, City, Country)\nVALUES (\'New Corp\', \'John Doe\', \'New York\', \'USA\');\n\nSELECT * FROM Customers;' },
  ],
};

const SHORTCUTS = [
  { keys: 'Ctrl + Enter', desc: 'Run code' },
  { keys: 'Ctrl + S', desc: 'Save' },
  { keys: 'Ctrl + /', desc: 'Toggle comment' },
  { keys: 'Ctrl + D', desc: 'Select next occurrence' },
  { keys: 'Ctrl + Shift + K', desc: 'Delete line' },
  { keys: 'Alt + ↑/↓', desc: 'Move line up/down' },
  { keys: 'Ctrl + ]', desc: 'Indent line' },
  { keys: 'Ctrl + [', desc: 'Outdent line' },
  { keys: 'Ctrl + F', desc: 'Find' },
  { keys: 'Ctrl + H', desc: 'Find & Replace' },
];

/* ─── Sophisticated Dark Monaco Theme ─── */
const CLAY_DARK_THEME = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: '', foreground: 'd4d0c8', background: '141a1e' },
    { token: 'comment', foreground: '5a6a6a', fontStyle: 'italic' },
    { token: 'keyword', foreground: 'e06080' },
    { token: 'string', foreground: 'd4a84a' },
    { token: 'number', foreground: 'e09060' },
    { token: 'type', foreground: '9a7acc' },
    { token: 'function', foreground: '5cb8a0' },
    { token: 'variable', foreground: 'd4d0c8' },
    { token: 'operator', foreground: 'e06060' },
    { token: 'delimiter', foreground: '7a8a8a' },
    { token: 'constant', foreground: 'e09060' },
    { token: 'tag', foreground: 'e06080' },
    { token: 'attribute.name', foreground: '9a7acc' },
    { token: 'attribute.value', foreground: 'd4a84a' },
  ],
  colors: {
    'editor.background': '#141a1e',
    'editor.foreground': '#d4d0c8',
    'editor.lineHighlightBackground': '#1c2428',
    'editor.selectionBackground': '#2a3a3a88',
    'editor.inactiveSelectionBackground': '#2a3a3a44',
    'editorCursor.foreground': '#e06080',
    'editorLineNumber.foreground': '#3a4a4a',
    'editorLineNumber.activeForeground': '#5cb8a0',
    'editor.selectionHighlightBackground': '#2a3a3a44',
    'editorBracketMatch.background': '#2a3a3a55',
    'editorBracketMatch.border': '#5cb8a055',
    'editorIndentGuide.background': '#1e2828',
    'editorIndentGuide.activeBackground': '#2a3a3a',
    'editorWidget.background': '#141a1e',
    'editorWidget.border': '#2a3438',
    'editorSuggestWidget.background': '#141a1e',
    'editorSuggestWidget.border': '#2a3438',
    'editorSuggestWidget.selectedBackground': '#1c2428',
    'editorHoverWidget.background': '#141a1e',
    'editorHoverWidget.border': '#2a3438',
    'scrollbarSlider.background': '#2a3a3a44',
    'scrollbarSlider.hoverBackground': '#3a4a4a66',
    'scrollbarSlider.activeBackground': '#4a5a5a88',
    'minimap.background': '#141a1e',
  },
};

/* ─── Sophisticated Light Monaco Theme ─── */
const CLAY_LIGHT_THEME = {
  base: 'vs',
  inherit: true,
  rules: [
    { token: '', foreground: '2a2a2a', background: 'fffaf0' },
    { token: 'comment', foreground: '9a9a9a', fontStyle: 'italic' },
    { token: 'keyword', foreground: 'c0254a' },
    { token: 'string', foreground: 'a07020' },
    { token: 'number', foreground: 'c06030' },
    { token: 'type', foreground: '7040b0' },
    { token: 'function', foreground: '1a8a6a' },
    { token: 'variable', foreground: '2a2a2a' },
    { token: 'operator', foreground: 'c03030' },
    { token: 'delimiter', foreground: '6a6a6a' },
    { token: 'constant', foreground: 'c06030' },
    { token: 'tag', foreground: 'c0254a' },
    { token: 'attribute.name', foreground: '7040b0' },
    { token: 'attribute.value', foreground: 'a07020' },
  ],
  colors: {
    'editor.background': '#fffaf0',
    'editor.foreground': '#2a2a2a',
    'editor.lineHighlightBackground': '#f5f0e0',
    'editor.selectionBackground': '#d4d0c888',
    'editor.inactiveSelectionBackground': '#d4d0c844',
    'editorCursor.foreground': '#c0254a',
    'editorLineNumber.foreground': '#c0c0c0',
    'editorLineNumber.activeForeground': '#1a8a6a',
    'editor.selectionHighlightBackground': '#d4d0c844',
    'editorBracketMatch.background': '#d4d0c855',
    'editorBracketMatch.border': '#1a8a6a55',
    'editorIndentGuide.background': '#ebe6d6',
    'editorIndentGuide.activeBackground': '#d4d0c8',
    'editorWidget.background': '#fffaf0',
    'editorWidget.border': '#e5e5e5',
    'editorSuggestWidget.background': '#fffaf0',
    'editorSuggestWidget.border': '#e5e5e5',
    'editorSuggestWidget.selectedBackground': '#f5f0e0',
    'editorHoverWidget.background': '#fffaf0',
    'editorHoverWidget.border': '#e5e5e5',
    'scrollbarSlider.background': '#d4d0c844',
    'scrollbarSlider.hoverBackground': '#d4d0c866',
    'scrollbarSlider.activeBackground': '#d4d0c888',
    'minimap.background': '#fffaf0',
  },
};

const EditorPage = () => {
  const { user } = useAuth();
  const { theme } = useTheme();
  const location = useLocation();
  const editorRef = useRef(null);

  const projectFile = location.state || {};
  const isProjectFile = !!(projectFile.projectId && projectFile.fileId);
  const isNewFile = !!(projectFile.projectId && projectFile.isNewFile);

  const getInitialLang = () => {
    if (isProjectFile) {
      const name = projectFile.fileName || '';
      if (name.endsWith('.py')) return LANGUAGES[0];
      if (name.endsWith('.c')) return LANGUAGES[1];
      if (name.endsWith('.cpp') || name.endsWith('.cc')) return LANGUAGES[2];
      if (name.endsWith('.sql')) return LANGUAGES[3];
    }
    return LANGUAGES[0];
  };

  const [language, setLanguage] = useState(getInitialLang);
  const [code, setCode] = useState(isProjectFile ? (projectFile.fileContent || '') : LANGUAGES[0].defaultCode);
  const [output, setOutput] = useState('');
  const [artifacts, setArtifacts] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [showInput, setShowInput] = useState(false);
  const [userInput, setUserInput] = useState('');
  const [executionTime, setExecutionTime] = useState(null);
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [showAI, setShowAI] = useState(false);
  const [aiMessages, setAiMessages] = useState([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiAction, setAiAction] = useState(null);
  const [saveStatus, setSaveStatus] = useState('');
  const [fontSize, setFontSize] = useState(14);
  const [tabSize, setTabSize] = useState(4);
  const [wordWrap, setWordWrap] = useState('on');
  const [minimap, setMinimap] = useState(true);
  const [showTemplates, setShowTemplates] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [outputTab, setOutputTab] = useState('output');
  const [cursorPos, setCursorPos] = useState({ line: 1, col: 1 });
  const [execHistory, setExecHistory] = useState([]);
  const [codeStats, setCodeStats] = useState({ lines: 1, chars: 0, words: 0 });
  const [newFileName, setNewFileName] = useState('');
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(0);
  // ─── Execution Trace state ───
  const [traceData, setTraceData] = useState([]);
  const [traceIndex, setTraceIndex] = useState(-1);
  const [traceLoading, setTraceLoading] = useState(false);
  const [tracePlaying, setTracePlaying] = useState(false);
  const [traceStdout, setTraceStdout] = useState('');
  const tracePlayRef = useRef(null);
  const traceDecoRef = useRef(null);
  const timerRef = useRef(null);
  const abortRef = useRef(null);
  const autoSaveTimer = useRef(null);
  const [historyTab, setHistoryTab] = useState('local'); // eslint-disable-line no-unused-vars
  const [toast, setToast] = useState(null);

  const containerRef = useRef(null);
  const monacoRef = useRef(null);
  const [splitRatio, setSplitRatio] = useState(0.6);
  const isDragging = useRef(false);
  const splitRef = useRef(null);
  const { registerProvider: registerAutocomplete } = useTabAutocomplete(language);
  const completionDisposableRef = useRef(null);
  const cursorDisposableRef = useRef(null);
  const { send: sendAIStream, streaming: aiStreaming, streamedText: aiStreamedText, disconnect: disconnectAI } = useAIStreaming();
  const aiStreamedMsgRef = useRef(null);
  const aiCooldownRef = useRef(false);
  const diagnosticsRef = useRef([]);
  const diagnosticsTimerRef = useRef(null);

  const switchLanguage = (lang) => {
    setLanguage(lang);
    setCode(lang.defaultCode);
    setOutput('');
    setArtifacts([]);
    setShowLangDropdown(false);
    setShowTemplates(false);
  };

  const handleEditorMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    monaco.editor.defineTheme('clay-dark', CLAY_DARK_THEME);
    monaco.editor.defineTheme('clay-light', CLAY_LIGHT_THEME);
    monaco.editor.setTheme(theme === 'dark' ? 'clay-dark' : 'clay-light');
    editor.focus();

    cursorDisposableRef.current = editor.onDidChangeCursorPosition((e) => {
      setCursorPos({ line: e.position.lineNumber, col: e.position.column });
    });

    // Register tab autocomplete provider
    completionDisposableRef.current = registerAutocomplete(editor, monaco);

    // ─── AI Quick-Fix Hover Provider ───
    monaco.languages.registerHoverProvider('*', {
      provideHover(model, position) {
        const error = diagnosticsRef.current.find(
          e => e.line === position.lineNumber
        );
        if (!error || !error.fix) return null;

        const fixLine = error.fix;
        const explanation = error.explanation || error.message;

        return {
          range: new monaco.Range(
            position.lineNumber, 1,
            position.lineNumber, model.getLineMaxColumn(position.lineNumber)
          ),
          contents: [
            { value: `**✨ AI Quick-Fix**` },
            { value: `**Error:** ${error.message}\n\n**Suggested fix:**\n\`\`\`${language.id}\n${fixLine}\n\`\`\`\n\n${explanation}` },
          ],
        };
      },
    });

    // ─── Quick-Fix Action (Ctrl+.) ───
    editor.addAction({
      id: 'ai-quick-fix',
      label: 'Apply AI Quick-Fix',
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Period],
      contextMenuGroupId: '1_modification',
      contextMenuOrder: 1.5,
      run: (ed) => {
        const pos = ed.getPosition();
        const error = diagnosticsRef.current.find(e => e.line === pos.lineNumber);
        if (error && error.fix) {
          applyQuickFix(error);
        }
      },
    });
  };

  // Switch Monaco theme when app theme changes
  useEffect(() => {
    if (monacoRef.current) {
      monacoRef.current.editor.setTheme(theme === 'dark' ? 'clay-dark' : 'clay-light');
    }
  }, [theme]);

  const updateCodeStats = (val) => {
    const text = val || '';
    const lines = text.split('\n').length;
    const chars = text.length;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    setCodeStats({ lines, chars, words });
  };

  const handleCodeChange = (val) => {
    setCode(val || '');
    updateCodeStats(val);
    scheduleDiagnostics(val || '');
  };

  // ─── Background Diagnostics ───
  const runDiagnostics = async (codeToCheck) => {
    if (!codeToCheck || codeToCheck.length < 5) return;
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/compiler/diagnose/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ code: codeToCheck, language: language.id }),
      });
      if (!res.ok) return;
      const data = await res.json();
      const errors = data.errors || [];
      diagnosticsRef.current = errors;
      applyMonacoMarkers(errors);
    } catch {
      // silently ignore — diagnostics are non-critical
    }
  };

  const scheduleDiagnostics = (codeToCheck) => {
    if (diagnosticsTimerRef.current) clearTimeout(diagnosticsTimerRef.current);
    diagnosticsTimerRef.current = setTimeout(() => runDiagnostics(codeToCheck), 800);
  };

  const applyMonacoMarkers = (errors) => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco) return;

    const model = editor.getModel();
    if (!model) return;

    const markers = errors.map((err) => ({
      severity: monaco.MarkerSeverity.Error,
      startLineNumber: err.line,
      startColumn: err.column || 1,
      endLineNumber: err.line,
      endColumn: (err.column || 1) + Math.max((model.getLineContent(err.line) || '').length, 1),
      message: err.fix
        ? `${err.message} — AI Fix: ${err.fix}`
        : err.message,
    }));

    monaco.editor.setModelMarkers(model, 'nexus-diagnostics', markers);
  };

  const applyQuickFix = (error) => {
    if (!error || !error.fix || !editorRef.current) return;
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    const model = editor.getModel();
    if (!model) return;

    const lineNum = error.line;
    const lineContent = model.getLineContent(lineNum);
    const fullLineRange = new monaco.Range(lineNum, 1, lineNum, lineContent.length + 1);

    editor.executeEdits('ai-quick-fix', [{
      range: fullLineRange,
      text: error.fix,
    }]);

    // Clear this marker
    diagnosticsRef.current = diagnosticsRef.current.filter(e => e !== error);
    applyMonacoMarkers(diagnosticsRef.current);
    setToast({ message: `AI fix applied: ${error.fix}`, type: 'success' });
    setTimeout(() => setToast(null), 3000);
  };

  // ─── Execution Trace ───
  const runTrace = async () => {
    if (traceLoading || language.id !== 'python') return;
    setTraceLoading(true);
    setTraceData([]);
    setTraceIndex(-1);
    setTraceStdout('');
    setOutputTab('trace');
    stopTracePlay();

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/compiler/trace/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ code, language: language.id }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setTraceData(data.trace || []);
      setTraceStdout(data.stdout || '');
      if (data.trace && data.trace.length > 0) {
        setTraceIndex(0);
        highlightTraceLine(0, data.trace);
      }
      if (data.error) {
        setToast({ message: `Trace error: ${data.error}`, type: 'error' });
        setTimeout(() => setToast(null), 4000);
      }
    } catch (err) {
      setToast({ message: `Trace failed: ${err.message}`, type: 'error' });
      setTimeout(() => setToast(null), 4000);
    } finally {
      setTraceLoading(false);
    }
  };

  const highlightTraceLine = (idx, data) => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco || !data || idx < 0 || idx >= data.length) return;

    const lineNum = data[idx].line;
    const model = editor.getModel();
    if (!model) return;

    // Remove old decorations
    if (traceDecoRef.current) {
      editor.deltaDecorations(traceDecoRef.current, []);
    }

    // Add new highlight decoration
    const newDecos = editor.deltaDecorations([], [
      {
        range: new monaco.Range(lineNum, 1, lineNum, model.getLineMaxColumn(lineNum)),
        options: {
          isWholeLine: true,
          className: 'trace-line-highlight',
          glyphMarginClassName: 'trace-line-glyph',
          overviewRuler: { color: '#5cb8a0', position: monaco.editor.OverviewRulerLane.Left },
        },
      },
    ]);
    traceDecoRef.current = newDecos;

    // Scroll to the line
    editor.revealLineInCenter(lineNum);
  };

  const traceStepForward = () => {
    if (traceIndex < traceData.length - 1) {
      const next = traceIndex + 1;
      setTraceIndex(next);
      highlightTraceLine(next, traceData);
    }
  };

  const traceStepBack = () => {
    if (traceIndex > 0) {
      const prev = traceIndex - 1;
      setTraceIndex(prev);
      highlightTraceLine(prev, traceData);
    }
  };

  const startTracePlay = () => {
    if (tracePlaying || traceData.length === 0) return;
    setTracePlaying(true);
    let idx = traceIndex;
    tracePlayRef.current = setInterval(() => {
      if (idx >= traceData.length - 1) {
        clearInterval(tracePlayRef.current);
        tracePlayRef.current = null;
        setTracePlaying(false);
        return;
      }
      idx++;
      setTraceIndex(idx);
      highlightTraceLine(idx, traceData);
    }, 400);
  };

  const stopTracePlay = () => {
    if (tracePlayRef.current) {
      clearInterval(tracePlayRef.current);
      tracePlayRef.current = null;
    }
    setTracePlaying(false);
  };

  const toggleTracePlay = () => {
    if (tracePlaying) stopTracePlay();
    else startTracePlay();
  };

  // Cleanup trace play interval on unmount
  useEffect(() => {
    return () => { if (tracePlayRef.current) clearInterval(tracePlayRef.current); };
  }, []);

  const runCode = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setOutput('');
    setArtifacts([]);
    setExecutionTime(null);
    setOutputTab('output');
    // Clear trace decorations
    if (traceDecoRef.current && editorRef.current) {
      editorRef.current.deltaDecorations(traceDecoRef.current, []);
      traceDecoRef.current = null;
    }
    stopTracePlay();
    setTraceData([]);
    setTraceIndex(-1);
    setTimerSeconds(0);
    const start = performance.now();
    timerRef.current = setInterval(() => {
      setTimerSeconds(((performance.now() - start) / 1000).toFixed(1));
    }, 100);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await api.post('/api/execute/', {
        code,
        language: language.id,
        stdin: userInput || '',
      }, { signal: controller.signal });

      const elapsed = ((performance.now() - start) / 1000).toFixed(2);
      setExecutionTime(elapsed);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
      setTimerSeconds(elapsed);

      const entry = {
        time: new Date().toLocaleTimeString(),
        language: language.label,
        duration: elapsed,
        status: res.data.status === 'success' ? 'success' : 'error',
        preview: (res.data.output || res.data.error || '').slice(0, 100),
        code,
        output: res.data.output,
        error: res.data.error,
      };

      if (res.data.status === 'success') {
        setOutput(res.data.output || '');
        setArtifacts(res.data.artifacts || []);
        entry.status = 'success';
      } else {
        setOutput(`Error:\n${res.data.error || res.data.output || 'Execution failed'}`);
        setArtifacts([]);
        entry.status = 'error';
      }
      setExecHistory(prev => [entry, ...prev].slice(0, 20));
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') {
        setOutput('Execution cancelled.');
      } else {
        const elapsed = ((performance.now() - start) / 1000).toFixed(2);
        setExecutionTime(elapsed);
        setOutput(`Error: ${err.response?.data?.error || err.message}`);
        setExecHistory(prev => [{
          time: new Date().toLocaleTimeString(),
          language: language.label,
          duration: elapsed,
          status: 'error',
          preview: (err.response?.data?.error || err.message).slice(0, 100),
          code,
        }, ...prev].slice(0, 20));
      }
    } finally {
      setIsRunning(false);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
      abortRef.current = null;
    }
  };

  const cancelRun = () => {
    if (abortRef.current) abortRef.current.abort();
  };

  const saveSnippet = async () => {
    // If this is a new file, prompt for filename first
    if (isNewFile && !projectFile.fileId) {
      if (!newFileName.trim()) {
        setShowNamePrompt(true);
        return;
      }
    }

    try {
      setSaveStatus('saving');
      if (isNewFile && !projectFile.fileId) {
        // Create new file in project
        const res = await api.post(`/api/projects/${projectFile.projectId}/add_file/`, {
          name: newFileName.trim(),
          content: code,
        });
        // Update location state so subsequent saves use PATCH
        projectFile.fileId = res.data.id;
        projectFile.fileName = res.data.name;
        projectFile.isNewFile = false;
        setSaveStatus('saved');
        setShowNamePrompt(false);
      } else if (isProjectFile) {
        await api.patch(`/api/projects/${projectFile.projectId}/files/${projectFile.fileId}/`, { content: code });
        setSaveStatus('saved');
      } else {
        await api.post('/api/code/', {
          title: `${language.label} snippet - ${new Date().toLocaleString()}`,
          code,
          language: language.id,
          is_public: false,
        });
        setSaveStatus('saved');
      }
      setTimeout(() => setSaveStatus(''), 2000);
    } catch {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus(''), 2000);
    }
  };

  const handleNewFileConfirm = () => {
    if (newFileName.trim()) {
      setShowNamePrompt(false);
      saveSnippet();
    }
  };

  const getLangFromFileName = (name) => {
    if (name.endsWith('.py')) return LANGUAGES[0];
    if (name.endsWith('.c') && !name.endsWith('.cpp') && !name.endsWith('.cc')) return LANGUAGES[1];
    if (name.endsWith('.cpp') || name.endsWith('.cc') || name.endsWith('.cxx')) return LANGUAGES[2];
    if (name.endsWith('.sql')) return LANGUAGES[3];
    return null;
  };

  const handleNewFileNameChange = (val) => {
    setNewFileName(val);
    const detected = getLangFromFileName(val);
    if (detected) {
      setLanguage(detected);
      setCode(detected.defaultCode);
    }
  };

  const copyOutput = () => {
    navigator.clipboard.writeText(output);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const copyCode = () => {
    navigator.clipboard.writeText(code);
  };

  const MAX_AI_MESSAGES = 20;
  const appendAIMessage = useCallback((msg) => {
    setAiMessages(prev => {
      const next = [...prev, msg];
      return next.length > MAX_AI_MESSAGES ? next.slice(-MAX_AI_MESSAGES) : next;
    });
  }, []);

  const sendAIMessage = async (overrideAction) => {
    const action = overrideAction || aiAction || 'chat';
    const msg = aiInput.trim() || action;
    if (!msg || aiLoading || aiCooldownRef.current) return;
    setAiInput('');
    setAiAction(null);
    appendAIMessage({ role: 'user', content: msg });
    setAiLoading(true);

    // Use REST API for all AI actions (reliable, no WebSocket dependency)
    try {
      const payload = {
        code,
        action,
        language: language.id,
        error: output.includes('Error:') ? output : '',
        output: output.includes('Error:') ? '' : output,
        context: msg,
      };
      if (isProjectFile) {
        payload.project_id = projectFile.projectId;
        payload.file_id = projectFile.fileId;
      }
      const res = await api.post('/api/ai/', payload, { timeout: 30000 });

      const responseText = res.data.response || res.data.message || 'No response';
      const extractedCode = res.data.extracted_code;

      appendAIMessage({
        role: 'assistant',
        content: responseText,
      });

      // Auto-apply code for fix, optimize, debug, generate actions
      if (['fix', 'optimize', 'debug', 'generate'].includes(action) && extractedCode) {
        setCode(extractedCode);
        updateCodeStats(extractedCode);
        if (editorRef.current) {
          editorRef.current.focus();
        }
        const actionLabel = action === 'generate' ? 'Code generated' : `${action.charAt(0).toUpperCase() + action.slice(1)} applied`;
        setToast({ message: `${actionLabel} — code updated in editor`, type: 'success' });
        setTimeout(() => setToast(null), 4000);
      }
    } catch (err) {
      const status = err.response?.status;
      const errMsg = err.response?.data?.error || err.response?.data?.detail || err.message || 'AI request failed';
      const refreshSeconds = err.response?.data?.refresh_seconds;

      if (status === 429) {
        const mins = refreshSeconds ? Math.ceil(refreshSeconds / 60) : '?';
        appendAIMessage({
          role: 'assistant',
          content: `⏰ ${errMsg}`,
          isRateLimit: true,
          refreshMinutes: mins,
        });
      } else {
        appendAIMessage({
          role: 'assistant',
          content: `Error: ${errMsg}`,
        });
      }
    } finally {
      setAiLoading(false);
      aiCooldownRef.current = true;
      setTimeout(() => { aiCooldownRef.current = false; }, 500);
    }
  };

  const insertTemplate = (template) => {
    setCode(template.code);
    updateCodeStats(template.code);
    setShowTemplates(false);
    if (editorRef.current) {
      editorRef.current.focus();
    }
  };

  const downloadArtifact = (artifact, index) => {
    const link = document.createElement('a');
    if (artifact.type === 'image' || (artifact.data && artifact.data.startsWith('data:image'))) {
      link.href = artifact.data || artifact;
      link.download = `plot_${index + 1}.png`;
    } else if (artifact.type === 'file' && artifact.data) {
      // Decode base64 to original content
      const binaryStr = atob(artifact.data);
      const bytes = new Uint8Array(binaryStr.length);
      for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: 'application/octet-stream' });
      link.href = URL.createObjectURL(blob);
      link.download = artifact.name || `output_${index + 1}.${artifact.ext || 'txt'}`;
    } else {
      const content = artifact.data || artifact;
      const blob = new Blob([content], { type: 'text/plain' });
      link.href = URL.createObjectURL(blob);
      link.download = `output_${index + 1}.txt`;
    }
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const shareCode = async () => {
    try {
      const res = await api.post('/api/code/', {
        title: `${language.label} snippet - ${new Date().toLocaleString()}`,
        code,
        language: language.id,
        is_public: true,
      });
      const snippetId = res.data.id;
      const url = `${window.location.origin}/compiler?snippet=${snippetId}`;
      await navigator.clipboard.writeText(url);
      setSaveStatus('shared');
      setTimeout(() => setSaveStatus(''), 2500);
    } catch {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus(''), 2500);
    }
  };

  const restoreFromHistory = (h) => {
    if (h.code) {
      setCode(h.code);
      updateCodeStats(h.code);
      setOutput(h.output || h.error || '');
      setArtifacts([]);
      setOutputTab('output');
      if (editorRef.current) editorRef.current.focus();
    }
  };

  useEffect(() => {
    updateCodeStats(code);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- run once on mount

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        runCode();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveSnippet();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [code, language, userInput, newFileName, isNewFile]); // eslint-disable-line react-hooks/exhaustive-deps -- keyboard shortcuts need current values

  useEffect(() => {
    const key = `nexuside_autosave_${language.id}`;
    const saved = localStorage.getItem(key);
    if (!isProjectFile && !isNewFile && saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.code && !code) setCode(parsed.code);
      } catch { /* ignore */ }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- restore autosave on mount

  useEffect(() => {
    if (isProjectFile || isNewFile) return;
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(() => {
      if (code) {
        const key = `nexuside_autosave_${language.id}`;
        localStorage.setItem(key, JSON.stringify({ code, language: language.id, savedAt: Date.now() }));
      }
    }, 2000);
    return () => { if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current); };
  }, [code, language.id, isProjectFile, isNewFile]);

  useEffect(() => {
    const fetchHistory = async () => {
      if (!user) return;
      try {
        const res = await api.get('/api/history/?page_size=20');
        const items = res.data.results || res.data || [];
        const mapped = items.map((h) => ({
          id: h.id,
          time: new Date(h.created_at).toLocaleString(),
          language: h.metadata?.language || 'Python',
          duration: h.execution_time?.toFixed?.(2) || h.execution_time || '0.00',
          status: h.status,
          preview: (h.output || h.error || '').slice(0, 100),
          code: h.code,
          output: h.output,
          error: h.error,
        }));
        setExecHistory(mapped);
      } catch { /* silently fail */ }
    };
    fetchHistory();
  }, [user]);

  useEffect(() => {
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  // Cleanup diagnostics timer on unmount
  useEffect(() => {
    return () => {
      if (diagnosticsTimerRef.current) clearTimeout(diagnosticsTimerRef.current);
    };
  }, []);

  // Re-register autocomplete when language changes
  useEffect(() => {
    if (editorRef.current && window.monaco) {
      if (completionDisposableRef.current) {
        completionDisposableRef.current.dispose();
      }
      completionDisposableRef.current = registerAutocomplete(editorRef.current, window.monaco);
      // Clear diagnostics for previous language
      diagnosticsRef.current = [];
      const model = editorRef.current.getModel();
      if (model) {
        window.monaco.editor.setModelMarkers(model, 'nexus-diagnostics', []);
      }
    }
    return () => {
      if (completionDisposableRef.current) {
        completionDisposableRef.current.dispose();
      }
    };
  }, [language, registerAutocomplete]);

  // Cleanup AI streaming on unmount
  useEffect(() => {
    return () => { disconnectAI(); };
  }, [disconnectAI]);

  // Dispose Monaco editor on unmount
  useEffect(() => {
    return () => {
      if (cursorDisposableRef.current) { cursorDisposableRef.current.dispose(); cursorDisposableRef.current = null; }
      if (editorRef.current) { editorRef.current.dispose(); editorRef.current = null; }
      monacoRef.current = null;
    };
  }, []);

  const onSplitMouseDown = useCallback((e) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const onMouseMove = (ev) => {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const ratio = Math.min(Math.max(x / rect.width, 0.2), 0.8);
      setSplitRatio(ratio);
    };

    const onMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }, []);

  const outputLines = output ? output.split('\n').length : 0;

  if (language.id === 'sql') {
    return (
      <div className={`flex flex-col ${isFullscreen ? 'fixed inset-0 z-50' : 'h-[calc(100vh-64px)]'} bg-[var(--color-canvas)]`}>
        <SQLPlayground
          languages={LANGUAGES}
          currentLanguage={language}
          onSwitchLanguage={(lang) => { switchLanguage(lang); }}
        />
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${isFullscreen ? 'fixed inset-0 z-50' : 'h-[calc(100vh-64px)]'} bg-[var(--color-canvas)]`}>
      {/* Trace line highlight styles */}
      <style>{`
        .trace-line-highlight { background: rgba(124, 58, 237, 0.10) !important; }
        .trace-line-glyph { background: #7c3aed; width: 3px !important; border-radius: 2px; }
      `}</style>
      {/* ─── Main Area ─── */}
      <div className="flex flex-1 min-h-0">
        {/* ─── Editor Panel ─── */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Toolbar */}
          <div className="flex items-center justify-between px-3 py-1.5 bg-[var(--color-surface-soft)] border-b border-[var(--color-hairline)]">
            <div className="flex items-center gap-2">
              {isNewFile && showNamePrompt && (
                <div className="flex items-center gap-1.5 px-2 py-1 bg-[var(--color-surface-card)] border border-[#5cb8a0]/40 rounded-md">
                  <FileCode2 size={11} className="text-[#5cb8a0]" />
                  <input
                    type="text"
                    value={newFileName}
                    onChange={(e) => handleNewFileNameChange(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleNewFileConfirm(); if (e.key === 'Escape') setShowNamePrompt(false); }}
                    placeholder="filename.py"
                    autoFocus
                    className="w-40 px-1.5 py-0.5 bg-transparent text-[var(--color-ink)] text-xs font-mono focus:outline-none placeholder-[var(--color-muted)]"
                  />
                  <button onClick={handleNewFileConfirm} className="text-[#5cb8a0] hover:text-[#4aa890] transition-colors">
                    <Check size={12} />
                  </button>
                  <button onClick={() => setShowNamePrompt(false)} className="text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors">
                    <X size={12} />
                  </button>
                </div>
              )}
              {isNewFile && !showNamePrompt && (
                <div className="flex items-center gap-1.5 px-2 py-1 bg-[#7c3aed]/10 border border-[#7c3aed]/20 rounded text-xs text-[#7c3aed]">
                  <FileCode2 size={11} />
                  <span className="font-medium">New File</span>
                  <button onClick={() => setShowNamePrompt(true)} className="text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors ml-1">
                    <span className="text-[10px] underline">set name</span>
                  </button>
                </div>
              )}
              {isProjectFile && !isNewFile && (
                <div className="flex items-center gap-1.5 px-2 py-1 bg-[#5cb8a0]/10 border border-[#5cb8a0]/20 rounded text-xs text-[#5cb8a0]">
                  <FileCode2 size={11} />
                  <span className="font-mono">{projectFile.fileName}</span>
                  <span className="text-[var(--color-muted-soft)]">in</span>
                  <span className="font-medium">{projectFile.projectName}</span>
                </div>
              )}

              {/* Language Selector */}
              <div className="relative">
                <button
                  onClick={() => setShowLangDropdown(!showLangDropdown)}
                  className="flex items-center gap-1.5 px-2.5 py-1 bg-[var(--color-surface-card)] hover:bg-[var(--color-surface-soft)] border border-[var(--color-hairline)] rounded-md text-xs text-[var(--color-ink)] transition-all"
                >
                  <span>{language.icon}</span>
                  <span className="font-medium">{language.label}</span>
                  <ChevronDown size={12} className="text-[var(--color-muted)]" />
                </button>
                <AnimatePresence>
                  {showLangDropdown && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="absolute top-full mt-1 left-0 bg-[var(--color-canvas)] border border-[var(--color-hairline)] rounded-md shadow-xl overflow-hidden z-50 min-w-[160px]"
                    >
                      {LANGUAGES.map((lang) => (
                        <button
                          key={lang.id}
                          onClick={() => switchLanguage(lang)}
                          className={`w-full flex items-center gap-2 px-3 py-2 text-xs transition-all ${
                            language.id === lang.id
                              ? 'bg-[#5cb8a0]/10 text-[#5cb8a0]'
                              : 'text-[var(--color-ink)] hover:bg-[var(--color-surface-card)]'
                          }`}
                        >
                          <span>{lang.icon}</span>
                          <span>{lang.label}</span>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <div className="h-4 w-px bg-hairline" />

              {/* Run */}
              {isRunning ? (
                <div className="flex items-center gap-1.5">
                  <div className="flex items-center gap-1.5 px-3 py-1 bg-[#b8860b]/20 border border-[#b8860b]/40 text-[#b8860b] rounded-md text-xs font-mono">
                    <Loader2 size={12} className="animate-spin" />
                    <span>{timerSeconds}s</span>
                    <span className="text-[10px] text-[#b8860b]/60">/ 30s</span>
                  </div>
                  <button
                    onClick={cancelRun}
                    className="flex items-center gap-1 px-2 py-1 bg-[#dc2626] hover:bg-[#b91c1c] text-white rounded-md text-xs font-semibold transition-all shadow-md shadow-[#dc2626]/15"
                  >
                    <Square size={10} className="fill-white" />
                    Stop
                  </button>
                </div>
              ) : (
                <button
                  onClick={runCode}
                  className="flex items-center gap-1.5 px-3 py-1 bg-[#16a34a] hover:bg-[#15803d] text-white rounded-md text-xs font-semibold transition-all shadow-md shadow-[#16a34a]/15"
                >
                  <Play size={12} /> Run
                </button>
              )}

              {/* Trace Code (Python only) */}
              {language.id === 'python' && !isRunning && (
                <button
                  onClick={runTrace}
                  disabled={traceLoading}
                  className="flex items-center gap-1.5 px-2.5 py-1 border border-[#7c3aed] text-[#7c3aed] hover:bg-[#7c3aed]/5 rounded-md text-xs font-medium transition-all"
                >
                  {traceLoading ? <Loader2 size={11} className="animate-spin" /> : <Map size={11} />}
                  <span>Trace</span>
                </button>
              )}

              {/* Input toggle */}
              <button
                onClick={() => setShowInput(!showInput)}
                className={`flex items-center gap-1 px-2.5 py-1 border rounded-md text-xs transition-all ${
                  showInput
                    ? 'border-[#5cb8a0] text-[#5cb8a0] bg-[#5cb8a0]/5'
                    : 'border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-ink)] hover:border-[var(--color-muted)]'
                }`}
              >
                <Terminal size={12} />
                <span>Input</span>
              </button>

              {/* Templates */}
              <div className="relative">
                <button
                  onClick={() => setShowTemplates(!showTemplates)}
                  className="flex items-center gap-1 px-2.5 py-1 border border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-ink)] hover:border-[var(--color-muted)] rounded-md text-xs transition-all"
                >
                  <Code size={12} />
                  <span>Templates</span>
                </button>
                <AnimatePresence>
                  {showTemplates && (
                    <motion.div
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="absolute top-full mt-1 left-0 bg-[var(--color-canvas)] border border-[var(--color-hairline)] rounded-lg shadow-xl overflow-hidden z-50 w-64 max-h-72 overflow-y-auto"
                    >
                      <div className="px-3 py-2 border-b border-[var(--color-hairline)] bg-[var(--color-surface-card)]">
                        <span className="text-xs font-semibold text-[var(--color-ink)]">{language.label} Templates</span>
                      </div>
                      {(TEMPLATES[language.id] || []).map((t, i) => (
                        <button
                          key={i}
                          onClick={() => insertTemplate(t)}
                          className="w-full text-left px-3 py-2 text-xs text-[var(--color-ink)] hover:bg-[var(--color-surface-card)] transition-colors border-b border-[var(--color-hairline)]/50 last:border-0"
                        >
                          <div className="font-medium">{t.name}</div>
                          <div className="text-[10px] text-[var(--color-muted-soft)] font-mono truncate mt-0.5">{t.code.split('\n')[0]}</div>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              {/* Font size */}
              <div className="flex items-center gap-0.5 border border-[var(--color-hairline)] rounded-md">
                <button onClick={() => setFontSize(s => Math.max(10, s - 1))} className="p-1 text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors">
                  <Minus size={12} />
                </button>
                <span className="text-[10px] text-[var(--color-ink)] font-mono w-6 text-center">{fontSize}</span>
                <button onClick={() => setFontSize(s => Math.min(24, s + 1))} className="p-1 text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors">
                  <Plus size={12} />
                </button>
              </div>

              {/* Tab size */}
              <div className="relative">
                <button
                  onClick={() => {
                    const sizes = [2, 4, 8];
                    const idx = sizes.indexOf(tabSize);
                    setTabSize(sizes[(idx + 1) % sizes.length]);
                  }}
                  className="flex items-center gap-1 px-2 py-1 border border-[var(--color-hairline)] rounded-md text-[10px] text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-all font-mono"
                  title="Tab size"
                >
                  <span>Tab:{tabSize}</span>
                </button>
              </div>

              {/* Word wrap */}
              <button
                onClick={() => setWordWrap(w => w === 'on' ? 'off' : 'on')}
                className={`p-1.5 border rounded-md transition-all ${
                  wordWrap === 'on'
                    ? 'border-[#5cb8a0] text-[#5cb8a0] bg-[#5cb8a0]/5'
                    : 'border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-ink)]'
                }`}
                title="Toggle word wrap"
              >
                <WrapText size={12} />
              </button>

              {/* Minimap */}
              <button
                onClick={() => setMinimap(m => !m)}
                className={`p-1.5 border rounded-md transition-all ${
                  minimap
                    ? 'border-[#5cb8a0] text-[#5cb8a0] bg-[#5cb8a0]/5'
                    : 'border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-ink)]'
                }`}
                title="Toggle minimap"
              >
                <Map size={12} />
              </button>

              <div className="h-4 w-px bg-hairline" />

              {/* Copy */}
              <button onClick={copyCode} className="p-1.5 text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors" title="Copy code">
                <Copy size={12} />
              </button>

              {/* Shortcuts */}
              <button
                onClick={() => setShowShortcuts(!showShortcuts)}
                className="p-1.5 text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors"
                title="Keyboard shortcuts"
              >
                <Keyboard size={12} />
              </button>

              <div className="h-4 w-px bg-hairline" />

              {/* Save */}
              <button
                onClick={saveSnippet}
                className="flex items-center gap-1 px-2.5 py-1 border border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-ink)] hover:border-[var(--color-muted)] rounded-md text-xs transition-all"
                title={isNewFile ? "Save new file (Ctrl+S)" : isProjectFile ? "Save to project (Ctrl+S)" : "Save snippet (Ctrl+S)"}
              >
                <Save size={12} />
                {saveStatus === 'saving' && <span className="text-[#b8860b]">Saving...</span>}
                {saveStatus === 'saved' && <span className="text-[#16a34a]">Saved</span>}
                {saveStatus === 'shared' && <span className="text-[#16a34a]">Link copied!</span>}
                {saveStatus === 'error' && <span className="text-[#dc2626]">Error</span>}
                {!saveStatus && <span className="hidden sm:inline">{isNewFile ? 'Save As...' : 'Save'}</span>}
              </button>

              {/* Share */}
              {!isProjectFile && !isNewFile && (
                <button
                  onClick={shareCode}
                  className="flex items-center gap-1 px-2.5 py-1 border border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-ink)] hover:border-[var(--color-muted)] rounded-md text-xs transition-all"
                  title="Share code via URL"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
                  <span className="hidden sm:inline">Share</span>
                </button>
              )}

              {/* AI */}
              <button
                onClick={() => setShowAI(!showAI)}
                className={`flex items-center gap-1 px-2.5 py-1 border rounded-md text-xs transition-all ${
                  showAI
                    ? 'border-[#7c3aed] text-[#7c3aed] bg-[#7c3aed]/5'
                    : 'border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-ink)] hover:border-[var(--color-muted)]'
                }`}
              >
                <Sparkles size={12} />
                <span className="hidden sm:inline">AI</span>
              </button>

              {/* Fullscreen */}
              <button
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="p-1.5 border border-[var(--color-hairline)] text-[var(--color-muted)] hover:text-[var(--color-ink)] rounded-md transition-all"
              >
                {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
              </button>
            </div>
          </div>

          {/* Editor + Output Split */}
          <div ref={containerRef} className="flex-1 flex min-h-0">
            {/* Code Editor */}
            <div className="min-h-0 relative" style={{ width: `${splitRatio * 100}%` }}>
              {showInput && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: 'auto' }}
                  exit={{ height: 0 }}
                  className="border-b border-[var(--color-hairline)] bg-[var(--color-surface-card)]"
                >
                  <div className="flex items-center justify-between px-3 py-1.5 border-b border-[var(--color-hairline)]/50">
                    <div className="flex items-center gap-1.5">
                      <Terminal size={11} className="text-[#5cb8a0]" />
                      <span className="text-[10px] font-semibold text-[var(--color-muted)] uppercase tracking-wider">Standard Input</span>
                    </div>
                    {userInput && (
                      <span className="text-[10px] text-[var(--color-muted)] font-mono">{userInput.length} chars</span>
                    )}
                  </div>
                  <textarea
                    value={userInput}
                    onChange={(e) => setUserInput(e.target.value)}
                    placeholder="Enter input here (stdin)..."
                    className="w-full p-3 bg-transparent text-[var(--color-ink)] text-sm font-mono resize-none focus:outline-none h-20"
                  />
                </motion.div>
              )}
              <Editor
                height="100%"
                language={language.id === 'cpp' ? 'cpp' : language.id}
                value={code}
                onChange={handleCodeChange}
                onMount={handleEditorMount}
                theme={theme === 'dark' ? 'clay-dark' : 'clay-light'}
                options={{
                  fontSize,
                  fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
                  fontLigatures: true,
                  minimap: { enabled: minimap, scale: 1 },
                  scrollBeyondLastLine: false,
                  smoothScrolling: true,
                  cursorBlinking: 'smooth',
                  cursorSmoothCaretAnimation: 'on',
                  wordWrap,
                  padding: { top: 12, bottom: 12 },
                  renderLineHighlight: 'all',
                  bracketPairColorization: { enabled: true },
                  guides: { bracketPairs: true, indentation: true },
                  suggest: { showKeywords: true },
                  tabSize,
                  lineNumbers: 'on',
                  glyphMargin: false,
                  folding: true,
                  automaticLayout: true,
                }}
              />
            </div>

            {/* Drag Handle */}
            <div
              ref={splitRef}
              onMouseDown={onSplitMouseDown}
              className="w-[5px] flex-shrink-0 cursor-col-resize bg-hairline hover:bg-primary active:bg-primary transition-colors flex items-center justify-center group"
            >
              <GripVertical size={12} className="text-[var(--color-muted)] group-hover:text-[var(--color-ink)] transition-colors" />
            </div>

            {/* Output Panel */}
            <div className="min-w-[240px] flex flex-col bg-[var(--color-surface-card)] min-h-[200px]" style={{ width: `${(1 - splitRatio) * 100}%` }}>
              {/* Output Tabs */}
              <div className="flex items-center border-b border-[var(--color-hairline)]">
                {[
                  { id: 'output', label: 'Output', icon: Terminal, count: outputLines },
                  ...(language.id === 'python' ? [{ id: 'trace', label: 'Trace', icon: Map, count: traceData.length }] : []),
                  { id: 'history', label: 'History', icon: Clock, count: execHistory.length },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setOutputTab(tab.id)}
                    className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-all border-b-2 ${
                      outputTab === tab.id
                        ? 'border-[#5cb8a0] text-[#5cb8a0]'
                        : 'border-transparent text-[var(--color-muted)] hover:text-[var(--color-ink)]'
                    }`}
                  >
                    <tab.icon size={12} />
                    {tab.label}
                    {tab.count > 0 && (
                      <span className="px-1.5 py-0.5 bg-[var(--color-surface-soft)] rounded-full text-[9px] font-mono">{tab.count}</span>
                    )}
                  </button>
                ))}
                <div className="flex-1" />
                <div className="flex items-center gap-1.5 px-3">
                  {executionTime && (
                    <span className="text-[10px] text-[var(--color-muted)] font-mono">{executionTime}s</span>
                  )}
                  {output && outputTab === 'output' && (
                    <>
                      <button onClick={copyOutput} className="text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors">
                        {copied ? <Check size={12} className="text-[#16a34a]" /> : <Copy size={12} />}
                      </button>
                      <button onClick={() => { setOutput(''); setArtifacts([]); setExecutionTime(null); }} className="text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors">
                        <Trash2 size={12} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              <div className="flex-1 overflow-auto">
                {outputTab === 'output' ? (
                  <div className="p-3">
                    {isRunning ? (
                      <div className="flex items-center gap-2 text-[#b8860b]">
                        <Loader2 size={14} className="animate-spin" />
                        <span className="text-xs">Executing…</span>
                      </div>
                    ) : (
                      <>
                        {output && (
                          <>
                            {output.startsWith('Error') ? (
                              <div className="mb-2 flex items-center gap-1.5 text-[10px] text-[#dc2626] font-semibold">
                                <XCircle size={11} /> Execution Failed
                              </div>
                            ) : (
                              <div className="mb-2 flex items-center gap-1.5 text-[10px] text-[#16a34a] font-semibold">
                                <CheckCircle2 size={11} /> Execution Successful
                              </div>
                            )}
                            {output.includes('SQL Error:') ? (
                              <pre className="text-xs font-mono text-[#dc2626] whitespace-pre-wrap break-words leading-relaxed bg-[#dc2626]/5 p-2 rounded-md border border-[#dc2626]/20">{output}</pre>
                            ) : language.id === 'sql' ? (
                              (() => {
                                try {
                                  const parsed = JSON.parse(output);
                                  if (parsed.type === 'table') {
                                    return (
                                      <div className="overflow-auto rounded-lg border border-[var(--color-hairline)]">
                                        <table className="w-full text-xs font-mono">
                                          <thead>
                                            <tr className="bg-[var(--color-surface-card)] border-b border-[var(--color-hairline)]">
                                              {parsed.columns.map((col, ci) => (
                                                <th key={ci} className="px-3 py-2 text-left font-semibold text-[var(--color-ink)]">{col}</th>
                                              ))}
                                            </tr>
                                          </thead>
                                          <tbody>
                                            {parsed.rows.map((row, ri) => (
                                              <tr key={ri} className={`border-b border-[var(--color-hairline)]/50 ${ri % 2 === 0 ? 'bg-[var(--color-canvas)]' : 'bg-[var(--color-surface-soft)]'}`}>
                                                {row.map((cell, ci) => (
                                                  <td key={ci} className="px-3 py-1.5 text-[var(--color-ink)]">{cell === null ? <span className="text-[var(--color-muted-soft)] italic">NULL</span> : String(cell)}</td>
                                                ))}
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                        <div className="px-3 py-1.5 bg-[var(--color-surface-card)] border-t border-[var(--color-hairline)] text-[10px] text-[var(--color-muted)]">
                                          {parsed.rows.length} row{parsed.rows.length !== 1 ? 's' : ''} returned
                                        </div>
                                      </div>
                                    );
                                  }
                                  if (parsed.type === 'message') {
                                    return (
                                      <div className="flex items-center gap-2 px-3 py-2 bg-[#5cb8a0]/10 border border-[#5cb8a0]/30 rounded-lg text-xs text-[#5cb8a0]">
                                        <CheckCircle2 size={12} />
                                        {parsed.message}
                                      </div>
                                    );
                                  }
                                } catch {
                                  // Fall through to default rendering
                                }
                                return <pre className="text-xs font-mono text-[var(--color-ink)] whitespace-pre-wrap break-words leading-relaxed">{output}</pre>;
                              })()
                            ) : (
                              <pre className="text-xs font-mono text-[var(--color-ink)] whitespace-pre-wrap break-words leading-relaxed">{output}</pre>
                            )}
                          </>
                        )}
                        {artifacts.length > 0 && (
                          <div className="flex flex-col gap-3 mt-3">
                            {artifacts.map((a, i) => (
                              <div key={i} className="rounded-lg overflow-hidden border border-[var(--color-hairline)] bg-[var(--color-canvas)]">
                                <div className="px-2 py-1 border-b border-[var(--color-hairline)] bg-[var(--color-surface-card)] flex items-center justify-between">
                                  <span className="text-[10px] text-[var(--color-muted)] font-medium">
                                    {a.type === 'image' || (a.data && a.data.startsWith('data:image')) ? 'Plot' : a.name || `File ${i + 1}`}
                                  </span>
                                  <button
                                    onClick={() => downloadArtifact(a, i)}
                                    className="text-[10px] text-[#5cb8a0] hover:text-[#4aa890] transition-colors flex items-center gap-1"
                                  >
                                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                                    Download
                                  </button>
                                </div>
                                {(a.type === 'image' || (a.data && a.data.startsWith('data:image'))) ? (
                                  <img
                                    src={a.data || a}
                                    alt={`Plot ${i + 1}`}
                                    className="w-full h-auto block"
                                  />
                                ) : (
                                  <pre className="p-2 text-[10px] font-mono text-[var(--color-ink)] whitespace-pre-wrap break-words max-h-40 overflow-auto">
                                    {a.type === 'file' && a.data
                                      ? (() => { try { return atob(a.data).slice(0, 2000); } catch { return 'Binary file'; } })()
                                      : typeof (a.data || a) === 'string' ? (a.data || a).slice(0, 2000) : JSON.stringify(a, null, 2)
                                    }
                                  </pre>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                        {!output && artifacts.length === 0 && (
                          <div className="text-center py-8">
                            <Terminal size={28} className="mx-auto mb-2 text-hairline" />
                            <p className="text-xs text-[var(--color-muted-soft)]">Run your code to see output</p>
                            <p className="text-[10px] text-hairline mt-1">Ctrl+Enter to run</p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ) : outputTab === 'trace' ? (
                  /* ─── Execution Trace Tab ─── */
                  <div className="flex flex-col h-full">
                    {/* Playback Controls */}
                    {traceData.length > 0 && (
                      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--color-hairline)]">
                        <button
                          onClick={traceStepBack}
                          disabled={traceIndex <= 0}
                          className="p-1 rounded hover:bg-[var(--color-surface-soft)] disabled:opacity-30 text-[var(--color-ink)] transition-all"
                          title="Step back"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
                        </button>

                        <button
                          onClick={toggleTracePlay}
                          className="p-1 rounded hover:bg-[var(--color-surface-soft)] text-[#7c3aed] transition-all"
                          title={tracePlaying ? 'Pause' : 'Play'}
                        >
                          {tracePlaying ? <Square size={14} /> : <Play size={14} />}
                        </button>

                        <button
                          onClick={traceStepForward}
                          disabled={traceIndex >= traceData.length - 1}
                          className="p-1 rounded hover:bg-[var(--color-surface-soft)] disabled:opacity-30 text-[var(--color-ink)] transition-all"
                          title="Step forward"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
                        </button>

                        <div className="flex-1 mx-2">
                          <input
                            type="range"
                            min={0}
                            max={traceData.length - 1}
                            value={traceIndex}
                            onChange={(e) => {
                              const idx = parseInt(e.target.value, 10);
                              setTraceIndex(idx);
                              highlightTraceLine(idx, traceData);
                            }}
                            className="w-full h-1 accent-[#7c3aed] cursor-pointer"
                          />
                        </div>

                        <span className="text-[10px] font-mono text-[var(--color-muted)] min-w-[60px] text-right">
                          {traceIndex + 1} / {traceData.length}
                        </span>
                      </div>
                    )}

                    {/* Trace Content */}
                    <div className="flex-1 overflow-auto p-3">
                      {traceData.length === 0 ? (
                        <div className="text-center py-8">
                          <Map size={28} className="mx-auto mb-2 text-hairline" />
                          <p className="text-xs text-[var(--color-muted-soft)]">Click Trace to visualize execution</p>
                          <p className="text-[10px] text-hairline mt-1">Step through your code line by line</p>
                        </div>
                      ) : traceData[traceIndex] ? (
                        <div className="space-y-3">
                          {/* Current Line Info */}
                          <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-[#7c3aed]/5 border border-[#7c3aed]/20">
                            <span className="text-[10px] font-semibold text-[#7c3aed]">Line {traceData[traceIndex].line}</span>
                            <span className="text-[10px] text-[var(--color-muted)]">•</span>
                            <span className="text-[10px] font-mono text-[var(--color-ink)]">
                              Step {traceIndex + 1} of {traceData.length}
                            </span>
                          </div>

                          {/* Call Stack */}
                          <div>
                            <div className="text-[10px] font-semibold text-[var(--color-muted)] uppercase tracking-wider mb-1 px-1">Call Stack</div>
                            <div className="flex flex-wrap gap-1">
                              {traceData[traceIndex].stack.map((fn, si) => (
                                <span key={si} className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                                  si === traceData[traceIndex].stack.length - 1
                                    ? 'bg-[#7c3aed]/10 text-[#7c3aed] font-semibold'
                                    : 'bg-[var(--color-surface-soft)] text-[var(--color-muted)]'
                                }`}>
                                  {fn}{si < traceData[traceIndex].stack.length - 1 ? ' →' : ''}
                                </span>
                              ))}
                            </div>
                          </div>

                          {/* Variables Table */}
                          <div>
                            <div className="text-[10px] font-semibold text-[var(--color-muted)] uppercase tracking-wider mb-1 px-1">Variables</div>
                            {Object.keys(traceData[traceIndex].variables).length > 0 ? (
                              <div className="rounded-lg border border-[var(--color-hairline)] overflow-hidden">
                                <table className="w-full text-[10px]">
                                  <thead>
                                    <tr className="bg-[var(--color-surface-card)] border-b border-[var(--color-hairline)]">
                                      <th className="px-2 py-1 text-left font-semibold text-[var(--color-ink)]">Name</th>
                                      <th className="px-2 py-1 text-left font-semibold text-[var(--color-ink)]">Value</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {Object.entries(traceData[traceIndex].variables).map(([k, v], vi) => (
                                      <tr key={vi} className={`border-b border-[var(--color-hairline)]/50 ${vi % 2 === 0 ? '' : 'bg-[var(--color-surface-soft)]/30'}`}>
                                        <td className="px-2 py-1 font-mono font-semibold text-[#7c3aed]">{k}</td>
                                        <td className="px-2 py-1 font-mono text-[var(--color-ink)] break-all">{v}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            ) : (
                              <p className="text-[10px] text-[var(--color-muted-soft)] px-1">No variables at this step</p>
                            )}
                          </div>

                          {/* Stdout */}
                          {traceStdout && traceIndex === traceData.length - 1 && (
                            <div>
                              <div className="text-[10px] font-semibold text-[var(--color-muted)] uppercase tracking-wider mb-1 px-1">Output</div>
                              <pre className="p-2 rounded-md bg-[var(--color-surface-soft)] text-[10px] font-mono text-[var(--color-ink)] whitespace-pre-wrap">{traceStdout}</pre>
                            </div>
                          )}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : (
                  /* History Tab */
                  <div className="p-2">
                    {execHistory.length > 0 ? (
                      <div className="space-y-1">
                        {execHistory.map((h, i) => (
                          <div key={h.id || i} className="group rounded-md hover:bg-[var(--color-surface-soft)] transition-colors">
                            <div className="flex items-center gap-2 px-2 py-1.5">
                              {h.status === 'success' ? (
                                <CheckCircle2 size={11} className="text-[#16a34a] flex-shrink-0" />
                              ) : (
                                <XCircle size={11} className="text-[#dc2626] flex-shrink-0" />
                              )}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <span className="font-medium text-[var(--color-ink)]">{h.language}</span>
                                  <span className="text-[var(--color-muted)] font-mono">{h.duration}s</span>
                                </div>
                                <div className="text-[10px] text-[var(--color-muted-soft)] truncate">{h.time} - {h.preview}</div>
                              </div>
                              {h.code && (
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button
                                    onClick={() => restoreFromHistory(h)}
                                    className="px-1.5 py-0.5 text-[10px] text-[#5cb8a0] hover:bg-[#5cb8a0]/10 rounded transition-colors"
                                    title="Restore this code"
                                  >
                                    Restore
                                  </button>
                                  <button
                                    onClick={() => { navigator.clipboard.writeText(h.code); }}
                                    className="px-1.5 py-0.5 text-[10px] text-[var(--color-muted)] hover:bg-[var(--color-hairline)] rounded transition-colors"
                                    title="Copy code"
                                  >
                                    Copy
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <Clock size={28} className="mx-auto mb-2 text-hairline" />
                        <p className="text-xs text-[var(--color-muted-soft)]">No execution history</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ─── AI Sidebar ─── */}
        <AnimatePresence>
          {showAI && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 360, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="border-l border-[var(--color-hairline)] bg-[var(--color-canvas)] flex flex-col overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--color-hairline)]">
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-[#7c3aed]" />
                  <span className="text-sm font-semibold text-[var(--color-ink)]">AI Assistant</span>
                </div>
                <button onClick={() => setShowAI(false)} className="text-[var(--color-muted)] hover:text-[var(--color-ink)] transition-colors">
                  <X size={14} />
                </button>
              </div>

              <div className="flex gap-1.5 px-3 py-2 border-b border-[var(--color-hairline)] overflow-x-auto">
                {[
                  { label: 'Generate', icon: Sparkles, action: 'generate' },
                  { label: 'Explain', icon: MessageSquare, action: 'explain' },
                  { label: 'Fix', icon: Bug, action: 'fix' },
                  { label: 'Optimize', icon: Zap, action: 'optimize' },
                  { label: 'Debug', icon: RefreshCw, action: 'debug' },
                  { label: 'Format', icon: FileCode2, action: 'format' },
                  { label: 'Test', icon: Braces, action: 'test' },
                ].map(({ label, icon: Icon, action }) => (
                  <button
                    key={label}
                    onClick={() => { setAiInput(label); setAiAction(action); if (action === 'generate') { /* don't auto-send — let user type a prompt */ } else { sendAIMessage(action); } }}
                    disabled={aiLoading}
                    className="flex items-center gap-1 px-2 py-1 bg-[var(--color-surface-card)] hover:bg-[var(--color-surface-soft)] border border-[var(--color-hairline)] rounded-md text-[10px] text-[#5cb8a0] whitespace-nowrap transition-all disabled:opacity-50"
                  >
                    <Icon size={10} />
                    {label}
                  </button>
                ))}
              </div>

              <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
                {aiMessages.length === 0 && (
                  <div className="text-center text-[var(--color-muted-soft)] text-xs mt-8">
                    <Sparkles size={28} className="mx-auto mb-2 text-hairline" />
                    <p className="font-medium">Ask me anything</p>
                    <p className="text-[10px] text-hairline mt-1">I can see your code and execution output</p>
                    <p className="text-[10px] text-hairline mt-1">Try "Generate" to write code from a description</p>
                  </div>
                )}
                {aiMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`p-2.5 rounded-lg text-xs ${
                      msg.role === 'user'
                        ? 'bg-[#5cb8a0]/10 text-[var(--color-ink)] ml-4'
                        : msg.isRateLimit
                          ? 'bg-[#b8860b]/10 text-[#b8860b] mr-4 border border-[#b8860b]/30'
                          : 'bg-[var(--color-surface-card)] text-[var(--color-ink)] mr-4 border border-[var(--color-hairline)]'
                    }`}
                  >
                    <pre className="whitespace-pre-wrap font-body text-xs leading-relaxed">{msg.content}</pre>
                  </div>
                ))}
                {aiLoading && (
                  <div className="flex items-center gap-2 text-[#7c3aed] p-2">
                    <Loader2 size={12} className="animate-spin" />
                    <span className="text-xs">Thinking…</span>
                  </div>
                )}
              </div>

              <div className="p-2.5 border-t border-[var(--color-hairline)]">
                <div className="flex gap-1.5">
                  <input
                    type="text"
                    value={aiInput}
                    onChange={(e) => setAiInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { const act = aiAction || 'chat'; sendAIMessage(act); } }}
                    placeholder="Ask about your code..."
                    className="flex-1 px-2.5 py-1.5 bg-[var(--color-surface-card)] border border-[var(--color-hairline)] rounded-md text-xs text-[var(--color-ink)] placeholder-[var(--color-hairline)] focus:outline-none focus:border-[#7c3aed] transition-all"
                  />
                  <button
                    onClick={() => { const act = aiAction || 'chat'; sendAIMessage(act); }}
                    disabled={aiLoading || !aiInput.trim()}
                    className="px-2.5 py-1.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white rounded-md transition-all disabled:opacity-50"
                  >
                    <Send size={12} />
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ─── Status Bar ─── */}
      <div className="flex items-center justify-between px-3 py-1 bg-[var(--color-surface-soft)] border-t border-[var(--color-hairline)] text-[10px]">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-[var(--color-muted)]">
            {isRunning ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-[#b8860b] animate-pulse" />
                Running {timerSeconds}s / 30s
              </>
            ) : (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-[#16a34a]" />
                Ready
              </>
            )}
          </span>
          <span className="text-hairline">|</span>
          <span className="text-[var(--color-muted)]">Ln {cursorPos.line}, Col {cursorPos.col}</span>
          <span className="text-hairline">|</span>
          <span className="text-[var(--color-muted)]">{codeStats.lines} lines</span>
          <span className="text-hairline">|</span>
          <span className="text-[var(--color-muted)]">{codeStats.chars} chars</span>
          <span className="text-hairline">|</span>
          <span className="text-[var(--color-muted)]">{codeStats.words} words</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[var(--color-muted)]">{language.label}</span>
          <span className="text-hairline">|</span>
          <span className="text-[var(--color-muted)]">UTF-8</span>
          <span className="text-hairline">|</span>
          <span className="text-[var(--color-muted)]">Spaces: {tabSize}</span>
          <span className="text-hairline">|</span>
          <span className="text-[var(--color-muted)]">{wordWrap === 'on' ? 'Wrap' : 'No Wrap'}</span>
          {executionTime && (
            <>
              <span className="text-hairline">|</span>
              <span className="text-[var(--color-muted)]">Last: {executionTime}s</span>
            </>
          )}
          {isProjectFile && (
            <>
              <span className="text-hairline">|</span>
              <span className="text-[#5cb8a0] font-medium">Project File</span>
            </>
          )}
        </div>
      </div>

      {/* ─── Keyboard Shortcuts Overlay ─── */}
      <AnimatePresence>
        {showShortcuts && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/30 flex items-center justify-center p-4"
            onClick={() => setShowShortcuts(false)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-[var(--color-canvas)] border border-[var(--color-hairline)] rounded-xl p-5 w-full max-w-sm shadow-2xl"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Keyboard size={16} className="text-[#5cb8a0]" />
                  <h3 className="text-sm font-semibold text-[var(--color-ink)]">Keyboard Shortcuts</h3>
                </div>
                <button onClick={() => setShowShortcuts(false)} className="text-[var(--color-muted)] hover:text-[var(--color-ink)]">
                  <X size={14} />
                </button>
              </div>
              <div className="space-y-1.5">
                {SHORTCUTS.map((s, i) => (
                  <div key={i} className="flex items-center justify-between py-1.5 border-b border-[var(--color-hairline)]/50 last:border-0">
                    <span className="text-xs text-[var(--color-ink)]">{s.desc}</span>
                    <kbd className="px-1.5 py-0.5 bg-[var(--color-surface-card)] border border-[var(--color-hairline)] rounded text-[10px] text-[var(--color-muted)] font-mono">{s.keys}</kbd>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Toast Notification ─── */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 40, x: '-50%' }}
            animate={{ opacity: 1, y: 0, x: '-50%' }}
            exit={{ opacity: 0, y: 40, x: '-50%' }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="fixed bottom-6 left-1/2 z-50 flex items-center gap-2 px-4 py-2.5 bg-[#16a34a]/90 backdrop-blur-sm text-white rounded-lg shadow-xl shadow-[#16a34a]/20 border border-[#16a34a]/30"
          >
            <CheckCircle2 size={14} />
            <span className="text-xs font-medium">{toast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default EditorPage;
