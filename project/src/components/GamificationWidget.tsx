import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Flame, Star, Trophy, ShoppingBag, X, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import GlassCard from './GlassCard';
import { updateSteps } from '../services/api';

const GamificationWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [points, setPoints] = useState(0);
  const [streak, setStreak] = useState(0);
  const [progress, setProgress] = useState(0);
  const [steps] = useState(0);
  const [isPulsing, setIsPulsing] = useState(false);
  const [showPointEarned, setShowPointEarned] = useState<number | null>(null);

  useEffect(() => {
    // Initial fetch of user data from localStorage
    const userData = localStorage.getItem('user');
    if (userData) {
      const user = JSON.parse(userData);
      setPoints(user.points || 0);
      setStreak(user.streak || 0);
    }

    // Listen for custom events or storage changes
    const handleUpdate = () => {
      const updated = localStorage.getItem('user');
      if (updated) {
        const u = JSON.parse(updated);
        setPoints(u.points || 0);
        setStreak(u.streak || 0);
      }
    };
    window.addEventListener('storage', handleUpdate);
    window.addEventListener('userUpdated', handleUpdate);
    return () => {
      window.removeEventListener('storage', handleUpdate);
      window.removeEventListener('userUpdated', handleUpdate);
    };
  }, []);

  // Simulate or fetch step progress
  useEffect(() => {
    const fetchProgress = async () => {
      try {
        // We use a default value of 2100 for demonstration if no data exists
        const res = await updateSteps(steps || 2100);
        if (res.success) {
          setProgress(res.progressPercent);
          if (res.earnedPoints > 0) {
            triggerPointAnimation(res.earnedPoints);
          }
        }
      } catch (err) {
        console.error("Failed to sync gamification stats", err);
      }
    };

    const token = localStorage.getItem('token');
    if (token) fetchProgress();
  }, []);

  const triggerPointAnimation = (amount: number) => {
    setShowPointEarned(amount);
    setIsPulsing(true);
    setTimeout(() => {
      setShowPointEarned(null);
      setIsPulsing(false);
    }, 3000);
  };

  if (!localStorage.getItem('token')) return null;

  return (
    <>
      {/* Floating Button */}
      <div className="fixed bottom-5 left-5 z-50">
        <AnimatePresence>
          {showPointEarned && (
            <motion.div
              initial={{ opacity: 0, y: 0, scale: 0.5 }}
              animate={{ opacity: 1, y: -50, scale: 1.2 }}
              exit={{ opacity: 0, y: -100 }}
              className="absolute left-0 w-max bg-gradient-to-r from-orange-500 to-red-600 text-white px-3 py-1 rounded-full font-bold text-sm shadow-lg pointer-events-none"
            >
              +{showPointEarned} Points 🎉
            </motion.div>
          )}
        </AnimatePresence>

        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9, rotate: -10 }}
          animate={isPulsing ? {
            scale: [1, 1.2, 1],
            boxShadow: ["0 0 0px rgba(147, 51, 234, 0)", "0 0 20px rgba(249, 115, 22, 0.5)", "0 0 0px rgba(147, 51, 234, 0)"]
          } : {}}
          transition={isPulsing ? { repeat: Infinity, duration: 1 } : { type: "spring", stiffness: 400, damping: 10 }}
          onClick={() => setIsOpen(true)}
          className="relative group p-4 bg-gradient-to-br from-purple-600 to-orange-500 rounded-full shadow-xl"
        >
          <Flame className="h-8 w-8 text-white group-hover:animate-bounce" />
          {streak > 0 && (
            <div className="absolute -top-1 -right-1 bg-yellow-400 text-red-700 text-[10px] font-black w-6 h-6 rounded-full flex items-center justify-center border-2 border-white shadow-sm">
              {streak}
            </div>
          )}
          <div className="absolute left-full ml-4 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap bg-gray-900/80 backdrop-blur text-white text-xs px-2 py-1 rounded-md pointer-events-none">
            Energy Points: {points}
          </div>
        </motion.button>
      </div>

      {/* Modal Dashboard */}
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[60]"
            />
            <motion.div
              initial={{ x: -400, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -400, opacity: 0 }}
              className="fixed left-5 bottom-24 w-[320px] max-w-[calc(100vw-40px)] z-[70]"
            >
              <GlassCard className="p-6 overflow-hidden border-2 border-purple-500/60 shadow-2xl relative">
                {/* Close Button */}
                <button
                  onClick={() => setIsOpen(false)}
                  className="absolute top-4 right-4 p-1 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <X className="h-5 w-5 text-gray-400" />
                </button>

                <div className="flex items-center space-x-3 mb-6">
                  <div className="p-3 bg-gradient-to-br from-orange-100 to-red-50 rounded-2xl">
                    <Trophy className="h-6 w-6 text-orange-500" />
                  </div>
                  <div>
                    <h3 className="font-black text-gray-900 tracking-tight">Health Status</h3>
                    <p className="text-xs text-purple-600 font-black uppercase tracking-widest">Rewards Level 1</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-6 text-center">
                  <motion.div
                    whileHover={{ scale: 1.05, borderColor: 'rgba(168,85,247,0.4)', boxShadow: '0 0 15px rgba(168,85,247,0.1)' }}
                    className="p-4 bg-orange-100/50 rounded-2xl border border-orange-200 transition-all duration-300"
                  >
                    <p className="text-[10px] text-orange-700 font-black uppercase tracking-widest mb-1">Energy Points</p>
                    <div className="flex items-center justify-center space-x-1">
                      <Star className="h-4 w-4 text-orange-500 fill-orange-500" />
                      <span className="text-2xl font-black text-orange-900">{points}</span>
                    </div>
                  </motion.div>
                  <motion.div
                    whileHover={{ scale: 1.05, borderColor: 'rgba(168,85,247,0.4)', boxShadow: '0 0 15px rgba(168,85,247,0.1)' }}
                    className="p-4 bg-red-100/50 rounded-2xl border border-red-200 transition-all duration-300"
                  >
                    <p className="text-[10px] text-red-700 font-black uppercase tracking-widest mb-1">Day Streak</p>
                    <div className="flex items-center justify-center space-x-1">
                      <Flame className="h-4 w-4 text-red-500 fill-red-500" />
                      <span className="text-2xl font-black text-red-900">{streak}</span>
                    </div>
                  </motion.div>
                </div>

                {/* Step Progress */}
                <div className="mb-6">
                  <div className="flex justify-between items-end mb-2">
                    <p className="text-[10px] text-purple-600 font-black uppercase tracking-widest">Daily Step Goal</p>
                    <p className="text-xs font-bold text-gray-900">2,100 / 3,000</p>
                  </div>
                  <div className="h-3 bg-purple-100/50 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 1, ease: "easeOut" }}
                      className={`h-full bg-gradient-to-r ${progress > 70 ? 'from-green-500 to-purple-400' : 'from-purple-600 to-orange-500'}`}
                    />
                  </div>
                  <p className="mt-2 text-[10px] text-gray-600 italic font-bold">
                    Keep moving! 900 more steps to +10 Points
                  </p>
                </div>

                <Link to="/shop" onClick={() => setIsOpen(false)}>
                  <motion.button
                    whileHover={{ scale: 1.02, x: 5 }}
                    whileTap={{ scale: 0.98 }}
                    className="w-full bg-gradient-to-r from-purple-600 to-orange-500 text-white p-4 rounded-2xl font-bold flex items-center justify-between group shadow-xl"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-white/20 rounded-lg">
                        <ShoppingBag className="h-5 w-5" />
                      </div>
                      <span className="font-black">Visit Health Shop</span>
                    </div>
                    <ChevronRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
                  </motion.button>
                </Link>
              </GlassCard>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};

export default GamificationWidget;
