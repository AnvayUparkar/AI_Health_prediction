import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, AlertCircle, CheckCircle2, Loader2,
  RefreshCcw, Bell, User, Home as RoomIcon, Hand, Volume2, Map as MapIcon, LocateFixed, XCircle
} from 'lucide-react';
import GlassCard from './GlassCard';
import { getAlerts, updateAlertStatus } from '../services/api';
import { io, Socket } from 'socket.io-client';

interface Alert {
  id: number | string;
  patient_id: string;
  room_number: string;
  status: 'SAFE' | 'WARNING' | 'CRITICAL';
  confidence: string;
  reason: string;
  detected_issues: string[];
  recommended_action: string;
  alert: boolean;
  acknowledged: boolean;
  resolved: boolean;
  created_at: string;
  latitude?: number;
  longitude?: number;
  location_type?: 'WARD' | 'REMOTE';
  nearest_hospital?: string;
  distance_km?: number;
  notified_doctors?: (string | number)[]; // IDs of staff to notify
}

// ── Normalise incoming alert so missing fields never crash the UI ─────────────
const normaliseAlert = (a: Partial<Alert> & { notified_doctor_ids?: string | (string|number)[] }): Alert => {
  // Parse notified_doctors - backend may send it as 'notified_doctors' (parsed array from SQL to_dict)
  // OR as 'notified_doctor_ids' (raw JSON string from Mongo dict)
  let notifiedDoctors: (string | number)[] = [];
  if (Array.isArray(a.notified_doctors) && a.notified_doctors.length > 0) {
    notifiedDoctors = a.notified_doctors;
  } else if (a.notified_doctor_ids) {
    try {
      const parsed = typeof a.notified_doctor_ids === 'string'
        ? JSON.parse(a.notified_doctor_ids)
        : a.notified_doctor_ids;
      if (Array.isArray(parsed)) notifiedDoctors = parsed;
    } catch { /* ignore parse errors */ }
  }

  return {
    id: a.id ?? `tmp-${Date.now()}-${Math.random()}`,
    patient_id: a.patient_id ?? 'UNKNOWN',
    room_number: a.room_number ?? 'N/A',
    status: a.status ?? 'CRITICAL',
    confidence: a.confidence ?? 'HIGH',
    reason: a.reason ?? 'Emergency alert',
    detected_issues: Array.isArray(a.detected_issues) ? a.detected_issues : [],
    recommended_action: a.recommended_action ?? 'Respond immediately',
    alert: a.alert ?? true,
    acknowledged: a.acknowledged ?? false,
    resolved: a.resolved ?? false,
    created_at: a.created_at ?? new Date().toISOString(),
    latitude: a.latitude,
    longitude: a.longitude,
    location_type: a.location_type ?? 'WARD',
    nearest_hospital: a.nearest_hospital,
    distance_km: a.distance_km,
    notified_doctors: notifiedDoctors,
  };
};

// ── Simple beep using Web Audio API (no external assets needed) ───────────────
const playAlertBeep = () => {
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    [0, 0.18, 0.36].forEach(offset => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.4, ctx.currentTime + offset);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + offset + 0.15);
      osc.start(ctx.currentTime + offset);
      osc.stop(ctx.currentTime + offset + 0.15);
    });
  } catch { /* AudioContext blocked — silently skip */ }
};

// ── Toast banner ──────────────────────────────────────────────────────────────
interface ToastProps { message: string; sub: string; isGesture: boolean; onDismiss: () => void; }
const AlertToast: React.FC<ToastProps> = ({ message, sub, isGesture, onDismiss }) => (
  <motion.div
    initial={{ opacity: 0, y: -60, x: '-50%' }}
    animate={{ opacity: 1, y: 0, x: '-50%' }}
    exit={{ opacity: 0, y: -60, x: '-50%' }}
    className="fixed top-6 left-1/2 z-[9999] bg-red-600 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-4 cursor-pointer min-w-[320px]"
    onClick={onDismiss}
  >
    <div className="p-2 bg-white/20 rounded-xl animate-bounce">
      {isGesture
        ? <Hand className="h-6 w-6 text-white" />
        : <Bell className="h-6 w-6 text-white" />
      }
    </div>
    <div className="flex-1">
      <p className="font-black text-sm uppercase tracking-wide">🚨 {message}</p>
      <p className="text-xs text-red-200 font-medium">{sub}</p>
    </div>
    <span className="text-xs text-red-300 font-bold">TAP TO DISMISS</span>
  </motion.div>
);

// ─────────────────────────────────────────────────────────────────────────────

const AlertMonitoringCard: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState<{ message: string; sub: string; isGesture: boolean } | null>(null);
  
  // Map Modal State
  const [selectedLocation, setSelectedLocation] = useState<{ lat: number; lon: number; name: string } | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback((message: string, sub: string, isGesture: boolean) => {
    playAlertBeep();
    setToast({ message, sub, isGesture });
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 7000);
  }, []);

  const fetchAlerts = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      // Get current logged-in user's ID for filtering
      const userStr = localStorage.getItem('user');
      const currentUser = userStr ? JSON.parse(userStr) : null;
      const myId = currentUser?.id ? String(currentUser.id) : null;

      const data = await getAlerts({ alert: true });
      const active: Alert[] = data
        .map(normaliseAlert)
        .filter((a: Alert) => {
          if (a.resolved) return false;
          // If no notified_doctors list, show to all staff (backward compat)
          if (!a.notified_doctors || a.notified_doctors.length === 0) return true;
          // Only show if this doctor/nurse is in the notified list
          if (!myId) return false;
          return a.notified_doctors.some((id) => String(id) === myId);
        })
        .sort((a: Alert, b: Alert) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
      setAlerts(active);
    } catch (err) {
      console.error('Failed to fetch alerts', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // ── Socket setup ──────────────────────────────────────────────────────────
  useEffect(() => {
    fetchAlerts();

    const socket = io('http://localhost:5000', {
      transports: ['websocket'],
      reconnectionAttempts: 5,
    });
    socketRef.current = socket;

    socket.on('new_alert', (raw: Partial<Alert>) => {
      console.log('[AlertMonitoringCard] new_alert received:', raw);
      const incoming = normaliseAlert(raw);

      // Only show active alerts
      if (!incoming.alert || incoming.resolved) return;

      // Filter: only show if this doctor/nurse is in notified_doctors
      const userStr = localStorage.getItem('user');
      const currentUser = userStr ? JSON.parse(userStr) : null;
      const myId = currentUser?.id ? String(currentUser.id) : null;
      const notified = incoming.notified_doctors ?? [];
      if (notified.length > 0 && myId && !notified.some((id) => String(id) === myId)) {
        console.log('[AlertMonitoringCard] Skipping alert — not in notified list for this doctor.');
        return;
      }

      setAlerts(prev => {
        // Deduplicate by id
        if (prev.some(a => a.id === incoming.id)) return prev;
        return [incoming, ...prev].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
      });

      // Determine toast wording
      const isGesture =
        incoming.reason.includes('GESTURE') ||
        incoming.reason.includes('FIST') ||
        incoming.reason.includes('CLENCH');

      const toastMessage = isGesture
        ? 'Gesture SOS Triggered!'
        : incoming.status === 'CRITICAL'
          ? 'Critical Alert!'
          : 'Warning Alert!';

      const toastSub = `${incoming.patient_id} — Room ${incoming.room_number}: ${incoming.reason}`;
      showToast(toastMessage, toastSub, isGesture);
    });

    // Real-time sync: when any staff resolves/acknowledges an alert
    socket.on('alert_updated', (data: { id: string | number; acknowledged?: boolean; resolved?: boolean }) => {
      console.log('[AlertMonitoringCard] alert_updated received:', data);
      setAlerts(prev => {
        if (data.resolved) {
          // Remove resolved alerts immediately
          return prev.filter(a => String(a.id) !== String(data.id));
        }
        if (data.acknowledged) {
          // Mark as acknowledged
          return prev.map(a =>
            String(a.id) === String(data.id) ? { ...a, acknowledged: true } : a
          );
        }
        return prev;
      });
    });

    // Polling fallback every 15s for edge cases
    const interval = setInterval(() => fetchAlerts(true), 15_000);

    return () => {
      socket.off('new_alert');
      socket.off('alert_updated');
      socket.disconnect();
      clearInterval(interval);
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, [fetchAlerts, showToast]);

  const handleAcknowledge = async (id: number | string) => {
    try {
      await updateAlertStatus(id, true);
      setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a));
    } catch (err) {
      console.error('Failed to acknowledge alert', err);
    }
  };

  const handleResolve = async (id: number | string) => {
    try {
      await updateAlertStatus(id, undefined, true);
      setAlerts(prev => prev.filter(a => a.id !== id));
    } catch (err) {
      console.error('Failed to resolve alert', err);
    }
  };

  const criticalCount = alerts.filter(a => a.status === 'CRITICAL').length;
  const warningCount = alerts.filter(a => a.status === 'WARNING').length;
  const gestureCount = alerts.filter(a =>
    a.reason.includes('GESTURE') || a.reason.includes('FIST')
  ).length;

  return (
    <>
      {/* ── Toast notification ── */}
      <AnimatePresence>
        {toast && (
          <AlertToast
            key="toast"
            message={toast.message}
            sub={toast.sub}
            isGesture={toast.isGesture}
            onDismiss={() => setToast(null)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {selectedLocation && (
          <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-md p-4">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="bg-white rounded-[2rem] p-8 max-w-4xl w-full shadow-2xl relative overflow-hidden"
            >
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h2 className="text-3xl font-black text-gray-800 flex items-center gap-3">
                    <LocateFixed className="text-red-500 h-8 w-8" /> LIVE TRACE: {selectedLocation.name}
                  </h2>
                  <p className="text-xs font-black text-gray-400 uppercase tracking-widest mt-1">
                    SOS Geolocation Tracing Active
                  </p>
                </div>
                <button 
                  onClick={() => setSelectedLocation(null)}
                  className="p-3 hover:bg-gray-100 rounded-2xl transition-all"
                >
                  <XCircle className="w-8 h-8 text-gray-400" />
                </button>
              </div>

              {/* Map Container - We will use the standalone MapModal logic here */}
              <div className="aspect-video bg-gray-50 rounded-3xl overflow-hidden border-2 border-gray-100 shadow-inner relative">
                 <iframe 
                    width="100%" 
                    height="100%" 
                    frameBorder="0" 
                    scrolling="no" 
                    marginHeight={0} 
                    marginWidth={0} 
                    title="SOS Location"
                    src={`https://www.openstreetmap.org/export/embed.html?bbox=${selectedLocation.lon-0.01}%2C${selectedLocation.lat-0.01}%2C${selectedLocation.lon+0.01}%2C${selectedLocation.lat+0.01}&layer=mapnik&marker=${selectedLocation.lat}%2C${selectedLocation.lon}`}
                 />
              </div>

              <div className="mt-8 flex flex-col md:flex-row gap-6 items-center">
                <div className="flex-1">
                   <div className="bg-red-50 p-4 rounded-2xl border-2 border-red-100 italic text-sm text-red-700 font-bold mb-4">
                     "Visualizing real-time coordinate feed. Nearest medical facility notified."
                   </div>
                   <div className="flex gap-4">
                      <div className="flex-1 bg-gray-50 p-4 rounded-2xl border border-gray-100">
                         <p className="text-[10px] font-black text-gray-400 uppercase mb-1">LATITUDE</p>
                         <p className="font-mono font-bold text-gray-700">{selectedLocation.lat.toFixed(6)}</p>
                      </div>
                      <div className="flex-1 bg-gray-50 p-4 rounded-2xl border border-gray-100">
                         <p className="text-[10px] font-black text-gray-400 uppercase mb-1">LONGITUDE</p>
                         <p className="font-mono font-bold text-gray-700">{selectedLocation.lon.toFixed(6)}</p>
                      </div>
                   </div>
                </div>
                <button 
                  onClick={() => setSelectedLocation(null)}
                  className="w-full md:w-auto px-12 py-5 bg-gray-900 text-white rounded-2xl font-black uppercase tracking-widest hover:bg-black transition-all shadow-xl hover:shadow-2xl border-b-4 border-black"
                >
                  Terminate Trace
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <GlassCard
        className="p-8 group overflow-hidden relative h-full flex flex-col hover:shadow-[0_0_30px_rgba(239,68,68,0.2)]"
        delay={0.8}
      >
        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
          <Shield className={`h-24 w-24 ${criticalCount > 0 ? 'text-red-500' : 'text-green-500'} rotate-12`} />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <motion.div
              className={`p-4 rounded-2xl shadow-lg ${criticalCount > 0
                  ? 'bg-gradient-to-r from-red-500 to-rose-600 animate-pulse'
                  : warningCount > 0
                    ? 'bg-gradient-to-r from-amber-500 to-orange-600'
                    : 'bg-gradient-to-r from-green-500 to-emerald-600'
                }`}
              whileHover={{ scale: 1.1 }}
            >
              {criticalCount > 0
                ? <AlertCircle className="h-8 w-8 text-white" />
                : <Shield className="h-8 w-8 text-white" />
              }
            </motion.div>
            <div>
              <h3 className="text-2xl font-bold text-gray-800 group-hover:text-red-500 group-hover:[text-shadow:0_0_12px_rgba(239,68,68,0.8)] transition-all duration-300">Ward Monitoring</h3>
              <p className="text-[10px] font-black uppercase tracking-widest text-gray-400">
                Real-time Patient Safety
              </p>
            </div>
          </div>
          <button
            onClick={() => fetchAlerts(true)}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            disabled={refreshing}
          >
            <RefreshCcw className={`h-4 w-4 text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Summary badges */}
        {(criticalCount > 0 || warningCount > 0 || gestureCount > 0) && (
          <div className="flex gap-2 mb-4">
            {criticalCount > 0 && (
              <div className="flex-1 bg-red-100 text-red-700 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase text-center">
                {criticalCount} Critical
              </div>
            )}
            {warningCount > 0 && (
              <div className="flex-1 bg-amber-100 text-amber-700 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase text-center">
                {warningCount} Warning
              </div>
            )}
            {gestureCount > 0 && (
              <div className="flex-1 bg-purple-100 text-purple-700 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase text-center flex items-center justify-center gap-1">
                <Hand className="h-3 w-3" /> {gestureCount} Gesture SOS
              </div>
            )}
          </div>
        )}

        {/* Alert list */}
        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex-grow flex flex-col items-center justify-center py-8"
            >
              <Loader2 className="h-10 w-10 text-blue-500 animate-spin mb-4" />
              <p className="text-gray-500 font-medium">Connecting to Ward...</p>
            </motion.div>
          ) : alerts.length === 0 ? (
            <motion.div
              key="safe"
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              className="flex-grow flex flex-col items-center justify-center py-8 text-center"
            >
              <div className="p-6 bg-green-50 rounded-full mb-4">
                <CheckCircle2 className="h-12 w-12 text-green-500" />
              </div>
              <h4 className="text-lg font-bold text-green-800">System Healthy</h4>
              <p className="text-sm text-gray-500 max-w-[200px]">
                No active critical alerts or warnings detected in the ward.
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="alerts"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="flex-grow"
            >
              <div className="max-h-[340px] overflow-y-auto pr-2 space-y-3 custom-scrollbar">
                {alerts.map(alert => {
                  const isGesture =
                    alert.reason.includes('GESTURE') ||
                    alert.reason.includes('FIST') ||
                    alert.reason.includes('CLENCH');

                  return (
                    <motion.div
                      key={alert.id}
                      layout
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      className={`p-4 rounded-2xl border-l-4 shadow-sm bg-white/50 backdrop-blur-sm ${isGesture
                          ? 'border-purple-500'
                          : alert.status === 'CRITICAL'
                            ? 'border-red-500'
                            : 'border-amber-500'
                        }`}
                    >
                      {/* Alert header */}
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center space-x-2">
                          <div className={`p-1.5 rounded-lg ${isGesture ? 'bg-purple-50'
                              : alert.status === 'CRITICAL' ? 'bg-red-50' : 'bg-amber-50'
                            }`}>
                            {isGesture
                              ? <Hand className="h-3.5 w-3.5 text-purple-600" />
                              : alert.status === 'CRITICAL'
                                ? <Bell className={`h-3.5 w-3.5 ${alert.acknowledged ? 'text-gray-400' : 'text-red-600 animate-bounce'}`} />
                                : <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
                            }
                          </div>
                          <span className={`text-[11px] font-bold ${isGesture ? 'text-purple-700'
                              : alert.status === 'CRITICAL' ? 'text-red-700' : 'text-amber-700'
                            }`}>
                            {isGesture ? 'GESTURE SOS' : alert.status}
                          </span>
                          {alert.acknowledged && (
                            <span className="text-[9px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full font-bold">
                              ACK'd
                            </span>
                          )}
                        </div>
                        <span className="text-[10px] text-gray-400 font-medium">
                          {new Date(alert.created_at).toLocaleTimeString([], {
                            hour: '2-digit', minute: '2-digit'
                          })}
                        </span>
                      </div>

                      <h5 className="text-sm font-bold text-gray-800 mb-1">{alert.reason}</h5>

                      {/* Patient + room info */}
                      <div className="flex flex-col gap-2 mb-3">
                        <div className="flex items-center space-x-4 text-[10px] text-gray-500 font-semibold">
                          <span className="flex items-center">
                            <User className="h-3 w-3 mr-1 opacity-50" /> {alert.patient_id}
                          </span>
                          <span className="flex items-center">
                            <RoomIcon className="h-3 w-3 mr-1 opacity-50" /> {alert.location_type === 'WARD' ? 'Ward' : 'Patient'} {alert.room_number}
                          </span>
                        </div>
                        
                        {alert.location_type === 'REMOTE' && alert.nearest_hospital && (
                          <div className="bg-amber-50 p-2 rounded-lg border border-amber-100">
                             <p className="text-[10px] font-black text-amber-800 uppercase flex items-center gap-1">
                               <MapIcon className="w-3 h-3" /> NEAREST HOSPITAL: {alert.nearest_hospital}
                             </p>
                             <p className="text-[9px] font-bold text-amber-600">
                               Distance: {alert.distance_km} km (Precise Haversine Trace)
                             </p>
                             <button 
                               onClick={() => setSelectedLocation({ lat: alert.latitude!, lon: alert.longitude!, name: alert.patient_id })}
                               className="mt-2 w-full py-1 bg-amber-600 text-white rounded-md text-[9px] font-black uppercase tracking-widest hover:bg-amber-700 transition"
                             >
                               Detect Exact Coordinates
                             </button>
                          </div>
                        )}
                      </div>

                      {/* Recommended action */}
                      <p className="text-[10px] text-gray-500 italic mb-3">
                        → {alert.recommended_action}
                      </p>

                      {/* Action buttons */}
                      <div className="flex gap-2">
                        {!alert.acknowledged ? (
                          <button
                            onClick={() => handleAcknowledge(alert.id)}
                            className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold text-white transition-all shadow-md ${isGesture
                                ? 'bg-purple-500 hover:bg-purple-600'
                                : alert.status === 'CRITICAL'
                                  ? 'bg-red-500 hover:bg-red-600'
                                  : 'bg-amber-500 hover:bg-amber-600'
                              }`}
                          >
                            Acknowledge
                          </button>
                        ) : (
                          <button
                            onClick={() => handleResolve(alert.id)}
                            className="flex-1 py-1.5 rounded-lg text-[10px] font-bold bg-green-500 text-white hover:bg-green-600 transition-all shadow-md"
                          >
                            Resolve Case
                          </button>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer */}
        <div className="mt-6 pt-6 border-t border-gray-100 flex items-center justify-between">
          <div className="flex -space-x-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="w-8 h-8 rounded-full border-2 border-white bg-blue-100 flex items-center justify-center overflow-hidden">
                <img src={`https://i.pravatar.cc/100?img=${i + 10}`} alt="staff" className="w-full h-full object-cover" />
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Volume2 className="h-3 w-3 text-gray-400" />
            <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
              3 Staff Online · Alerts Active
            </p>
          </div>
        </div>
      </GlassCard>
    </>
  );
};

export default AlertMonitoringCard;