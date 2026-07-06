import { lazy, Suspense, useState, useEffect } from 'react';
import { Routes, Route, useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Toaster } from 'sonner';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import ProtectedRoute from './components/ProtectedRoute';
import ErrorBoundary from './components/ErrorBoundary';
import CommandPalette from './components/CommandPalette';
import KeyboardShortcutsModal from './components/KeyboardShortcutsModal';
import { ThemeProvider } from './context/ThemeContext';

const Home = lazy(() => import('./pages/Home'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const PasswordReset = lazy(() => import('./pages/PasswordReset'));
const Editor = lazy(() => import('./pages/Editor'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Projects = lazy(() => import('./pages/Projects'));
const ProjectDetail = lazy(() => import('./pages/ProjectDetail'));
const Profile = lazy(() => import('./pages/Profile'));
const Community = lazy(() => import('./pages/Community'));
const Problems = lazy(() => import('./pages/Problems'));
const MasterDashboard = lazy(() => import('./pages/MasterDashboard'));
const NotFound = lazy(() => import('./pages/NotFound'));
const Status = lazy(() => import('./pages/Status'));

const PageLoader = () => (
  <div className="min-h-[60vh] flex items-center justify-center">
    <div className="flex flex-col items-center gap-3">
      <motion.div
        className="w-8 h-8 border-2 border-brand-pink border-t-transparent rounded-full"
        animate={{ rotate: 360 }}
        transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
      />
      <span className="text-muted text-sm">Loading...</span>
    </div>
  </div>
);

const pageTransition = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -12 },
  transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] },
};

const AnimatedPage = ({ children }) => (
  <motion.div {...pageTransition}>{children}</motion.div>
);

const fullChromeRoutes = [
  '/', '/login', '/register', '/password-reset',
  '/dashboard', '/projects', '/community', '/problems',
  '/master-dashboard', '/profile', '/compiler', '/status',
];

function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const [cmdOpen, setCmdOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCmdOpen(prev => !prev);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        setShortcutsOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const showChrome = fullChromeRoutes.some(
    (r) => location.pathname === r || location.pathname.startsWith(r + '/')
  );

  return (
    <ThemeProvider>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--color-surface-card)',
            color: 'var(--color-ink)',
            border: '1px solid var(--color-hairline)',
            borderRadius: '12px',
            fontSize: '13px',
          },
        }}
        richColors
        closeButton
      />
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
      <KeyboardShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />

      <div className="min-h-screen flex flex-col bg-canvas">
      {showChrome && <Navbar />}

      <main className="flex-1">
        <ErrorBoundary>
          <Suspense fallback={<PageLoader />}>
            <AnimatePresence mode="wait">
              <Routes location={location} key={location.pathname}>
                {/* Public */}
                <Route path="/" element={<AnimatedPage><Home /></AnimatedPage>} />
                <Route path="/login" element={<AnimatedPage><Login /></AnimatedPage>} />
                <Route path="/register" element={<AnimatedPage><Register /></AnimatedPage>} />
                <Route path="/password-reset" element={<AnimatedPage><PasswordReset /></AnimatedPage>} />
                <Route path="/status" element={<AnimatedPage><Status /></AnimatedPage>} />

                {/* Protected */}
                <Route path="/compiler" element={
                  <ProtectedRoute><Editor /></ProtectedRoute>
                } />
                <Route path="/dashboard" element={
                  <ProtectedRoute><AnimatedPage><Dashboard /></AnimatedPage></ProtectedRoute>
                } />
                <Route path="/projects" element={
                  <ProtectedRoute><AnimatedPage><Projects /></AnimatedPage></ProtectedRoute>
                } />
                <Route path="/projects/:id" element={
                  <ProtectedRoute><AnimatedPage><ProjectDetail /></AnimatedPage></ProtectedRoute>
                } />
                <Route path="/profile" element={
                  <ProtectedRoute><AnimatedPage><Profile /></AnimatedPage></ProtectedRoute>
                } />
                <Route path="/community" element={
                  <AnimatedPage><Community /></AnimatedPage>
                } />
                <Route path="/problems" element={
                  <AnimatedPage><Problems /></AnimatedPage>
                } />
                <Route path="/master-dashboard" element={
                  <ProtectedRoute><MasterDashboard /></ProtectedRoute>
                } />

                {/* Fallback */}
                <Route path="*" element={
                  <AnimatedPage><NotFound /></AnimatedPage>
                } />
              </Routes>
            </AnimatePresence>
          </Suspense>
        </ErrorBoundary>
      </main>

      {showChrome && location.pathname !== '/compiler' && <Footer />}
      </div>
    </ThemeProvider>
  );
}

export default App;
