import { useEffect, useCallback } from 'react';

const useKeyboardShortcuts = (shortcuts = {}) => {
  const handler = useCallback((e) => {
    const isCtrl = e.ctrlKey || e.metaKey;
    const key = e.key.toLowerCase();

    for (const [combo, callback] of Object.entries(shortcuts)) {
      const parts = combo.toLowerCase().split('+');
      const needsCtrl = parts.includes('ctrl');
      const needsShift = parts.includes('shift');
      const needsAlt = parts.includes('alt');
      const mainKey = parts.filter(p => !['ctrl', 'shift', 'alt'].includes(p))[0];

      if (
        needsCtrl === isCtrl &&
        needsShift === e.shiftKey &&
        needsAlt === e.altKey &&
        key === mainKey
      ) {
        e.preventDefault();
        callback(e);
        return;
      }
    }
  }, [shortcuts]);

  useEffect(() => {
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [handler]);
};

export default useKeyboardShortcuts;
