import { motion } from 'framer-motion';
import { scrollRevealVariants, staggerContainer } from '../utils/animations';

export function ScrollReveal({ children, className = '', variant, delay = 0 }) {
  const v = variant || {
    ...scrollRevealVariants,
    visible: {
      ...scrollRevealVariants.visible,
      transition: { ...scrollRevealVariants.visible.transition, delay },
    },
  };

  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.15 }}
      variants={v}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerGroup({ children, className = '' }) {
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, amount: 0.1 }}
      variants={staggerContainer}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className = '' }) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 20 },
        visible: {
          opacity: 1,
          y: 0,
          transition: { type: 'spring', stiffness: 120, damping: 14 },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
