import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle } from 'lucide-react';
import { useSOSContext } from '../context/SOSContext';

const SOSNavbarWidget: React.FC = () => {
  const { sosState, restoreSOS } = useSOSContext();

  if (!sosState.isActive || !sosState.isMinimized || sosState.isResolved) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={restoreSOS}
        className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-red-100 border border-red-200 text-red-700 shadow-sm"
      >
        <div className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
        </div>
        <AlertCircle className="h-4 w-4" />
        <span className="text-sm font-bold tracking-wide">SOS Active</span>
      </motion.button>
    </AnimatePresence>
  );
};

export default SOSNavbarWidget;
