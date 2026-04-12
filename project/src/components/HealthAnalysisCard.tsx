import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Utensils, Lightbulb, Loader2, RefreshCcw, LogIn, FileText, Smartphone, Cloud, WifiOff, Footprints } from 'lucide-react';
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
  data_source?: string;
  created_at?: string;
}

/** Detect if running inside an Android WebView that exposes our bridge */
const hasAndroidBridge = (): boolean =>
  typeof (window as any).AndroidBridge?.triggerHealthConnectSync === 'function';

/** Source badge config */
const SOURCE_BADGES: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  google_fit:      { label: 'Google Fit',      color: 'bg-blue-100 text-blue-700',   icon: <Cloud className="h-3 w-3 mr-1" /> },
  health_connect:  { label: 'Health Connect',  color: 'bg-green-100 text-green-700', icon: <Smartphone className="h-3 w-3 mr-1" /> },
  manual:          { label: 'Manual Entry',    color: 'bg-amber-100 text-amber-700', icon: <Footprints className="h-3 w-3 mr-1" /> },
};

const HealthAnalysisCard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [data, setData] = useState<HealthData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [expandedSection, setExpandedSection] = useState<'diet' | 'recommendation' | null>(null);
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [manualSteps, setManualSteps] = useState('');
  const [manualHR, setManualHR] = useState('');
  const [manualSleep, setManualSleep] = useState('');
  const [syncSource, setSyncSource] = useState<string>('google_fit');

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

  // Listen for Health Connect results from the Android WebView bridge
  useEffect(() => {
    const handleHCResult = (event: CustomEvent) => {
      if (event.detail?.success && event.detail?.data) {
        setData(event.detail.data);
        setSyncSource('health_connect');
        setError(null);
        setRefreshTrigger(prev => prev + 1);
      }
    };
    window.addEventListener('healthConnectResult' as any, handleHCResult);
    return () => window.removeEventListener('healthConnectResult' as any, handleHCResult);
  }, []);

  const fetchLatestAnalysis = async (token: string) => {
    try {
      const response = await fetch('http://localhost:5000/api/health-analysis', {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success && result.data) {
          setData(result.data);
          setSyncSource(result.data.data_source || 'google_fit');
        }
      }
    } catch (err) {
      console.error('Failed to fetch latest analysis', err);
    } finally {
      setInitialLoading(false);
    }
  };

  // ── Primary: Google Fit OAuth sync ──────────────────────────────────────
  const handleGoogleSync = useGoogleLogin({
    onSuccess: async (tokenResponse: any) => {
      setLoading(true);
      setError(null);
      setShowManualEntry(false);
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
          setSyncSource('google_fit');
          setRefreshTrigger(prev => prev + 1);
        } else {
          throw new Error(result.error || 'Google Fit sync failed');
        }
      } catch (err: any) {
        console.error('Google Fit sync failed, showing fallback options:', err.message);
        setError(err.message || 'Google Fit sync failed. Try an alternative below.');
      } finally {
        setLoading(false);
      }
    },
    onError: (error: any) => {
      console.error('Google Login Error:', error);
      setError('Google Fit connection failed. Try an alternative sync method below.');
    },
    scope: [
      'https://www.googleapis.com/auth/fitness.activity.read',
      'https://www.googleapis.com/auth/fitness.heart_rate.read',
      'https://www.googleapis.com/auth/fitness.body.read',
      'https://www.googleapis.com/auth/fitness.sleep.read',
    ].join(' ')
  });

  // ── Fallback 1: Health Connect (Android bridge) ─────────────────────────
  const handleHealthConnectSync = async () => {
    if (hasAndroidBridge()) {
      setLoading(true);
      setError(null);
      try {
        // The Android WebView exposes this method which triggers
        // HealthDataSyncWorker.triggerImmediateSync() on the native side
        (window as any).AndroidBridge.triggerHealthConnectSync();
        // Result will arrive via the 'healthConnectResult' CustomEvent
      } catch (err: any) {
        setError('Health Connect sync failed: ' + (err.message || 'Unknown error'));
        setLoading(false);
      }
    } else {
      // Not in Android WebView — show manual entry as final fallback
      setShowManualEntry(true);
    }
  };

  // ── Fallback 2: Manual entry ────────────────────────────────────────────
  const handleManualSubmit = async () => {
    const authToken = localStorage.getItem('token');
    if (!authToken || authToken === "null" || authToken === "undefined") {
      setError('Your session has expired. Please log in again.');
      return;
    }

    const steps = parseInt(manualSteps, 10);
    const hr = parseFloat(manualHR) || 72;
    const sleep = parseFloat(manualSleep) || 7;

    if (isNaN(steps) || steps < 0) {
      setError('Please enter a valid step count.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const today = new Date().toISOString().split('T')[0];
      const response = await fetch('http://localhost:5000/api/health-connect-sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({
          daily_metrics: [{
            date: today,
            steps: steps,
            avg_heart_rate: hr,
            sleep_hours: sleep
          }],
          timezone_offset: new Date().getTimezoneOffset()
        }),
      });

      const result = await response.json();
      if (result.success) {
        setData(result.data);
        setSyncSource('manual');
        setShowManualEntry(false);
        setManualSteps('');
        setManualHR('');
        setManualSleep('');
        setRefreshTrigger(prev => prev + 1);
      } else {
        throw new Error(result.error || 'Manual sync failed');
      }
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  // ── Source badge component ──────────────────────────────────────────────
  const SourceBadge = () => {
    const badge = SOURCE_BADGES[syncSource] || SOURCE_BADGES.google_fit;
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider ${badge.color}`}>
        {badge.icon}
        {badge.label}
      </span>
    );
  };

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
            <SourceBadge />
          </div>
        </div>

        <p className="text-gray-600 mb-6 leading-relaxed flex-grow text-sm">
          Sync your health metrics from Google Fit, Health Connect, or enter them manually.
          Your steps, heart rate, and sleep data power personalized AI insights.
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
              <p className="text-gray-500 font-medium animate-pulse">Syncing Health Metrics...</p>
            </motion.div>
          )}

          {isLoggedIn && !data && !loading && (
            <motion.div
              key="connect-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <div className="text-center py-4 p-4 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
                <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest mb-2">No Verified Link Found</p>
                <p className="text-[11px] text-gray-500">Connect to sync accurate health data from your device.</p>
              </div>

              {/* Primary: Google Fit */}
              <button
                onClick={() => handleGoogleSync()}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-3.5 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-2xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 shadow-xl"
              >
                <Cloud className="h-5 w-5" />
                <span>Connect Google Fit</span>
              </button>

              {/* Tier 2a: Health Connect — syncs via Google account */}
              <button
                onClick={() => handleGoogleSync()}
                className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-3.5 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-2xl hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 shadow-xl"
              >
                <Smartphone className="h-5 w-5" />
                <span>Sync Health Connect</span>
              </button>

              {/* Tier 2b: Manual Entry */}
              <button
                onClick={() => setShowManualEntry(true)}
                className="w-full bg-gradient-to-r from-amber-500 to-orange-500 text-white px-6 py-3 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all duration-300 text-sm"
              >
                <Footprints className="h-4 w-4" />
                <span>Enter Steps Manually</span>
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
                  <span>{loading ? 'Syncing...' : 'Cloud Resync'}</span>
                </button>
                {/* Manual Resync button commented out
                <button
                  onClick={handleHealthConnectSync}
                  disabled={loading}
                  className="py-3 bg-green-50 text-green-600 rounded-xl text-xs font-bold hover:bg-green-100 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <RefreshCcw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                  <span>{loading ? 'Syncing...' : 'Manual Resync'}</span>
                </button>
                */}
                <button
                  onClick={() => setIsModalOpen(true)}
                  className="py-3 bg-indigo-600 text-white rounded-xl text-xs font-bold hover:bg-indigo-700 transition-all flex items-center justify-center space-x-2 shadow-lg shadow-indigo-100"
                >
                  <FileText className="h-4 w-4" />
                  <span>Full Report</span>
                </button>
              </div>

              {/* Alternative sync options when data exists */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleGoogleSync()}
                  className="flex-1 py-2 bg-green-50 text-green-600 rounded-lg text-[10px] font-bold hover:bg-green-100 transition-all flex items-center justify-center space-x-1"
                >
                  <Smartphone className="h-3 w-3" />
                  <span>Health Connect</span>
                </button>
                <button
                  onClick={() => setShowManualEntry(true)}
                  className="flex-1 py-2 bg-amber-50 text-amber-600 rounded-lg text-[10px] font-bold hover:bg-amber-100 transition-all flex items-center justify-center space-x-1"
                >
                  <Footprints className="h-3 w-3" />
                  <span>Manual Entry</span>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Manual Entry Form ───────────────────────────────────────────── */}
        <AnimatePresence>
          {showManualEntry && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 p-4 bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl border border-amber-200 space-y-3 overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-amber-800 flex items-center space-x-1">
                  <Footprints className="h-4 w-4" />
                  <span>Manual Health Entry</span>
                </h4>
                <button
                  onClick={() => setShowManualEntry(false)}
                  className="text-amber-400 hover:text-amber-600 text-xs font-bold"
                >
                  ✕
                </button>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-[9px] text-gray-500 font-bold uppercase tracking-wider block mb-1">Steps</label>
                  <input
                    type="number"
                    value={manualSteps}
                    onChange={(e) => setManualSteps(e.target.value)}
                    placeholder="e.g. 5000"
                    className="w-full px-2 py-1.5 text-xs rounded-lg border border-amber-200 bg-white focus:ring-2 focus:ring-amber-300 focus:border-transparent outline-none"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-gray-500 font-bold uppercase tracking-wider block mb-1">Heart Rate</label>
                  <input
                    type="number"
                    value={manualHR}
                    onChange={(e) => setManualHR(e.target.value)}
                    placeholder="72"
                    className="w-full px-2 py-1.5 text-xs rounded-lg border border-amber-200 bg-white focus:ring-2 focus:ring-amber-300 focus:border-transparent outline-none"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-gray-500 font-bold uppercase tracking-wider block mb-1">Sleep (hrs)</label>
                  <input
                    type="number"
                    value={manualSleep}
                    onChange={(e) => setManualSleep(e.target.value)}
                    placeholder="7"
                    step="0.5"
                    className="w-full px-2 py-1.5 text-xs rounded-lg border border-amber-200 bg-white focus:ring-2 focus:ring-amber-300 focus:border-transparent outline-none"
                  />
                </div>
              </div>
              <button
                onClick={handleManualSubmit}
                disabled={loading || !manualSteps}
                className="w-full bg-gradient-to-r from-amber-500 to-orange-500 text-white px-4 py-2.5 rounded-xl text-xs font-bold hover:shadow-lg transition-all disabled:opacity-50 flex items-center justify-center space-x-2"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Footprints className="h-4 w-4" />
                )}
                <span>{loading ? 'Analyzing...' : 'Submit & Analyze'}</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Error state with fallback options ────────────────────────────── */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 p-4 bg-red-50 text-red-600 rounded-xl text-[10px] space-y-2"
          >
            <p className="font-medium flex items-center space-x-1">
              <WifiOff className="h-3 w-3" />
              <span>{error}</span>
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => { setError(null); handleGoogleSync(); }}
                className="flex-1 py-1.5 bg-white border border-red-200 text-red-600 rounded-lg text-[10px] font-bold hover:bg-red-50 transition-all"
              >
                Retry Google Fit
              </button>
              <button
                onClick={() => { setError(null); handleHealthConnectSync(); }}
                className="flex-1 py-1.5 bg-green-100 border border-green-200 text-green-700 rounded-lg text-[10px] font-bold hover:bg-green-200 transition-all"
              >
                {hasAndroidBridge() ? 'Try Health Connect' : 'Enter Manually'}
              </button>
            </div>
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
