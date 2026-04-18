import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Heart, AlertTriangle, ShieldCheck, BedDouble, Search, RefreshCw, User, Hospital, Check } from 'lucide-react';
import { getAdmittedPatients } from '../services/api';

interface AdmittedPatient {
  patient_id: number;
  appointment_id: number;
  name: string;
  email: string | null;
  age: number | null;
  sex: string | null;
  ward_number: string | null;
  doctor_id: string | null;
  admitted_at: string | null;
  risk_level: string;
  hospital: string | null;
}

const riskConfig: Record<string, { color: string; bg: string; border: string; icon: any; label: string }> = {
  CRITICAL: {
    color: 'text-red-400',
    bg: 'bg-red-500/15',
    border: 'border-red-500/30',
    icon: AlertTriangle,
    label: 'Critical',
  },
  WARNING: {
    color: 'text-amber-400',
    bg: 'bg-amber-500/15',
    border: 'border-amber-500/30',
    icon: AlertTriangle,
    label: 'Warning',
  },
  LOW: {
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/15',
    border: 'border-emerald-500/30',
    icon: ShieldCheck,
    label: 'Stable',
  },
};

export default function AdmittedPatients() {
  const [patients, setPatients] = useState<AdmittedPatient[]>([]);
  const [hospitals, setHospitals] = useState<string[]>([]);
  const [selectedHospital, setSelectedHospital] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // Get user role for default view
  const userStr = localStorage.getItem('user');
  const currentUser = userStr ? JSON.parse(userStr) : null;
  const isAdmin = currentUser?.role === 'admin';

  const fetchPatients = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await getAdmittedPatients();
      setPatients(res.patients || []);
      setHospitals(res.hospitals || []);
      
      // Auto-select first hospital for non-admins if they have any
      if (!isAdmin && res.hospitals && res.hospitals.length > 0 && selectedHospital === 'ALL') {
        setSelectedHospital(res.hospitals[0]);
      }
    } catch (e: any) {
      console.error('Failed to load admitted patients', e);
      setError('Failed to load admitted patients. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

  const filtered = patients.filter((p) => {
    const matchesSearch = 
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.ward_number || '').toLowerCase().includes(search.toLowerCase());
    
    const matchesHospital = selectedHospital === 'ALL' || p.hospital === selectedHospital;
    
    return matchesSearch && matchesHospital;
  });

  return (
    <div className="min-h-screen pt-28 pb-20 px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-6xl mx-auto mb-8"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-pink-500 bg-clip-text text-transparent">
              Admitted Patients
            </h1>
            <p className="text-gray-500 mt-1">
              {patients.length} patient{patients.length !== 1 ? 's' : ''} currently admitted
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                id="search-admitted"
                type="text"
                placeholder="Search by name or ward..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 pr-4 py-2.5 rounded-xl bg-white/60 backdrop-blur border border-white/30 text-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-purple-400/50 w-64 shadow-sm"
              />
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={fetchPatients}
              className="p-2.5 rounded-xl bg-white/60 backdrop-blur border border-white/30 text-gray-600 hover:text-purple-600 transition-colors shadow-sm"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </motion.button>
          </div>
        </div>
      </motion.div>

      {/* Facility Selection */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-6xl mx-auto mb-10"
      >
        <div className="flex items-center gap-2 mb-4">
          <Hospital className="h-5 w-5 text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-widest">
            {isAdmin ? 'Global Monitoring' : 'Your Medical Facilities'}
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {isAdmin && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedHospital('ALL')}
              className={`p-4 rounded-2xl border transition-all duration-300 text-left relative overflow-hidden ${
                selectedHospital === 'ALL'
                  ? 'bg-blue-600 border-blue-500 shadow-lg shadow-blue-200'
                  : 'bg-white/60 backdrop-blur border-white/30 hover:border-blue-200'
              }`}
            >
              <div className="flex flex-col h-full relative z-10">
                <div className={`p-2 rounded-lg w-fit mb-3 ${selectedHospital === 'ALL' ? 'bg-white/20' : 'bg-blue-50'}`}>
                  <Activity className={`h-5 w-5 ${selectedHospital === 'ALL' ? 'text-white' : 'text-blue-600'}`} />
                </div>
                <h3 className={`font-bold ${selectedHospital === 'ALL' ? 'text-white' : 'text-gray-800'}`}>Global View</h3>
                <p className={`text-xs mt-1 ${selectedHospital === 'ALL' ? 'text-blue-100' : 'text-gray-400'}`}>All Facilities</p>
              </div>
              {selectedHospital === 'ALL' && (
                <div className="absolute top-3 right-3">
                  <Check className="h-4 w-4 text-white" />
                </div>
              )}
            </motion.button>
          )}

          {hospitals.map((hospital) => {
            const isSelected = selectedHospital === hospital;
            const patientCount = patients.filter(p => p.hospital === hospital).length;

            return (
              <motion.button
                key={hospital}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSelectedHospital(hospital)}
                className={`p-4 rounded-2xl border transition-all duration-300 text-left relative overflow-hidden ${
                  isSelected
                    ? 'bg-purple-600 border-purple-500 shadow-lg shadow-purple-200'
                    : 'bg-white/60 backdrop-blur border-white/30 hover:border-purple-200'
                }`}
              >
                <div className="flex flex-col h-full relative z-10">
                  <div className={`p-2 rounded-lg w-fit mb-3 ${isSelected ? 'bg-white/20' : 'bg-purple-50'}`}>
                    <Hospital className={`h-5 w-5 ${isSelected ? 'text-white' : 'text-purple-600'}`} />
                  </div>
                  <h3 className={`font-bold truncate pr-6 ${isSelected ? 'text-white' : 'text-gray-800'}`} title={hospital}>
                    {hospital}
                  </h3>
                  <p className={`text-xs mt-1 ${isSelected ? 'text-purple-100' : 'text-gray-400'}`}>
                    {patientCount} Patient{patientCount !== 1 ? 's' : ''} Admitted
                  </p>
                </div>
                {isSelected && (
                  <div className="absolute top-3 right-3">
                    <Check className="h-4 w-4 text-white" />
                  </div>
                )}
              </motion.button>
            );
          })}
        </div>
      </motion.div>

      {/* Error State */}
      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-6xl mx-auto mb-6">
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-5 py-4 text-sm">
            {error}
          </div>
        </motion.div>
      )}

      {/* Loading Skeleton */}
      {loading ? (
        <div className="max-w-6xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="rounded-2xl bg-white/40 backdrop-blur border border-white/30 p-6 animate-pulse">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-12 w-12 rounded-full bg-gray-200" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4" />
                  <div className="h-3 bg-gray-200 rounded w-1/2" />
                </div>
              </div>
              <div className="space-y-2">
                <div className="h-3 bg-gray-200 rounded w-full" />
                <div className="h-3 bg-gray-200 rounded w-2/3" />
              </div>
            </div>
          ))}
        </div>
      ) : filtered.length === 0 ? (
        /* Empty State */
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-md mx-auto text-center py-20"
        >
          <div className="mx-auto h-20 w-20 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 flex items-center justify-center mb-5">
            <BedDouble className="h-10 w-10 text-purple-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-700 mb-2">
            {search ? 'No matching patients' : 'No admitted patients'}
          </h3>
          <p className="text-gray-400 text-sm">
            {search
              ? 'Try a different search term.'
              : 'Patients marked as "Admitted" by a doctor will appear here.'}
          </p>
        </motion.div>
      ) : (
        /* Patient Cards Grid */
        <div className="max-w-6xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          <AnimatePresence mode="popLayout">
            {filtered.map((patient, idx) => {
              const risk = riskConfig[patient.risk_level] || riskConfig.LOW;
              const RiskIcon = risk.icon;
              const initials = patient.name
                .split(' ')
                .map((w) => w[0])
                .join('')
                .toUpperCase()
                .slice(0, 2);

              return (
                <motion.div
                  key={patient.patient_id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: idx * 0.05 }}
                  className="group relative rounded-2xl bg-white/60 backdrop-blur-lg border border-white/30 shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden cursor-pointer"
                  onClick={() => navigate(`/patient/${patient.patient_id}/monitor`)}
                >
                  {/* Gradient accent bar */}
                  <div
                    className={`absolute top-0 left-0 right-0 h-1 ${
                      patient.risk_level === 'CRITICAL'
                        ? 'bg-gradient-to-r from-red-500 to-rose-400'
                        : patient.risk_level === 'WARNING'
                        ? 'bg-gradient-to-r from-amber-500 to-yellow-400'
                        : 'bg-gradient-to-r from-emerald-500 to-teal-400'
                    }`}
                  />

                  <div className="p-5 pt-6">
                    {/* Top Row: Avatar + Name + Risk Badge */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="h-12 w-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
                          {initials}
                        </div>
                        <div>
                          <h3 className="text-base font-semibold text-gray-800 group-hover:text-purple-700 transition-colors">
                            {patient.name}
                          </h3>
                          <p className="text-xs text-gray-400">
                            ID: {patient.patient_id}
                            {patient.age ? ` · ${patient.age}y` : ''}
                            {patient.sex ? ` · ${patient.sex}` : ''}
                          </p>
                        </div>
                      </div>

                      {/* Risk Badge */}
                      <div className={`flex items-center gap-1 px-2.5 py-1 rounded-full ${risk.bg} ${risk.border} border`}>
                        <RiskIcon className={`h-3.5 w-3.5 ${risk.color}`} />
                        <span className={`text-xs font-semibold ${risk.color}`}>{risk.label}</span>
                      </div>
                    </div>

                    {/* Info Row */}
                    <div className="flex items-center gap-4 mb-4 text-sm text-gray-500">
                      <div className="flex items-center gap-1.5">
                        <BedDouble className="h-3.5 w-3.5" />
                        <span>Ward {patient.ward_number || '—'} {patient.hospital ? `(${patient.hospital})` : ''}</span>
                      </div>
                      {patient.admitted_at && (
                        <div className="flex items-center gap-1.5">
                          <Activity className="h-3.5 w-3.5" />
                          <span>
                            Since{' '}
                            {new Date(patient.admitted_at).toLocaleDateString('en-IN', {
                              day: 'numeric',
                              month: 'short',
                            })}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Monitor Button */}
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      className="w-full py-2.5 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm font-semibold shadow-md hover:shadow-lg transition-shadow flex items-center justify-center gap-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/patient/${patient.patient_id}/monitor`);
                      }}
                    >
                      <Heart className="h-4 w-4" />
                      Monitor Patient
                    </motion.button>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
