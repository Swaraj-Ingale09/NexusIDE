import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, Database, HardDrive, Clock, Server, CheckCircle2, AlertTriangle, XCircle, Zap } from 'lucide-react';

const STATUS_COLORS = {
  healthy: { bg: 'bg-emerald-500/10', text: 'text-emerald-500', dot: 'bg-emerald-500' },
  warning: { bg: 'bg-amber-500/10', text: 'text-amber-500', dot: 'bg-amber-500' },
  unhealthy: { bg: 'bg-red-500/10', text: 'text-red-500', dot: 'bg-red-500' },
  degraded: { bg: 'bg-amber-500/10', text: 'text-amber-500', dot: 'bg-amber-500' },
  unknown: { bg: 'bg-gray-500/10', text: 'text-gray-500', dot: 'bg-gray-500' },
};

function StatusDot({ status, size = 'sm' }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.unknown;
  const sizeClass = size === 'lg' ? 'w-3 h-3' : 'w-2 h-2';
  return (
    <span className="relative flex items-center justify-center">
      {status === 'healthy' && (
        <span className={`absolute inline-flex h-full w-full rounded-full ${colors.bg} opacity-75 animate-ping`} />
      )}
      <span className={`relative inline-flex rounded-full ${sizeClass} ${colors.dot}`} />
    </span>
  );
}

function StatusCard({ name, icon: Icon, status, details }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.unknown;
  return (
    <motion.div
      className="bg-surface-card border border-hairline rounded-xl p-5"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2, boxShadow: '0 8px 30px rgba(0,0,0,0.08)' }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${colors.bg}`}>
          <Icon size={18} className={colors.text} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-ink">{name}</h3>
            <StatusDot status={status} />
          </div>
          <span className={`text-xs font-medium capitalize ${colors.text}`}>{status}</span>
        </div>
      </div>
      {details && (
        <div className="space-y-1.5 mt-3 pt-3 border-t border-hairline/50">
          {Object.entries(details).map(([key, value]) => (
            <div key={key} className="flex justify-between text-xs">
              <span className="text-muted-soft">{key.replace(/_/g, ' ')}</span>
              <span className="text-ink font-medium text-right">{String(value)}</span>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

export default function Status() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastCheck, setLastCheck] = useState(null);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health/');
      const data = await res.json();
      setHealth(data);
      setLastCheck(new Date());
      setError(null);
    } catch (err) {
      setError('Failed to fetch status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const overallStatus = health?.status || 'unknown';
  const overallColors = STATUS_COLORS[overallStatus] || STATUS_COLORS.unknown;

  return (
    <div className="min-h-[70vh] bg-canvas">
      <div className="max-w-4xl mx-auto px-4 md:px-8 py-16">
        {/* Header */}
        <motion.div
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <motion.div
            className="inline-flex items-center gap-3 px-5 py-2.5 rounded-full border border-hairline bg-surface-card mb-6"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
          >
            <StatusDot status={overallStatus} size="lg" />
            <span className={`text-sm font-semibold capitalize ${overallColors.text}`}>
              All Systems {overallStatus === 'healthy' ? 'Operational' : overallStatus}
            </span>
          </motion.div>

          <h1 className="font-display text-4xl md:text-5xl font-medium text-ink tracking-tight mb-3">
            System Status
          </h1>
          <p className="text-muted text-base font-body max-w-md mx-auto">
            Real-time monitoring of all NexusIDE services and infrastructure
          </p>
          {lastCheck && (
            <motion.div
              className="flex items-center justify-center gap-1.5 mt-4 text-xs text-muted-soft"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              <Clock size={12} />
              Last checked {lastCheck.toLocaleTimeString()}
            </motion.div>
          )}
        </motion.div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="bg-surface-card border border-hairline rounded-xl p-5 animate-pulse">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg bg-surface-soft" />
                  <div className="space-y-1.5">
                    <div className="w-24 h-3 bg-surface-soft rounded" />
                    <div className="w-16 h-2 bg-surface-soft rounded" />
                  </div>
                </div>
                <div className="space-y-2 mt-3 pt-3 border-t border-hairline/50">
                  {[1, 2, 3].map(j => (
                    <div key={j} className="flex justify-between">
                      <div className="w-20 h-2 bg-surface-soft rounded" />
                      <div className="w-12 h-2 bg-surface-soft rounded" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <motion.div
            className="text-center py-16 bg-surface-card border border-hairline rounded-xl"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <XCircle size={48} className="mx-auto mb-4 text-red-400" />
            <h3 className="font-display text-xl font-medium text-ink mb-2">Unable to Connect</h3>
            <p className="text-muted text-sm mb-4">{error}</p>
            <button onClick={fetchHealth}
              className="px-4 py-2 bg-primary text-canvas rounded-md text-sm font-semibold hover:bg-primary-active transition-colors">
              Retry
            </button>
          </motion.div>
        ) : health ? (
          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 gap-4"
            initial="hidden"
            animate="visible"
            variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.08 } } }}
          >
            <StatusCard
              name="API Server"
              icon={Server}
              status={health.checks?.database?.status || 'unknown'}
              details={{
                'Response Time': health.checks?.database?.response_time_ms
                  ? `${health.checks.database.response_time_ms}ms` : 'N/A',
                'Engine': health.checks?.database?.engine || 'N/A',
                'Database': health.checks?.database?.database || 'N/A',
              }}
            />
            <StatusCard
              name="Cache (Redis)"
              icon={Zap}
              status={health.checks?.cache?.status || 'unknown'}
              details={{
                'Response Time': health.checks?.cache?.response_time_ms
                  ? `${health.checks.cache.response_time_ms}ms` : 'N/A',
                'Backend': health.checks?.cache?.backend || 'N/A',
              }}
            />
            <StatusCard
              name="Disk Storage"
              icon={HardDrive}
              status={health.checks?.disk?.status || 'unknown'}
              details={{
                'Free Space': health.checks?.disk?.free_gb
                  ? `${health.checks.disk.free_gb} GB` : 'N/A',
                'Total': health.checks?.disk?.total_gb
                  ? `${health.checks.disk.total_gb} GB` : 'N/A',
                'Used': health.checks?.disk?.used_percent
                  ? `${health.checks.disk.used_percent}%` : 'N/A',
              }}
            />
            <StatusCard
              name="System"
              icon={Activity}
              status={overallStatus}
              details={{
                'Debug Mode': health.system?.debug ? 'On' : 'Off',
                'Installed Apps': health.system?.installed_apps || 'N/A',
                'Allowed Hosts': health.system?.allowed_hosts || 'N/A',
              }}
            />
          </motion.div>
        ) : null}

        {/* Footer note */}
        <motion.p
          className="text-center text-xs text-muted-soft mt-10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          Auto-refreshes every 30 seconds. Powered by NexusIDE health monitoring.
        </motion.p>
      </div>
    </div>
  );
}
