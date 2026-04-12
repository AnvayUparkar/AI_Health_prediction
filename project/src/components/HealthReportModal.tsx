import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Calendar, Activity, Heart, Moon, TrendingUp } from 'lucide-react';

interface MetricData {
  steps: number;
  avg_heart_rate: number;
  sleep_hours: number;
}

interface ReportEntry {
  id: number;
  health_score: number;
  risk_level: string;
  health_status: string;
  metrics: MetricData;
  created_at: string;
}

interface HealthReportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const HealthReportModal: React.FC<HealthReportModalProps> = ({ isOpen, onClose }) => {
  const [reports, setReports] = useState<ReportEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      fetchReport();
    }
  }, [isOpen]);

  const fetchReport = async () => {
    setLoading(true);
    const token = localStorage.getItem('token');
    try {
      const response = await fetch('http://localhost:5000/api/health-report', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const result = await response.json();
      if (result.success) {
        setReports(result.data);
      }
    } catch (err) {
      console.error('Failed to fetch health report', err);
    } finally {
      setLoading(false);
    }
  };

  // Helper to get the last 7 days as a fixed window
  const getWeeklyData = () => {
    const data: (ReportEntry & { dateLabel: string })[] = [];
    const today = new Date();
    
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(today.getDate() - i);
      const dateString = d.toLocaleDateString('en-CA'); // YYYY-MM-DD in local time
      const weekdayLong = d.toLocaleDateString([], { weekday: 'long' });
      
      // Find the LATEST report for this calendar day using local date comparison
      const dailyReport = reports.find(r => 
        new Date(r.created_at).toLocaleDateString('en-CA') === dateString
      );

      if (dailyReport) {
        data.push({ ...dailyReport, dateLabel: weekdayLong });
      } else {
        // Mock zero entry for missing days
        data.push({
          id: -i,
          health_score: 0,
          risk_level: 'None',
          health_status: 'No Data',
          metrics: { steps: 0, avg_heart_rate: 0, sleep_hours: 0 },
          created_at: d.toISOString(),
          dateLabel: weekdayLong
        });
      }
    }
    return data;
  };

  const weeklyData = getWeeklyData();
  const maxSteps = Math.max(...weeklyData.map(r => r.metrics.steps || 0), 10000);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 mb-10">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/40 backdrop-blur-md"
          />

          {/* Modal Content */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="relative w-full max-w-4xl bg-white/80 backdrop-blur-xl border border-white/40 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
          >
            {/* Header */}
            <div className="p-6 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-blue-50/50 to-indigo-50/50">
              <div className="flex items-center space-x-3">
                <div className="p-3 bg-blue-500 rounded-2xl shadow-lg shadow-blue-200">
                  <Activity className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-gray-800">Weekly Health Report</h2>
                  <p className="text-sm text-gray-500 flex items-center">
                    <Calendar className="h-3 w-3 mr-1" />
                    Last 7 Calendar Days
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              >
                <X className="h-6 w-6 text-gray-400" />
              </button>
            </div>

            {/* Body */}
            <div className="overflow-y-auto p-6 space-y-8 flex-grow custom-scrollbar">
              {loading ? (
                <div className="py-20 flex flex-col items-center justify-center space-y-4">
                  <div className="h-12 w-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin" />
                  <p className="text-gray-400 font-medium tracking-wide">Compiling Trends...</p>
                </div>
              ) : (
                <>
                  {/* Step Trend Chart */}
                  <div className="bg-white/50 border border-white rounded-3xl p-6 shadow-sm">
                    <h3 className="text-lg font-bold text-gray-800 mb-6 flex items-center">
                      <TrendingUp className="h-5 w-5 mr-2 text-blue-500" />
                      Daily Step Activity
                    </h3>
                    <div className="h-48 flex items-end justify-between items-stretch space-x-2 sm:space-x-4">
                      {weeklyData.map((report, idx) => (
                        <div key={idx} className="flex-1 flex flex-col items-center group">
                          <div className="relative flex-grow w-full flex items-end px-1">
                            <motion.div
                              initial={{ height: 0 }}
                              animate={{ height: `${(report.metrics.steps / maxSteps) * 100}%` }}
                              className={`w-full ${report.metrics.steps > 0 ? 'bg-gradient-to-t from-blue-600 to-indigo-400' : 'bg-gray-100'} rounded-t-lg transition-all group-hover:from-blue-500 group-hover:to-indigo-300 shadow-lg shadow-blue-100/20`}
                            >
                                <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                                    {report.metrics.steps.toLocaleString()} steps
                                </div>
                            </motion.div>
                          </div>
                          <p className="text-[10px] text-gray-400 font-bold mt-3 uppercase tracking-tighter">
                            {report.dateLabel}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Detailed Table (Showing only days with real data for brevity) */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-bold text-gray-800 pl-2">Daily Breakdown</h3>
                    <div className="grid gap-4">
                      {weeklyData.filter(r => r.health_score > 0).length === 0 ? (
                         <div className="py-10 text-center text-gray-400 italic text-sm">
                           No sync data recorded in the last 7 days.
                         </div>
                      ) : (
                        weeklyData.filter(r => r.health_score > 0).reverse().map((report, idx) => (
                          <motion.div
                            key={idx}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.1 }}
                            className="bg-white border border-gray-100 p-4 rounded-2xl flex items-center justify-between hover:shadow-md transition-shadow group"
                          >
                            <div className="flex items-center space-x-4">
                              <div className={`p-3 rounded-xl ${report.health_score > 80 ? 'bg-green-50' : 'bg-blue-50'}`}>
                                <p className={`text-xl font-black ${report.health_score > 80 ? 'text-green-600' : 'text-blue-600'}`}>
                                  {report.health_score}
                                </p>
                              </div>
                              <div>
                                <p className="text-sm font-bold text-gray-800 capitalize">{report.health_status}</p>
                                <p className="text-xs text-gray-400">
                                  {report.dateLabel}, {new Date(report.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center space-x-6 sm:space-x-10">
                              <div className="text-center">
                                <Heart className="h-4 w-4 text-red-500 mx-auto mb-1" />
                                <p className="text-[10px] text-gray-400 font-bold uppercase">BPM</p>
                                <p className="text-sm font-black text-gray-700">{report.metrics.avg_heart_rate}</p>
                              </div>
                              <div className="text-center">
                                <Moon className="h-4 w-4 text-indigo-500 mx-auto mb-1" />
                                <p className="text-[10px] text-gray-400 font-bold uppercase">Sleep</p>
                                <p className="text-sm font-black text-gray-700">{report.metrics.sleep_hours}h</p>
                              </div>
                              <div className="text-center hidden sm:block">
                                  <div className={`px-2 py-1 rounded-full text-[10px] font-bold ${report.risk_level === 'Low' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                      {report.risk_level} Risk
                                  </div>
                              </div>
                            </div>
                          </motion.div>
                        ))
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 bg-gray-50/50 border-t border-gray-100">
              <p className="text-xs text-center text-gray-400 font-medium italic">
                Trends are strictly based on the last 7 calendar days from your Google health profile.
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default HealthReportModal;
