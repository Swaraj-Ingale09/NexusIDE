import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, CheckCheck, Trophy, MessageCircle, Shield, AlertTriangle, Info } from 'lucide-react';
import api from '../utils/api';
import { useAuth } from '../context/AuthContext';

const ICON_MAP = {
  system: Info,
  achievement: Trophy,
  comment: MessageCircle,
  like: Heart,
  follow: Users,
  mention: AtSign,
  submission: Code2,
  security: Shield,
};

function Heart(props) {
  return <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" /></svg>;
}
function Users(props) {
  return <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>;
}
function AtSign(props) {
  return <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4" /><path d="M16 8v5a3 3 0 0 0 6 0v-1a10 10 0 1 0-4 8" /></svg>;
}
function Code2(props) {
  return <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m18 16 4-4-4-4" /><path d="m6 8-4 4 4 4" /><path d="m14.5 4-5 16" /></svg>;
}

export default function NotificationBell() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const ref = useRef(null);
  const wsRef = useRef(null);

  const connectWS = useCallback(() => {
    if (!user || wsRef.current) return;
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const host = window.location.host;
      const token = localStorage.getItem('access_token');
      if (!token) return;
      const ws = new WebSocket(`${protocol}://${host}/ws/notifications/?token=${token}`);
      wsRef.current = ws;
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === 'notification') {
          setNotifications(prev => [data, ...prev]);
          setUnreadCount(prev => prev + 1);
        } else if (data.type === 'unread_count') {
          setUnreadCount(data.count);
        } else if (data.type === 'init') {
          setUnreadCount(data.unread_count);
        }
      };
      ws.onclose = () => { wsRef.current = null; };
      ws.onerror = () => { wsRef.current?.close(); };
    } catch {}
  }, [user]);

  useEffect(() => {
    if (user) connectWS();
    return () => { wsRef.current?.close(); wsRef.current = null; };
  }, [user, connectWS]);

  useEffect(() => {
    if (!open || !user) return;
    setLoading(true);
    api.get('/api/notifications/?page_size=20')
      .then(res => {
        setNotifications(res.data.results || []);
        if (res.data.unread_count !== undefined) setUnreadCount(res.data.unread_count);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [open, user]);

  useEffect(() => {
    const handleClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const markRead = async (id) => {
    try {
      await api.post('/api/notifications/mark-read/', { id });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'mark_read', id }));
      }
    } catch {}
  };

  const markAllRead = async () => {
    try {
      await api.post('/api/notifications/mark-all-read/');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'mark_all_read' }));
      }
    } catch {}
  };

  const getIcon = (type) => {
    const Icon = ICON_MAP[type] || Info;
    return <Icon size={14} />;
  };

  const getTypeColor = (type) => {
    const colors = {
      system: 'text-muted-soft bg-surface-soft',
      achievement: 'text-brand-ochre bg-brand-ochre/10',
      comment: 'text-brand-lavender bg-brand-lavender/10',
      like: 'text-brand-pink bg-brand-pink/10',
      follow: 'text-brand-teal bg-brand-teal/10',
      mention: 'text-brand-peach bg-brand-peach/10',
      submission: 'text-brand-lavender bg-brand-lavender/10',
      security: 'text-red-500 bg-red-500/10',
    };
    return colors[type] || colors.system;
  };

  if (!user) return null;

  return (
    <div className="relative" ref={ref}>
      <motion.button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-md hover:bg-surface-soft text-muted-soft transition-colors"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <Bell size={18} />
        <AnimatePresence>
          {unreadCount > 0 && (
            <motion.span
              className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-brand-pink text-white text-[9px] font-bold flex items-center justify-center"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              transition={{ type: 'spring', stiffness: 500, damping: 15 }}
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </motion.span>
          )}
        </AnimatePresence>
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="absolute right-0 top-full mt-2 w-96 bg-surface-card border border-hairline rounded-xl shadow-2xl z-50 overflow-hidden"
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-hairline">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-ink">Notifications</span>
                {unreadCount > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full bg-brand-pink/10 text-brand-pink text-[10px] font-bold">
                    {unreadCount}
                  </span>
                )}
              </div>
              {unreadCount > 0 && (
                <button onClick={markAllRead}
                  className="text-xs text-brand-pink hover:underline font-semibold flex items-center gap-1">
                  <CheckCheck size={12} /> Mark all read
                </button>
              )}
            </div>

            <div className="max-h-96 overflow-y-auto divide-y divide-hairline/50">
              {loading ? (
                <div className="p-8 text-center">
                  <motion.div className="w-5 h-5 border-2 border-brand-pink border-t-transparent rounded-full mx-auto"
                    animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }} />
                </div>
              ) : notifications.length === 0 ? (
                <div className="p-8 text-center">
                  <Bell size={28} className="mx-auto mb-2 text-hairline" />
                  <p className="text-muted text-sm">No notifications yet</p>
                </div>
              ) : (
                notifications.map((n, i) => (
                  <motion.div
                    key={n.id}
                    className={`px-4 py-3 hover:bg-surface-soft/50 transition-colors cursor-pointer ${
                      !n.read ? 'bg-brand-pink/[0.03]' : ''
                    }`}
                    initial={{ opacity: 0, x: -12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                    onClick={() => !n.read && markRead(n.id)}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${getTypeColor(n.type)}`}>
                        {getIcon(n.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-ink truncate">{n.title}</span>
                          {!n.read && <div className="w-1.5 h-1.5 rounded-full bg-brand-pink shrink-0" />}
                        </div>
                        <p className="text-xs text-muted-soft mt-0.5 line-clamp-2">{n.message}</p>
                        <span className="text-[10px] text-muted-soft mt-1 block">
                          {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
