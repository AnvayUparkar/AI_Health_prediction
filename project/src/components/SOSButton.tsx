import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Bell, Loader2 } from 'lucide-react';
import { triggerSOS } from '../services/api';

const SOSButton: React.FC = () => {
    const [isTriggering, setIsTriggering] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [userName, setUserName] = useState('');

    useEffect(() => {
        const checkAuth = () => {
            const userStr = localStorage.getItem('user');
            if (userStr) {
                try {
                    const user = JSON.parse(userStr);
                    setIsAuthenticated(true);
                    setUserName(user.name || 'User');
                } catch (e) {
                    setIsAuthenticated(false);
                }
            } else {
                setIsAuthenticated(false);
            }
        };

        checkAuth();
        window.addEventListener('storage', checkAuth);
        return () => window.removeEventListener('storage', checkAuth);
    }, []);

    const handleSOS = async () => {
        setIsTriggering(true);
        try {
            await triggerSOS({
                patient_id: userName || 'EMERGENCY_USER',
                room_number: 'GENERAL_WARD'
            });
            setStatus('success');
            setTimeout(() => {
                setStatus('idle');
                setShowConfirm(false);
            }, 3000);
        } catch (error) {
            console.error('SOS failed', error);
            setStatus('error');
            setTimeout(() => setStatus('idle'), 3000);
        } finally {
            setIsTriggering(false);
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="fixed top-24 right-6 z-[60] flex flex-col items-end pointer-events-none">

            {/* Confirmation Dialog */}
            <AnimatePresence>
                {showConfirm && (
                    <motion.div
                        initial={{ opacity: 0, x: 20, scale: 0.9 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, x: 20, scale: 0.9 }}
                        className="mb-4 p-4 bg-white/90 backdrop-blur-md border border-red-200 rounded-2xl shadow-2xl pointer-events-auto max-w-xs"
                    >
                        <h4 className="text-red-600 font-bold mb-1 flex items-center">
                            <AlertTriangle className="h-4 w-4 mr-2" />
                            Emergency SOS
                        </h4>
                        <p className="text-sm text-gray-600 mb-3">
                            Confirming this will immediately notify all available medical staff of your emergency.
                        </p>
                        <div className="flex space-x-2">
                            <button
                                onClick={() => setShowConfirm(false)}
                                className="flex-1 px-3 py-2 text-xs font-semibold text-gray-500 hover:bg-gray-100 rounded-lg transition-colors"
                                disabled={isTriggering}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSOS}
                                className="flex-1 px-3 py-2 text-xs font-bold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-lg transition-colors flex items-center justify-center"
                                disabled={isTriggering}
                            >
                                {isTriggering ? (
                                    <Loader2 className="h-3 w-3 animate-spin mr-1" />
                                ) : status === 'success' ? (
                                    'Sent!'
                                ) : (
                                    'Confirm SOS'
                                )}
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Circular Button */}
            <motion.button
                onClick={() => setShowConfirm(!showConfirm)}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                className={`
                    pointer-events-auto
                    w-16 h-16 rounded-full 
                    flex items-center justify-center 
                    shadow-[0_0_20px_rgba(239,68,68,0.4)]
                    relative overflow-hidden
                    ${status === 'success' ? 'bg-green-500' : 'bg-red-600'}
                    transition-colors duration-300
                `}
            >
                {/* Pulsing ring animation */}
                <motion.div
                    animate={{
                        scale: [1, 1.5, 1],
                        opacity: [0.5, 0, 0.5],
                    }}
                    transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: "easeInOut",
                    }}
                    className="absolute inset-0 bg-red-400 rounded-full"
                />

                <div className="relative z-10 text-white flex flex-col items-center">
                    <Bell className={`h-7 w-7 ${status === 'idle' ? 'animate-bounce' : ''}`} />
                    <span className="text-[10px] font-black uppercase tracking-tighter">SOS</span>
                </div>
            </motion.button>
            
            {/* Feedback Message */}
            <AnimatePresence>
                {status !== 'idle' && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className={`mt-2 px-3 py-1 rounded-full text-[10px] font-bold text-white shadow-lg ${
                            status === 'success' ? 'bg-green-500' : 'bg-red-500'
                        }`}
                    >
                        {status === 'success' ? 'Staff Notified!' : 'Connection Failed'}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default SOSButton;
