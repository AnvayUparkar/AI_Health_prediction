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
  Info
} from 'lucide-react';
import GlassCard from './GlassCard';
import toast from 'react-hot-toast';
import { 
  getDoctorAppointments, 
  approveAppointment, 
  rejectAppointment, 
  updateAppointmentClinicalStatus,
  deleteAppointment,
  assignWard
} from '../services/api';

const AppointmentManagementCard = () => {
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
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

  const pendingAppointments = appointments.filter(a => a.status === 'PENDING' || a.status === 'pending');
  const activeAppointments = appointments.filter(a => a.status === 'APPROVED' || a.status === 'confirmed');

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
      // Clear input
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

  if (loading) {
    return (
      <GlassCard className="p-8 flex items-center justify-center min-h-[300px]">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </GlassCard>
    );
  }

  return (
    <>
      <GlassCard className="p-8 group flex flex-col h-full overflow-hidden relative hover:shadow-[0_0_30px_rgba(59,130,246,0.2)]">
        <div className="flex items-center space-x-4 mb-8">
          <motion.div 
            className="p-4 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl shadow-lg"
            whileHover={{ scale: 1.05 }}
          >
            <CalendarClock className="h-8 w-8 text-white" />
          </motion.div>
          <div>
            <h3 className="text-2xl font-bold text-gray-800 group-hover:text-blue-500 group-hover:[text-shadow:0_0_12px_rgba(59,130,246,0.8)] transition-all duration-300">Appointment Management</h3>
            <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              Clinical Dashboard
            </p>
          </div>
        </div>

        {/* Section 1: Pending */}
        <div className="mb-8">
          <h4 className="text-lg font-bold flex items-center text-gray-700 mb-4 border-b border-gray-200 pb-2">
            <Clock className="w-5 h-5 mr-2 text-amber-500" /> Waitlist / Pending
          </h4>
          {pendingAppointments.length === 0 ? (
            <p className="text-sm text-gray-400 italic">No pending requests.</p>
          ) : (
            <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
              {pendingAppointments.map(appt => (
                <motion.div 
                  key={appt.id}
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  className="p-4 bg-white/50 border border-gray-100 rounded-xl shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4"
                >
                  <div className="cursor-pointer group flex-1" onClick={() => setSelectedAppt(appt)}>
                    <p className="font-bold text-gray-800 flex items-center group-hover:text-blue-600 transition-colors">
                      <User className="w-4 h-4 mr-1 text-gray-400" /> {appt.patient_name || 'Patient'}
                      <Info className="w-4 h-4 ml-2 opacity-0 group-hover:opacity-100 text-blue-500 transition-opacity" />
                    </p>
                    <p className="text-xs text-gray-500 flex items-center mt-1">
                      <CalendarIcon className="w-3 h-3 mr-1" /> {appt.requested_date || appt.date || 'TBD'} &nbsp;|&nbsp;
                      <Clock className="w-3 h-3 mx-1" /> {appt.requested_time || appt.time || 'TBD'}
                    </p>
                  </div>
                  <div className="flex space-x-2 mt-4 sm:mt-0">
                    <button 
                      onClick={() => handleApprove(appt.id)}
                      className="px-3 py-2 bg-green-500 text-white rounded-lg text-sm font-bold shadow-sm hover:bg-green-600 transition flex items-center"
                    >
                      <Check className="w-4 h-4 mr-1" /> Approve
                    </button>
                    <button 
                      onClick={() => handleOpenReject(appt.id)}
                      className="px-3 py-2 bg-yellow-500 text-white rounded-lg text-sm font-bold shadow-sm hover:bg-yellow-600 transition flex items-center"
                    >
                      <CalendarClock className="w-4 h-4 mr-1" /> Reschedule
                    </button>
                    <button 
                      onClick={() => handleDelete(appt.id)}
                      className="px-3 py-2 bg-red-500 text-white rounded-lg text-sm font-bold shadow-sm hover:bg-red-600 transition flex items-center"
                    >
                      <X className="w-4 h-4 mr-1" /> Delete
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Section 2: Active / Approved */}
        <div>
          <h4 className="text-lg font-bold flex items-center text-gray-700 mb-4 border-b border-gray-200 pb-2">
            <CheckCircle className="w-5 h-5 mr-2 text-green-500" /> Active Appointments
          </h4>
          {activeAppointments.length === 0 ? (
            <p className="text-sm text-gray-400 italic">No approved appointments for today.</p>
          ) : (
            <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
              {activeAppointments.map(appt => {
                const isChecked = appt.isChecked || false;
                const isAdmitted = appt.isAdmitted || false;

                return (
                  <motion.div 
                    key={appt.id}
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="p-5 bg-gradient-to-r from-blue-50/50 to-indigo-50/50 border border-blue-100 rounded-xl shadow-sm"
                  >
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4 border-b border-blue-200/50 pb-4">
                      <div className="cursor-pointer group flex-1" onClick={() => setExpandedApptId(expandedApptId === appt.id ? null : appt.id)}>
                        <div className="font-bold text-gray-800 text-lg group-hover:text-blue-600 transition-colors flex items-center">
                          {appt.patient_name || 'Patient'}
                          <button 
                            onClick={(e) => { e.stopPropagation(); setSelectedAppt(appt); }}
                            className="ml-2 opacity-0 group-hover:opacity-100 p-1 hover:bg-blue-100 rounded-full transition-all"
                          >
                            <Info className="w-5 h-5 text-blue-500" />
                          </button>
                        </div>
                        <p className="text-sm text-blue-600 font-medium">
                          {appt.requested_date || appt.date} @ {appt.requested_time || appt.time}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <div className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold uppercase">
                          Approved
                        </div>
                        <button 
                          onClick={() => handleDelete(appt.id)}
                          className="px-3 py-1 bg-red-500 text-white rounded-full text-[10px] font-bold flex items-center hover:bg-red-600 transition shadow-sm"
                        >
                          <X className="w-3 h-3 mr-1" /> DELETE
                        </button>
                      </div>
                    </div>

                    <AnimatePresence>
                      {expandedApptId === appt.id && (
                        <motion.div 
                          initial={{ height: 0, opacity: 0 }} 
                          animate={{ height: 'auto', opacity: 1 }} 
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >

                    {/* Toggles */}
                    <div className="flex flex-col sm:flex-row gap-6">
                      <div className="flex items-center justify-between flex-1 bg-white/60 p-3 rounded-lg border border-gray-100">
                        <div className="flex items-center text-sm font-semibold text-gray-700">
                          <CheckCircle className={`w-4 h-4 mr-2 ${isChecked ? 'text-green-500' : 'text-gray-400'}`} /> 
                          Patient Verified
                        </div>
                        <button 
                          onClick={() => handleToggleStatus(appt.id, !isChecked, isAdmitted && !isChecked ? false : isAdmitted)}
                          className={`w-12 h-6 rounded-full p-1 transition-colors duration-300 ease-in-out ${isChecked ? 'bg-green-500' : 'bg-gray-300'}`}
                        >
                          <motion.div 
                            className="bg-white w-4 h-4 rounded-full shadow-md"
                            animate={{ x: isChecked ? 24 : 0 }}
                          />
                        </button>
                      </div>

                      <div className={`flex items-center justify-between flex-1 bg-white/60 p-3 rounded-lg border border-gray-100 transition-opacity ${!isChecked ? 'opacity-50 pointer-events-none' : ''}`}>
                        <div className="flex items-center text-sm font-semibold text-gray-700">
                          <Building className={`w-4 h-4 mr-2 ${isAdmitted ? 'text-blue-500' : 'text-gray-400'}`} /> 
                          Admitted to Ward
                        </div>
                        <button 
                          onClick={() => handleToggleStatus(appt.id, isChecked, !isAdmitted)}
                          disabled={!isChecked}
                          className={`w-12 h-6 rounded-full p-1 transition-colors duration-300 ease-in-out ${isAdmitted ? 'bg-blue-500' : 'bg-gray-300'}`}
                        >
                          <motion.div 
                            className="bg-white w-4 h-4 rounded-full shadow-md"
                            animate={{ x: isAdmitted ? 24 : 0 }}
                          />
                        </button>
                      </div>
                    </div>

                    {/* Ward Assignment Input */}
                    <AnimatePresence>
                      {isAdmitted && (
                        <motion.div 
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="mt-4 pt-4 border-t border-blue-200/50"
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex-1 relative">
                              <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                              <input 
                                type="text"
                                placeholder={appt.ward_number ? `Current: ${appt.ward_number}` : "Enter Ward Number (e.g. W-203)"}
                                value={wardInputs[appt.id] || ''}
                                onChange={(e) => setWardInputs(prev => ({ ...prev, [appt.id]: e.target.value }))}
                                className="w-full pl-10 pr-4 py-2 bg-white border border-blue-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                              />
                            </div>
                            <button 
                              onClick={() => handleAssignWard(appt.id)}
                              disabled={isAssigningWard === appt.id.toString()}
                              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold hover:bg-blue-700 transition disabled:opacity-50 flex items-center"
                            >
                              {isAssigningWard === appt.id.toString() ? (
                                <Loader2 className="w-4 h-4 animate-spin mr-1" />
                              ) : (
                                <Check className="w-4 h-4 mr-1" />
                              )}
                              Assign
                            </button>
                          </div>
                          {appt.ward_number && (
                            <p className="mt-2 text-xs font-bold text-blue-700 flex items-center">
                              <div className="w-2 h-2 rounded-full bg-green-500 mr-2 animate-pulse" />
                              CURRENTLY IN: {appt.ward_number}
                            </p>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>

                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </GlassCard>

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
                        className="w-full mt-1 px-3 py-2 bg-white border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-xs font-bold text-gray-400 uppercase">Time (Opt)</label>
                      <input 
                        type="time"
                        value={times[i]}
                        onChange={(e) => updateTime(i, e.target.value)}
                        className="w-full mt-1 px-3 py-2 bg-white border border-gray-200 rounded-lg outline-none focus:ring-2 focus:ring-blue-500 text-sm"
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
              className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden flex flex-col"
            >
              <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-blue-50/50">
                <h3 className="text-xl font-bold text-gray-800 flex items-center">
                  <User className="w-5 h-5 mr-2 text-blue-500" /> Patient Details
                </h3>
                <button onClick={() => setSelectedAppt(null)} className="text-gray-400 hover:text-gray-600 bg-white rounded-full p-1 shadow-sm">
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="p-6 space-y-4 text-sm max-h-[80vh] overflow-y-auto">
                <div className="bg-gray-50 rounded-xl p-4 border border-gray-100 text-center">
                  <p className="text-2xl font-bold text-gray-800">{selectedAppt.patient_name || 'Unknown'}</p>
                  {selectedAppt.patient_email && <p className="text-gray-500 mt-1">{selectedAppt.patient_email}</p>}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white border text-center p-3 rounded-xl border-gray-100 shadow-sm">
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-1">Age</p>
                    <p className="font-semibold text-gray-800 text-lg">{selectedAppt.patient_age || '--'}</p>
                  </div>
                  <div className="bg-white border text-center p-3 rounded-xl border-gray-100 shadow-sm">
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-1">Sex</p>
                    <p className="font-semibold text-gray-800 text-lg capitalize">{selectedAppt.patient_sex || '--'}</p>
                  </div>
                  <div className="bg-white border text-center p-3 rounded-xl border-gray-100 shadow-sm">
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-1">Weight</p>
                    <p className="font-semibold text-gray-800 text-lg">{selectedAppt.patient_weight ? `${selectedAppt.patient_weight} kg` : '--'}</p>
                  </div>
                  <div className="bg-white border text-center p-3 rounded-xl border-gray-100 shadow-sm">
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mb-1">Height</p>
                    <p className="font-semibold text-gray-800 text-lg">{selectedAppt.patient_height ? `${selectedAppt.patient_height} cm` : '--'}</p>
                  </div>
                </div>

                <div className="mt-4 bg-amber-50/50 p-4 rounded-xl border border-amber-100">
                  <h4 className="text-xs font-bold text-amber-800 uppercase tracking-wider mb-2">Reason for Visit</h4>
                  <p className="text-gray-700 italic">"{selectedAppt.reason || 'No reason provided.'}"</p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default AppointmentManagementCard;
