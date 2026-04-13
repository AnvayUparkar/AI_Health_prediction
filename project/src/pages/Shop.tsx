import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShoppingBag, Star, ArrowLeft, Lock, CheckCircle2, Loader2, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import confetti from 'canvas-confetti';
import GlassCard from '../components/GlassCard';
import AnimatedBackground from '../components/AnimatedBackground';
import { getShopItems, buyItem } from '../services/api';

interface ShopItem {
  id: number;
  name: string;
  description: string;
  pointsCost: number;
  imageUrl: string;
  category: string;
}

const Shop: React.FC = () => {
  const [items, setItems] = useState<ShopItem[]>([]);
  const [userPoints, setUserPoints] = useState(0);
  const [loading, setLoading] = useState(true);
  const [buyingId, setBuyingId] = useState<number | null>(null);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const userData = localStorage.getItem('user');
        if (userData) {
          setUserPoints(JSON.parse(userData).points || 0);
        }

        const res = await getShopItems();
        if (res.success) {
          setItems(res.items);
        }
      } catch (err) {
        console.error("Failed to load shop", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handlePurchase = async (item: ShopItem) => {
    if (userPoints < item.pointsCost) return;

    setBuyingId(item.id);
    try {
      const res = await buyItem(item.id);
      if (res.success) {
        setUserPoints(res.newPoints);

        // Update local user data
        const userData = JSON.parse(localStorage.getItem('user') || '{}');
        userData.points = res.newPoints;
        localStorage.setItem('user', JSON.stringify(userData));
        window.dispatchEvent(new Event('userUpdated'));

        // Success Feedback
        confetti({
          particleCount: 150,
          spread: 70,
          origin: { y: 0.6 },
          colors: ['#f97316', '#ef4444', '#fbbf24']
        });

        setMessage({ text: `Successfully purchased ${item.name}!`, type: 'success' });
      } else {
        setMessage({ text: res.error || "Purchase failed", type: 'error' });
      }
    } catch (err) {
      setMessage({ text: "Something went wrong", type: 'error' });
    } finally {
      setBuyingId(null);
      setTimeout(() => setMessage(null), 5000);
    }
  };

  return (
    <div className="relative min-h-screen pt-32 pb-20 px-4 sm:px-6 lg:px-8">
      <AnimatedBackground />

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 space-y-6 md:space-y-0">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <Link to="/" className="flex items-center text-gray-500 hover:text-gray-800 transition-colors mb-4 group">
              <ArrowLeft className="h-4 w-4 mr-2 group-hover:-translate-x-1 transition-transform" />
              <span className="text-sm font-bold uppercase tracking-widest">Back to Dashboard</span>
            </Link>
            <h1 className="text-4xl md:text-6xl font-black text-gray-900 tracking-tight flex items-center">
              Health Shop <Sparkles className="ml-4 h-8 w-8 text-orange-500" />
            </h1>
            <p className="text-gray-500 mt-2 font-medium">Redeem your hard-earned Energy Points for wellness rewards.</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white/40 backdrop-blur-xl border-2 border-purple-200 p-6 rounded-3xl shadow-xl flex items-center space-x-6"
          >
            <div className="p-4 bg-gradient-to-br from-purple-600 to-orange-500 rounded-2xl shadow-lg shadow-purple-200">
              <Star className="h-8 w-8 text-white fill-white" />
            </div>
            <div>
              <p className="text-[10px] text-purple-600 font-black uppercase tracking-[0.2em] mb-1">Your Balance</p>
              <p className="text-4xl font-black text-gray-900 tracking-tighter">{userPoints}</p>
            </div>
          </motion.div>
        </div>

        {message && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mb-8 p-4 rounded-2xl flex items-center space-x-3 ${message.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700'
              }`}
          >
            <CheckCircle2 className="h-5 w-5" />
            <span className="font-bold">{message.text}</span>
          </motion.div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <Loader2 className="h-12 w-12 text-orange-500 animate-spin" />
            <p className="text-gray-400 font-bold uppercase tracking-widest animate-pulse">Loading Inventory...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {items.map((item, index) => {
              const isLocked = userPoints < item.pointsCost;
              return (
                <GlassCard key={item.id} className="p-0 overflow-hidden group flex flex-col h-full border-2 border-purple-500/30 hover:border-purple-700 hover:shadow-[0_0_40px_rgba(126,34,206,0.3)] transition-all duration-500" delay={index * 0.1}>
                  {/* Image Container */}
                  <div className="relative h-56 overflow-hidden">
                    <img
                      src={item.imageUrl}
                      alt={item.name}
                      className={`w-full h-full object-cover transition-transform duration-700 group-hover:scale-110 ${isLocked ? 'grayscale brightness-75' : ''}`}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
                    <div className="absolute bottom-4 left-4">
                      <span className="px-3 py-1 bg-white/20 backdrop-blur-md border border-white/30 rounded-full text-[10px] font-black text-white uppercase tracking-widest">
                        {item.category}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-6 flex flex-col flex-grow">
                    <div className="flex justify-between items-start mb-4">
                      <h3 className="text-xl font-black text-gray-800 tracking-tight leading-tight group-hover:text-orange-600 transition-colors">
                        {item.name}
                      </h3>
                      <div className="flex items-center space-x-1 text-orange-500 font-black">
                        <Star className="h-4 w-4 fill-orange-500" />
                        <span>{item.pointsCost}</span>
                      </div>
                    </div>

                    <p className="text-gray-500 text-sm mb-8 flex-grow leading-relaxed">
                      {item.description}
                    </p>

                    <motion.button
                      whileHover={!isLocked ? { scale: 1.05 } : {}}
                      whileTap={!isLocked ? { scale: 0.95 } : {}}
                      onClick={() => handlePurchase(item)}
                      disabled={isLocked || buyingId === item.id}
                      className={`relative w-full py-4 rounded-2xl font-black flex items-center justify-center space-x-2 shadow-xl transition-all overflow-hidden ${isLocked
                        ? 'bg-gradient-to-r from-purple-50 to-orange-50 text-purple-300 border border-purple-100 cursor-not-allowed'
                        : 'bg-gradient-to-r from-purple-600 to-orange-500 text-white hover:shadow-purple-200 shadow-purple-100'
                        }`}
                    >
                      {buyingId === item.id ? (
                        <Loader2 className="h-5 w-5 animate-spin" />
                      ) : isLocked ? (
                        <>
                          <Lock className="h-4 w-4 opacity-70" />
                          <span className="uppercase tracking-widest text-xs opacity-80">LOCKED</span>
                        </>
                      ) : (
                        <>
                          <ShoppingBag className="h-5 w-5" />
                          <span>Redeem Reward</span>
                        </>
                      )}

                      {isLocked && (
                        <div className="absolute inset-0 bg-white/60 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                          <span className="text-[10px] text-purple-900 font-black uppercase tracking-widest">
                            Need {item.pointsCost - userPoints} more pts
                          </span>
                        </div>
                      )}
                    </motion.button>
                  </div>
                </GlassCard>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default Shop;
