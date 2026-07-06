import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { motion } from 'framer-motion';
import { Mail, Calendar, Code2, Trophy, Star, Loader2, Save } from 'lucide-react';

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.15 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 120, damping: 14 } },
};

const Profile = () => {
  const { user, profile, refreshProfile } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [bio, setBio] = useState('');
  const [saveMsg, setSaveMsg] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [profileRes, statsRes] = await Promise.all([
          api.get('/api/profile/'),
          api.get('/api/stats/').catch(() => ({ data: null })),
        ]);
        setStats(statsRes.data);
        setBio(profileRes.data.bio || '');
    } catch {
      // Profile fetch error - non-critical
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const saveProfile = async () => {
    setSaving(true);
    try {
      await api.put('/api/profile/', { bio });
      await refreshProfile();
      setSaveMsg('Profile updated!');
      setTimeout(() => setSaveMsg(''), 2000);
    } catch {
      setSaveMsg('Failed to save');
      setTimeout(() => setSaveMsg(''), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <motion.div className="flex flex-col items-center gap-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Loader2 size={32} className="animate-spin text-brand-pink" />
          <span className="text-muted text-sm">Loading profile...</span>
        </motion.div>
      </div>
    );
  }

  const xpPercent = Math.min(((profile?.xp_points ?? 0) % 100), 100);

  return (
    <div className="max-w-2xl mx-auto px-4 md:px-8 py-10">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="font-display text-3xl md:text-4xl font-medium text-ink tracking-tight mb-8">Profile</h1>

        {/* User Info Card */}
        <motion.div
          className="bg-surface-soft border border-hairline rounded-xl p-6 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="flex items-center gap-4 mb-6">
            <motion.div
              className="w-16 h-16 rounded-full bg-brand-peach text-ink font-bold flex items-center justify-center text-2xl"
              whileHover={{ scale: 1.1, rotate: 5 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              {profile?.avatar ? (
                <img src={profile.avatar} alt="avatar" className="w-full h-full rounded-full object-cover" />
              ) : (
                user?.username?.substring(0, 2).toUpperCase()
              )}
            </motion.div>
            <div>
              <h2 className="font-display text-xl font-medium text-ink">{user?.username}</h2>
              <p className="text-sm text-muted font-body flex items-center gap-1.5">
                <Mail size={14} /> {user?.email}
              </p>
            </div>
          </div>

          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {[
              { icon: Code2, label: 'Executions', value: profile?.total_code_executions ?? stats?.total_executions ?? 0, accent: 'bg-brand-pink/15 text-brand-pink' },
              { icon: Star, label: 'Snippets', value: profile?.total_snippets_created ?? 0, accent: 'bg-brand-ochre/15 text-brand-ochre' },
              { icon: Trophy, label: 'Level', value: profile?.level ?? 1, accent: 'bg-brand-peach/15 text-brand-peach' },
              { icon: Calendar, label: 'Streak', value: `${profile?.streak_days ?? 0}d`, accent: 'bg-brand-mint/15 text-brand-teal' },
            ].map((item) => (
              <motion.div
                key={item.label}
                variants={staggerItem}
                whileHover={{ y: -4, scale: 1.03 }}
                className="bg-canvas border border-hairline-soft rounded-lg p-4 text-center cursor-default"
              >
                <div className={`w-8 h-8 rounded-md flex items-center justify-center mx-auto mb-2 ${item.accent}`}>
                  <item.icon size={16} />
                </div>
                <div className="text-lg font-display font-medium text-ink">{item.value}</div>
                <div className="text-xs text-muted">{item.label}</div>
              </motion.div>
            ))}
          </motion.div>

          <div>
            <label className="text-xs font-bold text-ink uppercase tracking-wide mb-1 block">Bio</label>
            <textarea value={bio} onChange={(e) => setBio(e.target.value)}
              placeholder="Tell us about yourself..."
              rows={3}
              className="w-full px-4 py-2.5 bg-canvas border border-hairline rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink transition-all resize-none" />
          </div>

          <div className="flex items-center gap-3 mt-4">
            <motion.button
              onClick={saveProfile}
              disabled={saving}
              className="tactile-btn bg-primary text-canvas px-5 py-2.5 rounded-md text-sm font-semibold flex items-center gap-2 shadow-md hover:bg-primary-active disabled:opacity-50"
              whileHover={!saving ? { scale: 1.03 } : {}}
              whileTap={!saving ? { scale: 0.97 } : {}}
            >
              <Save size={14} /> {saving ? 'Saving...' : 'Save Changes'}
            </motion.button>
            {saveMsg && (
              <motion.span
                className="text-xs font-semibold text-brand-teal"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
              >
                {saveMsg}
              </motion.span>
            )}
          </div>
        </motion.div>

        {/* XP Bar */}
        <motion.div
          className="bg-surface-soft border border-hairline rounded-xl p-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <h3 className="font-display text-sm font-medium text-ink mb-3">Level {profile?.level ?? 1} Progress</h3>
          <div className="w-full h-3 bg-hairline-soft rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-brand-pink to-brand-lavender rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${xpPercent}%` }}
              transition={{ duration: 1, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
            />
          </div>
          <div className="flex justify-between mt-2">
            <span className="text-xs text-muted-soft">{profile?.xp_points ?? 0} XP</span>
            <span className="text-xs text-muted-soft">{100 - ((profile?.xp_points ?? 0) % 100)} XP to next level</span>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default Profile;
