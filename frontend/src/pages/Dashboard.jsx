import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { motion } from 'framer-motion';
import {
  Clock, Code2, Zap, TrendingUp,
  Trophy, Star, Activity, Loader2,
} from 'lucide-react';

const StatCard = ({ icon: Icon, label, value, accent, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 20, scale: 0.95 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    transition={{ delay, type: 'spring', stiffness: 100, damping: 15 }}
    whileHover={{ y: -6, scale: 1.02 }}
    className="bg-surface-soft border border-hairline rounded-xl p-6 flex flex-col gap-3 cursor-default"
  >
    <motion.div
      className={`w-10 h-10 rounded-lg flex items-center justify-center ${accent}`}
      whileHover={{ rotate: -10, scale: 1.15 }}
      transition={{ type: 'spring', stiffness: 300 }}
    >
      <Icon size={20} />
    </motion.div>
    <div>
      <div className="text-2xl font-display font-medium text-ink tracking-tight">{value}</div>
      <div className="text-sm text-muted font-body">{label}</div>
    </div>
  </motion.div>
);

const Dashboard = () => {
  const { user, profile } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [recentActivity, setRecentActivity] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, historyRes] = await Promise.all([
          api.get('/api/stats/'),
          api.get('/api/history/?page_size=10'),
        ]);
        setStats(statsRes.data);
        setRecentActivity(historyRes.data.results || historyRes.data || []);
      } catch (err) {
        // Dashboard fetch error - non-critical, user data will show defaults
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <motion.div
          className="flex flex-col items-center gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <Loader2 size={32} className="animate-spin text-brand-pink" />
          <span className="text-muted text-sm">Loading dashboard...</span>
        </motion.div>
      </div>
    );
  }

  const statCards = [
    { icon: Code2, label: 'Total Executions', value: stats?.total_executions ?? profile?.total_code_executions ?? 0, accent: 'bg-brand-pink/15 text-brand-pink' },
    { icon: Zap, label: 'Success Rate', value: `${stats?.success_rate ?? 0}%`, accent: 'bg-green-500/15 text-green-500' },
    { icon: Clock, label: 'Time Spent', value: stats?.total_time_spent ?? '0h', accent: 'bg-brand-lavender/15 text-brand-lavender' },
    { icon: Star, label: 'Snippets Saved', value: stats?.total_snippets ?? profile?.total_snippets_created ?? 0, accent: 'bg-brand-ochre/15 text-brand-ochre' },
    { icon: Trophy, label: 'Level', value: profile?.level ?? 1, accent: 'bg-brand-peach/15 text-brand-peach' },
    { icon: TrendingUp, label: 'XP Points', value: profile?.xp_points ?? 0, accent: 'bg-brand-mint/15 text-brand-teal' },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-10">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-10"
      >
        <h1 className="font-display text-3xl md:text-4xl font-medium text-ink tracking-tight">
          Welcome back, <motion.span
            className="text-brand-pink"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >{user?.username}</motion.span>
        </h1>
        <p className="text-muted text-base mt-2 font-body">
          Here's your coding activity overview
        </p>
      </motion.div>

      {/* Stat Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-10">
        {statCards.map((card, i) => (
          <StatCard key={card.label} {...card} delay={i * 0.08} />
        ))}
      </div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, type: 'spring', stiffness: 80 }}
      >
        <div className="flex items-center gap-2 mb-4">
          <Activity size={18} className="text-brand-coral" />
          <h2 className="font-display text-xl font-medium text-ink">Recent Executions</h2>
        </div>
        <div className="bg-surface-soft border border-hairline rounded-xl overflow-hidden">
          {recentActivity.length > 0 ? (
            <div className="divide-y divide-hairline-soft">
              {recentActivity.map((item, i) => (
                <motion.div
                  key={i}
                  className="flex items-center justify-between px-5 py-3.5 hover:bg-surface-card/50 transition-colors"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.6 + i * 0.05 }}
                >
                  <div className="flex items-center gap-3">
                    <motion.div
                      className={`w-2 h-2 rounded-full ${item.success ? 'bg-green-500' : 'bg-red-500'}`}
                      animate={item.success ? { scale: [1, 1.3, 1] } : {}}
                      transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                    />
                    <div>
                      <div className="text-sm font-medium text-ink">{item.language || 'Unknown'}</div>
                      <div className="text-xs text-muted">
                        {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                      </div>
                    </div>
                  </div>
                  <div className="text-xs text-muted-soft">
                    {item.execution_time ? `${item.execution_time}s` : '—'}
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <motion.div
              className="text-center py-12 text-muted text-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >
              <Code2 size={32} className="mx-auto mb-3 text-hairline" />
              <p>No executions yet. Start coding!</p>
            </motion.div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default Dashboard;
