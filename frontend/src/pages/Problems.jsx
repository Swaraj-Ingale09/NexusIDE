import { useState, useEffect } from 'react';
import api from '../utils/api';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, Loader2, CheckCircle, XCircle, Clock, Code2 } from 'lucide-react';

const DIFFICULTY_COLORS = {
  easy: 'bg-green-500/15 text-green-500',
  medium: 'bg-brand-ochre/15 text-brand-ochre',
  hard: 'bg-red-500/15 text-red-500',
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.06 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 120, damping: 14 } },
};

const Problems = () => {
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedProblem, setSelectedProblem] = useState(null);
  const [solution, setSolution] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    const fetchProblems = async () => {
      try {
        const res = await api.get('/api/problems/problems/');
        setProblems(res.data.results || res.data || []);
      } catch (err) {
        // Problems fetch error - non-critical
      } finally {
        setLoading(false);
      }
    };
    fetchProblems();
  }, []);

  const submitSolution = async () => {
    if (!selectedProblem || !solution.trim()) return;
    setSubmitting(true);
    setResult(null);
    try {
      const res = await api.post('/api/problems/submit/', {
        problem_id: selectedProblem.id,
        code: solution,
      });
      setResult(res.data);
    } catch (err) {
      setResult({ verdict: 'error', message: err.response?.data?.error || 'Submission failed' });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <motion.div className="flex flex-col items-center gap-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <Loader2 size={32} className="animate-spin text-brand-pink" />
        <span className="text-muted text-sm">Loading problems...</span>
      </motion.div>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 py-10">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 mb-2">
          <motion.div whileHover={{ rotate: 15, scale: 1.1 }}>
            <Trophy size={24} className="text-brand-ochre" />
          </motion.div>
          <h1 className="font-display text-3xl md:text-4xl font-medium text-ink tracking-tight">Problem Arena</h1>
        </div>
        <p className="text-muted text-base mb-8 font-body">Solve challenges, earn XP, and level up</p>
      </motion.div>

      {problems.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Problem List */}
          <motion.div
            className="lg:col-span-1 flex flex-col gap-3"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {problems.map((problem) => (
              <motion.button
                key={problem.id}
                variants={staggerItem}
                whileHover={{ x: 4, scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => { setSelectedProblem(problem); setResult(null); setSolution(''); }}
                className={`text-left p-4 rounded-xl border transition-all ${
                  selectedProblem?.id === problem.id
                    ? 'bg-surface-card border-brand-pink/30 shadow-md'
                    : 'bg-surface-soft border-hairline hover:border-muted'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-ink truncate">{problem.title}</span>
                  <span className={`px-2 py-0.5 rounded-pill text-[10px] font-bold uppercase ${DIFFICULTY_COLORS[problem.difficulty] || 'bg-surface-card text-ink'}`}>
                    {problem.difficulty}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-soft">
                  <span className="flex items-center gap-1"><Clock size={10} /> {problem.points || 10} pts</span>
                  <span className="flex items-center gap-1"><Code2 size={10} /> {problem.language || 'python'}</span>
                </div>
              </motion.button>
            ))}
          </motion.div>

          {/* Problem Detail + Editor */}
          <div className="lg:col-span-2">
            <AnimatePresence mode="wait">
              {selectedProblem ? (
                <motion.div
                  key={selectedProblem.id}
                  className="bg-surface-soft border border-hairline rounded-xl p-6"
                  initial={{ opacity: 0, scale: 0.97 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.97 }}
                  transition={{ type: 'spring', stiffness: 100, damping: 15 }}
                >
                  <h2 className="font-display text-xl font-medium text-ink mb-2">{selectedProblem.title}</h2>
                  <p className="text-sm text-body font-body mb-4 whitespace-pre-wrap">{selectedProblem.description}</p>
                  {selectedProblem.sample_input && (
                    <div className="mb-4">
                      <span className="text-xs font-bold text-ink uppercase tracking-wide">Sample Input</span>
                      <pre className="mt-1 p-3 bg-canvas border border-hairline-soft rounded-md text-xs font-mono text-body">{selectedProblem.sample_input}</pre>
                    </div>
                  )}
                  {selectedProblem.sample_output && (
                    <div className="mb-4">
                      <span className="text-xs font-bold text-ink uppercase tracking-wide">Sample Output</span>
                      <pre className="mt-1 p-3 bg-canvas border border-hairline-soft rounded-md text-xs font-mono text-body">{selectedProblem.sample_output}</pre>
                    </div>
                  )}

                  <div className="mt-4">
                    <label className="text-xs font-bold text-ink uppercase tracking-wide mb-1 block">Your Solution</label>
                    <textarea value={solution} onChange={(e) => setSolution(e.target.value)}
                      placeholder="# Write your solution here"
                      rows={12}
                      className="w-full px-4 py-2.5 bg-canvas border border-hairline rounded-md text-ink text-sm font-mono focus:outline-none focus:border-ink transition-all resize-none" />
                  </div>

                  <motion.button
                    onClick={submitSolution}
                    disabled={submitting || !solution.trim()}
                    className="tactile-btn mt-4 bg-primary text-canvas px-6 py-2.5 rounded-md text-sm font-semibold shadow-md hover:bg-primary-active disabled:opacity-50"
                    whileHover={!submitting ? { scale: 1.02 } : {}}
                    whileTap={!submitting ? { scale: 0.97 } : {}}
                  >
                    {submitting ? 'Judging...' : 'Submit Solution'}
                  </motion.button>

                  <AnimatePresence>
                    {result && (
                      <motion.div
                        className={`mt-4 p-4 rounded-md text-sm font-semibold ${
                          result.verdict === 'accepted' || result.success
                            ? 'bg-green-500/10 border border-green-500/25 text-green-500'
                            : 'bg-red-500/10 border border-red-500/25 text-red-500'
                        }`}
                        initial={{ opacity: 0, y: 10, height: 0 }}
                        animate={{ opacity: 1, y: 0, height: 'auto' }}
                        exit={{ opacity: 0, y: -10, height: 0 }}
                      >
                        {result.verdict === 'accepted' || result.success ? (
                          <span className="flex items-center gap-2"><CheckCircle size={16} /> Accepted! +{selectedProblem.points || 10} XP</span>
                        ) : (
                          <span className="flex items-center gap-2"><XCircle size={16} /> {result.verdict || result.message || 'Wrong Answer'}</span>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ) : (
                <motion.div
                  className="bg-surface-soft border border-hairline rounded-xl p-12 text-center"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                >
                  <motion.div
                    animate={{ y: [0, -8, 0] }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                  >
                    <Trophy size={48} className="mx-auto mb-4 text-hairline" />
                  </motion.div>
                  <p className="text-muted text-sm font-body">Select a problem to start solving</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      ) : (
        <div className="text-center py-20">
          <Trophy size={48} className="mx-auto mb-4 text-hairline" />
          <h3 className="font-display text-xl font-medium text-ink mb-2">No problems yet</h3>
          <p className="text-muted text-sm font-body">Problems will appear here soon</p>
        </div>
      )}
    </div>
  );
};

export default Problems;
