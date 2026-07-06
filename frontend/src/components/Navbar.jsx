import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Code2,
  FolderGit2,
  Trophy,
  Users2,
  LayoutDashboard,
  Crown,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import NotificationBell from './NotificationBell';

const Navbar = () => {
  const { user, profile, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const navLinks = [
    { name: 'Editor', path: '/compiler', icon: Code2 },
    { name: 'Projects', path: '/projects', icon: FolderGit2 },
    { name: 'Problems', path: '/problems', icon: Trophy },
    { name: 'Community', path: '/community', icon: Users2 },
  ];

  if (user) {
    navLinks.push({ name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard });
  }

  return (
    <motion.nav
      className="sticky top-0 z-50 glass-nav h-16 w-full px-4 md:px-8 flex items-center justify-between"
      initial={{ y: -60, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 100, damping: 15, delay: 0.05 }}
    >
      {/* Brand Logo */}
      <div className="flex items-center gap-2">
        <Link to="/" className="flex items-center gap-2" onClick={() => setMobileMenuOpen(false)}>
          <motion.img
            src="/favicon.svg"
            alt="NexusIDE"
            className="w-8 h-8 rounded-md shadow-md"
            whileHover={{ rotate: -10, scale: 1.1 }}
            transition={{ type: 'spring', stiffness: 300 }}
          />
          <span className="font-display text-xl font-medium tracking-tight text-ink">
            Nexus<span className="text-brand-pink font-semibold">IDE</span>
          </span>
        </Link>
      </div>

      {/* Desktop Menu */}
      <div className="hidden md:flex items-center gap-1">
        {navLinks.map((link, i) => {
          const Icon = link.icon;
          return (
            <motion.div
              key={link.path}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
            >
              <Link
                to={link.path}
                className={`flex items-center gap-2 px-4 py-2 rounded-pill font-body text-sm font-medium transition-all duration-200 ${
                  isActive(link.path)
                    ? 'bg-surface-card text-ink font-semibold'
                    : 'text-muted hover:text-ink hover:bg-surface-soft/60'
                }`}
              >
                <Icon size={16} />
                <span>{link.name}</span>
              </Link>
            </motion.div>
          );
        })}
      </div>

      {/* Auth Cluster */}
      <div className="hidden md:flex items-center gap-3">
        <ThemeToggle />
        {user && <NotificationBell />}
        {user ? (
          <div className="flex items-center gap-3">
            {user.is_master_admin && (
              <motion.div whileHover={{ scale: 1.15, rotate: 15 }} whileTap={{ scale: 0.9 }}>
                <Link
                  to="/master-dashboard"
                  className="p-2 rounded-md hover:bg-brand-ochre/15 text-brand-ochre transition-all"
                  title="Master Dashboard"
                >
                  <Crown size={20} className="fill-brand-ochre/20" />
                </Link>
              </motion.div>
            )}

            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Link
                to="/profile"
                className="flex items-center gap-2 p-1.5 pr-3 rounded-pill hover:bg-surface-soft border border-hairline-soft transition-all"
              >
                <div className="w-7 h-7 rounded-full bg-brand-peach text-ink font-bold flex items-center justify-center text-xs overflow-hidden">
                  {profile?.avatar ? (
                    <img src={profile.avatar} alt="avatar" className="w-full h-full object-cover" />
                  ) : (
                    user.username.substring(0, 2).toUpperCase()
                  )}
                </div>
                <span className="text-xs font-semibold text-ink max-w-[80px] truncate">{user.username}</span>
              </Link>
            </motion.div>

            <motion.button
              onClick={handleLogout}
              className="tactile-btn p-2 rounded-md hover:bg-red-500/10 text-red-500 transition-all"
              title="Sign Out"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <LogOut size={18} />
            </motion.button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="tactile-btn text-muted hover:text-ink px-4 py-2 font-body text-sm font-medium transition-all"
            >
              Sign In
            </Link>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Link
                to="/register"
                className="tactile-btn bg-primary text-canvas px-4 py-2 h-10 rounded-md font-body text-sm font-medium shadow-md transition-all hover:bg-primary-active"
              >
                Try Free
              </Link>
            </motion.div>
          </div>
        )}
      </div>

      {/* Mobile Menu Trigger */}
      <div className="flex md:hidden items-center gap-2">
        <ThemeToggle />
        {user?.is_master_admin && (
          <Link to="/master-dashboard" className="p-2 text-brand-ochre" title="Master Dashboard">
            <Crown size={20} className="fill-brand-ochre/20" />
          </Link>
        )}
        <motion.button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 text-ink hover:bg-surface-soft rounded-md transition-all"
          whileTap={{ scale: 0.9 }}
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </motion.button>
      </div>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            className="absolute top-16 left-0 w-full bg-canvas border-b border-hairline p-6 flex flex-col gap-4 shadow-xl z-50 md:hidden"
            initial={{ opacity: 0, y: -20, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -20, height: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
          >
            <div className="flex flex-col gap-1">
              {navLinks.map((link, i) => {
                const Icon = link.icon;
                return (
                  <motion.div
                    key={link.path}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <Link
                      to={link.path}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-md font-body text-sm font-medium ${
                        isActive(link.path)
                          ? 'bg-surface-card text-ink font-semibold'
                          : 'text-muted hover:text-ink hover:bg-surface-soft'
                      }`}
                    >
                      <Icon size={18} />
                      <span>{link.name}</span>
                    </Link>
                  </motion.div>
                );
              })}
            </div>

            <hr className="border-hairline" />

            {user ? (
              <div className="flex flex-col gap-3">
                <Link
                  to="/profile"
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-4 py-2"
                >
                  <div className="w-8 h-8 rounded-full bg-brand-peach text-ink font-bold flex items-center justify-center text-sm overflow-hidden">
                    {profile?.avatar ? (
                      <img src={profile.avatar} alt="avatar" className="w-full h-full object-cover" />
                    ) : (
                      user.username.substring(0, 2).toUpperCase()
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-ink">{user.username}</div>
                    <div className="text-xs text-muted">Level {profile?.level || 1} • {profile?.xp_points || 0} XP</div>
                  </div>
                </Link>
                <button
                  onClick={() => { setMobileMenuOpen(false); handleLogout(); }}
                  className="tactile-btn w-full bg-red-500/10 text-red-500 py-2.5 rounded-md text-sm font-semibold flex items-center justify-center gap-2"
                >
                  <LogOut size={16} />
                  <span>Sign Out</span>
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <Link to="/login" onClick={() => setMobileMenuOpen(false)} className="tactile-btn border border-hairline py-2.5 rounded-md text-center text-ink text-sm font-semibold">
                  Sign In
                </Link>
                <Link to="/register" onClick={() => setMobileMenuOpen(false)} className="tactile-btn bg-primary text-canvas py-2.5 rounded-md text-center text-sm font-semibold shadow-md">
                  Try Free
                </Link>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
};

export default Navbar;
