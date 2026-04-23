import { useState, useEffect } from 'react';

import { useParams, useNavigate, useLocation } from 'react-router-dom';

import { motion, AnimatePresence } from 'framer-motion';
import { Calendar, Clock, AlertCircle, ChevronDown } from 'lucide-react';

import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';
import { getDoctorAvailability } from '../services/api';

import toast from 'react-hot-toast';

const PatientBooking = () => {
  const { doctorId } = useParams<{ doctorId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [availability, setAvailability] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedHour, setExpandedHour] = useState<string | null>(null);
  const [bookingSlot, setBookingSlot] = useState<any | null>(null);
  const [userInfo, setUserInfo] = useState<any>(null);


  useEffect(() => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      setUserInfo(JSON.parse(userStr));
    }
  }, []);

  useEffect(() => {
    if (doctorId && selectedDate) {
      fetchAvailability();
    }
  }, [doctorId, selectedDate]);

  const fetchAvailability = async () => {
    setIsLoading(true);
    try {
      const data = await getDoctorAvailability(doctorId!, selectedDate);
      setAvailability(data.slots || []);
    } catch (error) {
      console.error('Fetch error:', error);
      toast.error('Failed to load availability');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBook = async (slot: any) => {
    if (!userInfo?.id) {
      toast.error('Please log in to book an appointment');
      navigate('/login');
      return;
    }

    const currentFormData = location.state?.currentFormData || {};

    // Carry over the selected slot info AND the previous form data
    navigate('/book-appointment', {
      state: {
        ...location.state,
        selectedSlot: {
          start: slot.start,
          end: slot.end
        },
        selectedDate: selectedDate,
        doctorId: doctorId,
        currentFormData: currentFormData
      }
    });
  };



  return (
    <div className="relative min-h-screen pt-24 pb-12 px-6">
      <AnimatedBackground />
      
      <div className="max-w-4xl mx-auto relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent mb-4">
            Book Your Appointment
          </h1>
          <p className="text-gray-600">Select a convenient time slot for your consultation.</p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Panel: Date Selection */}
          <GlassCard className="p-6 lg:col-span-1 h-fit">
            <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-500" />
              Select Date
            </h2>
            <input 
              type="date" 
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              min={new Date().toISOString().split('T')[0]}
              className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 transition-all outline-none bg-white/50"
            />
            
            <div className="mt-8 space-y-4">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                Available Hours
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <div className="w-3 h-3 rounded-full bg-gray-300" />
                Fully Booked
              </div>
            </div>
          </GlassCard>

          {/* Right Panel: Slots */}
          <div className="lg:col-span-2 space-y-4">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
                <p className="text-gray-500 font-medium">Loading availability...</p>
              </div>
            ) : availability.length > 0 ? (
              availability.map((hourSlot) => {
                const isFull = hourSlot.remaining === 0;
                const isExpanded = expandedHour === hourSlot.hour;

                return (
                  <GlassCard key={hourSlot.hour} className="overflow-hidden border-none shadow-sm hover:shadow-md transition-all">
                    <button
                      onClick={() => !isFull && setExpandedHour(isExpanded ? null : hourSlot.hour)}
                      disabled={isFull}
                      className={`w-full p-6 flex items-center justify-between text-left transition-colors ${
                        isFull ? 'bg-gray-50 opacity-60 cursor-not-allowed' : 'hover:bg-blue-50/30'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`p-3 rounded-xl ${isFull ? 'bg-gray-200 text-gray-500' : 'bg-green-100 text-green-600'}`}>
                          <Clock className="w-6 h-6" />
                        </div>
                        <div>
                          <h3 className="text-xl font-bold text-gray-800">{hourSlot.hour}</h3>
                          <p className={`text-sm font-bold ${isFull ? 'text-gray-500' : 'text-green-600'}`}>
                            {isFull ? 'FULL' : `${hourSlot.remaining} / ${hourSlot.total} slots left`}
                          </p>
                        </div>
                      </div>
                      {!isFull && (
                        <motion.div
                          animate={{ rotate: isExpanded ? 180 : 0 }}
                          className="text-gray-400"
                        >
                          <ChevronDown className="w-6 h-6" />
                        </motion.div>
                      )}
                    </button>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="bg-white/40 border-t border-white/60"
                        >
                          <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {hourSlot.subSlots.map((sub: any, idx: number) => (
                              <button
                                key={idx}
                                disabled={sub.isBooked}
                                onClick={() => setBookingSlot({ ...sub, hour: hourSlot.hour })}
                                className={`p-4 rounded-xl border-2 font-bold text-sm transition-all ${
                                  sub.isBooked
                                    ? 'bg-gray-100 border-gray-100 text-gray-400 cursor-not-allowed'
                                    : 'bg-white border-white hover:border-blue-500 hover:text-blue-600 shadow-sm'
                                }`}
                              >
                                {sub.start} - {sub.end}
                                {sub.isBooked && <span className="block text-[10px] uppercase mt-1">Booked</span>}
                              </button>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </GlassCard>
                );
              })
            ) : (
              <GlassCard className="p-12 text-center">
                <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-gray-800 mb-2">No Slots Available</h3>
                <p className="text-gray-500">The doctor hasn't set their availability for this date yet.</p>
              </GlassCard>
            )}
          </div>
        </div>
      </div>

      {/* Booking Confirmation Modal */}
      <AnimatePresence>
        {bookingSlot && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/20 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
            >
              <GlassCard className="p-8 max-w-md w-full shadow-2xl border-none">
                <h2 className="text-2xl font-bold text-gray-800 mb-6">Confirm Booking</h2>
                
                <div className="space-y-4 mb-8">
                  <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-2xl">
                    <Calendar className="w-5 h-5 text-blue-600" />
                    <span className="font-bold text-blue-800">{selectedDate}</span>
                  </div>
                  <div className="flex items-center gap-3 p-4 bg-indigo-50 rounded-2xl">
                    <Clock className="w-5 h-5 text-indigo-600" />
                    <span className="font-bold text-indigo-800">{bookingSlot.start} - {bookingSlot.end}</span>
                  </div>
                </div>

                <div className="flex gap-4">
                  <button
                    onClick={() => setBookingSlot(null)}
                    className="flex-1 py-3 px-6 rounded-xl font-bold text-gray-600 bg-gray-100 hover:bg-gray-200 transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleBook(bookingSlot)}
                    className="flex-1 py-3 px-6 rounded-xl font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all flex items-center justify-center gap-2"
                  >
                    Confirm
                  </button>

                </div>
              </GlassCard>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PatientBooking;
