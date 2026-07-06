import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 100, damping: 15 } },
};

const Footer = () => {
  return (
    <motion.footer
      className="bg-surface-soft border-t border-hairline pt-16 pb-8 px-4 md:px-8 mt-auto relative overflow-hidden"
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.1 }}
      variants={staggerContainer}
    >
      <div className="absolute bottom-0 left-0 w-full pointer-events-none opacity-20 z-0">
        <svg viewBox="0 0 1440 220" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
          <path d="M0 220H1440V120L1250 40L1020 130L850 70L610 170L380 90L210 180L0 120V220Z" fill="url(#paint0_linear)" />
          <defs>
            <linearGradient id="paint0_linear" x1="720" y1="40" x2="720" y2="220" gradientUnits="userSpaceOnUse">
              <stop stopColor="#ffb084" />
              <stop offset="1" stopColor="#ff4d8b" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-5 gap-8 mb-12 relative z-10">
        {/* Brand column */}
        <motion.div className="md:col-span-2" variants={staggerItem}>
          <Link to="/" className="flex items-center gap-2 mb-4">
            <motion.img
              src="/favicon.svg"
              alt="NexusIDE"
              className="w-8 h-8 rounded-md shadow-md"
              whileHover={{ rotate: -10, scale: 1.1 }}
              transition={{ type: 'spring', stiffness: 300 }}
            />
            <span className="font-display text-xl font-medium tracking-tight text-ink">
              Nexus<span className="text-brand-pink font-semibold">IDE</span>
            </span>
          </Link>
          <p className="text-muted text-sm font-body max-w-sm mb-6">
            The next-generation B2B Python IDE with integrated zero-latency local AI assistance, competitive solving features, and interactive workspaces.
          </p>
          <span className="text-xs font-semibold text-muted-soft tracking-wider uppercase">
            Designed on Clay principles
          </span>
        </motion.div>

        {/* Links Column 1 */}
        <motion.div variants={staggerItem}>
          <h4 className="text-ink font-semibold text-sm mb-4 font-display">Product</h4>
          <ul className="flex flex-col gap-2.5 text-sm font-body text-muted">
            <li><Link to="/compiler" className="hover:text-ink transition-colors">Cloud Compiler</Link></li>
            <li><Link to="/projects" className="hover:text-ink transition-colors">Workspaces</Link></li>
            <li><Link to="/problems" className="hover:text-ink transition-colors">Judge Arena</Link></li>
            <li><Link to="/community" className="hover:text-ink transition-colors">Snippets Shared</Link></li>
          </ul>
        </motion.div>

        {/* Links Column 2 */}
        <motion.div variants={staggerItem}>
          <h4 className="text-ink font-semibold text-sm mb-4 font-display">Resources</h4>
          <ul className="flex flex-col gap-2.5 text-sm font-body text-muted">
            <li><a href="#" className="hover:text-ink transition-colors">Documentation</a></li>
            <li><a href="#" className="hover:text-ink transition-colors">API Guide</a></li>
            <li><a href="#" className="hover:text-ink transition-colors">Security sandbox</a></li>
            <li><Link to="/community" className="hover:text-ink transition-colors">User Feedback</Link></li>
          </ul>
        </motion.div>

        {/* Links Column 3 */}
        <motion.div variants={staggerItem}>
          <h4 className="text-ink font-semibold text-sm mb-4 font-display">Company</h4>
          <ul className="flex flex-col gap-2.5 text-sm font-body text-muted">
            <li><a href="#" className="hover:text-ink transition-colors">About Us</a></li>
            <li><a href="#" className="hover:text-ink transition-colors">Careers</a></li>
            <li><a href="#" className="hover:text-ink transition-colors">Privacy Policy</a></li>
            <li><a href="#" className="hover:text-ink transition-colors">Terms of Service</a></li>
          </ul>
        </motion.div>
      </div>

      <motion.div
        className="max-w-7xl mx-auto border-t border-hairline pt-8 flex flex-col md:flex-row items-center justify-between relative z-10"
        variants={staggerItem}
      >
        <span className="text-xs text-muted-soft font-body mb-4 md:mb-0">
          &copy; {new Date().getFullYear()} NexusIDE Inc. Made with &#10084;&#65039; for developers.
        </span>
        <div className="flex gap-4 text-xs text-muted-soft">
          <a href="#" className="hover:text-ink transition-colors">Status</a>
          <a href="#" className="hover:text-ink transition-colors">Contact Support</a>
          <a href="#" className="hover:text-ink transition-colors">GitHub</a>
        </div>
      </motion.div>
    </motion.footer>
  );
};

export default Footer;
