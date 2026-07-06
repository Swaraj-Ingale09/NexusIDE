import { motion, AnimatePresence } from 'framer-motion';
import { X, Keyboard } from 'lucide-react';

const shortcuts = [
  { category: 'Navigation', items: [
    { keys: ['Ctrl', 'K'], desc: 'Command Palette' },
    { keys: ['Ctrl', 'Shift', 'D'], desc: 'Go to Dashboard' },
    { keys: ['Ctrl', 'Shift', 'P'], desc: 'Go to Profile' },
    { keys: ['Ctrl', 'K'], desc: 'Go to Editor (in editor)' },
    { keys: ['/'], desc: 'Focus search (in lists)' },
  ]},
  { category: 'Editor', items: [
    { keys: ['Ctrl', 'Enter'], desc: 'Run Code' },
    { keys: ['Ctrl', 'S'], desc: 'Save Snippet' },
    { keys: ['Ctrl', '/'], desc: 'Toggle Comment' },
    { keys: ['Ctrl', 'Shift', 'F'], desc: 'Format Code' },
    { keys: ['Tab'], desc: 'Indent' },
    { keys: ['Shift', 'Tab'], desc: 'Outdent' },
  ]},
  { category: 'AI Assistant', items: [
    { keys: ['Ctrl', 'Shift', 'E'], desc: 'Explain Code' },
    { keys: ['Ctrl', 'Shift', 'X'], desc: 'Fix Code' },
    { keys: ['Ctrl', 'Shift', 'O'], desc: 'Optimize Code' },
    { keys: ['Ctrl', 'Shift', 'B'], desc: 'Debug Code' },
  ]},
  { category: 'General', items: [
    { keys: ['Ctrl', '/'], desc: 'Keyboard Shortcuts' },
    { keys: ['Esc'], desc: 'Close Modal/Panel' },
    { keys: ['Ctrl', 'Shift', 'L'], desc: 'Toggle Dark Mode' },
  ]},
];

export default function KeyboardShortcutsModal({ open, onClose }) {
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
            className="fixed top-1/2 left-1/2 w-full max-w-xl z-[101]"
            initial={{ opacity: 0, y: '-50%', x: '-50%', scale: 0.96 }}
            animate={{ opacity: 1, y: '-50%', x: '-50%', scale: 1 }}
            exit={{ opacity: 0, y: '-50%', x: '-50%', scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <div className="bg-surface-card border border-hairline rounded-xl shadow-2xl overflow-hidden mx-4">
              <div className="flex items-center justify-between px-6 py-4 border-b border-hairline">
                <div className="flex items-center gap-2">
                  <Keyboard size={18} className="text-brand-pink" />
                  <h2 className="font-display text-lg font-semibold text-ink">Keyboard Shortcuts</h2>
                </div>
                <motion.button
                  onClick={onClose}
                  className="p-1.5 rounded-md hover:bg-surface-soft text-muted-soft transition-colors"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <X size={18} />
                </motion.button>
              </div>

              <div className="max-h-[60vh] overflow-y-auto px-6 py-4">
                {shortcuts.map((group) => (
                  <div key={group.category} className="mb-6 last:mb-0">
                    <h3 className="text-[10px] font-bold text-muted-soft uppercase tracking-wider mb-3">{group.category}</h3>
                    <div className="flex flex-col gap-2">
                      {group.items.map((item, i) => (
                        <div key={i} className="flex items-center justify-between py-1.5">
                          <span className="text-sm text-body font-body">{item.desc}</span>
                          <div className="flex items-center gap-1">
                            {item.keys.map((key, ki) => (
                              <span key={ki}>
                                <kbd className="px-2 py-1 rounded bg-surface-soft border border-hairline text-xs font-mono text-ink min-w-[24px] text-center">
                                  {key}
                                </kbd>
                                {ki < item.keys.length - 1 && <span className="text-muted-soft mx-0.5 text-xs">+</span>}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
