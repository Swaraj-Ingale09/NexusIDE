import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import {
  Search, Code2, FolderGit2, Trophy, Users2, LayoutDashboard,
  Crown, Settings, LogOut, ArrowRight, Command, Hash,
  Zap, FileCode, GitBranch, MessageSquare, ExternalLink,
} from 'lucide-react';

export default function CommandPalette({ open, onClose }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const commands = [
    { id: 'editor', label: 'Open Editor', desc: 'Write and run code', icon: Code2, action: () => navigate('/compiler'), category: 'Navigation' },
    { id: 'dashboard', label: 'Dashboard', desc: 'View your stats', icon: LayoutDashboard, action: () => navigate('/dashboard'), category: 'Navigation' },
    { id: 'projects', label: 'Projects', desc: 'Manage workspaces', icon: FolderGit2, action: () => navigate('/projects'), category: 'Navigation' },
    { id: 'problems', label: 'Problem Arena', desc: 'Solve coding challenges', icon: Trophy, action: () => navigate('/problems'), category: 'Navigation' },
    { id: 'community', label: 'Community', desc: 'Browse shared snippets', icon: Users2, action: () => navigate('/community'), category: 'Navigation' },
    { id: 'profile', label: 'Profile', desc: 'View your profile', icon: Settings, action: () => navigate('/profile'), category: 'Navigation' },
    ...(user?.is_master_admin ? [
      { id: 'master', label: 'Master Dashboard', desc: 'Platform admin panel', icon: Crown, action: () => navigate('/master-dashboard'), category: 'Navigation' },
    ] : []),
    { id: 'shortcuts', label: 'Keyboard Shortcuts', desc: 'View all shortcuts', icon: Hash, action: () => { onClose(); document.dispatchEvent(new KeyboardEvent('keydown', { key: '/', ctrlKey: true })); }, category: 'Actions' },
    { id: 'snippets', label: 'New Snippet', desc: 'Create a code snippet', icon: FileCode, action: () => navigate('/compiler'), category: 'Actions' },
    { id: 'project-new', label: 'New Project', desc: 'Start a new project', icon: GitBranch, action: () => navigate('/projects'), category: 'Actions' },
    ...(user ? [
      { id: 'logout', label: 'Sign Out', desc: 'Log out of your account', icon: LogOut, action: () => { logout(); navigate('/'); }, category: 'Account' },
    ] : [
      { id: 'login', label: 'Sign In', desc: 'Log in to your account', icon: ExternalLink, action: () => navigate('/login'), category: 'Account' },
      { id: 'register', label: 'Create Account', desc: 'Sign up for free', icon: Zap, action: () => navigate('/register'), category: 'Account' },
    ]),
  ];

  const filtered = query.trim()
    ? commands.filter(c =>
        c.label.toLowerCase().includes(query.toLowerCase()) ||
        c.desc.toLowerCase().includes(query.toLowerCase())
      )
    : commands;

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const execute = useCallback((cmd) => {
    cmd.action();
    onClose();
  }, [onClose]);

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(i => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      e.preventDefault();
      execute(filtered[selectedIndex]);
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  useEffect(() => {
    const selected = listRef.current?.children[selectedIndex];
    if (selected) {
      selected.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  const grouped = filtered.reduce((acc, cmd) => {
    if (!acc[cmd.category]) acc[cmd.category] = [];
    acc[cmd.category].push(cmd);
    return acc;
  }, {});

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[100]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className="fixed top-[15vh] left-1/2 w-full max-w-lg z-[101]"
            initial={{ opacity: 0, y: -20, x: '-50%', scale: 0.96 }}
            animate={{ opacity: 1, y: 0, x: '-50%', scale: 1 }}
            exit={{ opacity: 0, y: -20, x: '-50%', scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <div className="bg-surface-card border border-hairline rounded-xl shadow-2xl overflow-hidden mx-4">
              {/* Search Input */}
              <div className="flex items-center gap-3 px-4 py-3 border-b border-hairline">
                <Search size={18} className="text-muted-soft shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a command or search..."
                  className="flex-1 bg-transparent text-ink text-sm font-body outline-none placeholder:text-muted-soft"
                />
                <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-soft border border-hairline text-[10px] text-muted-soft font-mono">
                  ESC
                </kbd>
              </div>

              {/* Results */}
              <div ref={listRef} className="max-h-[50vh] overflow-y-auto py-2" role="listbox">
                {filtered.length === 0 ? (
                  <div className="px-4 py-8 text-center text-muted text-sm">
                    No commands found
                  </div>
                ) : (
                  Object.entries(grouped).map(([category, cmds]) => (
                    <div key={category}>
                      <div className="px-4 py-1.5 text-[10px] font-semibold text-muted-soft uppercase tracking-wider">
                        {category}
                      </div>
                      {cmds.map((cmd) => {
                        const globalIndex = filtered.indexOf(cmd);
                        const Icon = cmd.icon;
                        return (
                          <button
                            key={cmd.id}
                            onClick={() => execute(cmd)}
                            onMouseEnter={() => setSelectedIndex(globalIndex)}
                            className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                              globalIndex === selectedIndex
                                ? 'bg-surface-soft text-ink'
                                : 'text-muted hover:bg-surface-soft/50'
                            }`}
                            role="option"
                            aria-selected={globalIndex === selectedIndex}
                          >
                            <Icon size={16} className="shrink-0" />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-medium truncate">{cmd.label}</div>
                              <div className="text-[11px] text-muted-soft truncate">{cmd.desc}</div>
                            </div>
                            {globalIndex === selectedIndex && (
                              <ArrowRight size={14} className="text-muted-soft shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between px-4 py-2 border-t border-hairline text-[10px] text-muted-soft">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 py-0.5 rounded bg-surface-soft border border-hairline font-mono">↑↓</kbd>
                    Navigate
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1 py-0.5 rounded bg-surface-soft border border-hairline font-mono">↵</kbd>
                    Select
                  </span>
                </div>
                <span className="flex items-center gap-1">
                  <Command size={10} />
                  K
                </span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
