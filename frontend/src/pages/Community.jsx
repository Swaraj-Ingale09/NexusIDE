import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Heart, MessageCircle, Eye, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import { sanitize } from '../utils/sanitize';

const CATEGORIES = [
  { id: 'discussion', label: 'Discussion', color: 'bg-brand-lavender/15 text-brand-lavender' },
  { id: 'code_share', label: 'Code Share', color: 'bg-brand-pink/15 text-brand-pink' },
  { id: 'help', label: 'Help', color: 'bg-brand-ochre/15 text-brand-ochre' },
  { id: 'showcase', label: 'Showcase', color: 'bg-brand-teal/15 text-brand-teal' },
];

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 20, scale: 0.98 },
  visible: { opacity: 1, y: 0, scale: 1 },
};

const Community = () => {
  const auth = useAuth(); // eslint-disable-line no-unused-vars
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState('discussion');
  const [creating, setCreating] = useState(false);
  const [expandedPost, setExpandedPost] = useState(null);
  const [commentText, setCommentText] = useState('');

  const fetchPosts = useCallback(async () => {
    try {
      const res = await api.get('/api/community/');
      setPosts(res.data.results || res.data || []);
    } catch (err) {
      // Posts fetch error - non-critical
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPosts(); // eslint-disable-line react-hooks/set-state-in-effect
  }, [fetchPosts]);

  const createPost = async (e) => {
    e.preventDefault();
    if (!newTitle.trim() || !newContent.trim()) return;
    setCreating(true);
    try {
      await api.post('/api/community/', {
        title: sanitize(newTitle.trim()),
        content: sanitize(newContent.trim()),
        category: newCategory,
      });
      setNewTitle(''); setNewContent(''); setNewCategory('discussion');
      setShowCreate(false);
      toast.success('Post created successfully');
      fetchPosts();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to create post');
    } finally { setCreating(false); }
  };

  const likePost = async (postId) => {
    try {
      const res = await api.post(`/api/community/${postId}/like/`);
      setPosts(prev => prev.map(p =>
        p.id === postId ? { ...p, likes: res.data.likes || (p.likes || 0) + 1 } : p
      ));
    } catch {
      toast.error('Failed to like post');
    }
  };

  const addComment = async (postId) => {
    if (!commentText.trim()) return;
    try {
      const res = await api.post(`/api/community/${postId}/add_comment/`, { content: sanitize(commentText.trim()) });
      setPosts(prev => prev.map(p =>
        p.id === postId ? { ...p, comments: [...(p.comments || []), res.data] } : p
      ));
      setCommentText('');
      toast.success('Comment added');
    } catch {
      toast.error('Failed to add comment');
    }
  };

  const catColor = (cat) => CATEGORIES.find(c => c.id === cat)?.color || 'bg-surface-card text-ink';
  const catLabel = (cat) => CATEGORIES.find(c => c.id === cat)?.label || cat;

  if (loading) return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={32} className="animate-spin text-brand-pink" />
        <span className="text-muted text-sm">Loading community...</span>
      </div>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto px-4 md:px-8 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-10">
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-medium text-ink tracking-tight">Community</h1>
          <p className="text-muted text-base mt-2 font-body">Share code, ask questions, and connect</p>
        </div>
        <motion.button onClick={() => setShowCreate(true)}
          className="tactile-btn bg-primary text-canvas px-5 py-2.5 rounded-md text-sm font-semibold flex items-center gap-2 shadow-md hover:bg-primary-active"
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
          <Plus size={16} /> New Post
        </motion.button>
      </motion.div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setShowCreate(false)}>
          <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            onClick={(e) => e.stopPropagation()}
            className="bg-canvas border border-hairline rounded-xl p-6 w-full max-w-lg shadow-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-display text-xl font-medium text-ink">New Post</h3>
              <button onClick={() => setShowCreate(false)} className="text-muted hover:text-ink"><X size={20} /></button>
            </div>
            <form onSubmit={createPost} className="flex flex-col gap-4">
              <div>
                <label className="text-xs font-bold text-ink uppercase tracking-wide mb-1 block">Category</label>
                <div className="flex gap-2 flex-wrap">
                  {CATEGORIES.map(cat => (
                    <motion.button key={cat.id} type="button" onClick={() => setNewCategory(cat.id)}
                      className={`px-3 py-1.5 rounded-pill text-xs font-semibold border transition-all ${newCategory === cat.id ? 'border-ink ring-1 ring-ink' : 'border-hairline'} ${cat.color}`}
                      whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      {cat.label}
                    </motion.button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs font-bold text-ink uppercase tracking-wide mb-1 block">Title</label>
                <motion.input type="text" value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="What's on your mind?" autoFocus
                  className="w-full px-4 py-2.5 h-11 bg-canvas border border-hairline rounded-md text-ink text-sm focus:outline-none focus:border-ink transition-all"
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.05 }} />
              </div>
              <div>
                <label className="text-xs font-bold text-ink uppercase tracking-wide mb-1 block">Content</label>
                <motion.textarea value={newContent} onChange={(e) => setNewContent(e.target.value)}
                  placeholder="Share your thoughts, code, or questions..." rows={6}
                  className="w-full px-4 py-2.5 bg-canvas border border-hairline rounded-md text-ink text-sm focus:outline-none focus:border-ink transition-all resize-none"
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} />
              </div>
              <motion.button type="submit" disabled={creating || !newTitle.trim() || !newContent.trim()}
                className="tactile-btn w-full bg-primary text-canvas py-3 rounded-md text-sm font-semibold mt-2 disabled:opacity-50"
                whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
                {creating ? 'Posting...' : 'Post'}
              </motion.button>
            </form>
          </motion.div>
        </div>
      )}

      {posts.length > 0 ? (
        <motion.div className="flex flex-col gap-4" variants={staggerContainer} initial="hidden" animate="visible">
          <AnimatePresence mode="popLayout">
            {posts.map((post) => (
              <motion.div key={post.id} variants={staggerItem}
                layout
                className="bg-surface-soft border border-hairline rounded-xl p-6"
                whileHover={{ y: -2, boxShadow: '0 8px 30px rgba(0,0,0,0.06)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <motion.div className="w-9 h-9 rounded-full bg-brand-peach text-ink font-bold flex items-center justify-center text-xs"
                    whileHover={{ scale: 1.1, rotate: 5 }}>
                    {post.user?.username?.substring(0, 2).toUpperCase() || 'UN'}
                  </motion.div>
                  <div className="flex-1">
                    <div className="text-sm font-semibold text-ink">{post.user?.username || 'Anonymous'}</div>
                    <div className="text-xs text-muted-soft">{post.created_at ? new Date(post.created_at).toLocaleString() : 'Just now'}</div>
                  </div>
                  <motion.span className={`px-2.5 py-1 rounded-pill text-[10px] font-bold uppercase tracking-wider ${catColor(post.category)}`}
                    whileHover={{ scale: 1.05 }}>
                    {catLabel(post.category)}
                  </motion.span>
                </div>
                <h3 className="font-display text-lg font-medium text-ink mb-2">{post.title}</h3>
                <p className="text-sm text-body font-body leading-relaxed whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: sanitize(post.content) }} />
                <div className="flex items-center gap-4 mt-4 pt-4 border-t border-hairline-soft">
                  <motion.button onClick={() => likePost(post.id)}
                    className="flex items-center gap-1.5 text-xs text-muted hover:text-brand-pink transition-colors font-semibold"
                    whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                    <Heart size={14} /> <span>{post.likes || 0}</span>
                  </motion.button>
                  <motion.button onClick={() => setExpandedPost(expandedPost === post.id ? null : post.id)}
                    className="flex items-center gap-1.5 text-xs text-muted hover:text-brand-lavender transition-colors font-semibold"
                    whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                    <MessageCircle size={14} /> <span>{post.comments?.length || 0}</span>
                  </motion.button>
                  <span className="flex items-center gap-1.5 text-xs text-muted-soft">
                    <Eye size={14} /> <span>{post.views || 0}</span>
                  </span>
                </div>
                <AnimatePresence>
                  {expandedPost === post.id && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}
                      className="overflow-hidden">
                      <div className="mt-4 pt-4 border-t border-hairline-soft">
                        <div className="flex flex-col gap-3 mb-4">
                          {post.comments?.map((c, ci) => (
                            <motion.div key={ci} className="flex gap-3"
                              initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: ci * 0.05 }}>
                              <div className="w-7 h-7 rounded-full bg-brand-lavender/20 text-ink font-bold flex items-center justify-center text-[10px] shrink-0">
                                {c.user?.username?.substring(0, 2).toUpperCase() || 'UN'}
                              </div>
                              <div>
                                <div className="text-xs font-semibold text-ink">{c.user?.username || 'Anonymous'}</div>
                                <p className="text-xs text-body mt-0.5" dangerouslySetInnerHTML={{ __html: sanitize(c.content) }} />
                              </div>
                            </motion.div>
                          ))}
                        </div>
                        <div className="flex gap-2">
                          <input type="text" value={commentText}
                            onChange={(e) => setCommentText(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && addComment(post.id)}
                            placeholder="Write a comment..."
                            className="flex-1 px-3 py-2 bg-canvas border border-hairline rounded-md text-xs text-ink focus:outline-none focus:border-ink transition-all" />
                          <motion.button onClick={() => addComment(post.id)}
                            disabled={!commentText.trim()}
                            className="px-3 py-2 bg-brand-lavender hover:bg-brand-lavender/80 text-ink rounded-md text-xs font-semibold transition-all disabled:opacity-50"
                            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                            Send
                          </motion.button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>
      ) : (
        <div className="text-center py-20">
          <MessageCircle size={48} className="mx-auto mb-4 text-hairline" />
          <h3 className="font-display text-xl font-medium text-ink mb-2">No posts yet</h3>
          <p className="text-muted text-sm font-body mb-6">Be the first to start a discussion</p>
          <motion.button onClick={() => setShowCreate(true)}
            className="tactile-btn bg-primary text-canvas px-6 py-2.5 rounded-md text-sm font-semibold shadow-md"
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
            Create Post
          </motion.button>
        </div>
      )}
    </div>
  );
};

export default Community;
