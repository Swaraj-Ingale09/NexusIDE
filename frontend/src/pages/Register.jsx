import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mail, Lock, User, AlertCircle, ArrowLeft, UserPlus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const inputVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i) => ({
    opacity: 1,
    x: 0,
    transition: { delay: 0.3 + i * 0.1, type: 'spring', stiffness: 100, damping: 15 },
  }),
};

const Register = () => {
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/compiler');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setErrors({});

    if (!username || !email || !password) {
      setError('Please fill in all fields');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);
    try {
      const res = await register(username, email, password);
      setLoading(false);

      if (res.success) {
        navigate('/compiler');
      } else {
        if (res.errors) {
          setErrors(res.errors);
        } else {
          setError(res.error || 'Registration failed. Try again.');
        }
      }
    } catch (err) {
      setLoading(false);
      setError('An unexpected error occurred. Please try again.');
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8 relative">
      <motion.div
        className="glow-spot-pink top-10 right-10"
        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
        transition={{ duration: 6, repeat: Infinity }}
      />

      <motion.div
        className="w-full max-w-md bg-surface-soft border border-hairline p-8 md:p-10 rounded-xl shadow-xl z-10"
        initial={{ opacity: 0, y: 30, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 100, damping: 15 }}
      >
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Link to="/" className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink mb-6 transition-colors font-semibold">
            <ArrowLeft size={14} />
            <span>Back to Home</span>
          </Link>
        </motion.div>

        <div className="flex flex-col gap-2 mb-8">
          <motion.h2
            className="font-display text-3xl tracking-tight text-ink font-semibold"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            Create an account.
          </motion.h2>
          <motion.p
            className="text-muted text-sm font-body"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            Get started for free. Run Python, C, C++ code sandbox.
          </motion.p>
        </div>

        <AnimatePresence>
          {error && (
            <motion.div
              className="mb-6 p-4 bg-red-500/10 border border-red-500/25 rounded-md text-red-500 text-xs font-semibold flex items-center gap-2"
              initial={{ opacity: 0, y: -10, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: -10, height: 0 }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <motion.div className="flex flex-col gap-2" custom={0} variants={inputVariants} initial="hidden" animate="visible">
            <label className="text-xs font-bold text-ink uppercase tracking-wide">Username</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-muted-soft pointer-events-none">
                <User size={16} />
              </span>
              <motion.input
                type="text"
                placeholder="swaraj123"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={`w-full pl-10 pr-4 py-2.5 h-11 bg-canvas border rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all ${
                  errors.username ? 'border-red-500' : 'border-hairline'
                }`}
                disabled={loading}
                whileFocus={{ scale: 1.01 }}
              />
            </div>
            {errors.username && (
              <span className="text-[10px] text-red-500 font-semibold">{errors.username[0]}</span>
            )}
          </motion.div>

          <motion.div className="flex flex-col gap-2" custom={1} variants={inputVariants} initial="hidden" animate="visible">
            <label className="text-xs font-bold text-ink uppercase tracking-wide">Email Address</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-muted-soft pointer-events-none">
                <Mail size={16} />
              </span>
              <motion.input
                type="email"
                placeholder="swaraj@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`w-full pl-10 pr-4 py-2.5 h-11 bg-canvas border rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all ${
                  errors.email ? 'border-red-500' : 'border-hairline'
                }`}
                disabled={loading}
                whileFocus={{ scale: 1.01 }}
              />
            </div>
            {errors.email && (
              <span className="text-[10px] text-red-500 font-semibold">{errors.email[0]}</span>
            )}
          </motion.div>

          <motion.div className="flex flex-col gap-2" custom={2} variants={inputVariants} initial="hidden" animate="visible">
            <label className="text-xs font-bold text-ink uppercase tracking-wide">Password</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-muted-soft pointer-events-none">
                <Lock size={16} />
              </span>
              <motion.input
                type="password"
                placeholder="Minimum 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`w-full pl-10 pr-4 py-2.5 h-11 bg-canvas border rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all ${
                  errors.password ? 'border-red-500' : 'border-hairline'
                }`}
                disabled={loading}
                whileFocus={{ scale: 1.01 }}
              />
            </div>
            {errors.password && (
              <span className="text-[10px] text-red-500 font-semibold">{errors.password[0]}</span>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.65 }}
          >
            <motion.button
              type="submit"
              className="tactile-btn w-full bg-primary text-canvas py-3 h-11 rounded-md text-sm font-semibold shadow-md mt-4 transition-colors hover:bg-primary-active disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
              disabled={loading}
              whileHover={!loading ? { scale: 1.02 } : {}}
              whileTap={!loading ? { scale: 0.97 } : {}}
            >
              {loading ? (
                <motion.div
                  className="w-5 h-5 border-2 border-canvas border-t-transparent rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                />
              ) : (
                <>
                  <UserPlus size={16} />
                  <span>Create Account</span>
                </>
              )}
            </motion.button>
          </motion.div>
        </form>

        <motion.div
          className="mt-8 text-center text-sm font-body text-muted"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.75 }}
        >
          Already have an account?{' '}
          <Link to="/login" className="text-brand-pink hover:underline font-semibold">
            Sign In
          </Link>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default Register;
