import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Users, Search, XCircle, FileText, 
  ExternalLink, UserCheck, ShieldAlert
} from 'lucide-react';
import { getPendingDoctors, approveDoctor, rejectDoctor } from '../services/api';
import toast from 'react-hot-toast';

const ManageDoctors = () => {
  const [doctors, setDoctors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [selectedDoctor, setSelectedDoctor] = useState<any>(null);
  const [rejectionReason, setRejectionReason] = useState('');

  useEffect(() => {
    fetchDoctors();
  }, []);

  const fetchDoctors = async () => {
    try {
      const res = await getPendingDoctors();
      setDoctors(res.doctors || []);
    } catch (err) {
      toast.error('Failed to load pending doctors');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string | number) => {
    try {
      await approveDoctor(id);
      toast.success('Doctor approved successfully!');
      setDoctors(doctors.filter(d => d.id !== id));
    } catch (err) {
      toast.error('Failed to approve doctor');
    }
  };

  const handleReject = async () => {
    if (!rejectionReason) {
      toast.error('Please provide a reason for rejection');
      return;
    }
    try {
      await rejectDoctor(selectedDoctor.id, rejectionReason);
      toast.success('Doctor rejected');
      setDoctors(doctors.filter(d => d.id !== selectedDoctor.id));
      setShowRejectModal(false);
      setRejectionReason('');
    } catch (err) {
      toast.error('Failed to reject doctor');
    }
  };

  const filteredDoctors = doctors.filter(d => 
    d.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.email.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen pt-28 pb-12 px-4 bg-gray-50/50">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Doctor Verifications</h1>
            <p className="text-gray-500 mt-1">Review and manage professional credentials for medical staff.</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input 
                type="text"
                placeholder="Search by name or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2.5 rounded-2xl bg-white border border-gray-200 outline-none focus:ring-4 focus:ring-indigo-500/5 focus:border-indigo-500 w-full md:w-80 shadow-sm transition-all"
              />
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 flex items-center gap-4">
            <div className="p-3 bg-amber-50 rounded-2xl text-amber-600">
              <Users className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-500">Pending Review</p>
              <p className="text-2xl font-bold text-gray-900">{doctors.length}</p>
            </div>
          </div>
          {/* Add more stats if needed */}
        </div>

        {/* Table/List View */}
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
          {loading ? (
            <div className="p-20 text-center">
              <div className="animate-spin h-10 w-10 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-gray-500">Loading applications...</p>
            </div>
          ) : filteredDoctors.length === 0 ? (
            <div className="p-20 text-center">
              <div className="bg-gray-50 h-20 w-20 rounded-full flex items-center justify-center mx-auto mb-4">
                <ShieldAlert className="h-10 w-10 text-gray-300" />
              </div>
              <p className="text-lg font-semibold text-gray-700">No pending applications</p>
              <p className="text-gray-500 mt-1">All doctor verifications are up to date.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-gray-50/50 border-b border-gray-100">
                    <th className="px-6 py-4 text-sm font-semibold text-gray-600">Practitioner</th>
                    <th className="px-6 py-4 text-sm font-semibold text-gray-600">Credentials</th>
                    <th className="px-6 py-4 text-sm font-semibold text-gray-600">Status</th>
                    <th className="px-6 py-4 text-sm font-semibold text-gray-600">Attempts</th>
                    <th className="px-6 py-4 text-sm font-semibold text-gray-600 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredDoctors.map((doc) => (
                    <motion.tr 
                      layout
                      key={doc.id} 
                      className="hover:bg-gray-50/30 transition-colors group"
                    >
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold">
                            {doc.name.charAt(0)}
                          </div>
                          <div>
                            <p className="font-bold text-gray-900">{doc.name}</p>
                            <p className="text-sm text-gray-500">{doc.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        {doc.verification?.certificate_url ? (
                          <a 
                            href={doc.verification.certificate_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-blue-50 text-blue-700 text-sm font-medium hover:bg-blue-100 transition-colors border border-blue-100"
                          >
                            <FileText className="h-4 w-4" />
                            View Certificate
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        ) : (
                          <span className="text-xs font-semibold text-red-500 uppercase tracking-wider">Missing File</span>
                        )}
                      </td>
                      <td className="px-6 py-5">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 text-amber-700 text-xs font-bold border border-amber-100">
                          <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                          PENDING
                        </span>
                      </td>
                      <td className="px-6 py-5">
                        <span className="text-sm font-medium text-gray-600">
                          {doc.verification?.attempts || 0} / 3
                        </span>
                      </td>
                      <td className="px-6 py-5 text-right">
                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button 
                            onClick={() => handleApprove(doc.id)}
                            className="p-2 rounded-xl bg-green-50 text-green-600 hover:bg-green-600 hover:text-white transition-all shadow-sm border border-green-100"
                            title="Approve"
                          >
                            <UserCheck className="h-5 w-5" />
                          </button>
                          <button 
                            onClick={() => {
                              setSelectedDoctor(doc);
                              setShowRejectModal(true);
                            }}
                            className="p-2 rounded-xl bg-red-50 text-red-600 hover:bg-red-600 hover:text-white transition-all shadow-sm border border-red-100"
                            title="Reject"
                          >
                            <XCircle className="h-5 w-5" />
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Reject Modal */}
      <AnimatePresence>
        {showRejectModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowRejectModal(false)}
              className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
            />
            <motion.div 
              initial={{ scale: 0.9, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.9, opacity: 0, y: 20 }}
              className="relative max-w-md w-full bg-white rounded-3xl shadow-2xl overflow-hidden p-8"
            >
              <h3 className="text-xl font-bold text-gray-900 mb-2">Reject Application</h3>
              <p className="text-gray-500 text-sm mb-6">
                Reason will be visible to <strong>{selectedDoctor?.name}</strong>. Attempts left: {3 - (selectedDoctor?.verification?.attempts || 0)}
              </p>
              
              <textarea 
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="e.g. Certificate is blurred or expired..."
                className="w-full h-32 p-4 rounded-2xl bg-gray-50 border border-gray-100 focus:ring-4 focus:ring-red-500/5 focus:border-red-500 outline-none transition-all text-sm"
              />

              <div className="flex gap-4 mt-8">
                <button 
                  onClick={() => setShowRejectModal(false)}
                  className="flex-1 py-3 px-4 rounded-2xl bg-gray-100 text-gray-600 font-bold hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={handleReject}
                  className="flex-1 py-3 px-4 rounded-2xl bg-red-600 text-white font-bold hover:bg-red-700 transition-all shadow-xl shadow-red-200"
                >
                  Send Rejection
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ManageDoctors;
