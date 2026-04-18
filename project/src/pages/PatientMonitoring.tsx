import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Activity, Droplets, Heart, Wind, AlertTriangle,
  TrendingUp, TrendingDown, Minus, Clock, Utensils, RefreshCw,
  CheckCircle2, Circle, Sun, CloudSun, Moon,
} from 'lucide-react';
import { getPatientMonitoring, updatePatientMonitoring } from '../services/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface MonitoringRecord {
  id: number;
  patient_id: number;
  date: string;
  time_slot: string;
  glucose: number | null;
  bp_systolic: number | null;
  bp_diastolic: number | null;
  spo2: number | null;
  breakfast_done: boolean;
  lunch_done: boolean;
  snacks_done: boolean;
  dinner_done: boolean;
  created_at: string;
}

interface TrendData {
  trend: string;
  slope: number;
  average: number;
  count_increase: number;
  count_decrease: number;
}

interface AlertData {
  type: 'CRITICAL' | 'WARNING' | 'INFO';
  message: string;
  metric: string;
}

interface PatientInfo {
  patient_id: number;
  name: string;
  age: number | null;
  sex: string | null;
  ward_number: string | null;
}

// ── Constants ────────────────────────────────────────────────────────────────

const TIME_SLOTS = [
  { value: 'morning', label: 'Morning', icon: Sun, color: 'from-amber-400 to-orange-400' },
  { value: 'afternoon', label: 'Afternoon', icon: CloudSun, color: 'from-sky-400 to-blue-400' },
  { value: 'evening', label: 'Evening', icon: Moon, color: 'from-indigo-400 to-purple-500' },
];

const TREND_CONFIG: Record<string, { icon: any; color: string; label: string }> = {
  STRONGLY_INCREASING: { icon: TrendingUp, color: 'text-red-500', label: 'Strongly Rising' },
  INCREASING: { icon: TrendingUp, color: 'text-amber-500', label: 'Rising' },
  STABLE: { icon: Minus, color: 'text-emerald-500', label: 'Stable' },
  DECREASING: { icon: TrendingDown, color: 'text-sky-500', label: 'Declining' },
  STRONGLY_DECREASING: { icon: TrendingDown, color: 'text-red-500', label: 'Strongly Declining' },
  INSUFFICIENT_DATA: { icon: Minus, color: 'text-gray-400', label: 'Insufficient Data' },
};

const METRIC_CONFIG: Record<string, { label: string; unit: string; icon: any; color: string }> = {
  glucose: { label: 'Blood Glucose', unit: 'mg/dL', icon: Droplets, color: 'from-violet-500 to-purple-600' },
  bp_systolic: { label: 'Systolic BP', unit: 'mmHg', icon: Heart, color: 'from-rose-500 to-pink-600' },
  bp_diastolic: { label: 'Diastolic BP', unit: 'mmHg', icon: Heart, color: 'from-rose-400 to-pink-500' },
  spo2: { label: 'SpO2', unit: '%', icon: Wind, color: 'from-cyan-500 to-blue-600' },
};

// ── Mini Sparkline Chart Component ──────────────────────────────────────────

function Sparkline({ data, color, height = 48 }: { data: number[]; color: string; height?: number }) {
  if (!data.length) return <div className="text-xs text-gray-400 italic">No data yet</div>;

  const width = 200;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const padding = 4;

  const points = data.map((val, i) => {
    const x = padding + (i / (data.length - 1 || 1)) * (width - padding * 2);
    const y = padding + (1 - (val - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const areaPoints = [
    `${padding},${height - padding}`,
    ...points,
    `${width - padding},${height - padding}`,
  ].join(' ');

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }}>
      <defs>
        <linearGradient id={`grad-${color}`} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style={{ stopColor: color, stopOpacity: 0.3 }} />
          <stop offset="100%" style={{ stopColor: color, stopOpacity: 0.02 }} />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill={`url(#grad-${color})`} />
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Latest value dot */}
      {data.length > 0 && (
        <circle
          cx={parseFloat(points[points.length - 1].split(',')[0])}
          cy={parseFloat(points[points.length - 1].split(',')[1])}
          r="3.5"
          fill={color}
          stroke="white"
          strokeWidth="2"
        />
      )}
    </svg>
  );
}

// ── Main Component ──────────────────────────────────────────────────────────

export default function PatientMonitoringPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const navigate = useNavigate();

  const [patient, setPatient] = useState<PatientInfo | null>(null);
  const [records, setRecords] = useState<MonitoringRecord[]>([]);
  const [trends, setTrends] = useState<Record<string, TrendData>>({});
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState('');

  // Form state
  const [timeSlot, setTimeSlot] = useState('morning');
  const [glucose, setGlucose] = useState('');
  const [bpSystolic, setBpSystolic] = useState('');
  const [bpDiastolic, setBpDiastolic] = useState('');
  const [spo2, setSpo2] = useState('');

  // Diet state
  const [breakfastDone, setBreakfastDone] = useState(false);
  const [lunchDone, setLunchDone] = useState(false);
  const [snacksDone, setSnacksDone] = useState(false);
  const [dinnerDone, setDinnerDone] = useState(false);

  const toastTimer = useRef<ReturnType<typeof setTimeout>>();

  const showToast = (msg: string) => {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(''), 3000);
  };

  // ── Data Fetching ──────────────────────────────────────────────────────

  const fetchData = useCallback(async () => {
    if (!patientId) return;
    setLoading(true);
    try {
      const res = await getPatientMonitoring(patientId, 7);
      setPatient(res.patient);
      setRecords(res.records || []);
      setTrends(res.trends || {});
      setAlerts(res.alerts || []);

      // Hydrate diet checkboxes from today's latest record
      const today = new Date().toISOString().slice(0, 10);
      const todayRecords = (res.records || []).filter((r: MonitoringRecord) => r.date === today);
      if (todayRecords.length > 0) {
        const latest = todayRecords[todayRecords.length - 1];
        setBreakfastDone(!!latest.breakfast_done);
        setLunchDone(!!latest.lunch_done);
        setSnacksDone(!!latest.snacks_done);
        setDinnerDone(!!latest.dinner_done);
      }
    } catch (e) {
      console.error('Failed to fetch monitoring', e);
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ── Submit Vitals ──────────────────────────────────────────────────────

  const handleSubmitVitals = async () => {
    if (!patientId) return;
    setSaving(true);
    try {
      const payload: any = {
        time_slot: timeSlot,
        breakfast_done: breakfastDone,
        lunch_done: lunchDone,
        snacks_done: snacksDone,
        dinner_done: dinnerDone,
      };
      if (glucose) payload.glucose = parseFloat(glucose);
      if (bpSystolic) payload.bp_systolic = parseFloat(bpSystolic);
      if (bpDiastolic) payload.bp_diastolic = parseFloat(bpDiastolic);
      if (spo2) payload.spo2 = parseFloat(spo2);

      const res = await updatePatientMonitoring(patientId, payload);

      // Update trends/alerts from response
      if (res.trends) setTrends(res.trends);
      if (res.alerts) setAlerts(res.alerts);

      showToast('✅ Vitals saved successfully');
      // Refresh full data
      await fetchData();

      // Clear form
      setGlucose('');
      setBpSystolic('');
      setBpDiastolic('');
      setSpo2('');
    } catch (e: any) {
      console.error('Failed to save vitals', e);
      showToast('❌ Failed to save vitals');
    } finally {
      setSaving(false);
    }
  };

  // ── Update Diet Only ──────────────────────────────────────────────────

  const handleDietUpdate = async (field: string, value: boolean) => {
    if (!patientId) return;

    // Save previous state for rollback
    const prev = { breakfast_done: breakfastDone, lunch_done: lunchDone, snacks_done: snacksDone, dinner_done: dinnerDone };
    const newState = { ...prev, [field]: value };

    // Optimistically update UI immediately
    setBreakfastDone(newState.breakfast_done);
    setLunchDone(newState.lunch_done);
    setSnacksDone(newState.snacks_done);
    setDinnerDone(newState.dinner_done);

    try {
      await updatePatientMonitoring(patientId, {
        time_slot: timeSlot,
        ...newState,
      });
      showToast(value ? '✅ Marked as done' : '↩️ Unmarked');
    } catch (err) {
      console.error('Diet update failed:', err);
      // Rollback on failure
      setBreakfastDone(prev.breakfast_done);
      setLunchDone(prev.lunch_done);
      setSnacksDone(prev.snacks_done);
      setDinnerDone(prev.dinner_done);
      showToast('❌ Failed to update diet');
    }
  };

  // ── Helpers ────────────────────────────────────────────────────────────

  const getMetricValues = (metric: string) =>
    records.filter((r) => (r as any)[metric] != null).map((r) => (r as any)[metric] as number);

  const getSparkColor = (trend: string) => {
    if (trend === 'STRONGLY_INCREASING') return '#ef4444';
    if (trend === 'INCREASING') return '#f59e0b';
    if (trend === 'STABLE') return '#10b981';
    if (trend === 'DECREASING') return '#0ea5e9';
    if (trend === 'STRONGLY_DECREASING') return '#ef4444';
    return '#9ca3af';
  };

  // ── Render ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen pt-28 pb-20 px-4 flex items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
        >
          <Activity className="h-10 w-10 text-purple-500" />
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-28 pb-20 px-4 sm:px-6 lg:px-8">
      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-20 right-6 z-50 bg-white/90 backdrop-blur-lg border border-white/30 rounded-xl shadow-xl px-5 py-3 text-sm font-medium text-gray-700"
          >
            {toast}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <button
            onClick={() => navigate('/admitted-patients')}
            className="flex items-center gap-2 text-gray-500 hover:text-purple-600 transition-colors mb-4 text-sm"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Admitted Patients
          </button>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-800">{patient?.name || 'Patient'}</h1>
              <p className="text-sm text-gray-400 mt-0.5">
                Ward {patient?.ward_number || '—'}
                {patient?.age ? ` · ${patient.age}y` : ''}
                {patient?.sex ? ` · ${patient.sex}` : ''}
                {' · '}Patient #{patient?.patient_id}
              </p>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/60 backdrop-blur border border-white/30 text-gray-600 hover:text-purple-600 shadow-sm text-sm font-medium transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </motion.button>
          </div>
        </motion.div>

        {/* ── Alert Box ─────────────────────────────────────────────── */}
        <AnimatePresence>
          {alerts.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6 space-y-3"
            >
              {alerts.map((alert, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`rounded-xl border p-4 flex items-start gap-3 ${
                    alert.type === 'CRITICAL'
                      ? 'bg-red-50/80 border-red-200 text-red-800'
                      : alert.type === 'WARNING'
                      ? 'bg-amber-50/80 border-amber-200 text-amber-800'
                      : 'bg-blue-50/80 border-blue-200 text-blue-800'
                  }`}
                >
                  <AlertTriangle
                    className={`h-5 w-5 flex-shrink-0 mt-0.5 ${
                      alert.type === 'CRITICAL' ? 'text-red-500' : alert.type === 'WARNING' ? 'text-amber-500' : 'text-blue-500'
                    }`}
                  />
                  <div>
                    <span
                      className={`text-xs font-bold uppercase tracking-wide ${
                        alert.type === 'CRITICAL' ? 'text-red-600' : alert.type === 'WARNING' ? 'text-amber-600' : 'text-blue-600'
                      }`}
                    >
                      {alert.type}
                    </span>
                    <p className="text-sm mt-0.5">{alert.message}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Trend Cards Grid ──────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
        >
          {Object.entries(METRIC_CONFIG).map(([key, cfg]) => {
            const trend = trends[key];
            const trendInfo = TREND_CONFIG[trend?.trend || 'INSUFFICIENT_DATA'];
            const TIcon = trendInfo.icon;
            const MetricIcon = cfg.icon;
            const values = getMetricValues(key);
            const latestVal = values.length > 0 ? values[values.length - 1] : null;
            const sparkColor = getSparkColor(trend?.trend || '');

            return (
              <motion.div
                key={key}
                whileHover={{ y: -2 }}
                className="rounded-2xl bg-white/60 backdrop-blur-lg border border-white/30 shadow-md p-4 relative overflow-hidden"
              >
                {/* Background gradient */}
                <div className={`absolute inset-0 bg-gradient-to-br ${cfg.color} opacity-[0.04]`} />

                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-lg bg-gradient-to-br ${cfg.color} text-white`}>
                        <MetricIcon className="h-3.5 w-3.5" />
                      </div>
                      <span className="text-xs font-medium text-gray-500">{cfg.label}</span>
                    </div>
                    <div className={`flex items-center gap-1 ${trendInfo.color}`}>
                      <TIcon className="h-3.5 w-3.5" />
                      <span className="text-xs font-semibold">{trendInfo.label}</span>
                    </div>
                  </div>

                  {/* Value */}
                  <div className="flex items-baseline gap-1 mb-2">
                    <span className="text-2xl font-bold text-gray-800">
                      {latestVal !== null ? latestVal : '—'}
                    </span>
                    <span className="text-xs text-gray-400">{cfg.unit}</span>
                  </div>

                  {/* Sparkline */}
                  <Sparkline data={values} color={sparkColor} height={40} />

                  {/* Slope info */}
                  {trend && trend.trend !== 'INSUFFICIENT_DATA' && (
                    <div className="mt-2 text-xs text-gray-400">
                      Avg: {trend.average} · Slope: {trend.slope > 0 ? '+' : ''}
                      {trend.slope}
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </motion.div>

        {/* ── Bottom Grid: Diet + Vitals Input ──────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ── Diet Tracker ──────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="rounded-2xl bg-white/60 backdrop-blur-lg border border-white/30 shadow-lg p-6"
          >
            <div className="flex items-center gap-2 mb-5">
              <div className="p-2 rounded-xl bg-gradient-to-br from-green-400 to-emerald-500 text-white">
                <Utensils className="h-5 w-5" />
              </div>
              <h2 className="text-lg font-bold text-gray-800">Diet Tracker</h2>
              <span className="text-xs text-gray-400 ml-auto">Today</span>
            </div>

            <div className="space-y-3">
              {[
                { label: 'Breakfast', field: 'breakfast_done', val: breakfastDone, set: setBreakfastDone, emoji: '🥣' },
                { label: 'Lunch', field: 'lunch_done', val: lunchDone, set: setLunchDone, emoji: '🍛' },
                { label: 'Snacks', field: 'snacks_done', val: snacksDone, set: setSnacksDone, emoji: '🍎' },
                { label: 'Dinner', field: 'dinner_done', val: dinnerDone, set: setDinnerDone, emoji: '🍽️' },
              ].map((item) => (
                <motion.button
                  key={item.field}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    handleDietUpdate(item.field, !item.val);
                  }}
                  className={`w-full flex items-center gap-4 px-4 py-3.5 rounded-xl border transition-all duration-200 ${
                    item.val
                      ? 'bg-emerald-50/80 border-emerald-200 text-emerald-800'
                      : 'bg-white/40 border-gray-200/60 text-gray-600 hover:bg-white/60'
                  }`}
                >
                  <span className="text-xl">{item.emoji}</span>
                  <span className="font-medium flex-1 text-left">{item.label}</span>
                  {item.val ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  ) : (
                    <Circle className="h-5 w-5 text-gray-300" />
                  )}
                </motion.button>
              ))}
            </div>

            {/* Diet completion bar */}
            <div className="mt-5">
              <div className="flex justify-between text-xs text-gray-500 mb-1.5">
                <span>Completion</span>
                <span>
                  {[breakfastDone, lunchDone, snacksDone, dinnerDone].filter(Boolean).length}/4
                </span>
              </div>
              <div className="w-full h-2 bg-gray-200/60 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-emerald-400 to-green-500 rounded-full"
                  initial={{ width: 0 }}
                  animate={{
                    width: `${([breakfastDone, lunchDone, snacksDone, dinnerDone].filter(Boolean).length / 4) * 100}%`,
                  }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          </motion.div>

          {/* ── Vitals Input ──────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="rounded-2xl bg-white/60 backdrop-blur-lg border border-white/30 shadow-lg p-6"
          >
            <div className="flex items-center gap-2 mb-5">
              <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 text-white">
                <Activity className="h-5 w-5" />
              </div>
              <h2 className="text-lg font-bold text-gray-800">Record Vitals</h2>
            </div>

            {/* Time Slot Selector */}
            <div className="flex gap-2 mb-5">
              {TIME_SLOTS.map((slot) => {
                const SlotIcon = slot.icon;
                const active = timeSlot === slot.value;
                return (
                  <motion.button
                    key={slot.value}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setTimeSlot(slot.value)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 border ${
                      active
                        ? `bg-gradient-to-r ${slot.color} text-white border-transparent shadow-md`
                        : 'bg-white/40 border-gray-200/60 text-gray-500 hover:bg-white/60'
                    }`}
                  >
                    <SlotIcon className="h-4 w-4" />
                    {slot.label}
                  </motion.button>
                );
              })}
            </div>

            {/* Input Fields */}
            <div className="grid grid-cols-2 gap-3 mb-5">
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">
                  <Droplets className="h-3 w-3 inline mr-1" />
                  Glucose (mg/dL)
                </label>
                <input
                  id="input-glucose"
                  type="number"
                  value={glucose}
                  onChange={(e) => setGlucose(e.target.value)}
                  placeholder="e.g. 140"
                  className="w-full px-3 py-2.5 rounded-xl bg-white/60 border border-gray-200/60 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50 placeholder-gray-300"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">
                  <Wind className="h-3 w-3 inline mr-1" />
                  SpO2 (%)
                </label>
                <input
                  id="input-spo2"
                  type="number"
                  value={spo2}
                  onChange={(e) => setSpo2(e.target.value)}
                  placeholder="e.g. 98"
                  className="w-full px-3 py-2.5 rounded-xl bg-white/60 border border-gray-200/60 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50 placeholder-gray-300"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">
                  <Heart className="h-3 w-3 inline mr-1" />
                  BP Systolic (mmHg)
                </label>
                <input
                  id="input-bp-systolic"
                  type="number"
                  value={bpSystolic}
                  onChange={(e) => setBpSystolic(e.target.value)}
                  placeholder="e.g. 120"
                  className="w-full px-3 py-2.5 rounded-xl bg-white/60 border border-gray-200/60 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50 placeholder-gray-300"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">
                  <Heart className="h-3 w-3 inline mr-1" />
                  BP Diastolic (mmHg)
                </label>
                <input
                  id="input-bp-diastolic"
                  type="number"
                  value={bpDiastolic}
                  onChange={(e) => setBpDiastolic(e.target.value)}
                  placeholder="e.g. 80"
                  className="w-full px-3 py-2.5 rounded-xl bg-white/60 border border-gray-200/60 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50 placeholder-gray-300"
                />
              </div>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              disabled={saving}
              onClick={handleSubmitVitals}
              className={`w-full py-3 rounded-xl text-white font-semibold text-sm shadow-lg transition-all duration-200 flex items-center justify-center gap-2 ${
                saving
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:shadow-xl'
              }`}
            >
              {saving ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Activity className="h-4 w-4" />
                  Save Vitals
                </>
              )}
            </motion.button>
          </motion.div>
        </div>

        {/* ── Recent Records Table ──────────────────────────────────── */}
        {records.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-8 rounded-2xl bg-white/60 backdrop-blur-lg border border-white/30 shadow-lg overflow-hidden"
          >
            <div className="px-6 py-4 border-b border-gray-100/50">
              <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                <Clock className="h-5 w-5 text-purple-500" />
                Recent Readings
                <span className="text-xs font-normal text-gray-400 ml-2">Last 7 days</span>
              </h2>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50/50">
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Slot</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Glucose</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">BP</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">SpO2</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Diet</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100/50">
                  {[...records].reverse().slice(0, 21).map((rec) => {
                    const dietCount = [rec.breakfast_done, rec.lunch_done, rec.snacks_done, rec.dinner_done].filter(Boolean).length;
                    return (
                      <tr key={rec.id} className="hover:bg-white/40 transition-colors">
                        <td className="px-4 py-3 text-gray-700 font-medium">
                          {new Date(rec.date + 'T00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                            rec.time_slot === 'morning' ? 'bg-amber-100 text-amber-700' :
                            rec.time_slot === 'afternoon' ? 'bg-sky-100 text-sky-700' :
                            'bg-indigo-100 text-indigo-700'
                          }`}>
                            {rec.time_slot === 'morning' ? '☀️' : rec.time_slot === 'afternoon' ? '🌤️' : '🌙'}
                            {rec.time_slot}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          {rec.glucose != null ? (
                            <span className={rec.glucose > 180 ? 'text-red-600 font-semibold' : rec.glucose < 70 ? 'text-amber-600 font-semibold' : 'text-gray-700'}>
                              {rec.glucose}
                            </span>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {rec.bp_systolic != null ? (
                            <span className={rec.bp_systolic > 140 ? 'text-red-600 font-semibold' : 'text-gray-700'}>
                              {rec.bp_systolic}/{rec.bp_diastolic || '—'}
                            </span>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {rec.spo2 != null ? (
                            <span className={rec.spo2 < 95 ? 'text-red-600 font-semibold' : 'text-gray-700'}>
                              {rec.spo2}%
                            </span>
                          ) : <span className="text-gray-300">—</span>}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`text-xs font-medium ${dietCount === 4 ? 'text-emerald-600' : dietCount >= 2 ? 'text-amber-600' : 'text-gray-400'}`}>
                            {dietCount}/4
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
