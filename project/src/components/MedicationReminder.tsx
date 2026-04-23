import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, Pill, Clock, X, ChevronRight, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { io } from 'socket.io-client';
import { getPendingNotifications, markMedicationGiven } from '../services/api';

const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5000';

interface Reminder {
  log_id: number;
  patient_name: string;
  patient_id: number;
  medicine_name: string;
  dosage: string;
  time: string;
  is_overdue?: boolean;
}

export default function MedicationReminder() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [showPopup, setShowPopup] = useState<Reminder | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const navigate = useNavigate();

  // Sound effect (soft pleasant chime)
  const playSound = useCallback(() => {
    const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
    audio.volume = 0.4;
    audio.play().catch(e => console.log('Audio play blocked:', e));
  }, []);

  const fetchReminders = useCallback(async () => {
    try {
      const data = await getPendingNotifications();
      setReminders(data.notifications || []);
    } catch (err) {
      console.error('Failed to fetch reminders', err);
    }
  }, []);

  useEffect(() => {
    fetchReminders();

    // Socket implementation with multiple transports for Windows compatibility
    const socket = io(API_URL, {
      transports: ['polling', 'websocket'],
      reconnectionAttempts: 5,
      timeout: 10000
    });
    
    socket.on('connect', () => {
      console.log('Connected to medication socket');
      const userStr = localStorage.getItem('user');
      if (userStr) {
        try {
          const user = JSON.parse(userStr);
          socket.emit('join_medication_rooms', {
            user_id: user.id,
            role: user.role,
            hospitals: user.hospitals || []
          });

        } catch (e) {
          console.error('Failed to join medication rooms', e);
        }
      }
    });

    socket.on('connect_error', (err) => {
      console.warn('Socket connection error, falling back to polling:', err.message);
    });

    socket.on('medication_reminder', (data: Reminder) => {

      console.log('Received medication reminder:', data);
      setReminders(prev => {
        // Prevent duplicate reminders
        if (prev.some(r => r.log_id === data.log_id)) return prev;
        return [...prev, data];
      });
      setShowPopup(data);
      playSound();
    });

    socket.on('medicine_updated', () => {
      fetchReminders();
    });

    return () => {
      socket.disconnect();
    };
  }, [fetchReminders, playSound]);

  const handleMarkGiven = async (logId: number) => {
    try {
      await markMedicationGiven(logId);
      setReminders(prev => prev.filter(r => r.log_id !== logId));
      if (showPopup?.log_id === logId) setShowPopup(null);
    } catch (err) {
      console.error('Failed to mark given', err);
    }
  };

  return (
    <>
      {/* Navbar Icon with Badge */}
      <div className="relative">
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => setShowDropdown(!showDropdown)}
          className="p-2 rounded-xl bg-white/20 hover:bg-white/30 transition-colors relative"
        >
          <Bell className="h-5 w-5 text-gray-700" />
          {reminders.length > 0 && (
            <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-lg animate-pulse">
              {reminders.length}
            </span>
          )}
        </motion.button>

        {/* Dropdown */}
        <AnimatePresence>
          {showDropdown && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="absolute right-0 mt-3 w-80 backdrop-blur-xl bg-white/90 border border-white/20 rounded-2xl shadow-2xl overflow-hidden z-50"
            >
              <div className="p-4 border-b border-gray-100 bg-gradient-to-r from-blue-500/10 to-purple-500/10">
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <Pill className="h-4 w-4 text-purple-600" />
                  Medication Reminders
                </h3>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {reminders.length === 0 ? (
                  <div className="p-8 text-center text-gray-400 text-sm">
                    All caught up! No pending medications.
                  </div>
                ) : (
                  reminders.map((r) => (
                    <div key={r.log_id} className="p-4 hover:bg-gray-50 transition-colors border-b border-gray-50 group">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="text-xs font-bold text-purple-600 uppercase tracking-wider">{r.patient_name}</p>
                          <p className="text-sm font-semibold text-gray-800">{r.medicine_name} - {r.dosage}</p>
                        </div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${r.is_overdue ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-600'}`}>
                          {r.time}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <button 
                          onClick={() => {
                            setShowDropdown(false);
                            navigate(`/patient/${r.patient_id}/monitor`);
                          }}
                          className="flex-1 py-1.5 rounded-lg bg-gray-100 text-gray-600 text-xs font-medium hover:bg-gray-200 transition-colors flex items-center justify-center gap-1"
                        >
                          View Details <ChevronRight className="h-3 w-3" />
                        </button>
                        <button 
                          onClick={() => handleMarkGiven(r.log_id)}
                          className="px-3 py-1.5 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Floating Popup Card */}
      <AnimatePresence>
        {showPopup && (
          <motion.div
            initial={{ opacity: 0, x: 100, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8, transition: { duration: 0.2 } }}
            className="fixed bottom-6 right-6 w-80 z-[100]"
          >
            <div className="backdrop-blur-xl bg-white/95 border border-white/30 rounded-2xl shadow-2xl overflow-hidden ring-1 ring-black/5">
              <div className="h-1.5 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500" />
              <div className="p-5">
                <div className="flex justify-between items-start mb-4">
                  <div className="p-2 rounded-xl bg-purple-100">
                    <Pill className="h-6 w-6 text-purple-600" />
                  </div>
                  <button onClick={() => setShowPopup(null)} className="p-1 hover:bg-gray-100 rounded-lg text-gray-400">
                    <X className="h-4 w-4" />
                  </button>
                </div>
                
                <div className="space-y-1 mb-5">
                  <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Medication Alert</h4>
                  <h3 className="text-lg font-bold text-gray-800">{showPopup.patient_name}</h3>
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <Clock className="h-3.5 w-3.5 text-blue-500" />
                    <span>Due at {showPopup.time}</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-gray-50 border border-gray-100 mb-5">
                  <p className="text-sm font-bold text-gray-800">{showPopup.medicine_name}</p>
                  <p className="text-xs text-gray-500">{showPopup.dosage}</p>
                </div>

                <div className="flex gap-3">
                  <button 
                    onClick={() => {
                      setShowPopup(null);
                      navigate(`/patient/${showPopup.patient_id}/monitor`);
                    }}
                    className="flex-1 py-2.5 rounded-xl bg-white border border-gray-200 text-gray-700 text-sm font-bold hover:bg-gray-50 transition-all shadow-sm"
                  >
                    View Details
                  </button>
                  <button 
                    onClick={() => handleMarkGiven(showPopup.log_id)}
                    className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-bold hover:shadow-lg transition-all shadow-md flex items-center justify-center gap-2"
                  >
                    <Check className="h-4 w-4" />
                    Mark Given
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
