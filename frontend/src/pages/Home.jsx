import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import AnimatedCounter from '../components/AnimatedCounter';
import {
  Code2, Sparkles, ShieldCheck, Terminal, Trophy,
  ArrowRight, Play, Brain, GitBranch, BarChart3,
  Zap, FileCode, MessageSquare, Layers,
} from 'lucide-react';

const Home = () => {
  const { isAuthenticated } = useAuth();
  const heroRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, -60]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 24 },
    visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 100, damping: 15 } }
  };

  return (
    <div className="relative min-h-screen overflow-hidden pb-12">
      <motion.div
        className="glow-spot-pink top-10 right-10"
        animate={{ scale: [1, 1.15, 1], opacity: [0.6, 0.9, 0.6] }}
        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="glow-spot-teal top-1/3 left-10"
        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
      />

      {/* ─── Hero ─── */}
      <section ref={heroRef} className="max-w-7xl mx-auto px-4 md:px-8 py-16 md:py-24 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
        <motion.div
          style={{ y: heroY, opacity: heroOpacity }}
          className="lg:col-span-7 flex flex-col gap-6"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: 'spring', stiffness: 120, damping: 12, delay: 0.1 }}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-pill bg-surface-card border border-hairline text-ink font-body text-xs font-semibold w-fit"
          >
            <motion.span
              animate={{ scale: [1, 1.3, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="text-brand-pink"
            >●</motion.span>
            Open-Source Cloud IDE with AI
          </motion.div>

          <motion.h1
            className="font-display text-5xl md:text-7xl font-medium tracking-tighter text-ink leading-[1.0] pr-6"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 70, damping: 15, delay: 0.2 }}
          >
            Write code. <motion.span
              className="text-brand-pink"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >Run it.</motion.span> Understand it.
          </motion.h1>

          <motion.p
            className="text-muted text-base md:text-lg font-body max-w-xl"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            NexusIDE is a browser-based development environment where you can write, execute, and debug Python, C, and C++ code — with an AI assistant that explains errors, suggests fixes, and helps you learn as you build.
          </motion.p>

          <motion.div
            className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 mt-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Link
                to={isAuthenticated ? "/compiler" : "/register"}
                className="tactile-btn bg-primary text-canvas px-7 py-3.5 h-12 rounded-md font-body text-sm font-semibold shadow-lg transition-all hover:bg-primary-active flex items-center justify-center gap-2"
              >
                <span>{isAuthenticated ? 'Open Editor' : 'Start Coding Free'}</span>
                <Play size={14} className="fill-canvas" />
              </Link>
            </motion.div>
            <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Link
                to="/problems"
                className="tactile-btn bg-canvas text-ink border border-hairline px-7 py-3.5 h-12 rounded-md font-body text-sm font-semibold transition-all hover:bg-surface-soft flex items-center justify-center gap-2"
              >
                <span>Try Problems</span>
                <ArrowRight size={14} />
              </Link>
            </motion.div>
          </motion.div>
        </motion.div>

        {/* Editor mockup */}
        <motion.div
          className="lg:col-span-5 relative"
          initial={{ opacity: 0, scale: 0.85, rotateY: -10 }}
          animate={{ opacity: 1, scale: 1, rotateY: 0 }}
          transition={{ type: 'spring', stiffness: 60, damping: 15, delay: 0.3 }}
        >
          <motion.div
            className="w-full aspect-[4/3] rounded-xl bg-surface-soft border border-hairline p-6 shadow-xl relative overflow-hidden flex flex-col justify-between"
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          >
            <div className="absolute -top-12 -right-12 w-36 h-36 rounded-full bg-brand-peach/25 z-0" />
            <div className="absolute -bottom-8 -left-8 w-24 h-24 rounded-full bg-brand-mint/30 z-0" />

            <div className="bg-canvas border border-hairline-soft rounded-lg p-4 shadow-lg z-10 w-full flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-hairline-soft pb-2">
                <div className="flex gap-1.5">
                  <motion.div className="w-2.5 h-2.5 rounded-full bg-red-400" whileHover={{ scale: 1.4 }} />
                  <motion.div className="w-2.5 h-2.5 rounded-full bg-yellow-400" whileHover={{ scale: 1.4 }} />
                  <motion.div className="w-2.5 h-2.5 rounded-full bg-green-400" whileHover={{ scale: 1.4 }} />
                </div>
                <span className="text-[10px] font-mono text-muted-soft">fibonacci.py</span>
              </div>
              <pre className="font-mono text-xs text-body leading-relaxed overflow-x-auto select-none">
                <code>
                  <span className="text-brand-pink">def</span> <span className="text-brand-teal">fibonacci</span>(n):<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-muted-soft">"""Return the n-th Fibonacci number."""</span><br />
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-brand-pink">if</span> n &lt;= <span className="text-indigo-500">1</span>:<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-brand-pink">return</span> n<br />
                  &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-brand-pink">return</span> fibonacci(n-<span className="text-indigo-500">1</span>) + fibonacci(n-<span className="text-indigo-500">2</span>)<br /><br />
                  <span className="text-muted-soft"># Run and see output instantly</span><br />
                  print(fibonacci(<span className="text-indigo-500">10</span>))
                </code>
              </pre>
            </div>

            <motion.div
              className="bg-brand-teal rounded-lg p-3.5 text-white flex items-center justify-between shadow-md z-10 w-4/5 self-end -mt-6 border border-white/10"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 1.2, type: 'spring', stiffness: 80 }}
            >
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-full bg-white/20 flex items-center justify-center">
                  <Sparkles size={12} className="fill-white/30" />
                </div>
                <div className="text-xs">
                  <div className="font-semibold">AI Explains</div>
                  <div className="opacity-80">"This recursive approach works but has O(2^n) time complexity"</div>
                </div>
              </div>
              <div className="text-[10px] bg-white/20 px-2 py-0.5 rounded-pill font-mono">Explain</div>
            </motion.div>
          </motion.div>
        </motion.div>
      </section>

      {/* ─── What is NexusIDE ─── */}
      <section className="max-w-7xl mx-auto px-4 md:px-8 py-16">
        <motion.div
          className="text-center max-w-3xl mx-auto mb-16 flex flex-col gap-4"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ type: 'spring', stiffness: 80, damping: 15 }}
        >
          <span className="text-xs font-semibold tracking-widest text-muted-soft uppercase">What is NexusIDE</span>
          <h2 className="font-display text-4xl md:text-5xl tracking-tight text-ink font-medium leading-[1.1]">
            A complete coding environment, in your browser.
          </h2>
          <p className="text-muted font-body text-sm leading-relaxed">
            NexusIDE combines a code editor, compiler, AI assistant, and project manager into a single platform. Write Python, C, or C++ code, run it instantly, see results — including matplotlib charts rendered directly in the output — and get AI-powered explanations for every error or suggestion. No installations. No configuration. Just open and code.
          </p>
        </motion.div>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          {[
            { icon: Code2, title: 'Write & Run Instantly', desc: 'Type code, hit Run. Output appears in milliseconds. Supports Python 3.14, C (GCC), and C++ with full standard libraries.' },
            { icon: Brain, title: 'AI That Actually Helps', desc: 'Ask the AI to explain your code, find bugs, optimize performance, or generate tests. It reads your code AND your execution errors to give contextual help.' },
            { icon: Layers, title: 'Organize Everything', desc: 'Save code as snippets, group them into projects with multiple files, share with the community, or keep them private.' },
          ].map((item, i) => (
            <motion.div
              key={i}
              variants={itemVariants}
              whileHover={{ y: -8, scale: 1.02 }}
              transition={{ type: 'spring', stiffness: 300, damping: 12 }}
              className="bg-surface-soft border border-hairline rounded-xl p-8 flex flex-col gap-4 cursor-default"
            >
              <motion.div
                className="w-10 h-10 rounded-lg bg-brand-teal/10 flex items-center justify-center"
                whileHover={{ rotate: 12, scale: 1.1 }}
              >
                <item.icon size={20} className="text-brand-teal" />
              </motion.div>
              <h3 className="font-display text-lg font-semibold text-ink">{item.title}</h3>
              <p className="text-sm text-muted font-body leading-relaxed">{item.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ─── Core Features ─── */}
      <section className="max-w-7xl mx-auto px-4 md:px-8 py-16">
        <motion.div
          className="text-center max-w-2xl mx-auto mb-16 flex flex-col gap-3"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <span className="text-xs font-semibold tracking-widest text-muted-soft uppercase">Core Features</span>
          <h2 className="font-display text-4xl md:text-5xl tracking-tight text-ink font-medium leading-[1.1]">
            Everything a developer needs.
          </h2>
        </motion.div>

        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-80px' }}
        >
          {[
            { icon: Sparkles, title: 'AI Code Assistant', desc: 'Explain, fix, optimize, debug, format, or generate tests for any code. The AI reads your execution output and errors to provide context-aware suggestions — not generic responses.', color: 'bg-brand-pink/10 text-brand-pink', tag: 'AI' },
            { icon: ShieldCheck, title: 'Sandboxed Execution', desc: 'Code runs in isolated Docker containers with strict memory, CPU, and process limits. Python, C, and C++ are fully supported with timeout protection and resource caps.', color: 'bg-brand-teal/10 text-brand-teal', tag: 'SECURE' },
            { icon: BarChart3, title: 'Matplotlib Visualization', desc: 'Python plots and animations render directly in the output panel. Run matplotlib code and see charts, graphs, and animated visualizations without leaving the editor.', color: 'bg-brand-lavender/10 text-brand-lavender', tag: 'VISUAL' },
            { icon: Terminal, title: 'Interactive Input', desc: 'Programs that need user input work seamlessly. Toggle the input panel, type your data, and run — stdin is passed directly to your program.', color: 'bg-brand-peach/10 text-brand-peach', tag: 'INTERACTIVE' },
            { icon: GitBranch, title: 'Project Management', desc: 'Create multi-file projects, add dependencies, track versions, and manage files — all from the browser. Open any file directly in the editor with auto-save.', color: 'bg-brand-ochre/10 text-brand-ochre', tag: 'ORGANIZE' },
            { icon: Trophy, title: 'Problem Arena', desc: 'Solve curated coding challenges with hidden test cases, timed execution, and XP rewards. Track your progress, compete on leaderboards, and level up.', color: 'bg-emerald-500/10 text-emerald-600', tag: 'CHALLENGES' },
          ].map((card, idx) => (
            <motion.div
              key={idx}
              variants={itemVariants}
              whileHover={{ y: -8, scale: 1.01 }}
              transition={{ type: 'spring', stiffness: 300, damping: 12 }}
              className="bg-surface-soft border border-hairline rounded-xl p-6 flex flex-col gap-4 hover:border-hairline-soft transition-all cursor-default"
            >
              <div className="flex items-center justify-between">
                <motion.div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${card.color}`}
                  whileHover={{ rotate: -8, scale: 1.15 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  <card.icon size={20} />
                </motion.div>
                <span className="text-[10px] font-mono tracking-widest px-2 py-0.5 rounded-pill bg-surface-card text-muted-soft border border-hairline">
                  {card.tag}
                </span>
              </div>
              <h3 className="font-display text-lg font-semibold text-ink">{card.title}</h3>
              <p className="text-sm text-muted font-body leading-relaxed">{card.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ─── AI Section ─── */}
      <section className="bg-surface-soft border-y border-hairline py-20 px-4 md:px-8">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <motion.div
            className="flex flex-col gap-6"
            initial={{ opacity: 0, x: -40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ type: 'spring', stiffness: 70, damping: 15 }}
          >
            <span className="text-xs font-semibold tracking-widest text-muted-soft uppercase">AI-Powered Development</span>
            <h2 className="font-display text-3xl md:text-4xl tracking-tight text-ink font-medium">
              An AI that reads your code and your errors.
            </h2>
            <p className="text-muted font-body text-sm leading-relaxed">
              Most AI coding tools just guess from your prompt. NexusIDE's AI reads your actual code, your execution output, and your error messages to give precise, contextual help. It knows what went wrong because it sees the same terminal output you do.
            </p>
            <motion.div
              className="flex flex-col gap-3 mt-2"
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
            >
              {[
                { action: 'Explain', desc: 'Break down any code line-by-line. Understand what it does and why.' },
                { action: 'Fix', desc: 'Auto-detect errors from execution output and suggest working corrections.' },
                { action: 'Optimize', desc: 'Get performance improvements, readability suggestions, and best practices.' },
                { action: 'Debug', desc: 'Analyze error traces, identify root causes, and provide step-by-step fixes.' },
                { action: 'Format', desc: 'Auto-format code to follow language conventions and style guides.' },
                { action: 'Test', desc: 'Generate unit tests for your functions with edge case coverage.' },
              ].map((item, i) => (
                <motion.div key={i} variants={itemVariants} className="flex items-start gap-3">
                  <span className="text-xs font-bold text-brand-pink font-mono bg-brand-pink/10 px-2 py-0.5 rounded mt-0.5 shrink-0">{item.action}</span>
                  <span className="text-sm text-muted font-body">{item.desc}</span>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>
          <motion.div
            className="bg-canvas border border-hairline rounded-xl p-6 shadow-xl font-mono text-sm"
            initial={{ opacity: 0, x: 40 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ type: 'spring', stiffness: 70, damping: 15, delay: 0.2 }}
          >
            <div className="flex items-center gap-2 mb-4 border-b border-hairline-soft pb-3">
              <MessageSquare size={14} className="text-brand-pink" />
              <span className="text-xs font-semibold text-ink">AI Assistant</span>
            </div>
            <div className="space-y-4">
              <motion.div
                className="bg-surface-soft rounded-lg p-3 text-xs text-body"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.3 }}
              >
                <span className="text-brand-teal font-semibold">You:</span> Why is this loop so slow?
              </motion.div>
              <motion.div
                className="bg-brand-pink/5 border border-brand-pink/20 rounded-lg p-3 text-xs text-body"
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.5 }}
              >
                <span className="text-brand-pink font-semibold">AI:</span> Your nested loop runs in O(n²) time. The inner list comprehension on line 12 re-scans the entire array each iteration. Use a set lookup for O(1) membership testing instead — this alone cuts execution from 2.4s to 0.03s on 10k elements.
              </motion.div>
              <motion.div
                className="bg-surface-soft rounded-lg p-3 text-xs text-body"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.7 }}
              >
                <span className="text-brand-teal font-semibold">You:</span> Show me the fix
              </motion.div>
              <motion.div
                className="bg-brand-teal/5 border border-brand-teal/20 rounded-lg p-3 text-xs text-body font-mono"
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: 0.9 }}
              >
                <span className="text-brand-pink">def</span> <span className="text-brand-teal">find_pairs</span>(nums, target):<br />
                &nbsp;&nbsp;&nbsp;&nbsp;seen = set()<br />
                &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-brand-pink">for</span> n <span className="text-brand-pink">in</span> nums:<br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-brand-pink">if</span> target - n <span className="text-brand-pink">in</span> seen:<br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span className="text-brand-pink">yield</span> (target - n, n)<br />
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;seen.add(n)
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─── How It Works ─── */}
      <section className="max-w-7xl mx-auto px-4 md:px-8 py-20">
        <motion.div
          className="text-center max-w-2xl mx-auto mb-16 flex flex-col gap-3"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <span className="text-xs font-semibold tracking-widest text-muted-soft uppercase">How It Works</span>
          <h2 className="font-display text-4xl md:text-5xl tracking-tight text-ink font-medium leading-[1.1]">
            Three steps. Zero setup.
          </h2>
        </motion.div>
        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-8"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          {[
            { step: '01', title: 'Write Code', desc: 'Open the editor, pick Python/C/C++, and start typing. Syntax highlighting, auto-indent, and error detection work out of the box.', icon: FileCode },
            { step: '02', title: 'Run & See Results', desc: 'Hit Ctrl+Enter. Your code executes in a secure sandbox. Output, errors, and matplotlib plots appear instantly in the output panel.', icon: Zap },
            { step: '03', title: 'Learn with AI', desc: 'Stuck? Ask the AI to explain, fix, or optimize. It reads your code and errors to give real help — not generic suggestions.', icon: Brain },
          ].map((item, i) => (
            <motion.div
              key={i}
              variants={itemVariants}
              className="text-center flex flex-col items-center gap-4"
            >
              <motion.div
                className="w-14 h-14 rounded-full bg-surface-soft border border-hairline flex items-center justify-center"
                whileHover={{ scale: 1.15, rotate: 10 }}
                transition={{ type: 'spring', stiffness: 300 }}
              >
                <item.icon size={24} className="text-brand-teal" />
              </motion.div>
              <span className="text-xs font-mono text-muted-soft">{item.step}</span>
              <h3 className="font-display text-xl font-semibold text-ink">{item.title}</h3>
              <p className="text-sm text-muted font-body leading-relaxed max-w-xs">{item.desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ─── Stats ─── */}
      <section className="max-w-7xl mx-auto px-4 md:px-8 py-12">
        <motion.div
          className="grid grid-cols-2 md:grid-cols-4 gap-6"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          {[
            { value: 3, label: 'Languages Supported', sub: 'Python, C, C++' },
            { value: 6, label: 'AI Actions', sub: 'Explain, Fix, Optimize, Debug, Format, Test' },
            { value: 1, label: 'Execution Time', suffix: '<1s', sub: 'Sandboxed code runs in under a second' },
            { value: 100, label: 'Free & Open', suffix: '%', sub: 'No paywalls, no limits on usage' },
          ].map((stat, i) => (
            <motion.div
              key={i}
              variants={itemVariants}
              className="text-center py-6"
              whileHover={{ scale: 1.05 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <div className="text-3xl md:text-4xl font-bold font-display text-ink mb-1">
                {stat.suffix ? (
                  <>{stat.value === 1 ? '<' : ''}{stat.value}{stat.suffix}</>
                ) : (
                  <AnimatedCounter target={stat.value} />
                )}
              </div>
              <div className="text-sm font-semibold text-ink mb-0.5">{stat.label}</div>
              <div className="text-xs text-muted">{stat.sub}</div>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* ─── CTA ─── */}
      <section className="max-w-7xl mx-auto px-4 md:px-8 py-16">
        <motion.div
          className="bg-surface-soft border border-hairline rounded-xl p-10 md:p-16 flex flex-col md:flex-row justify-between items-center gap-8 relative overflow-hidden"
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ type: 'spring', stiffness: 70, damping: 15 }}
        >
          <motion.div
            className="absolute top-0 right-0 w-64 h-64 rounded-full bg-brand-lavender/10 pointer-events-none filter blur-xl"
            animate={{ scale: [1, 1.3, 1], x: [0, 20, 0] }}
            transition={{ duration: 8, repeat: Infinity }}
          />
          <motion.div
            className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-brand-peach/15 pointer-events-none filter blur-xl"
            animate={{ scale: [1, 1.2, 1], y: [0, -15, 0] }}
            transition={{ duration: 6, repeat: Infinity, delay: 1 }}
          />

          <div className="flex flex-col gap-4 relative z-10 max-w-xl">
            <h2 className="font-display text-3xl md:text-4xl font-medium tracking-tight text-ink">
              Start coding in seconds.
            </h2>
            <p className="text-muted text-sm font-body">
              No downloads. No setup. Open the editor, write code, and run it. The AI is ready to help whenever you get stuck.
            </p>
          </div>

          <div className="flex gap-4 relative z-10 shrink-0 w-full md:w-auto">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} className="w-full md:w-auto">
              <Link
                to={isAuthenticated ? "/compiler" : "/register"}
                className="tactile-btn bg-primary text-canvas px-6 py-3 h-11 rounded-md font-body text-xs font-semibold shadow-lg transition-all hover:bg-primary-active w-full md:w-auto text-center block"
              >
                {isAuthenticated ? 'Open Editor' : 'Get Started Free'}
              </Link>
            </motion.div>
          </div>
        </motion.div>
      </section>
    </div>
  );
};

export default Home;
