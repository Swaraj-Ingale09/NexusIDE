import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { motion } from 'framer-motion';
import { ArrowLeft, FileCode2, Trash2, Loader2, Plus, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';

const ProjectDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { } = useAuth(); // eslint-disable-line no-empty-pattern
  const [project, setProject] = useState(null);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchProject = useCallback(async () => {
    try {
      const res = await api.get(`/api/projects/${id}/`);
      setProject(res.data);
      setFiles(res.data.files || []);
    } catch (err) {
      // Project fetch error - non-critical
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchProject(); // eslint-disable-line react-hooks/set-state-in-effect
  }, [fetchProject]);

  const deleteFile = async (fileId) => {
    if (!window.confirm('Delete this file?')) return;
    try {
      await api.delete(`/api/projects/${id}/files/${fileId}/`);
      setFiles(prev => prev.filter(f => f.id !== fileId));
      toast.success('File deleted');
    } catch {
      toast.error('Failed to delete file');
    }
  };

  const openInEditor = (file) => {
    navigate('/compiler', {
      state: {
        projectId: parseInt(id),
        projectName: project.name,
        fileId: file.id,
        fileName: file.name,
        fileContent: file.content,
      }
    });
  };

  const addNewFile = () => {
    navigate('/compiler', {
      state: {
        projectId: parseInt(id),
        projectName: project.name,
        isNewFile: true,
      }
    });
  };

  if (loading) return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <Loader2 size={32} className="animate-spin text-brand-pink" />
    </div>
  );

  if (!project) return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <p className="text-muted">Project not found</p>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto px-4 md:px-8 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <button onClick={() => navigate('/projects')}
          className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-ink mb-6 transition-colors font-semibold">
          <ArrowLeft size={14} /> Back to Projects
        </button>

        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="font-display text-3xl font-medium text-ink tracking-tight">{project.name}</h1>
            <p className="text-muted text-sm mt-1 font-body">{project.description || 'No description'}</p>
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-soft">
              <span>{files.length} {files.length === 1 ? 'file' : 'files'}</span>
              <span>{project.views || 0} views</span>
              <span>{new Date(project.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          <button onClick={addNewFile}
            className="tactile-btn bg-primary text-canvas px-4 py-2 rounded-md text-sm font-semibold flex items-center gap-2 shadow-md hover:bg-primary-active">
            <Plus size={14} /> Add File
          </button>
        </div>

        {files.length > 0 ? (
          <div className="flex flex-col gap-3">
            {files.map((file, i) => (
              <motion.div key={file.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="bg-surface-soft border border-hairline rounded-xl p-5 group">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <FileCode2 size={16} className="text-brand-teal" />
                    <span className="text-sm font-semibold text-ink font-mono">{file.name}</span>
                    <span className="text-[10px] text-muted-soft bg-surface px-1.5 py-0.5 rounded">{file.file_type}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => openInEditor(file)}
                      className="opacity-0 group-hover:opacity-100 flex items-center gap-1 px-2 py-1 text-xs font-medium text-brand-teal hover:bg-brand-teal/10 rounded transition-all"
                      title="Open in Editor">
                      <ExternalLink size={12} /> Edit
                    </button>
                    <button onClick={() => deleteFile(file.id)}
                      className="opacity-0 group-hover:opacity-100 text-muted hover:text-red-500 transition-all">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                {file.content && (
                  <pre className="text-xs text-body font-mono bg-canvas border border-hairline-soft rounded-md p-3 overflow-x-auto max-h-40">
                    {file.content}
                  </pre>
                )}
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <FileCode2 size={48} className="mx-auto mb-4 text-hairline" />
            <h3 className="font-display text-xl font-medium text-ink mb-2">No files yet</h3>
            <p className="text-muted text-sm font-body mb-6">Add your first file to this project</p>
            <button onClick={addNewFile}
              className="tactile-btn bg-primary text-canvas px-6 py-2.5 rounded-md text-sm font-semibold shadow-md">
              Add File
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default ProjectDetail;
