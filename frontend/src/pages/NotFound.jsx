import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, ArrowLeft, Code2, Search } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <motion.div
        className="text-center max-w-md"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 80, damping: 15 }}
      >
        <motion.div
          className="relative inline-block mb-6"
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        >
          <span className="font-display text-[120px] md:text-[160px] font-bold text-surface-card leading-none select-none">
            404
          </span>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-16 h-16 rounded-full bg-brand-pink/10 flex items-center justify-center">
              <Search size={28} className="text-brand-pink" />
            </div>
          </div>
        </motion.div>

        <motion.h1
          className="font-display text-2xl md:text-3xl font-medium text-ink mb-3"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          Page not found
        </motion.h1>

        <motion.p
          className="text-muted text-sm font-body mb-8 leading-relaxed"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          The page you're looking for doesn't exist or has been moved.
          Try navigating from the dashboard or use the command palette.
        </motion.p>

        <motion.div
          className="flex flex-col sm:flex-row items-center justify-center gap-3"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <Link
              to="/"
              className="tactile-btn bg-primary text-canvas px-6 py-3 rounded-md text-sm font-semibold shadow-md flex items-center gap-2"
            >
              <Home size={16} />
              Go Home
            </Link>
          </motion.div>
          <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            <button
              onClick={() => window.history.back()}
              className="tactile-btn bg-surface-soft border border-hairline text-ink px-6 py-3 rounded-md text-sm font-semibold flex items-center gap-2"
            >
              <ArrowLeft size={16} />
              Go Back
            </button>
          </motion.div>
        </motion.div>

        <motion.div
          className="mt-8 flex items-center justify-center gap-2 text-xs text-muted-soft"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <Code2 size={12} />
          <span>Press <kbd className="px-1.5 py-0.5 rounded bg-surface-soft border border-hairline font-mono">Ctrl+K</kbd> to open command palette</span>
        </motion.div>
      </motion.div>
    </div>
  );
}
