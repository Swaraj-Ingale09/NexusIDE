import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '../utils/api';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FolderGit2, Plus, FileCode2, Trash2,
  Loader2, X, FolderOpen, ExternalLink,
} from 'lucide-react';
import { toast } from 'sonner';

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 20, scale: 0.96 },
  visible: { opacity: 1, y: 0, scale: 1 },
};

const PROJECT_TYPES = [
  { id: 'basic', label: 'Basic' },
  { id: 'django', label: 'Django' },
  { id: 'fastapi', label: 'FastAPI' },
  { id: 'data_science', label: 'Data Science' },
  { id: 'ml', label: 'ML' },
  { id: 'automation', label: 'Automation' },
];

const Projects = () => {
  const { } = useAuth(); // eslint-disable-line no-empty-pattern
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newType, setNewType] = useState('basic');
  const [creating, setCreating] = useState(false);
  const [openingId, setOpeningId] = useState(null);
  const [createError, setCreateError] = useState('');

  const fetchProjects = useCallback(async () => {
    try {
      const res = await api.get('/api/projects/');
      setProjects(res.data.results || res.data || []);
    } catch (err) {
      // Projects fetch error - non-critical
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects(); // eslint-disable-line react-hooks/set-state-in-effect
  }, [fetchProjects]);

  const createProject = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setCreateError('');
    try {
      const res = await api.post('/api/projects/', {
        name: newName.trim(),
        description: newDesc.trim(),
        project_type: newType,
      });
      setNewName('');
      setNewDesc('');
      setNewType('basic');
      setShowCreate(false);
      if (res.data?.id) {
        navigate(`/projects/${res.data.id}`);
      } else {
        await fetchProjects();
      }
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.detail || err.message || 'Failed to create project';
      setCreateError(msg);
    } finally {
      setCreating(false);
    }
  };

  const deleteProject = async (id) => {
    if (!window.confirm('Are you sure you want to delete this project?')) return;
    try {
      await api.delete(`/api/projects/${id}/`);
      setProjects(prev => prev.filter(p => p.id !== id));
      toast.success('Project deleted');
    } catch {
      toast.error('Failed to delete project');
    }
  };

  const openInEditor = (project) => {
    const files = project.files || [];
    if (files.length > 0) {
      setOpeningId(project.id);
      navigate('/compiler', {
        state: {
          projectId: project.id,
          projectName: project.name,
          fileId: files[0].id,
          fileName: files[0].name,
          fileContent: files[0].content,
        }
      });
    } else {
      navigate('/compiler', {
        state: {
          projectId: project.id,
          projectName: project.name,
          isNewFile: true,
        }
      });
    }
  };

  const openSpecificFile = (project, file) => {
    setOpeningId(project.id);
    navigate('/compiler', {
      state: {
        projectId: project.id,
        projectName: project.name,
        fileId: file.id,
        fileName: file.name,
        fileContent: file.content,
      }
    });
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={32} className="animate-spin text-brand-pink" />
          <span className="text-muted text-sm">Loading projects...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-10">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-10"
      >
        <div>
          <h1 className="font-display text-3xl md:text-4xl font-medium text-ink tracking-tight">Projects</h1>
          <p className="text-muted text-base mt-2 font-body">Manage your project workspaces</p>
        </div>
        <motion.button
          onClick={() => setShowCreate(true)}
          className="tactile-btn bg-primary text-canvas px-5 py-2.5 rounded-md text-sm font-semibold flex items-center gap-2 shadow-md hover:bg-primary-active"
          whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
        >
          <Plus size={16} />
          New Project
        </motion.button>
      </motion.div>

      {/* Create Modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowCreate(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-canvas border border-hairline rounded-xl p-6 w-full max-w-md shadow-2xl"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-display text-xl font-medium text-ink">Create Project</h3>
                <button onClick={() => setShowCreate(false)} className="text-muted hover:text-ink transition-colors">
                  <X size={20} />
                </button>
              </div>
              <form onSubmit={createProject} className="flex flex-col gap-4">
                {createError && (
                  <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                    className="px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-md text-xs text-red-500">
                    {createError}
                  </motion.div>
                )}
                <div>
                  <label className="text-xs font-bold text-ink uppercase tracking-wide mb-1 block">Name</label>
                  <motion.input
                    type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                    placeholder="my-awesome-project" autoFocus
                    className="w-full px-4 py-2.5 h-11 bg-canvas border border-hairline rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all"
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.05 }}
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-ink uppercase tracking-wide mb-1 block">Description</label>
                  <motion.textarea
                    value={newDesc} onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="A brief description..." rows={3}
                    className="w-full px-4 py-2.5 bg-canvas border border-hairline rounded-md text-ink text-sm font-body focus:outline-none focus:border-ink focus:ring-1 focus:ring-ink transition-all resize-none"
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-ink uppercase tracking-wide mb-1 block">Type</label>
                  <div className="grid grid-cols-3 gap-2">
                    {PROJECT_TYPES.map((t, i) => (
                      <motion.button
                        key={t.id} type="button" onClick={() => setNewType(t.id)}
                        className={`px-3 py-2 rounded-md text-xs font-medium border transition-all ${
                          newType === t.id
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-hairline text-muted hover:border-hairline-strong hover:text-ink'
                        }`}
                        whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                        initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.12 + i * 0.03 }}
                      >
                        {t.label}
                      </motion.button>
                    ))}
                  </div>
                </div>
                <motion.button
                  type="submit" disabled={creating || !newName.trim()}
                  className="tactile-btn w-full bg-primary text-canvas py-3 rounded-md text-sm font-semibold mt-2 disabled:opacity-50"
                  whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                >
                  {creating ? 'Creating...' : 'Create Project'}
                </motion.button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Project Grid */}
      {projects.length > 0 ? (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
        >
          <AnimatePresence mode="popLayout">
            {projects.map((project) => {
              const fileCount = project.files?.length ?? 0;
              return (
                <motion.div
                  key={project.id}
                  variants={staggerItem}
                  layout
                  className="bg-surface-soft border border-hairline rounded-xl p-6 brand-card-hover group"
                  whileHover={{ y: -4, boxShadow: '0 12px 40px rgba(0,0,0,0.08)' }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <motion.div
                      className="w-10 h-10 rounded-lg bg-brand-teal/15 flex items-center justify-center text-brand-teal cursor-pointer hover:bg-brand-teal/25 transition-colors"
                      onClick={() => navigate(`/projects/${project.id}`)}
                      whileHover={{ scale: 1.1, rotate: 5 }}
                    >
                      <FolderGit2 size={20} />
                    </motion.div>
                    <motion.button
                      onClick={() => deleteProject(project.id)}
                      className="opacity-0 group-hover:opacity-100 text-muted hover:text-red-500 transition-all"
                      whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
                    >
                      <Trash2 size={16} />
                    </motion.button>
                  </div>

                  <h3
                    className="font-display text-lg font-medium text-ink mb-1 cursor-pointer hover:text-brand-teal transition-colors"
                    onClick={() => navigate(`/projects/${project.id}`)}
                  >
                    {project.name}
                  </h3>
                  <p className="text-sm text-muted font-body line-clamp-2 mb-3">
                    {project.description || 'No description'}
                  </p>

                  {fileCount > 0 && (
                    <div className="mb-3 max-h-24 overflow-y-auto space-y-1">
                      {project.files.slice(0, 5).map((file, fi) => (
                        <motion.button
                          key={file.id}
                          onClick={() => openSpecificFile(project, file)}
                          className="w-full flex items-center gap-1.5 px-2 py-1 text-xs text-left text-muted-soft hover:text-brand-teal hover:bg-brand-teal/5 rounded transition-colors"
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: fi * 0.03 }}
                        >
                          <FileCode2 size={10} className="flex-shrink-0" />
                          <span className="font-mono truncate">{file.name}</span>
                        </motion.button>
                      ))}
                      {fileCount > 5 && (
                        <span className="text-[10px] text-muted-soft pl-2">+{fileCount - 5} more files</span>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-1.5 text-xs text-muted-soft">
                      <FileCode2 size={12} />
                      <span>{fileCount} {fileCount === 1 ? 'file' : 'files'}</span>
                    </div>
                    <span className="text-xs text-muted-soft">
                      {project.created_at ? new Date(project.created_at).toLocaleDateString() : '---'}
                    </span>
                  </div>

                  <div className="flex gap-2 pt-3 border-t border-hairline-soft">
                    <motion.button
                      onClick={() => openInEditor(project)}
                      disabled={openingId === project.id}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-brand-teal/10 hover:bg-brand-teal/20 text-brand-teal rounded-md text-xs font-semibold transition-colors disabled:opacity-50"
                      whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                    >
                      {openingId === project.id ? (
                        <><Loader2 size={12} className="animate-spin" /> Opening...</>
                      ) : (
                        <><ExternalLink size={12} /> {fileCount > 0 ? 'Open in Editor' : 'Add File'}</>
                      )}
                    </motion.button>
                    <motion.button
                      onClick={() => navigate(`/projects/${project.id}`)}
                      className="px-3 py-2 bg-surface-card hover:bg-surface-soft text-muted hover:text-ink border border-hairline rounded-md text-xs font-semibold transition-colors"
                      whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                    >
                      Details
                    </motion.button>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center py-20"
        >
          <motion.div animate={{ y: [0, -8, 0] }} transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}>
            <FolderOpen size={48} className="mx-auto mb-4 text-hairline" />
          </motion.div>
          <h3 className="font-display text-xl font-medium text-ink mb-2">No projects yet</h3>
          <p className="text-muted text-sm font-body mb-6">Create your first project to get started</p>
          <motion.button
            onClick={() => setShowCreate(true)}
            className="tactile-btn bg-primary text-canvas px-6 py-2.5 rounded-md text-sm font-semibold shadow-md"
            whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
          >
            Create Project
          </motion.button>
        </motion.div>
      )}
    </div>
  );
};

export default Projects;
