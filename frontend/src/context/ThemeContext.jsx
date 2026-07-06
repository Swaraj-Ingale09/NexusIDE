import { createContext, useState, useEffect, useContext, useCallback } from 'react';

const ThemeContext = createContext(null);

const THEMES = {
  light: {
    canvas: '#fffaf0',
    ink: '#0a0a0a',
    primary: '#0a0a0a',
    primaryActive: '#1f1f1f',
    body: '#3a3a3a',
    bodyStrong: '#1a1a1a',
    muted: '#6a6a6a',
    mutedSoft: '#9a9a9a',
    hairline: '#e5e5e5',
    hairlineSoft: '#f0f0f0',
    surfaceSoft: '#faf5e8',
    surfaceCard: '#f5f0e0',
    surfaceStrong: '#ebe6d6',
    glassBg: 'rgba(255, 250, 240, 0.85)',
    glassBorder: 'rgba(240, 240, 240, 1)',
    scrollTrack: '#fffaf0',
    scrollThumb: '#ebe6d6',
    scrollThumbHover: '#9a9a9a',
  },
  dark: {
    canvas: '#0f1117',
    ink: '#f0f0f0',
    primary: '#f0f0f0',
    primaryActive: '#d4d4d4',
    body: '#a1a1aa',
    bodyStrong: '#e4e4e7',
    muted: '#71717a',
    mutedSoft: '#52525b',
    hairline: '#27272a',
    hairlineSoft: '#1e1e22',
    surfaceSoft: '#18181b',
    surfaceCard: '#1e1e22',
    surfaceStrong: '#27272a',
    glassBg: 'rgba(15, 17, 23, 0.85)',
    glassBorder: 'rgba(39, 39, 42, 1)',
    scrollTrack: '#0f1117',
    scrollThumb: '#27272a',
    scrollThumbHover: '#52525b',
  },
};

function applyTheme(theme) {
  const root = document.documentElement;
  const t = THEMES[theme];
  if (!t) return;

  root.style.setProperty('--color-canvas', t.canvas);
  root.style.setProperty('--color-ink', t.ink);
  root.style.setProperty('--color-primary', t.primary);
  root.style.setProperty('--color-primary-active', t.primaryActive);
  root.style.setProperty('--color-body', t.body);
  root.style.setProperty('--color-body-strong', t.bodyStrong);
  root.style.setProperty('--color-muted', t.muted);
  root.style.setProperty('--color-muted-soft', t.mutedSoft);
  root.style.setProperty('--color-hairline', t.hairline);
  root.style.setProperty('--color-hairline-soft', t.hairlineSoft);
  root.style.setProperty('--color-surface-soft', t.surfaceSoft);
  root.style.setProperty('--color-surface-card', t.surfaceCard);
  root.style.setProperty('--color-surface-strong', t.surfaceStrong);

  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', t.canvas);

  root.classList.toggle('dark', theme === 'dark');

  const style = document.getElementById('dynamic-theme-styles') || document.createElement('style');
  style.id = 'dynamic-theme-styles';
  style.textContent = `
    ::-webkit-scrollbar-track { background: ${t.scrollTrack}; }
    ::-webkit-scrollbar-thumb { background: ${t.scrollThumb}; }
    ::-webkit-scrollbar-thumb:hover { background: ${t.scrollThumbHover}; }
    .glass-nav { background: ${t.glassBg}; border-bottom-color: ${t.glassBorder}; }
    .glass-panel { background: ${t.glassBg}; }
    .brand-card-hover:hover { box-shadow: 0 30px 60px -20px ${theme === 'dark' ? 'rgba(0,0,0,0.4)' : 'rgba(10,26,26,0.12)'}; }
    .brand-card-shadow { box-shadow: 0 20px 40px -15px ${theme === 'dark' ? 'rgba(0,0,0,0.3)' : 'rgba(10,26,26,0.06)'}; }
    .glow-spot-pink { background: radial-gradient(circle, rgba(255,77,139,${theme === 'dark' ? '0.08' : '0.05'}) 0%, transparent 70%); }
    .glow-spot-teal { background: radial-gradient(circle, rgba(164,212,197,${theme === 'dark' ? '0.10' : '0.08'}) 0%, transparent 70%); }
    .monaco-editor-container { border-color: ${t.hairline}; box-shadow: 0 10px 30px -10px ${theme === 'dark' ? 'rgba(0,0,0,0.3)' : 'rgba(10,26,26,0.08)'}; }
  `;
  if (!style.parentNode) document.head.appendChild(style);
}

export const ThemeProvider = ({ children }) => {
  const [theme, setThemeState] = useState(() => {
    try {
      return localStorage.getItem('nexuside_theme') || 'light';
    } catch {
      return 'light';
    }
  });

  const setTheme = useCallback((newTheme) => {
    setThemeState(newTheme);
    try { localStorage.setItem('nexuside_theme', newTheme); } catch { /* ignore */ }
    applyTheme(newTheme);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  }, [theme, setTheme]);

  useEffect(() => {
    applyTheme(theme);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run on mount only
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components -- context provider exports hook
export const useTheme = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
};
