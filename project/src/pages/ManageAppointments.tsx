import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Calendar as CalendarIcon, 
  Clock, 
  CheckCircle, 
  XCircle, 
  CalendarClock,
  User,
  Building,
  Loader2,
  Check,
  X,
  Info,
  ChevronLeft,
  Search,
  ClipboardList
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import GlassCard from '../components/GlassCard';
import AnimatedBackground from '../components/AnimatedBackground';
import toast from 'react-hot-toast';
import { 
  getDoctorAppointments, 
  approveAppointment, 
  rejectAppointment, 
  updateAppointmentClinicalStatus,
  deleteAppointment,
  assignWard
} from '../services/api';

const ManageAppointments = () => {
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Reject Modal State
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectingApptId, setRejectingApptId] = useState<string | null>(null);
  const [dates, setDates] = useState(['', '', '']);
  const [times, setTimes] = useState(['', '', '']);
  const [isRejecting, setIsRejecting] = useState(false);

  // Patient Details Modal State
  const [selectedAppt, setSelectedAppt] = useState<any | null>(null);

  // Ward Assignment State
  const [wardInputs, setWardInputs] = useState<{[key: string]: string}>({});
  const [isAssigningWard, setIsAssigningWard] = useState<string | null>(null);

  // Accordion State
  const [expandedApptId, setExpandedApptId] = useState<string | null>(null);

  const userString = localStorage.getItem('user');
  const currentUser = userString ? JSON.parse(userString) : null;

  useEffect(() => {
    fetchAppointments();
  }, []);

  const fetchAppointments = async () => {
    if (!currentUser?.id) return;
    try {
      setLoading(true);
      const res = await getDoctorAppointments(currentUser.id);
      setAppointments(res.appointments || []);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load appointments');
    } finally {
      setLoading(false);
    }
  };

  const filteredAppointments = appointments.filter(appt => 
    (appt.patient_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (appt.ward_number || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const pendingAppointments = filteredAppointments.filter(a => a.status === 'PENDING' || a.status === 'pending');
  const activeAppointments = filteredAppointments.filter(a => a.status === 'APPROVED' || a.status === 'confirmed');

  const handleApprove = async (id: string | number) => {
    try {
      await approveAppointment(id);
      toast.success('Appointment approved!');
      fetchAppointments();
    } catch (err) {
      toast.error('Failed to approve appointment');
    }
  };

  const handleOpenReject = (id: string | number) => {
    setRejectingApptId(id.toString());
    setShowRejectModal(true);
  };

  const handleDelete = async (id: string | number) => {
    if (!window.confirm("Are you sure you want to permanently delete this appointment?")) return;
    try {
      await deleteAppointment(id);
      toast.success('Appointment permanently deleted');
      fetchAppointments();
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed to delete appointment');
    }
  };

  const handleRejectSubmit = async () => {
    if (!rejectingApptId) return;
    if (dates.some(d => !d)) {
      toast.error('Please select exactly 3 alternative dates.');
      return;
    }
    
    setIsRejecting(true);
    try {
      await rejectAppointment(rejectingApptId, dates, times.filter(t => t));
      toast.success('Appointment rejected and alternatives sent!');
      setShowRejectModal(false);
      setDates(['', '', '']);
      setTimes(['', '', '']);
      fetchAppointments();
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed to reject appointment');
    } finally {
      setIsRejecting(false);
    }
  };

  const handleToggleStatus = async (id: string | number, isChecked: boolean, isAdmitted: boolean) => {
    try {
      await updateAppointmentClinicalStatus(id, isChecked, isAdmitted);
      toast.success('Clinical status updated');
      fetchAppointments();
    } catch (err) {
      toast.error('Failed to update status');
    }
  };

  const handleAssignWard = async (id: string | number) => {
    const ward = wardInputs[id];
    if (!ward) {
      toast.error('Please enter a ward number');
      return;
    }

    setIsAssigningWard(id.toString());
    try {
      await assignWard(id, ward);
      toast.success(`Patient assigned to Ward ${ward}`);
      fetchAppointments();
      setWardInputs(prev => ({ ...prev, [id]: '' }));
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed to assign ward');
    } finally {
      setIsAssigningWard(null);
    }
  };

  const updateDate = (index: number, val: string) => {
    const newDates = [...dates];
    newDates[index] = val;
    setDates(newDates);
  };

  const updateTime = (index: number, val: string) => {
    const newTimes = [...times];
    newTimes[index] = val;
    setTimes(newTimes);
  };

  return (
    <div className="relative min-h-screen">
      <AnimatedBackground />
      
      <div className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-12 gap-6">
            <div className="flex items-center gap-4">
              <motion.button
                whileHover={{ scale: 1.1, x: -5 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => navigate('/')}
                className="p-3 bg-white/50 backdrop-blur-md rounded-2xl shadow-lg border border-white/50 hover:bg-white transition-all group"
              >
                <ChevronLeft className="h-6 w-6 text-blue-600" />
              </motion.button>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  Appointment Management
                </h1>
                <p className="text-gray-500 font-medium flex items-center mt-1">
                  <ClipboardList className="w-4 h-4 mr-1.5 text-blue-500" />
                  Clinical Workflow Dashboard
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="relative group">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
                <input
                  type="text"
                  placeholder="Search patients or wards..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-12 pr-6 py-3 bg-white/50 backdrop-blur-md border border-white shadow-xl rounded-2xl w-full md:w-80 outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
                />
              </div>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Waitlist Section */}
              <div className="lg:col-span-4 space-y-6">
                <div className="flex items-center justify-between px-2">
                  <h3 className="text-xl font-bold text-gray-800 flex items-center">
                    <Clock className="w-5 h-5 mr-2 text-amber-500" /> Waitlist / Pending
                  </h3>
                  <span className="px-2.5 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-bold">
                    {pendingAppointments.length}
                  </span>
                </div>

                {pendingAppointments.length === 0 ? (
                  <GlassCard className="p-8 text-center bg-white/30">
                    <p className="text-gray-400 italic">No pending requests found.</p>
                  </GlassCard>
                ) : (
                  <div className="space-y-4">
                    {pendingAppointments.map((appt, index) => (
                      <motion.div
                        key={appt.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                      >
                        <GlassCard className="p-5 hover:shadow-xl transition-all border-l-4 border-l-amber-500">
                          <div className="flex justify-between items-start mb-4">
                            <div className="cursor-pointer group" onClick={() => setSelectedAppt(appt)}>
                              <h4 className="font-bold text-gray-800 group-hover:text-amber-600 transition-colors flex items-center">
                                <User className="w-4 h-4 mr-2 text-gray-400" /> {appt.patient_name || 'Patient'}
                                <Info className="w-4 h-4 ml-2 opacity-0 group-hover:opacity-100 text-blue-500 transition-opacity" />
                              </h4>
                              <div className="text-xs text-gray-500 mt-1 flex flex-col gap-1">
                                <span className="flex items-center"><CalendarIcon className="w-3 h-3 mr-1" /> {appt.requested_date || appt.date || 'TBD'}</span>
                                <span className="flex items-center"><Clock className="w-3 h-3 mr-1" /> {appt.requested_time || appt.time || 'TBD'}</span>
                              </div>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-1 gap-2">
                            <motion.button 
                              whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                              onClick={() => handleApprove(appt.id)}
                              className="w-full py-2.5 bg-green-500 text-white rounded-xl text-sm font-bold shadow-sm hover:bg-green-600 transition flex items-center justify-center"
                            >
                              <Check className="w-4 h-4 mr-1" /> Approve
                            </motion.button>
                            <div className="grid grid-cols-2 gap-2">
                              <motion.button 
                                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                onClick={() => handleOpenReject(appt.id)}
                                className="py-2.5 bg-amber-500 text-white rounded-xl text-xs font-bold shadow-sm hover:bg-amber-600 transition flex items-center justify-center"
                              >
                                <CalendarClock className="w-3 h-3 mr-1" /> Reschedule
                              </motion.button>
                              <motion.button 
                                whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                                onClick={() => handleDelete(appt.id)}
                                className="py-2.5 bg-red-500 text-white rounded-xl text-xs font-bold shadow-sm hover:bg-red-600 transition flex items-center justify-center"
                              >
                                <X className="w-3 h-3 mr-1" /> Delete
                              </motion.button>
                            </div>
                          </div>
                        </GlassCard>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>

              {/* Active Appointments Section */}
              <div className="lg:col-span-8 space-y-6">
                <div className="flex items-center justify-between px-2">
                  <h3 className="text-xl font-bold text-gray-800 flex items-center">
                    <CheckCircle className="w-5 h-5 mr-2 text-green-500" /> Active Appointments
                  </h3>
                  <span className="px-2.5 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">
                    {activeAppointments.length}
                  </span>
                </div>

                {activeAppointments.length === 0 ? (
                  <GlassCard className="p-12 text-center bg-white/30">
                    <div className="bg-gray-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                      <CalendarIcon className="w-8 h-8 text-gray-400" />
                    </div>
                    <p className="text-gray-500 font-medium">No approved appointments scheduled.</p>
                  </GlassCard>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {activeAppointments.map((appt, index) => {
                      const isChecked = appt.isChecked || false;
                      const isAdmitted = appt.isAdmitted || false;
                      const isExpanded = expandedApptId === appt.id;

                      return (
                        <motion.div
                          key={appt.id}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.1 }}
                        >
                          <GlassCard className={`p-6 hover:shadow-xl transition-all border-l-4 ${isAdmitted ? 'border-l-blue-500 bg-blue-50/20' : 'border-l-green-500 bg-white/50'}`}>
                            <div className="flex justify-between items-start mb-6">
                              <div 
                                className="cursor-pointer group flex-1" 
                                onClick={() => setExpandedApptId(expandedApptId === appt.id ? null : appt.id)}
                              >
                                <h4 className="text-xl font-bold text-gray-800 flex items-center group-hover:text-blue-600 transition-colors">
                                  {appt.patient_name || 'Patient'}
                                  <button 
                                    onClick={(e) => { e.stopPropagation(); setSelectedAppt(appt); }}
                                    className="ml-2 p-1 hover:bg-white/50 rounded-full transition-all"
                                  >
                                    <Info className="w-4 h-4 text-blue-500" />
                                  </button>
                                </h4>
                                <p className="text-sm text-blue-600 font-semibold mt-1">
                                  <CalendarIcon className="w-3.5 h-3.5 inline mr-1" />
                                  {appt.requested_date || appt.date} @ {appt.requested_time || appt.time}
                                </p>
                              </div>
                              <div className="flex flex-col items-end gap-2">
                                <span className="px-3 py-1 bg-green-100/50 text-green-700 text-[10px] font-black rounded-full border border-green-200">
                                  CONFIRMED
                                </span>
                                <button 
                                  onClick={() => handleDelete(appt.id)}
                                  className="px-3 py-1 bg-red-500 text-white rounded-full text-[10px] font-bold flex items-center hover:bg-red-600 transition shadow-sm"
                                >
                                  <X className="w-3 h-3 mr-1" /> DELETE
                                </button>
                              </div>
                            </div>

                            {/* Management Actions - Only show if expanded */}
                            <AnimatePresence>
                              {isExpanded && (
                                <motion.div 
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  className="space-y-4 overflow-hidden"
                                >
                                  <div className="flex items-center justify-between p-3 bg-white/60 rounded-xl border border-white/80 shadow-sm">
                                    <div className="flex items-center text-xs font-bold text-gray-600 uppercase">
                                      <CheckCircle className={`w-4 h-4 mr-2 ${isChecked ? 'text-green-500' : 'text-gray-400'}`} /> 
                                      Verified
                                    </div>
                                    <button 
                                      onClick={() => handleToggleStatus(appt.id, !isChecked, isAdmitted && !isChecked ? false : isAdmitted)}
                                      className={`w-10 h-5 rounded-full p-1 transition-colors duration-300 ${isChecked ? 'bg-green-500' : 'bg-gray-300'}`}
                                    >
                                      <motion.div 
                                        className="bg-white w-3 h-3 rounded-full shadow-sm"
                                        animate={{ x: isChecked ? 20 : 0 }}
                                      />
                                    </button>
                                  </div>

                                  <div className={`flex items-center justify-between p-3 bg-white/60 rounded-xl border border-white/80 shadow-sm transition-opacity ${!isChecked ? 'opacity-40 pointer-events-none' : ''}`}>
                                    <div className="flex items-center text-xs font-bold text-gray-600 uppercase">
                                      <Building className={`w-4 h-4 mr-2 ${isAdmitted ? 'text-blue-500' : 'text-gray-400'}`} /> 
                                      Admitted
                                    </div>
                                    <button 
                                      onClick={() => handleToggleStatus(appt.id, isChecked, !isAdmitted)}
                                      disabled={!isChecked}
                                      className={`w-10 h-5 rounded-full p-1 transition-colors duration-300 ${isAdmitted ? 'bg-blue-500' : 'bg-gray-300'}`}
                                    >
                                      <motion.div 
                                        className="bg-white w-3 h-3 rounded-full shadow-sm"
                                        animate={{ x: isAdmitted ? 20 : 0 }}
                                      />
                                    </button>
                                  </div>

                                  <AnimatePresence>
                                    {isAdmitted && (
                                      <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="pt-2 overflow-hidden"
                                      >
                                        {appt.ward_number ? (
                                          <div className="mb-2 text-[10px] font-black text-blue-600 flex items-center bg-blue-100/50 px-2.5 py-1 rounded-full w-fit">
                                            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mr-1.5 animate-pulse" />
                                            CURRENT WARD: {appt.ward_number}
                                          </div>
                                        ) : (
                                          <div className="mb-2 text-[10px] font-black text-amber-600 flex items-center bg-amber-100/50 px-2.5 py-1 rounded-full w-fit">
                                            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5" />
                                            WARD: Not Assigned
                                          </div>
                                        )}
                                        <div className="flex gap-2">
                                          <div className="relative flex-1">
                                            <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                                            <input 
                                              type="text"
                                              placeholder="Update Ward..."
                                              value={wardInputs[appt.id] || ''}
                                              onChange={(e) => setWardInputs(prev => ({ ...prev, [appt.id]: e.target.value }))}
                                              className="w-full pl-9 pr-4 py-2 bg-white/80 border border-blue-200 rounded-xl text-xs font-semibold focus:ring-2 focus:ring-blue-500 outline-none"
                                            />
                                          </div>
                                          <motion.button 
                                            whileHover={{ scale: 1.05 }}
                                            onClick={() => handleAssignWard(appt.id)}
                                            disabled={isAssigningWard === appt.id.toString()}
                                            className="px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-bold hover:bg-blue-700 transition"
                                          >
                                            {isAssigningWard === appt.id.toString() ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Update'}
                                          </motion.button>
                                        </div>
                                      </motion.div>
                                    )}
                                  </AnimatePresence>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </GlassCard>
                        </motion.div>
                      );
                    })}
                  </div>
                )}
              </div>

            </div>
          )}
        </div>
      </div>

      {/* Reject Modal */}
      <AnimatePresence>
        {showRejectModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-3xl p-8 w-full max-w-lg shadow-2xl relative"
            >
              <button 
                onClick={() => setShowRejectModal(false)}
                className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
              >
                <XCircle className="w-6 h-6" />
              </button>
              
              <h3 className="text-2xl font-bold text-gray-800 mb-2 border-b pb-4 flex items-center">
                <CalendarClock className="w-6 h-6 mr-2 text-yellow-500" /> Cancel & Reschedule
              </h3>
              <p className="text-sm text-gray-500 mb-6">
                Please provide exactly 3 alternative future dates for the patient to choose from. Time slots are optional but recommended.
              </p>

              <div className="space-y-4 mb-8">
                {[0, 1, 2].map(i => (
                  <div key={i} className="flex gap-4 items-center bg-gray-50 p-3 rounded-xl border border-gray-100">
                    <span className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-sm">
                      {i + 1}
                    </span>
                    <div className="flex-1">
                      <label className="text-xs font-bold text-gray-400 uppercase">Date</label>
                      <input 
                        type="date"
                        value={dates[i]}
                        onChange={(e) => updateDate(i, e.target.value)}
                        className="w-full mt-1 px-3 py-2 bg-white border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 text-sm font-semibold"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs font-bold text-gray-400 uppercase">Time (Opt)</label>
                      <input 
                        type="time"
                        value={times[i]}
                        onChange={(e) => updateTime(i, e.target.value)}
                        className="w-full mt-1 px-3 py-2 bg-white border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 text-sm font-semibold"
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex space-x-4">
                <button 
                  onClick={() => setShowRejectModal(false)}
                  className="flex-1 py-3 bg-gray-100 text-gray-600 font-bold rounded-xl hover:bg-gray-200 transition"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleRejectSubmit}
                  disabled={isRejecting}
                  className="flex-1 py-3 bg-yellow-500 text-white font-bold rounded-xl flex items-center justify-center shadow-lg hover:bg-yellow-600 transition disabled:opacity-50"
                >
                  {isRejecting ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Confirm Reschedule'}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Patient Details Modal */}
      <AnimatePresence>
        {selectedAppt && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
            onClick={() => setSelectedAppt(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-3xl shadow-xl w-full max-w-md overflow-hidden flex flex-col"
            >
              <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-blue-50/50 backdrop-blur-md">
                <h3 className="text-xl font-bold text-gray-800 flex items-center">
                  <User className="w-5 h-5 mr-2 text-blue-500" /> Patient Details
                </h3>
                <button onClick={() => setSelectedAppt(null)} className="text-gray-400 hover:text-gray-600 bg-white rounded-full p-1 shadow-sm">
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="p-6 space-y-6 text-sm max-h-[80vh] overflow-y-auto custom-scrollbar">
                <div className="bg-gradient-to-br from-blue-500 to-indigo-600 rounded-3xl p-6 text-center text-white shadow-lg">
                  <p className="text-3xl font-black">{selectedAppt.patient_name || 'Unknown'}</p>
                  {selectedAppt.patient_email && <p className="text-blue-100 mt-2 font-medium">{selectedAppt.patient_email}</p>}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {[
                    { label: 'Age', value: selectedAppt.patient_age || '--' },
                    { label: 'Sex', value: selectedAppt.patient_sex || '--', classes: 'capitalize' },
                    { label: 'Weight', value: selectedAppt.patient_weight ? `${selectedAppt.patient_weight} kg` : '--' },
                    { label: 'Height', value: selectedAppt.patient_height ? `${selectedAppt.patient_height} cm` : '--' }
                  ].map((stat, i) => (
                    <div key={i} className="bg-white border-2 border-gray-50 text-center p-4 rounded-2xl shadow-sm">
                      <p className="text-[10px] text-gray-400 font-black uppercase tracking-widest mb-1">{stat.label}</p>
                      <p className={`font-bold text-gray-800 text-xl ${stat.classes || ''}`}>{stat.value}</p>
                    </div>
                  ))}
                </div>

                <div className="bg-amber-50 rounded-2xl p-5 border border-amber-100">
                  <h4 className="text-[10px] font-black text-amber-800 uppercase tracking-widest mb-2 flex items-center">
                    <Info className="w-3 h-3 mr-1.5" /> Reason for Visit
                  </h4>
                  <p className="text-gray-700 italic leading-relaxed">"{selectedAppt.reason || 'No reason provided.'}"</p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ManageAppointments;
