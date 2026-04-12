import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Utensils, Lightbulb, Loader2, RefreshCcw, LogIn, FileText, Smartphone, Cloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useGoogleLogin } from '@react-oauth/google';
import GlassCard from './GlassCard';
import HealthReportModal from './HealthReportModal';

interface HealthData {
  health_score: number;
  risk_level: string;
  health_status: string;
  diet_plan: string[];
  recommendations: string[];
  created_at?: string;
}

const HealthAnalysisCard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [data, setData] = useState<HealthData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [expandedSection, setExpandedSection] = useState<'diet' | 'recommendation' | null>(null);

  useEffect(() => {
    const checkAuthAndFetch = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        setIsLoggedIn(true);
        await fetchLatestAnalysis(token);
      } else {
        setIsLoggedIn(false);
        setInitialLoading(false);
      }
    };

    checkAuthAndFetch();

    const handleAuthChange = () => {
      const token = localStorage.getItem('token');
      setIsLoggedIn(!!token);
      if (token) fetchLatestAnalysis(token);
      else setData(null);
    };
    window.addEventListener('storage', handleAuthChange);
    return () => window.removeEventListener('storage', handleAuthChange);
  }, [refreshTrigger]);

  const fetchLatestAnalysis = async (token: string) => {
    try {
      const response = await fetch('http://localhost:5000/api/health-analysis', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.data) {
          setData(result.data);
        }
      }
    } catch (err) {
      console.error('Failed to fetch latest analysis', err);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleGoogleSync = useGoogleLogin({
    onSuccess: async (tokenResponse: any) => {
      setLoading(true);
      setError(null);
      const authToken = localStorage.getItem('token');
      if (!authToken || authToken === "null" || authToken === "undefined") {
        setError('Your session has expired. Please log in again.');
        setLoading(false);
        return;
      }
      
      try {
        const response = await fetch('http://localhost:5000/api/google-fit-sync', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify({
            google_token: tokenResponse.access_token,
            timezone_offset: new Date().getTimezoneOffset()
          }),
        });

        const result = await response.json();
        if (result.success) {
          setData(result.data);
          setRefreshTrigger(prev => prev + 1); // This forces the chart to reload
        } else {
          throw new Error(result.error || 'Google Fit sync failed');
        }
      } catch (err: any) {
        setError(err.message || 'Something went wrong');
      } finally {
        setLoading(false);
      }
    },
    onError: (error: any) => {
      console.error('Google Login Error:', error);
      setError('Failed to connect to Google Fit');
    },
    scope: [
      'https://www.googleapis.com/auth/fitness.activity.read',
      'https://www.googleapis.com/auth/fitness.heart_rate.read',
      'https://www.googleapis.com/auth/fitness.body.read',
      'https://www.googleapis.com/auth/fitness.sleep.read',
    ].join(' ')
  });

  if (initialLoading) {
    return (
      <GlassCard className="p-8 h-full flex items-center justify-center">
        <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
      </GlassCard>
    );
  }

  return (
    <>
      <GlassCard className="p-8 group overflow-hidden relative h-full flex flex-col" delay={0.6}>
        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
          <Activity className="h-24 w-24 text-blue-500 rotate-12" />
        </div>

        <div className="flex items-center space-x-4 mb-6">
          <motion.div
            className="p-4 bg-gradient-to-r from-blue-400 to-indigo-500 rounded-2xl shadow-lg"
            whileHover={{ scale: 1.1, rotate: 5 }}
          >
            <Cloud className="h-8 w-8 text-white" />
          </motion.div>
          <div>
            <h3 className="text-2xl font-bold text-gray-800 group-hover:text-blue-600 transition-colors duration-300">
              Health Cloud
            </h3>
            <p className="text-sm text-gray-500">Google Fit Verified</p>
          </div>
        </div>

        <p className="text-gray-600 mb-6 leading-relaxed flex-grow text-sm">
          Fetching **real-time metrics** directly from your Gmail health profile.
          Your steps and heart rate are now verified via Google Cloud.
        </p>

        <AnimatePresence mode="wait">
          {!isLoggedIn && (
            <motion.div
              key="auth-required"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="p-6 bg-blue-50 rounded-2xl border border-blue-100 text-center"
            >
              <p className="text-sm text-blue-800 mb-4 font-medium">Please login with your health account to begin accurate syncing.</p>
              <Link to="/login">
                <button className="w-full flex items-center justify-center space-x-2 bg-white text-blue-600 px-4 py-2 border border-blue-200 rounded-xl font-bold hover:bg-blue-100 transition-all">
                  <LogIn className="h-4 w-4" />
                  <span>Login</span>
                </button>
              </Link>
            </motion.div>
          )}

          {isLoggedIn && loading && !data && (
            <motion.div
              key="loading-state"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="py-12 flex flex-col items-center justify-center space-y-4"
            >
              <Loader2 className="h-12 w-12 text-blue-500 animate-spin" />
              <p className="text-gray-500 font-medium animate-pulse">Fetching Real-Time Metrics...</p>
            </motion.div>
          )}

          {isLoggedIn && !data && !loading && (
            <motion.div
              key="connect-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              <div className="text-center py-4 p-4 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
                <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-2">No Verified Link Found</p>
                <p className="text-[11px] text-gray-500">Connect to your Google account to fetch accurate data from your phone.</p>
              </div>
              <button
                onClick={() => handleGoogleSync()}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-2xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 shadow-xl"
              >
                <RefreshCcw className="h-5 w-5" />
                <span>Connect Google Fit</span>
              </button>
            </motion.div>
          )}

          {isLoggedIn && data && (
            <motion.div
              key="data-state"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              <div className="flex items-center justify-between p-4 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl border border-blue-100 shadow-sm">
                <div>
                  <p className="text-[10px] text-blue-600 font-black uppercase tracking-widest mb-1 flex items-center">
                    <Smartphone className="h-3 w-3 mr-1" />
                    Verified Sync
                  </p>
                  <p className="text-4xl font-black text-blue-900">{data.health_score}<span className="text-lg font-medium opacity-50">/100</span></p>
                </div>
                <div className="text-right">
                  <div className={`inline-block px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${data.risk_level === 'Low' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'} mb-1 shadow-sm`}>
                    {data.risk_level} Risk
                  </div>
                  <p className="text-[10px] text-gray-400 font-bold opacity-60">
                    {data.created_at ? new Date(data.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Just Now'}
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                {/* Diet Plan Section */}
                <motion.div 
                  layout
                  onClick={() => setExpandedSection(expandedSection === 'diet' ? null : 'diet')}
                  className="flex items-start space-x-3 p-3 -m-1 rounded-2xl hover:bg-white/60 hover:shadow-sm transition-all cursor-pointer group/diet"
                >
                  <div className="p-2.5 bg-green-50 rounded-xl shrink-0 group-hover/diet:scale-110 transition-transform">
                    <Utensils className="h-4 w-4 text-green-600" />
                  </div>
                  <div className="flex-grow min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-[10px] font-black text-gray-700 uppercase tracking-widest mb-1">Diet Plan</h4>
                      <div className="text-[10px] text-blue-400 font-bold opacity-0 group-hover/diet:opacity-100 transition-opacity whitespace-nowrap">
                        {expandedSection === 'diet' ? 'Show Less' : 'Click for Details'}
                      </div>
                    </div>
                    <motion.p 
                      layout
                      className={`text-[11px] text-gray-500 italic leading-relaxed ${expandedSection === 'diet' ? '' : 'line-clamp-1'}`}
                    >
                      {expandedSection === 'diet' 
                        ? (Array.isArray(data.diet_plan) ? data.diet_plan.join(' • ') : data.diet_plan)
                        : (Array.isArray(data.diet_plan) ? data.diet_plan[0] : data.diet_plan)
                      }
                    </motion.p>
                  </div>
                </motion.div>

                {/* Recommendation Section */}
                <motion.div 
                  layout
                  onClick={() => setExpandedSection(expandedSection === 'recommendation' ? null : 'recommendation')}
                  className="flex items-start space-x-3 p-3 -m-1 rounded-2xl hover:bg-white/60 hover:shadow-sm transition-all cursor-pointer group/rec"
                >
                  <div className="p-2.5 bg-purple-50 rounded-xl shrink-0 group-hover/rec:scale-110 transition-transform">
                    <Lightbulb className="h-4 w-4 text-purple-600" />
                  </div>
                  <div className="flex-grow min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-[10px] font-black text-gray-700 uppercase tracking-widest mb-1">Recommendation</h4>
                      <div className="text-[10px] text-blue-400 font-bold opacity-0 group-hover/rec:opacity-100 transition-opacity whitespace-nowrap">
                        {expandedSection === 'recommendation' ? 'Show Less' : 'Click for Details'}
                      </div>
                    </div>
                    <motion.p 
                      layout
                      className={`text-[11px] text-gray-500 italic leading-relaxed ${expandedSection === 'recommendation' ? '' : 'line-clamp-1'}`}
                    >
                      {expandedSection === 'recommendation' 
                        ? (Array.isArray(data.recommendations) ? data.recommendations.join(' • ') : data.recommendations)
                        : (Array.isArray(data.recommendations) ? data.recommendations[0] : data.recommendations)
                      }
                    </motion.p>
                  </div>
                </motion.div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleGoogleSync()}
                  disabled={loading}
                  className="py-3 bg-blue-50 text-blue-600 rounded-xl text-xs font-bold hover:bg-blue-100 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                  <span>{loading ? 'Fetching...' : 'Cloud Resync'}</span>
                </button>
                <button
                  onClick={() => setIsModalOpen(true)}
                  className="py-3 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition-all flex items-center justify-center space-x-2 shadow-lg shadow-indigo-100"
                >
                  <FileText className="h-4 w-4" />
                  <span>Full Report</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 p-4 bg-red-50 text-red-600 rounded-xl text-[10px]"
          >
            <p className="font-medium">{error}</p>
            <button onClick={() => handleGoogleSync()} className="mt-1 font-bold underline">Try Again</button>
          </motion.div>
        )}
      </GlassCard>

      <HealthReportModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </>
  );
};

export default HealthAnalysisCard;
