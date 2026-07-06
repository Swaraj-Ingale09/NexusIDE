import { useState, useEffect, useCallback, useRef, Component } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Crown, Users, Code2, Activity, Loader2, Shield, Brain,
  BarChart3, Clock, Zap, Trophy, RefreshCw,
  Terminal, MessageSquare, Folder, Heart, Database,
  TrendingUp, AlertTriangle, CheckCircle, XCircle,
  Search, ArrowUpRight, Flame, Star, Server,
  FileCode, Timer, Key,
} from 'lucide-react';

class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[60vh] flex items-center justify-center bg-canvas">
          <div className="text-center max-w-md">
            <AlertTriangle size={48} className="mx-auto mb-4 text-[#dc2626]/50" />
            <h2 className="text-xl font-bold text-ink mb-2">Dashboard Error</h2>
            <p className="text-muted text-sm mb-2">Something went wrong loading the dashboard.</p>
            {this.state.error && (
              <p className="text-[10px] text-muted-soft mb-4 font-mono bg-surface-soft rounded p-2">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}
              className="px-4 py-2 bg-surface-soft border border-hairline text-primary rounded-lg text-sm hover:bg-surface transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const fmt = (n) => {
  if (n == null || isNaN(n)) return '0';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toLocaleString();
};

const pct = (a, b) => {
  if (!b || b === 0) return '0%';
  return ((a / b) * 100).toFixed(1) + '%';
};

const timeAgo = (ts) => {
  if (!ts) return 'never';
  const diff = (Date.now() - new Date(ts).getTime()) / 1000;
  if (diff < 0) return 'just now';
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
};

const formatDuration = (seconds) => {
  if (!seconds || seconds === 0) return '0m';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
};

const COLORS = {
  pink: '#d6336c',
  teal: '#0d7c66',
  purple: '#7c3aed',
  orange: '#c45e28',
  green: '#16a34a',
  gold: '#b8860b',
  red: '#dc2626',
};

const PALETTE = [COLORS.pink, COLORS.teal, COLORS.purple, COLORS.orange, COLORS.green, COLORS.gold];

const MiniBar = ({ data, maxH = 48, color = COLORS.teal, showLabels = false }) => {
  if (!data || !data.length) return (
    <div className="flex items-center justify-center text-xs text-muted-soft" style={{ height: maxH }}>No data</div>
  );
  const max = Math.max(...data.map(d => d.value), 1);
  return (
    <div>
      <div className="flex items-end gap-px" style={{ height: maxH }}>
        {data.map((d, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              className="w-full rounded-t-sm transition-all duration-300 hover:opacity-80 cursor-crosshair"
              style={{
                height: `${Math.max((d.value / max) * maxH, d.value > 0 ? 2 : 0)}px`,
                backgroundColor: d.color || color,
                minHeight: d.value > 0 ? 2 : 0,
              }}
            />
            <div className="opacity-0 group-hover:opacity-100 absolute -top-8 bg-ink text-canvas text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap transition-opacity z-20 pointer-events-none shadow-lg">
              {d.label}: {fmt(d.value)}
            </div>
          </div>
        ))}
      </div>
      {showLabels && (
        <div className="flex justify-between mt-1 text-[10px] text-muted-soft">
          {data.filter((_, i) => i % Math.ceil(data.length / 6) === 0 || i === data.length - 1).map((d, i) => (
            <span key={i}>{d.label}</span>
          ))}
        </div>
      )}
    </div>
  );
};

const StatCard = ({ icon: Icon, label, value, sub, color, trend, loading }) => (
  <div className="bg-surface border border-hairline rounded-xl p-4 hover:border-hairline-strong transition-all group">
    <div className="flex items-start justify-between mb-2">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color} transition-transform group-hover:scale-110`}>
        <Icon size={18} />
      </div>
      {trend != null && (
        <span className={`text-xs font-medium flex items-center gap-0.5 ${trend >= 0 ? 'text-[#16a34a]' : 'text-[#dc2626]'}`}>
          {trend >= 0 ? <ArrowUpRight size={12} /> : <XCircle size={12} />}
          {Math.abs(trend)}%
        </span>
      )}
    </div>
    {loading ? (
      <div className="h-6 w-16 bg-surface-soft rounded animate-pulse" />
    ) : (
      <div className="text-xl font-bold text-ink font-mono">{value}</div>
    )}
    <div className="text-xs text-muted mt-0.5">{label}</div>
    {sub && <div className="text-[10px] text-muted-soft mt-1">{sub}</div>}
  </div>
);

const Section = ({ icon: Icon, title, children, className = '', badge }) => (
  <div className={`bg-surface border border-hairline rounded-xl overflow-hidden ${className}`}>
    <div className="flex items-center justify-between px-5 py-3 border-b border-hairline">
      <div className="flex items-center gap-2">
        <Icon size={16} className="text-primary" />
        <h3 className="text-sm font-semibold text-ink tracking-wide">{title}</h3>
      </div>
      {badge && (
        <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">
          {badge}
        </span>
      )}
    </div>
    <div className="p-5">{children}</div>
  </div>
);

const HealthBadge = ({ status }) => {
  const config = {
    healthy: { color: 'bg-[#16a34a]/10 text-[#16a34a] border-[#16a34a]/20', icon: CheckCircle, label: 'Healthy' },
    warning: { color: 'bg-[#b8860b]/10 text-[#b8860b] border-[#b8860b]/20', icon: AlertTriangle, label: 'Warning' },
    critical: { color: 'bg-[#dc2626]/10 text-[#dc2626] border-[#dc2626]/20', icon: XCircle, label: 'Critical' },
  };
  const c = config[status] || config.healthy;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full border ${c.color}`}>
      <c.icon size={12} />
      {c.label}
    </span>
  );
};

const MasterDashboard = () => {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState(null);
  const [users, setUsers] = useState([]);
  const [usersMeta, setUsersMeta] = useState({ count: 0, page: 1, total_pages: 1 });
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('overview');
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchTimeout, setSearchTimeout] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userDetail, setUserDetail] = useState(null);
  const [userDetailLoading, setUserDetailLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [now, setNow] = useState(() => Date.now());
  const [poolData, setPoolData] = useState(null);
  const [optimisticPool, setOptimisticPool] = useState(null);
  const refreshIntervalRef = useRef(null);

  // Expose pool optimizer globally so Editor.jsx can call it
  useEffect(() => {
    window.__nexuside_pool_optimize = () => {
      setPoolData(prev => {
        if (!prev || !prev.keys) return prev;
        const updated = { ...prev };
        // Find key with most RPD left and decrement it
        let bestIdx = 0;
        let bestRpd = 0;
        updated.keys.forEach((k, i) => {
          const parts = k.rpd.split('/');
          const avail = parseInt(parts[0]) || 0;
          if (avail > bestRpd) { bestRpd = avail; bestIdx = i; }
        });
        if (bestRpd > 0) {
          const keys = [...updated.keys];
          const k = { ...keys[bestIdx] };
          const parts = k.rpd.split('/');
          const used = parseInt(parts[0]) || 0;
          const total = parseInt(parts[1]) || 1000;
          k.rpd = `${used + 1}/${total}`;
          k.total_requests = (k.total_requests || 0) + 1;
          keys[bestIdx] = k;
          updated.keys = keys;
          updated.total_rpd_capacity = Math.max(0, (updated.total_rpd_capacity || 0) - 1);
        }
        return updated;
      });
    };
    return () => { delete window.__nexuside_pool_optimize; };
  }, []);

  useEffect(() => {
    if (!loading && (!isAuthenticated || !user?.is_master_admin)) {
      setError('Access denied. Master admin privileges required.');
      setLoading(false);
    }
  }, [isAuthenticated, user, loading]);

  const fetchAll = useCallback(async (isManualRefresh = false) => {
    if (!isAuthenticated || !user?.is_master_admin) {
      setError('Access denied. Master admin privileges required.');
      setLoading(false);
      return;
    }
    try {
      if (isManualRefresh) setRefreshing(true);
      const [metricsRes, usersRes, healthRes, poolRes] = await Promise.allSettled([
        api.get('/api/master/metrics/'),
        api.get('/api/master/users/'),
        api.get('/api/master/health/'),
        api.get('/api/ai/pool-status/'),
      ]);
      const allFailed = [metricsRes, usersRes, healthRes].every(r => r.status === 'rejected');
      if (allFailed) {
        setError(metricsRes.reason?.response?.data?.error || 'Access denied or server error');
        return;
      }
      if (metricsRes.status === 'fulfilled') setMetrics(metricsRes.value.data);
      if (usersRes.status === 'fulfilled') {
        setUsers(usersRes.value.data?.users || []);
        setUsersMeta({
          count: usersRes.value.data?.count || 0,
          page: usersRes.value.data?.page || 1,
          total_pages: usersRes.value.data?.total_pages || 1,
        });
      }
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data);
      if (poolRes.status === 'fulfilled') setPoolData(poolRes.value.data);
      setError('');
      setLastRefresh(new Date());
      setNow(Date.now());
    } catch (err) {
      setError(err.response?.data?.error || 'Access denied');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data fetch is safe
  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Auto-refresh every 60s
  useEffect(() => {
    if (autoRefresh) {
      refreshIntervalRef.current = setInterval(() => fetchAll(false), 60000);
    }
    return () => { if (refreshIntervalRef.current) clearInterval(refreshIntervalRef.current); };
  }, [autoRefresh, fetchAll]);

  // Fast pool data polling — every 1 second for real-time RPD/RPM bars
  const poolIntervalRef = useRef(null);
  useEffect(() => {
    const fetchPool = async () => {
      try {
        const res = await api.get('/api/ai/pool-status/');
        setPoolData(prev => {
          const next = res.data;
          // Detect changes and trigger visual feedback
          if (prev && prev.keys && next.keys) {
            const prevTotal = prev.total_rpd_capacity;
            const nextTotal = next.total_rpd_capacity;
            if (nextTotal < prevTotal) {
              // RPD decreased — flash effect
              document.documentElement.style.setProperty('--pool-flash', '1');
              setTimeout(() => document.documentElement.style.setProperty('--pool-flash', '0'), 300);
            }
          }
          return next;
        });
      } catch { /* silent */ }
    };
    poolIntervalRef.current = setInterval(fetchPool, 1000);
    return () => { if (poolIntervalRef.current) clearInterval(poolIntervalRef.current); };
  }, []);

  const fetchUsers = useCallback(async (search = '', page = 1) => {
    if (!isAuthenticated || !user?.is_master_admin) return;
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' });
      if (search) params.set('search', search);
      const res = await api.get(`/api/master/users/?${params}`);
      setUsers(res.data?.users || []);
      setUsersMeta({
        count: res.data?.count || 0,
        page: res.data?.page || 1,
        total_pages: res.data?.total_pages || 1,
      });
    } catch { /* keep existing data */ }
  }, []);

  const handleSearch = useCallback((value) => {
    setSearchQuery(value);
    if (searchTimeout) clearTimeout(searchTimeout);
    const timeout = setTimeout(() => fetchUsers(value, 1), 400);
    setSearchTimeout(timeout);
  }, [searchTimeout, fetchUsers]);

  const fetchUserDetail = async (userId) => {
    if (!isAuthenticated || !user?.is_master_admin) return;
    try {
      setSelectedUser(userId);
      setUserDetailLoading(true);
      setUserDetail(null);
      const res = await api.get(`/api/master/users/${userId}/`);
      setUserDetail(res.data);
    } catch {
      setUserDetail(null);
    } finally {
      setUserDetailLoading(false);
    }
  };

  const closeModal = () => { setSelectedUser(null); setUserDetail(null); };

  if (loading) return (
    <div className="min-h-[60vh] flex items-center justify-center bg-canvas">
      <div className="text-center">
        <Loader2 size={32} className="animate-spin text-primary mx-auto" />
        <p className="text-xs text-muted mt-3">Loading dashboard...</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-[60vh] flex items-center justify-center bg-canvas">
      <div className="text-center max-w-md">
        <Shield size={48} className="mx-auto mb-4 text-[#dc2626]/50" />
        <h2 className="text-xl font-bold text-ink mb-2">Access Denied</h2>
        <p className="text-muted text-sm mb-4">{error}</p>
        <button
          onClick={() => { setError(''); setLoading(true); fetchAll(); }}
          className="px-4 py-2 bg-primary/10 text-primary rounded-lg text-sm hover:bg-primary/20 transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  );

  const ov = metrics?.overview || {};
  const code = metrics?.code_execution || {};
  const ai = metrics?.ai_usage || {};
  const proj = metrics?.projects || {};
  const comm = metrics?.community || {};
  const sat = metrics?.satisfaction || {};
  const topPerformers = Array.isArray(metrics?.top_performers) ? metrics.top_performers : [];
  const langPop = Array.isArray(metrics?.language_popularity) ? metrics.language_popularity : [];
  const aiActions = Array.isArray(metrics?.ai_action_breakdown) ? metrics.ai_action_breakdown : [];
  const hourlyAct = Array.isArray(metrics?.hourly_activity) ? metrics.hourly_activity : [];
  const dailyAct = Array.isArray(metrics?.daily_activity) ? metrics.daily_activity : [];
  const weeklyAi = Array.isArray(metrics?.weekly_ai_tokens) ? metrics.weekly_ai_tokens : [];

  const filteredUsers = searchQuery
    ? users.filter(u =>
        u.username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.email?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : users;

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'users', label: 'Users', icon: Users, badge: usersMeta.count },
    { id: 'code', label: 'Code & AI', icon: Brain },
    { id: 'system', label: 'System', icon: Server },
  ];

  return (
    <div className="min-h-screen bg-canvas">
      <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#d6336c]/10 flex items-center justify-center">
              <Crown size={20} className="text-[#d6336c]" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-ink">Master Dashboard</h1>
              <p className="text-xs text-muted">
                {lastRefresh ? `Last updated ${timeAgo(lastRefresh.toISOString())}` : 'Loading...'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-1.5 px-3 py-1.5 border rounded-lg text-xs transition-all ${
                autoRefresh
                  ? 'bg-[#16a34a]/10 border-[#16a34a]/20 text-[#16a34a]'
                  : 'bg-surface-soft border-hairline text-muted'
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${autoRefresh ? 'bg-[#16a34a] animate-pulse' : 'bg-muted-soft'}`} />
              Auto-refresh {autoRefresh ? 'on' : 'off'}
            </button>
            <button
              onClick={() => fetchAll(true)}
              disabled={refreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-soft hover:bg-surface border border-hairline rounded-lg text-xs text-primary transition-all disabled:opacity-50"
            >
              <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-surface border border-hairline rounded-xl p-1 w-fit">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                tab === t.id
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted hover:text-ink hover:bg-surface-soft'
              }`}
            >
              <t.icon size={14} />
              {t.label}
              {t.badge != null && (
                <span className="ml-1 text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full">
                  {fmt(t.badge)}
                </span>
              )}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* ══════════════ OVERVIEW TAB ══════════════ */}
          {tab === 'overview' && (
            <motion.div key="overview" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
              {/* Top stats */}
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
                <StatCard icon={Users} label="Total Users" value={fmt(ov.total_users)} color="bg-[#d6336c]/10 text-[#d6336c]" />
                <StatCard icon={Code2} label="Code Executions" value={fmt(code.total)} color="bg-primary/10 text-primary" sub={pct(code.successful, code.total) + ' success'} />
                <StatCard icon={Brain} label="AI Queries" value={fmt(ai.total_queries)} color="bg-[#7c3aed]/10 text-[#7c3aed]" sub={fmt(ai.total_tokens) + ' tokens'} />
                <StatCard icon={Flame} label="Active Today" value={fmt(ov.active_today)} color="bg-[#c45e28]/10 text-[#c45e28]" sub={`${fmt(ov.active_week)} this week`} />
                <StatCard icon={Folder} label="Projects" value={fmt(proj.total)} color="bg-[#16a34a]/10 text-[#16a34a]" />
                <StatCard icon={MessageSquare} label="Community Posts" value={fmt(comm.total_posts)} color="bg-[#b8860b]/10 text-[#b8860b]" />
              </div>

              {/* Activity + Language */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
                <Section icon={Clock} title="24h Activity" className="lg:col-span-2" badge={`${fmt(ov.current_sessions)} active sessions`}>
                  <MiniBar
                    data={hourlyAct.map(h => ({
                      label: `${h.hour}:00`,
                      value: h.count || 0,
                      color: h.count > 0 ? COLORS.teal : '#e5e7eb',
                    }))}
                    maxH={80}
                    showLabels
                  />
                </Section>

                <Section icon={FileCode} title="Language Popularity">
                  <div className="space-y-2.5">
                    {langPop.slice(0, 5).map((l, i) => {
                      const maxCount = Math.max(...langPop.map(x => x.count || 0), 1);
                      const count = l.count || 0;
                      return (
                        <div key={i}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-ink w-16 truncate capitalize">{l.language}</span>
                            <span className="text-[10px] text-muted">{fmt(count)} snippets</span>
                          </div>
                          <div className="h-2 bg-surface-soft rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{ width: `${(count / maxCount) * 100}%`, backgroundColor: PALETTE[i % PALETTE.length] }}
                            />
                          </div>
                          {l.executions > 0 && (
                            <span className="text-[10px] text-muted-soft">{fmt(l.executions)} executions</span>
                          )}
                        </div>
                      );
                    })}
                    {langPop.length === 0 && <p className="text-xs text-muted-soft text-center py-4">No language data yet</p>}
                  </div>
                </Section>
              </div>

              {/* 7-Day Trend + AI Breakdown */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
                <Section icon={TrendingUp} title="7-Day Activity Trend">
                  <MiniBar
                    data={dailyAct.map(d => ({
                      label: d.day || d.date,
                      value: d.count || 0,
                      color: COLORS.purple,
                    }))}
                    maxH={60}
                    showLabels
                  />
                  <div className="mt-2 grid grid-cols-7 gap-1 text-center">
                    {dailyAct.map((d, i) => (
                      <div key={i} className="text-[10px] text-muted-soft">
                        <div className="font-mono">{fmt(d.count)}</div>
                        <div>{d.day}</div>
                      </div>
                    ))}
                  </div>
                </Section>

                <Section icon={Brain} title="AI Usage Breakdown" badge={`${fmt(ai.total_tokens)} tokens`}>
                  <div className="space-y-2.5">
                    {aiActions.map((a, i) => {
                      const total = aiActions.reduce((s, x) => s + (x.count || 0), 0) || 1;
                      const count = a.count || 0;
                      return (
                        <div key={i}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-ink w-20 truncate capitalize">{a.action}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] text-muted-soft">{a.success_rate}% ok</span>
                              <span className="text-[10px] text-muted w-10 text-right">{fmt(count)}</span>
                            </div>
                          </div>
                          <div className="h-2 bg-surface-soft rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{ width: `${(count / total) * 100}%`, backgroundColor: PALETTE[i % PALETTE.length] }}
                            />
                          </div>
                        </div>
                      );
                    })}
                    {aiActions.length === 0 && <p className="text-xs text-muted-soft text-center py-4">No AI usage yet</p>}
                  </div>
                </Section>
              </div>

              {/* Top Performers + Satisfaction */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <Section icon={Trophy} title="Top Performers" className="lg:col-span-2">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-hairline">
                          <th className="text-left py-2 text-muted font-medium w-8">#</th>
                          <th className="text-left py-2 text-muted font-medium">User</th>
                          <th className="text-right py-2 text-muted font-medium">XP</th>
                          <th className="text-right py-2 text-muted font-medium">Level</th>
                          <th className="text-right py-2 text-muted font-medium">Executions</th>
                          <th className="text-right py-2 text-muted font-medium">AI Queries</th>
                          <th className="text-right py-2 text-muted font-medium">Streak</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topPerformers.map((p, i) => (
                          <tr key={p.id || i} className="border-b border-hairline/50 hover:bg-surface-soft/50 transition-colors">
                            <td className="py-2 text-muted-soft">
                              {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}
                            </td>
                            <td className="py-2 text-ink font-medium">{p.username}</td>
                            <td className="py-2 text-[#c45e28] text-right font-mono">{fmt(p.xp)}</td>
                            <td className="py-2 text-[#7c3aed] text-right">Lv.{p.level}</td>
                            <td className="py-2 text-primary text-right font-mono">{fmt(p.executions)}</td>
                            <td className="py-2 text-[#7c3aed] text-right font-mono">{fmt(p.ai_queries)}</td>
                            <td className="py-2 text-[#b8860b] text-right">
                              {p.streak > 0 ? `${p.streak}d 🔥` : '—'}
                            </td>
                          </tr>
                        ))}
                        {topPerformers.length === 0 && (
                          <tr><td colSpan={7} className="py-6 text-center text-muted-soft">No user activity yet</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </Section>

                <Section icon={Heart} title="User Satisfaction">
                  <div className="text-center mb-4">
                    <div className="text-3xl font-bold text-[#b8860b] font-mono">
                      {sat.average_rating ? sat.average_rating.toFixed(1) : '—'}
                    </div>
                    <div className="flex justify-center gap-0.5 mt-1">
                      {[1, 2, 3, 4, 5].map(s => (
                        <Star key={s} size={14} className={s <= Math.round(sat.average_rating || 0) ? 'text-[#b8860b] fill-[#b8860b]' : 'text-hairline'} />
                      ))}
                    </div>
                    <div className="text-[10px] text-muted mt-1">{sat.feedback_count || 0} reviews</div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="text-muted w-16">Recommended</span>
                      <div className="flex-1 h-1.5 bg-surface-soft rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#16a34a] rounded-full transition-all duration-500"
                          style={{ width: `${sat.recommended_percent || 0}%` }}
                        />
                      </div>
                      <span className="text-muted-soft w-8 text-right font-mono">{sat.recommended_percent || 0}%</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="text-muted w-16">Avg Session</span>
                      <span className="text-ink font-mono">{formatDuration(ov.avg_session_duration_seconds)}</span>
                    </div>
                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="text-muted w-16">Sessions Today</span>
                      <span className="text-ink font-mono">{fmt(ov.sessions_today)}</span>
                    </div>
                  </div>
                </Section>
              </div>
            </motion.div>
          )}

          {/* ══════════════ USERS TAB ══════════════ */}
          {tab === 'users' && (
            <motion.div key="users" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
              <div className="flex items-center gap-3 mb-4">
                <div className="flex-1 relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-soft" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => handleSearch(e.target.value)}
                    placeholder="Search users by name or email..."
                    className="w-full pl-9 pr-3 py-2 bg-surface border border-hairline rounded-lg text-xs text-ink placeholder-hairline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
                  />
                </div>
                <span className="text-xs text-muted whitespace-nowrap">{fmt(usersMeta.count)} total users</span>
              </div>

              <div className="bg-surface border border-hairline rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-hairline bg-surface-soft/50">
                        <th className="text-left px-4 py-3 text-muted font-medium">User</th>
                        <th className="text-left px-4 py-3 text-muted font-medium">Level</th>
                        <th className="text-right px-4 py-3 text-muted font-medium">XP</th>
                        <th className="text-right px-4 py-3 text-muted font-medium">Executions</th>
                        <th className="text-right px-4 py-3 text-muted font-medium">AI Tokens</th>
                        <th className="text-right px-4 py-3 text-muted font-medium">Snippets</th>
                        <th className="text-right px-4 py-3 text-muted font-medium">Submissions</th>
                        <th className="text-left px-4 py-3 text-muted font-medium">Active</th>
                        <th className="text-left px-4 py-3 text-muted font-medium">Joined</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredUsers.map((u) => (
                        <tr
                          key={u.id}
                          className="border-b border-hairline/30 hover:bg-surface-soft/50 cursor-pointer transition-all"
                          onClick={() => fetchUserDetail(u.id)}
                        >
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-[10px] font-bold text-primary">
                                {(u.username || '?')[0].toUpperCase()}
                              </div>
                              <div>
                                <div className="text-ink font-medium">{u.username}</div>
                                <div className="text-[10px] text-muted-soft">{u.email}</div>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-[#7c3aed]">Lv.{u.level || 1}</td>
                          <td className="px-4 py-3 text-[#c45e28] text-right font-mono">{fmt(u.xp_points)}</td>
                          <td className="px-4 py-3 text-primary text-right font-mono">{fmt(u.total_code_executions)}</td>
                          <td className="px-4 py-3 text-[#7c3aed] text-right font-mono">{fmt(u.total_ai_tokens)}</td>
                          <td className="px-4 py-3 text-[#b8860b] text-right font-mono">{fmt(u.total_snippets)}</td>
                          <td className="px-4 py-3 text-[#16a34a] text-right font-mono">{fmt(u.total_submissions)}</td>
                          <td className="px-4 py-3">
                            {u.last_login && (now - new Date(u.last_login).getTime()) < 3600000 ? (
                              <span className="inline-flex items-center gap-1 text-[10px] text-[#16a34a]">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#16a34a] animate-pulse" />
                                Online
                              </span>
                            ) : (
                              <span className="text-[10px] text-muted-soft">{timeAgo(u.last_login)}</span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-muted">{u.date_joined ? new Date(u.date_joined).toLocaleDateString() : '—'}</td>
                        </tr>
                      ))}
                      {filteredUsers.length === 0 && (
                        <tr>
                          <td colSpan={9} className="py-8 text-center text-muted-soft">
                            {searchQuery ? 'No users match your search' : 'No users found'}
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                {usersMeta.total_pages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t border-hairline">
                    <span className="text-xs text-muted">
                      Page {usersMeta.page} of {usersMeta.total_pages}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => fetchUsers(searchQuery, usersMeta.page - 1)}
                        disabled={usersMeta.page <= 1}
                        className="px-3 py-1 text-xs border border-hairline rounded-lg disabled:opacity-30 hover:bg-surface-soft transition-colors"
                      >
                        Prev
                      </button>
                      <button
                        onClick={() => fetchUsers(searchQuery, usersMeta.page + 1)}
                        disabled={usersMeta.page >= usersMeta.total_pages}
                        className="px-3 py-1 text-xs border border-hairline rounded-lg disabled:opacity-30 hover:bg-surface-soft transition-colors"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* User Detail Modal */}
              <AnimatePresence>
                {selectedUser && (
                  <motion.div
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
                    onClick={closeModal}
                  >
                    <motion.div
                      initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
                      className="bg-canvas border border-hairline rounded-2xl max-w-lg w-full max-h-[85vh] overflow-y-auto shadow-2xl"
                      onClick={e => e.stopPropagation()}
                    >
                      {userDetailLoading ? (
                        <div className="p-8 flex items-center justify-center">
                          <Loader2 size={24} className="animate-spin text-primary" />
                        </div>
                      ) : userDetail ? (
                        <div className="p-6">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-sm font-bold text-primary">
                                {(userDetail.user?.username || '?')[0].toUpperCase()}
                              </div>
                              <div>
                                <h3 className="text-lg font-bold text-ink">{userDetail.user?.username}</h3>
                                <p className="text-xs text-muted-soft">{userDetail.user?.email}</p>
                              </div>
                            </div>
                            <button onClick={closeModal} className="text-muted hover:text-ink transition-colors p-1">
                              <XCircle size={18} />
                            </button>
                          </div>

                          <div className="grid grid-cols-3 gap-2 mb-4">
                            {[
                              { label: 'XP', value: fmt(userDetail.profile?.xp_points), color: 'text-[#c45e28]', icon: Zap },
                              { label: 'Level', value: `Lv.${userDetail.profile?.level || 1}`, color: 'text-[#7c3aed]', icon: Trophy },
                              { label: 'Streak', value: `${userDetail.profile?.streak_days || 0}d`, color: 'text-[#b8860b]', icon: Flame },
                              { label: 'Executions', value: fmt(userDetail.execution_stats?.total_executions), color: 'text-primary', icon: Terminal },
                              { label: 'Success Rate', value: `${userDetail.execution_stats?.success_rate || 0}%`, color: 'text-[#16a34a]', icon: CheckCircle },
                              { label: 'AI Queries', value: fmt(userDetail.ai_stats?.total_queries), color: 'text-[#7c3aed]', icon: Brain },
                              { label: 'AI Tokens', value: fmt(userDetail.ai_stats?.total_tokens), color: 'text-[#b8860b]', icon: Zap },
                              { label: 'Snippets', value: fmt(userDetail.snippets?.total || 0), color: 'text-[#d6336c]', icon: FileCode },
                              { label: 'Time Spent', value: formatDuration(userDetail.session_stats?.total_session_time), color: 'text-[#16a34a]', icon: Clock },
                            ].map(s => (
                              <div key={s.label} className="bg-surface-soft border border-hairline rounded-lg p-2.5">
                                <div className="flex items-center gap-1 mb-1">
                                  <s.icon size={10} className={s.color} />
                                  <span className="text-[10px] text-muted">{s.label}</span>
                                </div>
                                <div className={`text-sm font-bold ${s.color} font-mono`}>{s.value}</div>
                              </div>
                            ))}
                          </div>

                          {userDetail.recent_activities?.length > 0 && (
                            <div>
                              <h4 className="text-xs font-semibold text-muted mb-2">Recent Activity</h4>
                              <div className="space-y-1.5 max-h-40 overflow-y-auto">
                                {userDetail.recent_activities.map((a, i) => (
                                  <div key={i} className="flex items-center gap-2 text-[11px]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                                    <span className="text-ink truncate">{a.description || a.activity_type}</span>
                                    <span className="text-muted-soft ml-auto whitespace-nowrap">{timeAgo(a.timestamp)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="p-8 text-center text-muted-soft text-sm">Failed to load user details</div>
                      )}
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* ══════════════ CODE & AI TAB ══════════════ */}
          {tab === 'code' && (
            <motion.div key="code" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <StatCard icon={Terminal} label="Total Executions" value={fmt(code.total)} color="bg-primary/10 text-primary" sub={`${pct(code.successful, code.total)} success rate`} />
                <StatCard icon={CheckCircle} label="Successful" value={fmt(code.successful)} color="bg-[#16a34a]/10 text-[#16a34a]" />
                <StatCard icon={XCircle} label="Failed" value={fmt(code.failed)} color="bg-[#dc2626]/10 text-[#dc2626]" />
                <StatCard icon={Timer} label="Avg Exec Time" value={`${(code.avg_execution_time || 0).toFixed(2)}s`} color="bg-[#c45e28]/10 text-[#c45e28]" sub={`Total: ${formatDuration(code.total_execution_time)}`} />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <StatCard icon={Brain} label="Total AI Queries" value={fmt(ai.total_queries)} color="bg-[#7c3aed]/10 text-[#7c3aed]" />
                <StatCard icon={Zap} label="AI Tokens Used" value={fmt(ai.total_tokens)} color="bg-[#b8860b]/10 text-[#b8860b]" />
                <StatCard icon={CheckCircle} label="AI Success Rate" value={pct(ai.successful, ai.total_queries)} color="bg-[#16a34a]/10 text-[#16a34a]" />
                <StatCard icon={Timer} label="Avg AI Response" value={`${(ai.avg_response_time || 0).toFixed(1)}s`} color="bg-[#d6336c]/10 text-[#d6336c]" />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Section icon={FileCode} title="Executions by Language">
                  <div className="space-y-3">
                    {langPop.map((l, i) => {
                      const maxCount = Math.max(...langPop.map(x => x.count || 0), 1);
                      const count = l.count || 0;
                      return (
                        <div key={i}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-ink capitalize">{l.language}</span>
                            <div className="flex items-center gap-3">
                              <span className="text-[10px] text-muted font-mono">{fmt(l.executions)} runs</span>
                              <span className="text-[10px] text-muted font-mono">{fmt(count)} snippets</span>
                            </div>
                          </div>
                          <div className="h-2 bg-surface-soft rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-500"
                              style={{ width: `${(count / maxCount) * 100}%`, backgroundColor: PALETTE[i % PALETTE.length] }}
                            />
                          </div>
                        </div>
                      );
                    })}
                    {langPop.length === 0 && <p className="text-xs text-muted-soft text-center py-4">No language data yet</p>}
                  </div>
                </Section>

                <Section icon={Brain} title="AI Tokens (4 Weeks)">
                  <MiniBar
                    data={weeklyAi.map(d => ({
                      label: d.label || '—',
                      value: d.tokens || 0,
                      color: COLORS.purple,
                    }))}
                    maxH={80}
                    showLabels
                  />
                  <div className="mt-3 grid grid-cols-4 gap-2 text-center">
                    {weeklyAi.map((d, i) => (
                      <div key={i} className="bg-surface-soft rounded-lg p-2">
                        <div className="text-[10px] text-muted">{d.label}</div>
                        <div className="text-xs font-bold text-[#7c3aed] font-mono">{fmt(d.tokens)}</div>
                      </div>
                    ))}
                  </div>
                </Section>
              </div>
            </motion.div>
          )}

          {/* ══════════════ SYSTEM TAB ══════════════ */}
          {tab === 'system' && (
            <motion.div key="system" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                <StatCard icon={Database} label="Total Users" value={fmt(health?.database?.users)} color="bg-primary/10 text-primary" />
                <StatCard icon={Activity} label="Active Sessions" value={fmt(health?.current_state?.active_sessions)} color="bg-[#16a34a]/10 text-[#16a34a]" />
                <StatCard icon={XCircle} label="Errors (1h)" value={fmt(health?.current_state?.recent_errors_1h)} color="bg-[#dc2626]/10 text-[#dc2626]" />
                <div className="bg-surface border border-hairline rounded-xl p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#b8860b]/10 text-[#b8860b]">
                      <Heart size={18} />
                    </div>
                  </div>
                  <div className="mt-1">
                    <HealthBadge status={health?.health_status} />
                  </div>
                  <div className="text-xs text-muted mt-2">System Health</div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Section icon={Database} title="Database Statistics">
                  <div className="space-y-0">
                    {health?.database ? Object.entries(health.database).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between py-2 border-b border-hairline/30 last:border-0">
                        <span className="text-xs text-ink capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="text-xs text-muted font-mono">{fmt(val)}</span>
                      </div>
                    )) : <p className="text-xs text-muted-soft text-center py-4">No data</p>}
                  </div>
                </Section>

                <Section icon={Activity} title="Current Activity">
                  <div className="space-y-0">
                    {health?.current_state ? Object.entries(health.current_state).map(([key, val]) => (
                      <div key={key} className="flex items-center justify-between py-2 border-b border-hairline/30 last:border-0">
                        <span className="text-xs text-ink capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="text-xs text-muted font-mono">{fmt(val)}</span>
                      </div>
                    )) : <p className="text-xs text-muted-soft text-center py-4">No data</p>}
                  </div>
                </Section>
              </div>

              {/* ══════════════ API KEY POOL MONITOR ══════════════ */}
              {poolData && poolData.keys && poolData.keys.length > 0 && (
                <div className="mt-6">
                  <Section icon={Key} title="API Key Pool Monitor" badge={`${poolData.available_keys}/${poolData.total_keys} available`}>
                    {/* Summary Bar */}
                    <div className="mb-4 p-3 bg-surface-soft rounded-lg border border-hairline/50">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium text-ink">Total RPD Capacity</span>
                        <span className="text-xs text-muted font-mono">{fmt(poolData.total_rpd_capacity)} / {fmt(poolData.total_keys * 1000)}</span>
                      </div>
                      <div className="w-full h-2.5 bg-hairline/30 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-300 ease-out"
                          style={{
                            width: `${((poolData.total_rpd_capacity) / (poolData.total_keys * 1000)) * 100}%`,
                            backgroundColor: poolData.total_rpd_capacity > poolData.total_keys * 500 ? COLORS.green
                              : poolData.total_rpd_capacity > poolData.total_keys * 200 ? COLORS.gold : COLORS.red,
                            boxShadow: 'var(--pool-flash, 0) === 1' ? `0 0 8px ${COLORS.teal}` : 'none',
                          }}
                        />
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] text-muted-soft">{poolData.total_keys * 1000 - poolData.total_rpd_capacity} requests used today</span>
                        <span className="text-[10px] text-muted-soft">Resets at midnight UTC</span>
                      </div>
                    </div>

                    {/* Individual Keys */}
                    <div className="space-y-2">
                      {poolData.keys.map((k, i) => {
                        const rpdParts = k.rpd.split('/');
                        const rpdUsed = parseInt(rpdParts[0]) || 0;
                        const rpdTotal = parseInt(rpdParts[1]) || 1000;
                        const rpmParts = k.rpm.split('/');
                        const rpmUsed = parseInt(rpmParts[0]) || 0;
                        const rpmTotal = parseInt(rpmParts[1]) || 30;
                        const rpdPct = (rpdUsed / rpdTotal) * 100;
                        const rpmPct = (rpmUsed / rpmTotal) * 100;

                        return (
                          <div key={i} className={`flex items-center gap-3 p-2.5 rounded-lg border transition-all ${
                            k.available
                              ? 'bg-surface border-hairline/50 hover:border-hairline'
                              : 'bg-[#dc2626]/5 border-[#dc2626]/20 opacity-60'
                          }`}>
                            {/* Key Name + Status */}
                            <div className="flex-shrink-0 w-20">
                              <div className="text-xs font-medium text-ink truncate">{k.name}</div>
                              <div className="flex items-center gap-1 mt-0.5">
                                <span className={`w-1.5 h-1.5 rounded-full ${k.available ? 'bg-[#16a34a]' : 'bg-[#dc2626]'}`} />
                                <span className="text-[10px] text-muted">{k.available ? 'Active' : 'Exhausted'}</span>
                              </div>
                            </div>

                            {/* RPD Bar */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-[10px] text-muted">RPD</span>
                                <span className="text-[10px] text-muted font-mono">{k.rpd}</span>
                              </div>
                              <div className="w-full h-1.5 bg-hairline/30 rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all duration-300 ease-out"
                                  style={{
                                    width: `${rpdPct}%`,
                                    backgroundColor: rpdPct < 50 ? COLORS.green : rpdPct < 80 ? COLORS.gold : COLORS.red,
                                  }}
                                />
                              </div>
                            </div>

                            {/* RPM Bar */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-[10px] text-muted">RPM</span>
                                <span className="text-[10px] text-muted font-mono">{k.rpm}</span>
                              </div>
                              <div className="w-full h-1.5 bg-hairline/30 rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all duration-300 ease-out"
                                  style={{
                                    width: `${rpmPct}%`,
                                    backgroundColor: rpmPct < 50 ? COLORS.teal : rpmPct < 80 ? COLORS.gold : COLORS.red,
                                  }}
                                />
                              </div>
                            </div>

                            {/* Stats */}
                            <div className="flex-shrink-0 text-right">
                              <div className="text-[10px] text-muted">
                                <span className="text-[#16a34a]">{k.total_requests}</span> ok
                                {k.total_failures > 0 && <span className="text-[#dc2626] ml-1">{k.total_failures} fail</span>}
                              </div>
                              {k.in_flight > 0 && (
                                <div className="text-[10px] text-[#7c3aed] mt-0.5">{k.in_flight} in-flight</div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </Section>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default function MasterDashboardWrapper() {
  return (
    <ErrorBoundary>
      <MasterDashboard />
    </ErrorBoundary>
  );
}
