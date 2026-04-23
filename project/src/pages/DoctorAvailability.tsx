import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Calendar, Clock, Save, Plus, X, CheckCircle, AlertCircle, ChevronRight } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';
import toast from 'react-hot-toast';

const DoctorAvailability = () => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [selectedHours, setSelectedHours] = useState<string[]>([]);
  const [avgTime, setAvgTime] = useState(15);
  const [applyToAll, setApplyToAll] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [doctorInfo, setDoctorInfo] = useState<any>(null);

  useEffect(() => {
    const userStr = localStorage.getItem('user');
    if (userStr) {
      setDoctorInfo(JSON.parse(userStr));
    }
  }, []);

  const availableHours = [
    '08:00', '09:00', '10:00', '11:00', '12:00', 
    '13:00', '14:00', '15:00', '16:00', '17:00', 
    '18:00', '19:00', '20:00', '21:00', '22:00'
  ];


  const toggleHour = (hour: string) => {
    setSelectedHours(prev => 
      prev.includes(hour) 
        ? prev.filter(h => h !== hour) 
        : [...prev, hour].sort()
    );
  };

  const handleSave = async () => {
    if (!doctorInfo?.id) {
      toast.error('Doctor information not found. Please log in again.');
      return;
    }

    if (selectedHours.length === 0) {
      toast.error('Please select at least one available hour.');
      return;
    }

    if (avgTime <= 0 || avgTime > 60) {
      toast.error('Average consultation time must be between 1 and 60 minutes.');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/doctor/availability', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doctorId: doctorInfo.id,
          date: selectedDate,
          hours: selectedHours,
          avgConsultationTime: avgTime,
          applyToAll: applyToAll
        })
      });

      if (response.ok) {
        toast.success(`Availability saved successfully ${applyToAll ? 'for the next 30 days' : ''}!`);
      } else {
        const err = await response.json();
        toast.error(err.error || 'Failed to save availability');
      }
    } catch (error) {
      console.error('Save error:', error);
      toast.error('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
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
          <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent mb-4">
            Manage Your Schedule
          </h1>
          <p className="text-gray-600">Set your available hours and consultation duration for each day.</p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Left Panel: Date & Duration */}
          <GlassCard className="p-6 md:col-span-1 h-fit">
            <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-indigo-500" />
              Day Settings
            </h2>
            
            <div className="space-y-6">
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Select Date</label>
                <input 
                  type="date" 
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 transition-all outline-none bg-white/50"
                />
              </div>

              <div className="flex items-center gap-3 p-4 bg-indigo-50/50 rounded-xl border border-indigo-100 cursor-pointer" onClick={() => setApplyToAll(!applyToAll)}>
                <div className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all ${applyToAll ? 'bg-indigo-600 border-indigo-600' : 'border-indigo-200 bg-white'}`}>
                   {applyToAll && <CheckCircle className="w-4 h-4 text-white" />}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-indigo-900">Apply to Every Day</p>
                  <p className="text-[10px] text-indigo-500">Populate schedule for the next 30 days</p>
                </div>
              </div>


              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">
                  Avg. Consultation Time (Min)
                </label>
                <div className="relative">
                  <input 
                    type="number" 
                    value={avgTime}
                    onChange={(e) => setAvgTime(parseInt(e.target.value) || 0)}
                    min="1"
                    max="60"
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:border-indigo-500 transition-all outline-none bg-white/50"
                  />
                  <Clock className="absolute right-4 top-3.5 w-4 h-4 text-gray-400" />
                </div>
                <p className="text-[10px] text-gray-400 mt-2 italic">Sub-slots will be generated automatically based on this time.</p>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleSave}
                disabled={isLoading}
                className="w-full py-4 bg-indigo-600 text-white rounded-xl font-bold shadow-lg shadow-indigo-200 hover:shadow-indigo-300 transition-all flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <Save className="w-5 h-5" />
                    Save Availability
                  </>
                )}
              </motion.button>
            </div>
          </GlassCard>

          {/* Right Panel: Hour Selection */}
          <GlassCard className="p-6 md:col-span-2">
            <h2 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
              <Clock className="w-5 h-5 text-indigo-500" />
              Available Hours
            </h2>
            
            <p className="text-sm text-gray-500 mb-6">Select the starting hours you are available. We'll divide each hour into consultation slots.</p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {availableHours.map(hour => {
                const isSelected = selectedHours.includes(hour);
                return (
                  <motion.button
                    key={hour}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => toggleHour(hour)}
                    className={`py-4 px-4 rounded-2xl border-2 transition-all font-bold text-sm flex items-center justify-between ${
                      isSelected 
                        ? 'border-indigo-500 bg-indigo-50 text-indigo-700' 
                        : 'border-white/60 bg-white/40 text-gray-600 hover:border-indigo-200'
                    }`}
                  >
                    {hour}
                    {isSelected ? <Plus className="w-4 h-4 rotate-45" /> : <Plus className="w-4 h-4 text-gray-300" />}
                  </motion.button>
                );
              })}
            </div>

            <div className="mt-8 p-4 bg-indigo-50/50 rounded-2xl border border-indigo-100">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-indigo-500 mt-0.5" />
                <div>
                  <h3 className="text-sm font-bold text-indigo-800">Preview</h3>
                  <p className="text-xs text-indigo-600 mt-1">
                    For each selected hour, patients will see <strong>{Math.floor(60/avgTime)} slots</strong> of {avgTime} minutes each.
                  </p>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
};

export default DoctorAvailability;
