import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { Mail, Key, ShieldAlert, ArrowLeft, AlertCircle, CheckCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const PasswordReset = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: request, 2: verify token, 3: complete reset
  
  const [email, setEmail] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRequest = async (e) => {
    e.preventDefault();
    if (!email) {
      setError('Email is required');
      return;
    }
    
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/api/password-reset/request/', { email });
      if (res.data.success) {
        setSuccess('Reset code sent to your email.');
        setStep(2);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to send reset code');
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!token) {
      setError('Verification code is required');
      return;
    }

    setError('');
    setLoading(true);
    try {
      const res = await api.post('/api/password-reset/verify/', { email, token });
      if (res.data.success) {
        setSuccess('Code verified successfully.');
        setStep(3);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid reset code');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (e) => {
    e.preventDefault();
    if (!newPassword || !confirmPassword) {
      setError('Please fill in all fields');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setError('');
    setLoading(true);
    try {
      const res = await api.post('/api/password-reset/complete/', {
        email,
        token,
        new_password: newPassword
      });
      if (res.data.success) {
        setSuccess('Password reset completed successfully.');
        setTimeout(() => {
          navigate('/login');
        }, 2000);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  const slideVariants = {
    enter: { opacity: 0, x: 20 },
    center: { opacity: 1, x: 0, transition: { duration: 0.3 } },
    exit: { opacity: 0, x: -20, transition: { duration: 0.2 } }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 relative">
      <div className="glow-spot-pink top-10 right-10" />
      
      <div className="w-full max-w-md bg-surface-soft border border-hairline p-8 md:p-10 rounded-xl shadow-xl z-10">
        <Link to="/login" className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink mb-6 transition-colors font-semibold">
          <ArrowLeft size={14} />
          <span>Back to Sign In</span>
        </Link>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/25 rounded-md text-red-500 text-xs font-semibold flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/25 rounded-md text-emerald-600 text-xs font-semibold flex items-center gap-2">
            <CheckCircle size={16} />
            <span>{success}</span>
          </div>
        )}

        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div
              key="step1"
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
            >
              <div className="flex flex-col gap-2 mb-8">
                <h2 className="font-display text-3xl tracking-tight text-ink font-semibold">
                  Reset password.
                </h2>
                <p className="text-muted text-sm font-body">
                  Enter your email address and we'll send you a 6-digit verification code.
                </p>
              </div>

              <form onSubmit={handleRequest} className="flex flex-col gap-5">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-ink uppercase tracking-wide">Email Address</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-muted-soft pointer-events-none">
                      <Mail size={16} />
                    </span>
                    <input
                      type="email"
                      placeholder="swaraj@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 h-11 bg-canvas border border-hairline rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all"
                      disabled={loading}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="tactile-btn w-full bg-primary text-canvas py-3 h-11 rounded-md text-sm font-semibold shadow-md mt-4 transition-all hover:bg-primary-active disabled:opacity-50"
                  disabled={loading}
                >
                  {loading ? 'Sending code...' : 'Send Verification Code'}
                </button>
              </form>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div
              key="step2"
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
            >
              <div className="flex flex-col gap-2 mb-8">
                <h2 className="font-display text-3xl tracking-tight text-ink font-semibold">
                  Verify code.
                </h2>
                <p className="text-muted text-sm font-body">
                  We've sent a 6-digit code to <strong>{email}</strong>. Enter it below.
                </p>
              </div>

              <form onSubmit={handleVerify} className="flex flex-col gap-5">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-ink uppercase tracking-wide">6-Digit Code</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-muted-soft pointer-events-none">
                      <ShieldAlert size={16} />
                    </span>
                    <input
                      type="text"
                      placeholder="123456"
                      maxLength={6}
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 h-11 bg-canvas border border-hairline rounded-md text-ink text-sm font-body tracking-widest font-mono text-center focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all"
                      disabled={loading}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="tactile-btn w-full bg-primary text-canvas py-3 h-11 rounded-md text-sm font-semibold shadow-md mt-4 transition-all hover:bg-primary-active disabled:opacity-50"
                  disabled={loading}
                >
                  {loading ? 'Verifying...' : 'Verify Code'}
                </button>
              </form>
            </motion.div>
          )}

          {step === 3 && (
            <motion.div
              key="step3"
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
            >
              <div className="flex flex-col gap-2 mb-8">
                <h2 className="font-display text-3xl tracking-tight text-ink font-semibold">
                  New password.
                </h2>
                <p className="text-muted text-sm font-body">
                  Set a secure new password for your account.
                </p>
              </div>

              <form onSubmit={handleComplete} className="flex flex-col gap-5">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-ink uppercase tracking-wide">New Password</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-muted-soft pointer-events-none">
                      <Key size={16} />
                    </span>
                    <input
                      type="password"
                      placeholder="Minimum 8 characters"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 h-11 bg-canvas border border-hairline rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all"
                      disabled={loading}
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs font-bold text-ink uppercase tracking-wide">Confirm Password</label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-muted-soft pointer-events-none">
                      <Key size={16} />
                    </span>
                    <input
                      type="password"
                      placeholder="Repeat new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 h-11 bg-canvas border border-hairline rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all"
                      disabled={loading}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  className="tactile-btn w-full bg-primary text-canvas py-3 h-11 rounded-md text-sm font-semibold shadow-md mt-4 transition-all hover:bg-primary-active disabled:opacity-50"
                  disabled={loading}
                >
                  {loading ? 'Updating password...' : 'Update Password'}
                </button>
              </form>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default PasswordReset;
