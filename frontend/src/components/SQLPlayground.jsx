import { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react';
import { useTheme } from '../context/ThemeContext';
import api from '../utils/api';
import Editor from '@monaco-editor/react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play, Square, Loader2, Copy, Check, Clock,
  ChevronDown, ChevronRight, Database, Table2,
  Download, Search, X, CheckCircle2,
  XCircle, History, Braces, PanelLeftClose,
  PanelLeftOpen, ArrowUpDown, Clipboard, BookOpen,
  Key, Link, Hash, Rows3, Sparkles, Send, MessageSquare,
  Zap, Wrench,
} from 'lucide-react';

const TABLE_META = {
  Customers: { icon: '\u{1F464}', color: '#5cb8a0', desc: 'Customer information' },
  Products:  { icon: '\u{1F4E6}', color: '#e09060', desc: 'Product catalog' },
  Orders:    { icon: '\u{1F6D2}', color: '#9a7acc', desc: 'Order transactions' },
};

const TEMPLATES = [
  { name: 'Select All', sql: 'SELECT * FROM Customers;', cat: 'Basic', desc: 'Fetch all customer records' },
  { name: 'Filter Rows', sql: "SELECT CustomerName, City, Country\nFROM Customers\nWHERE Country = 'Germany';", cat: 'Basic', desc: 'Filter by country' },
  { name: 'Sort Results', sql: 'SELECT CustomerName, City\nFROM Customers\nORDER BY CustomerName ASC;', cat: 'Basic', desc: 'Sort alphabetically' },
  { name: 'Limit Results', sql: 'SELECT * FROM Products\nORDER BY Price DESC\nLIMIT 5;', cat: 'Basic', desc: 'Top 5 most expensive' },
  { name: 'Count Rows', sql: 'SELECT COUNT(*) AS TotalCustomers\nFROM Customers;', cat: 'Aggregate', desc: 'Count all customers' },
  { name: 'Group By', sql: 'SELECT Country, COUNT(*) AS CustomerCount\nFROM Customers\nGROUP BY Country\nORDER BY CustomerCount DESC;', cat: 'Aggregate', desc: 'Customers per country' },
  { name: 'Avg Price', sql: 'SELECT ROUND(AVG(Price), 2) AS AveragePrice\nFROM Products;', cat: 'Aggregate', desc: 'Average product price' },
  { name: 'Sum Quantity', sql: 'SELECT SUM(Quantity) AS TotalOrdered\nFROM Orders;', cat: 'Aggregate', desc: 'Total items ordered' },
  { name: 'Inner Join', sql: "SELECT c.CustomerName, p.ProductName, o.Quantity\nFROM Orders o\nINNER JOIN Customers c ON o.CustomerID = c.CustomerID\nINNER JOIN Products p ON o.ProductID = p.ProductID\nORDER BY o.Quantity DESC;", cat: 'Join', desc: 'Orders with details' },
  { name: 'Left Join', sql: "SELECT c.CustomerName, o.OrderID, o.Quantity\nFROM Customers c\nLEFT JOIN Orders o ON c.CustomerID = o.CustomerID;", cat: 'Join', desc: 'All customers with orders' },
  { name: 'Multi Join', sql: "SELECT c.CustomerName, c.Country, p.ProductName, p.Price, o.Quantity,\n       (o.Quantity * p.Price) AS TotalCost\nFROM Orders o\nJOIN Customers c ON o.CustomerID = c.CustomerID\nJOIN Products p ON o.ProductID = p.ProductID\nORDER BY TotalCost DESC;", cat: 'Join', desc: 'Full order breakdown' },
  { name: 'Subquery', sql: 'SELECT ProductName, Price\nFROM Products\nWHERE Price > (SELECT AVG(Price) FROM Products)\nORDER BY Price DESC;', cat: 'Advanced', desc: 'Above average price' },
  { name: 'CASE Expression', sql: "SELECT ProductName, Price,\n       CASE\n         WHEN Price < 20 THEN 'Budget'\n         WHEN Price < 50 THEN 'Standard'\n         ELSE 'Premium'\n       END AS PriceCategory\nFROM Products\nORDER BY Price;", cat: 'Advanced', desc: 'Price categorization' },
  { name: 'Insert Row', sql: "INSERT INTO Customers (CustomerName, ContactName, City, Country)\nVALUES ('New Corp', 'John Doe', 'New York', 'USA');", cat: 'DML', desc: 'Add a new customer' },
  { name: 'Update Rows', sql: "UPDATE Products\nSET Price = Price * 1.10\nWHERE Price < 20;", cat: 'DML', desc: 'Increase budget prices' },
  { name: 'Delete Rows', sql: "DELETE FROM Orders\nWHERE Quantity < 3;", cat: 'DML', desc: 'Remove small orders' },
  { name: 'Create Table', sql: "CREATE TABLE Employees (\n  EmployeeID INTEGER PRIMARY KEY AUTOINCREMENT,\n  FirstName TEXT NOT NULL,\n  LastName TEXT NOT NULL,\n  Department TEXT,\n  Salary REAL\n);", cat: 'DDL', desc: 'Create employees table' },
];

const SQLPlayground = ({ languages = [], currentLanguage, onSwitchLanguage }) => {
  const { theme } = useTheme();
  const editorRef = useRef(null);
  const monacoRef = useRef(null);
  const cursorDisposableRef = useRef(null);
  const [showLangDropdown, setShowLangDropdown] = useState(false);

  const [code, setCode] = useState('SELECT * FROM Customers;');
  const [output, setOutput] = useState(null);
  const [error, setError] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [executionTime, setExecutionTime] = useState(null);
  const [outputTab, setOutputTab] = useState('results');
  const [schemaOpen, setSchemaOpen] = useState(true);
  const [expandedTables, setExpandedTables] = useState({});
  const [liveSchema, setLiveSchema] = useState(null);

  // Transform live schema into rendering-friendly format
  const schemaTables = useMemo(() => {
    if (!liveSchema) return null;
    return Object.entries(liveSchema).map(([name, info]) => {
      const meta = TABLE_META[name] || { icon: '\u{1F4CB}', color: '#888', desc: 'User table' };
      return {
        name,
        icon: meta.icon,
        color: meta.color,
        desc: meta.desc,
        columns: info.columns.map(c => ({
          name: c.name,
          type: c.type,
          pk: !!c.pk,
        })),
        rowCount: info.row_count,
      };
    });
  }, [liveSchema]);

  const [queryHistory, setQueryHistory] = useState([]);
  const [historySearch, setHistorySearch] = useState('');
  const [showTemplates, setShowTemplates] = useState(false);
  const [templateCategory, setTemplateCategory] = useState('Basic');
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');
  const [tableFilter, setTableFilter] = useState('');
  const [copied, setCopied] = useState(false);
  const [fontSize, setFontSize] = useState(14);
  const [verticalSplit, setVerticalSplit] = useState(0.4);
  const isDraggingH = useRef(false);
  const containerRef = useRef(null);
  const [toast, setToast] = useState(null);

  // AI Assistant state
  const [showAI, setShowAI] = useState(false);
  const [aiMessages, setAiMessages] = useState([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const aiMessagesEndRef = useRef(null);
  const aiCooldownRef = useRef(false);

  const fetchSchema = async () => {
    try {
      const res = await api.get('/api/sql/schema/');
      setLiveSchema(res.data.tables);
    } catch { /* ignore */ }
  };

  useEffect(() => { fetchSchema(); }, []);

  // Dispose Monaco editor on unmount
  useEffect(() => {
    return () => {
      if (cursorDisposableRef.current) { cursorDisposableRef.current.dispose(); cursorDisposableRef.current = null; }
      if (editorRef.current) { editorRef.current.dispose(); editorRef.current = null; }
      monacoRef.current = null;
    };
  }, []);

  const resetDB = async () => {
    try {
      await api.post('/api/sql/reset/');
      setLiveSchema(null);
      await fetchSchema();
      setOutput(null);
      setToast({ message: 'Database reset to default tables' });
      setTimeout(() => setToast(null), 2500);
    } catch { /* ignore */ }
  };

  const [codeStats, setCodeStats] = useState({ lines: 1, chars: 0, words: 0 });
  const [cursorPos, setCursorPos] = useState({ line: 1, col: 1 });
  const [timerSeconds, setTimerSeconds] = useState(0);
  const timerRef = useRef(null);
  const abortRef = useRef(null);

  const updateCodeStats = (val) => {
    const text = val || '';
    setCodeStats({
      lines: text.split('\n').length,
      chars: text.length,
      words: text.trim() ? text.trim().split(/\s+/).length : 0,
    });
  };

  const handleCodeChange = (val) => { setCode(val || ''); updateCodeStats(val); };

  const handleEditorMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    editor.focus();
    cursorDisposableRef.current = editor.onDidChangeCursorPosition((e) => {
      setCursorPos({ line: e.position.lineNumber, col: e.position.column });
    });
  };

  const runQuery = async () => {
    if (isRunning) return;
    const query = code.trim();
    if (!query) return;
    setIsRunning(true);
    setOutput(null);
    setError('');
    setExecutionTime(null);
    setOutputTab('results');
    setSortColumn(null);
    setSortDirection('asc');
    setTableFilter('');
    setTimerSeconds(0);
    const start = performance.now();
    timerRef.current = setInterval(() => {
      setTimerSeconds(((performance.now() - start) / 1000).toFixed(1));
    }, 100);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const res = await api.post('/api/execute/', { code: query, language: 'sql', stdin: '' }, { signal: controller.signal });
      const elapsed = ((performance.now() - start) / 1000).toFixed(2);
      setExecutionTime(elapsed);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
      setTimerSeconds(elapsed);
      const historyEntry = { id: Date.now(), query, time: new Date().toLocaleTimeString(), duration: elapsed, status: res.data.status === 'success' ? 'success' : 'error', rowsReturned: 0 };
      if (res.data.status === 'success') {
        try {
          const parsed = JSON.parse(res.data.output);
          setOutput(parsed);
          if (parsed.type === 'table') historyEntry.rowsReturned = parsed.rows.length;
        } catch { setOutput({ type: 'raw', data: res.data.output }); }
      } else {
        setError(res.data.error || 'Execution failed');
        historyEntry.status = 'error';
      }
      setQueryHistory(prev => [historyEntry, ...prev].slice(0, 50));
      fetchSchema();
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') {
        setError('Execution cancelled.');
      } else {
        const elapsed = ((performance.now() - start) / 1000).toFixed(2);
        setExecutionTime(elapsed);
        setError(err.response?.data?.error || err.message);
        setQueryHistory(prev => [{ id: Date.now(), query, time: new Date().toLocaleTimeString(), duration: elapsed, status: 'error', rowsReturned: 0 }, ...prev].slice(0, 50));
      }
    } finally {
      setIsRunning(false);
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
      abortRef.current = null;
    }
  };

  const cancelRun = () => { if (abortRef.current) abortRef.current.abort(); };

  const formatSQL = () => {
    const formatted = code.replace(/\s+/g, ' ').replace(/\s*,\s*/g, ',\n  ')
      .replace(/\bSELECT\b/gi, 'SELECT\n  ').replace(/\bFROM\b/gi, '\nFROM')
      .replace(/\bWHERE\b/gi, '\nWHERE').replace(/\bAND\b/gi, '\n  AND')
      .replace(/\bOR\b/gi, '\n  OR').replace(/\bORDER BY\b/gi, '\nORDER BY')
      .replace(/\bGROUP BY\b/gi, '\nGROUP BY').replace(/\bHAVING\b/gi, '\nHAVING')
      .replace(/\bLIMIT\b/gi, '\nLIMIT').replace(/\bJOIN\b/gi, '\nJOIN')
      .replace(/\bINNER JOIN\b/gi, '\nINNER JOIN').replace(/\bLEFT JOIN\b/gi, '\nLEFT JOIN')
      .replace(/\bRIGHT JOIN\b/gi, '\nRIGHT JOIN').replace(/\bON\b/gi, '\n  ON')
      .replace(/\bVALUES\b/gi, '\nVALUES').replace(/\bSET\b/gi, '\n  SET')
      .trim();
    setCode(formatted);
    setToast({ message: 'SQL formatted' });
    setTimeout(() => setToast(null), 2000);
  };

  const copyQuery = () => { navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); };

  const MAX_AI_MESSAGES = 20;
  const appendAIMessage = useCallback((msg) => {
    setAiMessages(prev => {
      const next = [...prev, msg];
      return next.length > MAX_AI_MESSAGES ? next.slice(-MAX_AI_MESSAGES) : next;
    });
  }, []);

  // ─── SQL AI Assistant ───
  const sendSQLAI = async (action, userMsg) => {
    const msg = userMsg || aiInput.trim();
    if (!msg || aiLoading || aiCooldownRef.current) return;
    if (action !== 'chat') setAiInput('');
    appendAIMessage({ role: 'user', content: msg });
    setAiLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/sql-ai/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ action, query: code, message: msg }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let aiContent = '';
      let buffer = '';

      appendAIMessage({ role: 'assistant', content: '' });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6);
            if (payload === '[DONE]') break;
            if (payload.startsWith('[ERROR]')) {
              aiContent += payload.replace('[ERROR] ', '');
            } else {
              aiContent += payload.replace(/\\n/g, '\n');
            }
            setAiMessages(prev => {
              const updated = [...prev];
              updated[updated.length - 1] = { role: 'assistant', content: aiContent };
              return updated;
            });
          }
        }
      }

      // Auto-apply generated SQL to editor
      if (action === 'generate' && aiContent) {
        const sqlMatch = aiContent.match(/```sql\s*([\s\S]*?)```/);
        const sql = sqlMatch ? sqlMatch[1].trim() : aiContent.trim();
        if (sql) {
          setCode(sql);
          updateCodeStats(sql);
          setToast({ message: 'AI-generated SQL applied to editor' });
          setTimeout(() => setToast(null), 3000);
        }
      }
    } catch (err) {
      appendAIMessage({ role: 'assistant', content: `Error: ${err.message}` });
    } finally {
      setAiLoading(false);
      aiCooldownRef.current = true;
      setTimeout(() => { aiCooldownRef.current = false; }, 500);
    }
  };

  const exportResults = (fmt) => {
    if (!output || output.type !== 'table') return;
    const { columns, rows } = output;
    let content, filename, mimeType;
    if (fmt === 'csv') {
      content = columns.join(',') + '\n' + rows.map(r => r.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
      filename = 'query_results.csv'; mimeType = 'text/csv';
    } else if (fmt === 'json') {
      content = JSON.stringify(rows.map(r => { const o = {}; columns.forEach((c, i) => { o[c] = r[i]; }); return o; }), null, 2);
      filename = 'query_results.json'; mimeType = 'application/json';
    } else {
      content = '| ' + columns.join(' | ') + ' |\n| ' + columns.map(() => '---').join(' | ') + ' |\n' + rows.map(r => '| ' + r.map(c => String(c ?? '')).join(' | ') + ' |').join('\n');
      filename = 'query_results.md'; mimeType = 'text/markdown';
    }
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
    setToast({ message: `Exported as ${fmt.toUpperCase()}` });
    setTimeout(() => setToast(null), 2000);
  };

  const insertTemplate = (sql) => { setCode(sql); updateCodeStats(sql); setShowTemplates(false); if (editorRef.current) editorRef.current.focus(); };

  const insertSchemaName = (name) => {
    if (editorRef.current) {
      const s = editorRef.current.getSelection();
      editorRef.current.executeEdits('schema-insert', [{ range: { startLineNumber: s.startLineNumber, startColumn: s.startColumn, endLineNumber: s.endLineNumber, endColumn: s.endColumn }, text: name, forceMoveMarkers: true }]);
      editorRef.current.focus();
    } else { setCode(prev => prev + name); }
  };

  const toggleTable = (t) => setExpandedTables(prev => ({ ...prev, [t]: !prev[t] }));

  const sortedOutput = useMemo(() => {
    if (!output) return null;
    // Pass through messages as-is
    if (output.type === 'message') return output;
    if (output.type !== 'table') return null;
    let rows = [...output.rows];
    if (tableFilter) { const l = tableFilter.toLowerCase(); rows = rows.filter(r => r.some(c => String(c ?? '').toLowerCase().includes(l))); }
    if (sortColumn !== null) {
      rows.sort((a, b) => {
        const av = a[sortColumn], bv = b[sortColumn];
        if (av === null) return 1; if (bv === null) return -1;
        if (typeof av === 'number' && typeof bv === 'number') return sortDirection === 'asc' ? av - bv : bv - av;
        return sortDirection === 'asc' ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
      });
    }
    return { ...output, rows };
  }, [output, sortColumn, sortDirection, tableFilter]);

  const filteredHistory = useMemo(() => {
    if (!historySearch) return queryHistory;
    const l = historySearch.toLowerCase();
    return queryHistory.filter(h => h.query.toLowerCase().includes(l));
  }, [queryHistory, historySearch]);

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); runQuery(); }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'F') { e.preventDefault(); formatSQL(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [code, isRunning]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  useEffect(() => {
    if (!showLangDropdown) return;
    const handler = (e) => {
      if (!e.target.closest('[data-lang-switcher]')) setShowLangDropdown(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showLangDropdown]);

  const onHorizontalDrag = useCallback((e) => {
    e.preventDefault(); isDraggingH.current = true;
    document.body.style.cursor = 'row-resize'; document.body.style.userSelect = 'none';
    const onMove = (ev) => { if (!isDraggingH.current || !containerRef.current) return; const r = containerRef.current.getBoundingClientRect(); setVerticalSplit(Math.min(Math.max((ev.clientY - r.top) / r.height, 0.15), 0.85)); };
    const onUp = () => { isDraggingH.current = false; document.body.style.cursor = ''; document.body.style.userSelect = ''; document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
    document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp);
  }, []);

  const monacoOptions = {
    fontSize, fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontLigatures: true,
    minimap: { enabled: false }, scrollBeyondLastLine: false, smoothScrolling: true,
    cursorBlinking: 'smooth', cursorSmoothCaretAnimation: 'on', wordWrap: 'on',
    padding: { top: 16, bottom: 16 }, renderLineHighlight: 'all',
    bracketPairColorization: { enabled: true }, suggest: { showKeywords: true, showSnippets: true },
    tabSize: 2, lineNumbers: 'on', glyphMargin: false, folding: true, automaticLayout: true,
    quickSuggestions: true, formatOnPaste: true,
  };

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]" style={{ background: 'var(--color-canvas)' }}>
      {/* ═══ TOP BAR ═══ */}
      <div className="flex items-center justify-between px-4 py-2 border-b" style={{ background: 'var(--color-surface-soft)', borderColor: 'var(--color-hairline)' }}>
        <div className="flex items-center gap-3">
          {/* Language Switcher */}
          <div className="relative" data-lang-switcher>
            <button onClick={() => setShowLangDropdown(!showLangDropdown)} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all" style={{ border: '1px solid #5cb8a040', background: 'linear-gradient(135deg, #5cb8a015, #1a3a3a10)', color: '#5cb8a0' }}>
              <span>{currentLanguage?.icon || '🗄️'}</span>
              <span>{currentLanguage?.label || 'SQL'}</span>
              <ChevronDown size={10} />
            </button>
            <AnimatePresence>
              {showLangDropdown && (
                <motion.div initial={{ opacity: 0, y: -4, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -4, scale: 0.98 }} transition={{ duration: 0.12 }} className="absolute top-full mt-2 left-0 rounded-xl shadow-2xl overflow-hidden z-50 min-w-[160px]" style={{ background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)' }}>
                  {languages.map((lang) => (
                    <button key={lang.id} onClick={() => { onSwitchLanguage(lang); setShowLangDropdown(false); }} className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs transition-all" style={{ color: lang.id === 'sql' ? '#5cb8a0' : 'var(--color-ink)', background: lang.id === 'sql' ? '#5cb8a008' : 'transparent' }} onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-card)'} onMouseLeave={e => e.currentTarget.style.background = lang.id === 'sql' ? '#5cb8a008' : 'transparent'}>
                      <span className="text-sm">{lang.icon}</span>
                      <span className="font-medium">{lang.label}</span>
                      {lang.id === 'sql' && <Check size={10} className="ml-auto text-[#5cb8a0]" />}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="h-5 w-px" style={{ background: 'var(--color-hairline)' }} />
          <button onClick={() => setSchemaOpen(!schemaOpen)} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-all" style={{ border: schemaOpen ? '1px solid #5cb8a040' : '1px solid var(--color-hairline)', background: schemaOpen ? '#5cb8a008' : 'transparent', color: schemaOpen ? '#5cb8a0' : 'var(--color-muted)' }}>
            {schemaOpen ? <PanelLeftClose size={12} /> : <PanelLeftOpen size={12} />}
            <span>Schema</span>
          </button>
          <div className="relative">
            <button onClick={() => setShowTemplates(!showTemplates)} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-all" style={{ border: '1px solid var(--color-hairline)', color: 'var(--color-muted)' }}>
              <BookOpen size={12} /><span>Templates</span><ChevronDown size={10} />
            </button>
            <AnimatePresence>
              {showTemplates && (
                <motion.div initial={{ opacity: 0, y: -4, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -4, scale: 0.98 }} transition={{ duration: 0.15 }} className="absolute top-full mt-2 left-0 rounded-xl shadow-2xl overflow-hidden z-50 w-96" style={{ background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)' }}>
                  <div className="flex items-center gap-1 px-3 py-2 border-b" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-card)' }}>
                    {['Basic', 'Aggregate', 'Join', 'Advanced', 'DML', 'DDL'].map(cat => (
                      <button key={cat} onClick={() => setTemplateCategory(cat)} className="px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all" style={{ background: templateCategory === cat ? '#5cb8a0' : 'transparent', color: templateCategory === cat ? 'white' : 'var(--color-muted)' }}>{cat}</button>
                    ))}
                  </div>
                  <div className="overflow-y-auto max-h-80 p-1">
                    {TEMPLATES.filter(t => t.cat === templateCategory).map((t, i) => (
                      <button key={i} onClick={() => insertTemplate(t.sql)} className="w-full text-left px-3 py-2.5 rounded-lg transition-all" style={{ border: '1px solid transparent' }} onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-surface-card)'; e.currentTarget.style.borderColor = 'var(--color-hairline)'; }} onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; }}>
                        <div className="flex items-center justify-between"><span className="text-xs font-semibold" style={{ color: 'var(--color-ink)' }}>{t.name}</span><span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: '#5cb8a015', color: '#5cb8a0' }}>{t.cat}</span></div>
                        <div className="text-[10px] mt-0.5" style={{ color: 'var(--color-muted-soft)' }}>{t.desc}</div>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          <button onClick={formatSQL} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-all" style={{ border: '1px solid var(--color-hairline)', color: 'var(--color-muted)' }} title="Ctrl+Shift+F">
            <Braces size={12} /><span>Format</span>
          </button>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg overflow-hidden" style={{ border: '1px solid var(--color-hairline)' }}>
            <button onClick={() => setFontSize(s => Math.max(10, s - 1))} className="px-2 py-1.5 text-xs transition-colors" style={{ color: 'var(--color-muted)' }}>-</button>
            <span className="text-[10px] font-mono w-6 text-center" style={{ color: 'var(--color-ink)', borderLeft: '1px solid var(--color-hairline)', borderRight: '1px solid var(--color-hairline)' }}>{fontSize}</span>
            <button onClick={() => setFontSize(s => Math.min(24, s + 1))} className="px-2 py-1.5 text-xs transition-colors" style={{ color: 'var(--color-muted)' }}>+</button>
          </div>
          <button onClick={copyQuery} className="p-2 rounded-lg transition-all" style={{ border: '1px solid var(--color-hairline)', color: copied ? '#16a34a' : 'var(--color-muted)' }} title="Copy query">
            {copied ? <Check size={12} /> : <Copy size={12} />}
          </button>
          <button onClick={() => setShowAI(!showAI)} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all" style={{ border: showAI ? '1px solid #7c3aed40' : '1px solid var(--color-hairline)', background: showAI ? '#7c3aed10' : 'transparent', color: showAI ? '#7c3aed' : 'var(--color-muted)' }}>
            <Sparkles size={12} /><span>AI</span>
          </button>
          {isRunning ? (
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg font-mono text-xs" style={{ background: '#b8860b15', border: '1px solid #b8860b30', color: '#b8860b' }}>
                <Loader2 size={12} className="animate-spin" /><span>{timerSeconds}s</span>
              </div>
              <button onClick={cancelRun} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-white transition-all" style={{ background: '#dc2626' }}>
                <Square size={10} className="fill-white" />Stop
              </button>
            </div>
          ) : (
            <button onClick={runQuery} className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold text-white transition-all shadow-lg" style={{ background: 'linear-gradient(135deg, #16a34a, #15803d)', boxShadow: '0 2px 8px #16a34a30' }}>
              <Play size={12} className="fill-white" />Run Query<kbd className="text-[9px] opacity-50 font-normal ml-1">Ctrl+Enter</kbd>
            </button>
          )}
        </div>
      </div>

      {/* ═══ MAIN AREA ═══ */}
      <div ref={containerRef} className="flex-1 flex min-h-0">
        {/* ─── Schema Browser ─── */}
        <AnimatePresence>
          {schemaOpen && (
            <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: 280, opacity: 1 }} exit={{ width: 0, opacity: 0 }} transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }} className="flex-shrink-0 flex flex-col overflow-hidden" style={{ borderRight: '1px solid var(--color-hairline)', background: 'var(--color-surface-card)' }}>
              {/* Schema Header */}
              <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-soft)' }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center justify-center w-5 h-5 rounded-md" style={{ background: '#5cb8a015' }}><Database size={10} className="text-[#5cb8a0]" /></div>
                    <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--color-muted)' }}>Database Schema</span>
                  </div>
                  <button onClick={resetDB} className="text-[9px] px-2 py-1 rounded-md font-semibold transition-all" style={{ color: 'var(--color-muted)', border: '1px solid var(--color-hairline)' }} onMouseEnter={e => { e.currentTarget.style.borderColor = '#dc262640'; e.currentTarget.style.color = '#dc2626'; }} onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--color-hairline)'; e.currentTarget.style.color = 'var(--color-muted)'; }} title="Reset database to defaults">
                    Reset
                  </button>
                </div>
                <p className="text-[10px] mt-1.5 ml-7" style={{ color: 'var(--color-muted-soft)' }}>SQLite in-memory &middot; {schemaTables ? schemaTables.length : '...'} tables</p>
              </div>

              {/* Table List */}
              <div className="flex-1 overflow-y-auto py-2 px-2">
                {!schemaTables ? (
                  <div className="text-center py-6" style={{ color: 'var(--color-muted-soft)' }}>
                    <Loader2 size={14} className="animate-spin mx-auto mb-1" />
                    <span className="text-[10px]">Loading schema...</span>
                  </div>
                ) : schemaTables.length === 0 ? (
                  <div className="text-center py-6" style={{ color: 'var(--color-muted-soft)' }}>
                    <span className="text-[10px]">No tables found</span>
                  </div>
                ) : schemaTables.map((table) => (
                  <div key={table.name} className="mb-1.5">
                    {/* Table Header */}
                    <button onClick={() => toggleTable(table.name)} className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg transition-all group" style={{ background: expandedTables[table.name] ? `${table.color}08` : 'transparent' }} onMouseEnter={e => { if (!expandedTables[table.name]) e.currentTarget.style.background = `${table.color}05`; }} onMouseLeave={e => { if (!expandedTables[table.name]) e.currentTarget.style.background = 'transparent'; }}>
                      <div className="flex items-center justify-center w-6 h-6 rounded-md" style={{ background: `${table.color}15` }}>
                        <span className="text-xs">{table.icon}</span>
                      </div>
                      <div className="flex-1 text-left">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold" style={{ color: 'var(--color-ink)' }}>{table.name}</span>
                          <span className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold" style={{ background: `${table.color}15`, color: table.color }}>{table.columns.length} cols</span>
                        </div>
                        <div className="text-[9px] mt-0.5" style={{ color: 'var(--color-muted-soft)' }}>{table.desc}</div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[9px] font-mono" style={{ color: 'var(--color-muted-soft)' }}>{table.rowCount}r</span>
                        <motion.div animate={{ rotate: expandedTables[table.name] ? 90 : 0 }} transition={{ duration: 0.15 }}>
                          <ChevronRight size={10} style={{ color: 'var(--color-muted)' }} />
                        </motion.div>
                      </div>
                    </button>

                    {/* Column List */}
                    <AnimatePresence>
                      {expandedTables[table.name] && (
                        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
                          <div className="ml-4 mr-1 mb-1 rounded-lg overflow-hidden" style={{ border: '1px solid var(--color-hairline)' }}>
                            {table.columns.map((col, ci) => (
                              <button key={col.name} onClick={() => insertSchemaName(col.name)} className="w-full flex items-center gap-2 px-3 py-2 transition-all group" style={{ borderTop: ci > 0 ? '1px solid var(--color-hairline)' : 'none' }} onMouseEnter={e => e.currentTarget.style.background = '#5cb8a008'} onMouseLeave={e => e.currentTarget.style.background = 'transparent'} title={`Insert ${col.name}`}>
                                <div className="flex items-center justify-center w-4 h-4 rounded" style={{ background: col.pk ? '#e0906015' : col.fk ? '#9a7acc15' : '#5cb8a010' }}>
                                  {col.pk ? <Key size={8} className="text-[#e09060]" /> : col.fk ? <Link size={8} className="text-[#9a7acc]" /> : <Hash size={8} style={{ color: 'var(--color-muted-soft)' }} />}
                                </div>
                                <div className="flex-1 text-left">
                                  <span className="text-[11px] font-mono font-medium" style={{ color: 'var(--color-ink)' }}>{col.name}</span>
                                </div>
                                <span className="text-[9px] font-mono" style={{ color: 'var(--color-muted-soft)' }}>{col.type}</span>
                                {col.pk && <span className="text-[8px] px-1 py-0.5 rounded font-bold" style={{ background: '#e0906015', color: '#e09060' }}>PK</span>}
                                {col.fk && <span className="text-[8px] px-1 py-0.5 rounded font-bold" style={{ background: '#9a7acc15', color: '#9a7acc' }}>FK</span>}
                              </button>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))}

                {/* Relationships */}
                <div className="mt-3 px-3 py-2.5 rounded-lg" style={{ background: 'var(--color-surface-soft)', border: '1px solid var(--color-hairline)' }}>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Link size={9} className="text-[#9a7acc]" />
                    <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: 'var(--color-muted)' }}>Relationships</span>
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1 text-[10px]">
                      <span className="font-mono font-medium" style={{ color: '#e09060' }}>Orders.CustomerID</span>
                      <span style={{ color: 'var(--color-muted-soft)' }}>&rarr;</span>
                      <span className="font-mono font-medium" style={{ color: '#5cb8a0' }}>Customers.ID</span>
                    </div>
                    <div className="flex items-center gap-1 text-[10px]">
                      <span className="font-mono font-medium" style={{ color: '#e09060' }}>Orders.ProductID</span>
                      <span style={{ color: 'var(--color-muted-soft)' }}>&rarr;</span>
                      <span className="font-mono font-medium" style={{ color: '#5cb8a0' }}>Products.ID</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ─── Editor + Results ─── */}
        <div className="flex-1 flex flex-col min-w-0 min-h-0">
          {/* Editor */}
          <div style={{ height: `${verticalSplit * 100}%`, minHeight: 0 }}>
            <Editor height="100%" language="sql" value={code} onChange={handleCodeChange} onMount={handleEditorMount} theme={theme === 'dark' ? 'vs-dark' : 'vs'} options={monacoOptions} />
          </div>

          {/* Drag Handle */}
          <div onMouseDown={onHorizontalDrag} className="h-1.5 flex-shrink-0 cursor-row-resize flex items-center justify-center transition-colors group" style={{ background: 'var(--color-hairline)' }} onMouseEnter={e => e.currentTarget.style.background = '#5cb8a040'} onMouseLeave={e => e.currentTarget.style.background = 'var(--color-hairline)'}>
            <div className="w-10 h-[3px] rounded-full transition-colors" style={{ background: 'var(--color-muted)', opacity: 0.2 }} />
          </div>

          {/* Results */}
          <div className="flex flex-col overflow-hidden" style={{ height: `${(1 - verticalSplit) * 100}%`, minHeight: 0 }}>
            {/* Tabs */}
            <div className="flex items-center justify-between px-4 border-b" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-card)' }}>
              <div className="flex items-center">
                {[{ id: 'results', label: 'Results', icon: Rows3 }, { id: 'history', label: 'History', icon: History, count: queryHistory.length }].map(tab => (
                  <button key={tab.id} onClick={() => setOutputTab(tab.id)} className="flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold transition-all relative" style={{ color: outputTab === tab.id ? '#5cb8a0' : 'var(--color-muted)' }}>
                    <tab.icon size={12} />{tab.label}
                    {tab.count > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded-full font-mono" style={{ background: '#5cb8a015', color: '#5cb8a0' }}>{tab.count}</span>}
                    {outputTab === tab.id && <motion.div layoutId="sql-tab" className="absolute bottom-0 left-0 right-0 h-[2px] rounded-full" style={{ background: '#5cb8a0' }} />}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2">
                {executionTime && outputTab === 'results' && (
                  <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded-md" style={{ background: '#5cb8a010', color: '#5cb8a0' }}>
                    <Clock size={10} />{executionTime}s
                  </span>
                )}
                {sortedOutput && sortedOutput.type === 'table' && (
                  <>
                    <span className="text-[10px] font-mono px-2 py-1 rounded-md" style={{ background: 'var(--color-surface-soft)', color: 'var(--color-muted)' }}>{sortedOutput.rows.length} rows</span>
                    <div className="relative group">
                      <button className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium transition-all" style={{ border: '1px solid var(--color-hairline)', color: 'var(--color-muted)' }}>
                        <Download size={10} />Export
                      </button>
                      <div className="absolute right-0 top-full mt-1 rounded-lg shadow-xl overflow-hidden hidden group-hover:block z-50 w-32" style={{ background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)' }}>
                        {[{ fmt: 'csv', label: 'CSV File' }, { fmt: 'json', label: 'JSON' }, { fmt: 'markdown', label: 'Markdown' }].map(o => (
                          <button key={o.fmt} onClick={() => exportResults(o.fmt)} className="w-full text-left px-3 py-2 text-xs transition-colors" style={{ color: 'var(--color-ink)' }} onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-card)'} onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>{o.label}</button>
                        ))}
                      </div>
                    </div>
                    <button onClick={() => { navigator.clipboard.writeText(JSON.stringify({ columns: sortedOutput.columns, rows: sortedOutput.rows }, null, 2)); setToast({ message: 'Copied to clipboard' }); setTimeout(() => setToast(null), 2000); }} className="p-1.5 rounded-lg transition-all" style={{ border: '1px solid var(--color-hairline)', color: 'var(--color-muted)' }} title="Copy as JSON">
                      <Clipboard size={10} />
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto" style={{ minHeight: 0 }}>
              {outputTab === 'results' ? (
                <div className="h-full flex flex-col">
                  {isRunning ? (
                    <div className="flex flex-col items-center justify-center h-full gap-3">
                      <div className="relative">
                        <div className="w-10 h-10 rounded-full border-2 animate-spin" style={{ borderColor: '#5cb8a020', borderTopColor: '#5cb8a0' }} />
                        <Loader2 size={16} className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 animate-spin" style={{ color: '#5cb8a0' }} />
                      </div>
                      <span className="text-xs font-medium" style={{ color: 'var(--color-muted)' }}>Executing query...</span>
                    </div>
                  ) : error ? (
                    <div className="p-5">
                      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #dc262625', background: '#dc262608' }}>
                        <div className="flex items-center gap-2 px-4 py-2.5" style={{ background: '#dc262610', borderBottom: '1px solid #dc262620' }}>
                          <XCircle size={13} className="text-[#dc2626]" />
                          <span className="text-xs font-bold text-[#dc2626]">Query Error</span>
                        </div>
                        <pre className="px-4 py-3 text-xs font-mono whitespace-pre-wrap break-words text-[#dc2626]" style={{ lineHeight: '1.6' }}>{error}</pre>
                      </div>
                    </div>
                  ) : sortedOutput ? (
                    sortedOutput.type === 'table' ? (
                      <div className="h-full flex flex-col">
                        {/* Filter */}
                        <div className="px-4 py-2 border-b" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-soft)' }}>
                          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)' }}>
                            <Search size={11} style={{ color: 'var(--color-muted)' }} />
                            <input type="text" value={tableFilter} onChange={(e) => setTableFilter(e.target.value)} placeholder="Filter rows..." className="flex-1 bg-transparent text-xs focus:outline-none" style={{ color: 'var(--color-ink)' }} />
                            {tableFilter && <button onClick={() => setTableFilter('')} style={{ color: 'var(--color-muted)' }}><X size={10} /></button>}
                          </div>
                        </div>
                        {/* Table */}
                        <div className="flex-1 overflow-auto">
                          <table className="w-full">
                            <thead className="sticky top-0 z-10">
                              <tr>
                                <th className="px-3 py-2.5 text-center text-[9px] font-bold uppercase tracking-wider w-12" style={{ background: 'var(--color-surface-card)', color: 'var(--color-muted)', borderBottom: '2px solid var(--color-hairline)' }}>#</th>
                                {sortedOutput.columns.map((col, ci) => (
                                  <th key={ci} onClick={() => { setSortColumn(ci); setSortDirection(d => sortColumn === ci ? (d === 'asc' ? 'desc' : 'asc') : 'asc'); }} className="px-4 py-2.5 text-left text-[10px] font-bold uppercase tracking-wider cursor-pointer transition-colors group" style={{ background: 'var(--color-surface-card)', color: 'var(--color-ink)', borderBottom: '2px solid var(--color-hairline)' }} onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-soft)'} onMouseLeave={e => e.currentTarget.style.background = 'var(--color-surface-card)'}>
                                    <div className="flex items-center gap-1.5">
                                      {col}
                                      <ArrowUpDown size={8} className="transition-opacity" style={{ opacity: sortColumn === ci ? 1 : 0, color: '#5cb8a0' }} />
                                    </div>
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {sortedOutput.rows.map((row, ri) => (
                                <tr key={ri} className="transition-colors" style={{ background: ri % 2 === 0 ? 'var(--color-canvas)' : 'var(--color-surface-soft)' }} onMouseEnter={e => e.currentTarget.style.background = '#5cb8a008'} onMouseLeave={e => e.currentTarget.style.background = ri % 2 === 0 ? 'var(--color-canvas)' : 'var(--color-surface-soft)'}>
                                  <td className="px-3 py-2 text-center text-[9px] font-mono" style={{ color: 'var(--color-muted-soft)', borderBottom: '1px solid var(--color-hairline)' }}>{ri + 1}</td>
                                  {row.map((cell, ci) => (
                                    <td key={ci} className="px-4 py-2 text-[11px] font-mono" style={{ color: 'var(--color-ink)', borderBottom: '1px solid var(--color-hairline)' }}>
                                      {cell === null ? (
                                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] italic" style={{ background: 'var(--color-surface-strong)', color: 'var(--color-muted-soft)' }}>NULL</span>
                                      ) : typeof cell === 'number' ? (
                                        <span className="font-semibold" style={{ color: '#e09060' }}>{cell.toLocaleString()}</span>
                                      ) : (
                                        <span className="max-w-[200px] truncate inline-block">{String(cell)}</span>
                                      )}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        {/* Footer */}
                        <div className="flex items-center justify-between px-4 py-2 border-t" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-card)' }}>
                          <span className="text-[10px] font-medium" style={{ color: 'var(--color-muted)' }}>{sortedOutput.rows.length} row{sortedOutput.rows.length !== 1 ? 's' : ''} returned</span>
                          <span className="text-[10px] font-medium" style={{ color: 'var(--color-muted)' }}>{sortedOutput.columns.length} column{sortedOutput.columns.length !== 1 ? 's' : ''}</span>
                        </div>
                      </div>
                    ) : sortedOutput.type === 'message' ? (
                      <div className="flex flex-col items-center justify-center h-full gap-3">
                        <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: '#16a34a10', border: '2px solid #16a34a30' }}>
                          <CheckCircle2 size={24} className="text-[#16a34a]" />
                        </div>
                        <div className="text-center">
                          <p className="text-sm font-semibold" style={{ color: '#16a34a' }}>Success</p>
                          <p className="text-[11px] mt-1" style={{ color: 'var(--color-muted-soft)' }}>{sortedOutput.message}</p>
                        </div>
                      </div>
                    ) : (
                      <div className="p-4"><pre className="text-xs font-mono whitespace-pre-wrap break-words" style={{ color: 'var(--color-ink)' }}>{sortedOutput.data}</pre></div>
                    )
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full gap-3">
                      <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{ background: 'var(--color-surface-card)', border: '2px dashed var(--color-hairline)' }}>
                        <Table2 size={24} style={{ color: 'var(--color-muted-soft)', opacity: 0.5 }} />
                      </div>
                      <div className="text-center">
                        <p className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>Ready to query</p>
                        <p className="text-[11px] mt-1" style={{ color: 'var(--color-muted-soft)' }}>Write SQL and press <kbd className="px-1.5 py-0.5 rounded text-[9px] font-mono" style={{ background: 'var(--color-surface-card)', border: '1px solid var(--color-hairline)' }}>Ctrl+Enter</kbd> to execute</p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-3">
                  <div className="mb-3">
                    <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: 'var(--color-surface-soft)', border: '1px solid var(--color-hairline)' }}>
                      <Search size={11} style={{ color: 'var(--color-muted)' }} />
                      <input type="text" value={historySearch} onChange={(e) => setHistorySearch(e.target.value)} placeholder="Search queries..." className="flex-1 bg-transparent text-xs focus:outline-none" style={{ color: 'var(--color-ink)' }} />
                    </div>
                  </div>
                  {filteredHistory.length > 0 ? (
                    <div className="space-y-1.5">
                      {filteredHistory.map((h) => (
                        <div key={h.id} className="rounded-lg transition-all group" style={{ border: '1px solid var(--color-hairline)' }} onMouseEnter={e => e.currentTarget.style.borderColor = '#5cb8a040'} onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-hairline)'}>
                          <div className="flex items-start gap-3 px-3 py-2.5">
                            <div className="mt-0.5">{h.status === 'success' ? <CheckCircle2 size={12} className="text-[#16a34a]" /> : <XCircle size={12} className="text-[#dc2626]" />}</div>
                            <div className="flex-1 min-w-0">
                              <pre className="text-[11px] font-mono whitespace-pre-wrap break-words line-clamp-2" style={{ color: 'var(--color-ink)' }}>{h.query}</pre>
                              <div className="flex items-center gap-3 mt-1.5">
                                <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: 'var(--color-surface-card)', color: 'var(--color-muted-soft)' }}>{h.time}</span>
                                <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: '#5cb8a010', color: '#5cb8a0' }}>{h.duration}s</span>
                                {h.rowsReturned > 0 && <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: '#e0906010', color: '#e09060' }}>{h.rowsReturned} rows</span>}
                              </div>
                            </div>
                            <button onClick={() => { setCode(h.query); updateCodeStats(h.query); setOutputTab('results'); if (editorRef.current) editorRef.current.focus(); }} className="px-2 py-1 text-[9px] font-semibold rounded-md transition-all opacity-0 group-hover:opacity-100" style={{ color: '#5cb8a0', background: '#5cb8a010' }}>Restore</button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-12 gap-2">
                      <History size={28} style={{ color: 'var(--color-muted-soft)', opacity: 0.3 }} />
                      <p className="text-xs" style={{ color: 'var(--color-muted-soft)' }}>No query history yet</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ─── AI Sidebar ─── */}
        <AnimatePresence>
          {showAI && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 340, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="flex-shrink-0 flex flex-col overflow-hidden"
              style={{ borderLeft: '1px solid var(--color-hairline)', background: 'var(--color-canvas)' }}
            >
              {/* AI Header */}
              <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-card)' }}>
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-[#7c3aed]" />
                  <span className="text-sm font-semibold" style={{ color: 'var(--color-ink)' }}>SQL AI Assistant</span>
                </div>
                <button onClick={() => setShowAI(false)} className="p-1 rounded-md transition-colors" style={{ color: 'var(--color-muted)' }} onMouseEnter={e => e.currentTarget.style.color = 'var(--color-ink)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--color-muted)'}>
                  <X size={14} />
                </button>
              </div>

              {/* Quick Actions */}
              <div className="flex gap-1.5 px-3 py-2 border-b overflow-x-auto" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-soft)' }}>
                {[
                  { label: 'Generate', icon: Sparkles, action: 'generate', desc: 'Write SQL from description' },
                  { label: 'Explain', icon: MessageSquare, action: 'explain', desc: 'Explain current query' },
                  { label: 'Optimize', icon: Zap, action: 'optimize', desc: 'Improve performance' },
                  { label: 'Fix', icon: Wrench, action: 'fix', desc: 'Fix query errors' },
                ].map(({ label, icon: Icon, action }) => (
                  <button
                    key={label}
                    onClick={() => {
                      if (action === 'generate') {
                        const msg = aiInput.trim();
                        if (msg) {
                          sendSQLAI('generate', msg);
                        } else {
                          setAiInput('Describe the SQL query you want...');
                        }
                      } else if (action === 'explain') {
                        sendSQLAI('explain', 'Explain this query');
                      } else if (action === 'optimize') {
                        sendSQLAI('optimize', 'Optimize this query');
                      } else if (action === 'fix') {
                        sendSQLAI('fix', 'Fix this query');
                      }
                    }}
                    disabled={aiLoading}
                    className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-semibold whitespace-nowrap transition-all disabled:opacity-50"
                    style={{ background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)', color: '#7c3aed' }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = '#7c3aed40'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-hairline)'}
                  >
                    <Icon size={10} />{label}
                  </button>
                ))}
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
                {aiMessages.length === 0 && (
                  <div className="text-center mt-8" style={{ color: 'var(--color-muted-soft)' }}>
                    <Sparkles size={28} className="mx-auto mb-2" style={{ opacity: 0.3 }} />
                    <p className="text-xs font-medium">Ask me anything about SQL</p>
                    <p className="text-[10px] mt-1" style={{ color: 'var(--color-hairline)' }}>I can see your schema and current query</p>
                    <div className="mt-4 space-y-1.5 text-left max-w-[240px] mx-auto">
                      {['Generate a query to find top customers', 'Explain this JOIN', 'Optimize for large datasets', 'Fix my syntax error'].map((hint, i) => (
                        <button key={i} onClick={() => { setAiInput(hint); }} className="w-full text-left px-2.5 py-1.5 rounded-md text-[10px] transition-all" style={{ background: 'var(--color-surface-card)', border: '1px solid var(--color-hairline)', color: 'var(--color-muted)' }}
                          onMouseEnter={e => e.currentTarget.style.borderColor = '#7c3aed40'}
                          onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-hairline)'}
                        >{hint}</button>
                      ))}
                    </div>
                  </div>
                )}
                {aiMessages.map((msg, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg text-xs leading-relaxed"
                    style={{
                      background: msg.role === 'user' ? '#7c3aed10' : 'var(--color-surface-card)',
                      color: 'var(--color-ink)',
                      border: msg.role === 'assistant' ? '1px solid var(--color-hairline)' : 'none',
                      marginLeft: msg.role === 'user' ? '1rem' : 0,
                      marginRight: msg.role === 'assistant' ? '1rem' : 0,
                    }}
                  >
                    <pre className="whitespace-pre-wrap font-body text-xs" style={{ fontFamily: 'inherit' }}>{msg.content}</pre>
                  </div>
                ))}
                {aiLoading && (
                  <div className="flex items-center gap-2 p-2" style={{ color: '#7c3aed' }}>
                    <Loader2 size={12} className="animate-spin" />
                    <span className="text-xs">Thinking...</span>
                  </div>
                )}
                <div ref={aiMessagesEndRef} />
              </div>

              {/* Input */}
              <div className="p-2.5 border-t" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-card)' }}>
                <div className="flex gap-1.5">
                  <input
                    type="text"
                    value={aiInput}
                    onChange={(e) => setAiInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendSQLAI('chat', aiInput); } }}
                    placeholder="Ask about SQL..."
                    className="flex-1 px-2.5 py-1.5 rounded-md text-xs focus:outline-none transition-all"
                    style={{ background: 'var(--color-canvas)', border: '1px solid var(--color-hairline)', color: 'var(--color-ink)' }}
                    onFocus={e => e.target.style.borderColor = '#7c3aed'}
                    onBlur={e => e.target.style.borderColor = 'var(--color-hairline)'}
                  />
                  <button
                    onClick={() => sendSQLAI('chat', aiInput)}
                    disabled={aiLoading || !aiInput.trim()}
                    className="px-2.5 py-1.5 rounded-md transition-all disabled:opacity-50"
                    style={{ background: '#7c3aed', color: 'white' }}
                  >
                    <Send size={12} />
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ═══ STATUS BAR ═══ */}
      <div className="flex items-center justify-between px-4 py-1.5 border-t text-[10px]" style={{ borderColor: 'var(--color-hairline)', background: 'var(--color-surface-soft)' }}>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5" style={{ color: 'var(--color-muted)' }}>
            <span className="w-2 h-2 rounded-full" style={{ background: isRunning ? '#b8860b' : '#16a34a', animation: isRunning ? 'pulse 1s infinite' : 'none' }} />
            {isRunning ? `Running ${timerSeconds}s` : 'Ready'}
          </span>
          <span style={{ color: 'var(--color-hairline)' }}>|</span>
          <span style={{ color: 'var(--color-muted)' }}>Ln {cursorPos.line}, Col {cursorPos.col}</span>
          <span style={{ color: 'var(--color-hairline)' }}>|</span>
          <span style={{ color: 'var(--color-muted)' }}>{codeStats.lines} lines</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="px-2 py-0.5 rounded-md" style={{ background: '#5cb8a010', color: '#5cb8a0' }}>SQLite 3</span>
          <span style={{ color: 'var(--color-hairline)' }}>|</span>
          <span style={{ color: 'var(--color-muted)' }}>UTF-8</span>
          {executionTime && <><span style={{ color: 'var(--color-hairline)' }}>|</span><span style={{ color: 'var(--color-muted)' }}>Last: {executionTime}s</span></>}
        </div>
      </div>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div initial={{ opacity: 0, y: 20, x: '-50%' }} animate={{ opacity: 1, y: 0, x: '-50%' }} exit={{ opacity: 0, y: 20, x: '-50%' }} className="fixed bottom-6 left-1/2 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl shadow-2xl" style={{ background: 'linear-gradient(135deg, #16a34a, #15803d)', color: 'white', boxShadow: '0 8px 32px #16a34a40' }}>
            <CheckCircle2 size={14} /><span className="text-xs font-semibold">{toast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default memo(SQLPlayground);
