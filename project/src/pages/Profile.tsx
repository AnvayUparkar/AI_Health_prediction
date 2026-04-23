import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { motion, AnimatePresence } from 'framer-motion';
import { User, Mail, Shield, Search, Hospital, Save, Plus, X, HeartPulse, Stethoscope, Activity, Heart, Edit, Upload, Clock, CalendarClock, ShieldCheck, AlertCircle, FileText, ExternalLink, Check, ChevronRight, Info, Utensils } from 'lucide-react';

import GlassCard from '../components/GlassCard';
import AnimatedBackground from '../components/AnimatedBackground';
import { getProfile, updateProfile, searchUsers, updatePatientProfile, uploadDoctorCertificate, getAppointments } from '../services/api';

import toast from 'react-hot-toast';

const Profile = () => {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);

  // Profile Form States
  const [age, setAge] = useState('');
  const [sex, setSex] = useState('');
  const [weight, setWeight] = useState('');
  const [height, setHeight] = useState('');

  // Dietary States
  const [dietPreference, setDietPreference] = useState('veg');
  const [nonVegPreferences, setNonVegPreferences] = useState<string[]>([]);
  const [allergies, setAllergies] = useState<string[]>([]);
  const [allergyInput, setAllergyInput] = useState('');
  const [showNonVegModal, setShowNonVegModal] = useState(false);

  // Doctor/Nurse Search States
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [newHospital, setNewHospital] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [loadingAppointments, setLoadingAppointments] = useState(false);


  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const data = await getProfile();
      setCurrentUser(data);
      setAge(data.profile?.age || '');
      setSex(data.profile?.sex || '');
      setWeight(data.profile?.weight || '');
      setHeight(data.profile?.height || '');
      setDietPreference(data.profile?.diet_preference || 'veg');
      setNonVegPreferences(data.profile?.non_veg_preferences || []);
      setAllergies(data.profile?.allergies || []);
      
      // Keep localStorage in sync for other components
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        const parsed = JSON.parse(storedUser);
        localStorage.setItem('user', JSON.stringify({ ...parsed, ...data }));
      }
      fetchAppointments(data.id);
    } catch (error) {
      console.error("Failed to fetch profile", error);
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };


  const fetchAppointments = async (userId: string | number) => {
    setLoadingAppointments(true);
    try {
      const data = await getAppointments({ patient_id: userId });
      setAppointments(data.appointments || []);
    } catch (error) {
      console.error("Failed to fetch appointments", error);
    } finally {
      setLoadingAppointments(false);
    }
  };


  const handleCertificateUpload = async (file: File) => {
    setIsUploading(true);
    const toastId = toast.loading('Uploading medical certificate...');
    try {
      await uploadDoctorCertificate(file);
      toast.success('Certificate uploaded successfully. Pending admin review.', { id: toastId });
      fetchProfile();
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed to upload certificate', { id: toastId });
    } finally {
      setIsUploading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const profileData: any = { sex };

      if (age && !isNaN(parseInt(age))) profileData.age = parseInt(age);
      if (weight && !isNaN(parseFloat(weight))) profileData.weight = parseFloat(weight);
      if (height && !isNaN(parseFloat(height))) profileData.height = parseFloat(height);

      profileData.diet_preference = dietPreference;
      profileData.non_veg_preferences = nonVegPreferences;
      
      // Auto-add pending allergy if exists before save
      let finalAllergies = [...allergies];
      if (allergyInput.trim()) {
        const pending = allergyInput.trim().toLowerCase();
        if (!finalAllergies.includes(pending)) {
          finalAllergies.push(pending);
          setAllergies(finalAllergies);
          setAllergyInput('');
        }
      }
      profileData.allergies = finalAllergies;

      await updateProfile(profileData);
      toast.success("Profile updated successfully");
      setEditing(false);
      fetchProfile();
    } catch (error) {
      toast.error("Failed to update profile");
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const results = await searchUsers(searchQuery);
      setSearchResults(results);
    } catch (error) {
      toast.error("Search failed");
    } finally {
      setSearching(false);
    }
  };

  const handleAddHospital = async (userId: string | number, hospitals: string[]) => {
    if (!newHospital.trim()) return;
    const updatedHospitals = [...hospitals, newHospital.trim()];
    try {
      await updatePatientProfile(userId, { hospitals: updatedHospitals });
      toast.success("Hospital association added");
      setNewHospital('');
      // If we updated ourselves, refresh profile, else refresh search result
      if (userId === currentUser.id) {
        fetchProfile();
      } else {
        handleSearch();
      }
    } catch (error) {
      toast.error("Failed to add hospital");
    }
  };

  const handleRemoveHospital = async (userId: string | number, hospitals: string[], hospitalToRemove: string) => {
    const updatedHospitals = hospitals.filter(h => h !== hospitalToRemove);
    try {
      await updatePatientProfile(userId, { hospitals: updatedHospitals });
      toast.success("Hospital association removed");
      if (userId === currentUser.id) {
        fetchProfile();
      } else {
        handleSearch();
      }
    } catch (error) {
      toast.error("Failed to remove hospital");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  const userRole = currentUser?.role?.toLowerCase();
  const isProfessional = ['doctor', 'nurse'].includes(userRole?.trim().toLowerCase() || '');
  return (
    <div className="relative min-h-screen pb-20">
      <AnimatedBackground />

      <div className="relative pt-32 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 lg:grid-cols-3 gap-8"
        >
          {/* Main Profile Info Card */}
          <GlassCard className="lg:col-span-1 p-8">
            <div className="flex flex-col items-center text-center mb-8">
              <div className={`w-32 h-32 rounded-full flex items-center justify-center mb-4 shadow-xl bg-gradient-to-r ${userRole === 'doctor' ? 'from-blue-500 to-indigo-600' :
                  userRole === 'nurse' ? 'from-emerald-500 to-teal-600' :
                    'from-pink-500 to-rose-600'
                }`}>
                <User className="w-16 h-16 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-gray-800">{currentUser.name}</h2>
              <p className={`font-medium capitalize flex items-center mt-1 ${userRole === 'doctor' ? 'text-blue-600' :
                  userRole === 'nurse' ? 'text-emerald-600' :
                    'text-rose-600'
                }`}>
                {userRole === 'doctor' && <Stethoscope className="w-4 h-4 mr-1" />}
                {userRole === 'nurse' && <Activity className="w-4 h-4 mr-1" />}
                {userRole === 'user' && <Heart className="h-4 w-4 mr-1" />}
                {!['doctor', 'nurse', 'user'].includes(userRole || '') && <Shield className="w-4 h-4 mr-1" />}
                {currentUser.role}
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-white/40 rounded-xl">
                <div className="flex items-center flex-1">
                  <Mail className="w-5 h-5 text-gray-500 mr-3" />
                  <div className="text-left">
                    <p className="text-xs text-gray-500 uppercase tracking-wider">Email Address</p>
                    <p className="text-gray-800 font-medium">{currentUser.email}</p>
                  </div>
                </div>
                <motion.button
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.95 }}
                  className="ml-4 p-2 text-gray-500 hover:text-blue-500 transition-colors duration-200 hover:bg-white/30 rounded-lg"
                  title="Edit email"
                >
                  <Edit className="w-5 h-5" />
                </motion.button>
              </div>

              <div className="flex items-center p-4 bg-white/40 rounded-xl">
                <div className={`${userRole === 'doctor' ? 'text-blue-500' :
                    userRole === 'nurse' ? 'text-emerald-500' :
                      'text-rose-500'
                  } mr-3`}>
                  {userRole === 'doctor' && <Stethoscope className="w-5 h-5" />}
                  {userRole === 'nurse' && <Activity className="w-5 h-5" />}
                  {userRole === 'user' && <Heart className="w-5 h-5" />}
                  {!['doctor', 'nurse', 'user'].includes(userRole || '') && <Shield className="w-5 h-5" />}
                </div>
                <div className="text-left">
                  <p className="text-xs text-gray-500 uppercase tracking-wider">Account Role</p>
                  <p className="text-gray-800 font-medium capitalize">{currentUser.role}</p>
                </div>
              </div>
            </div>
          </GlassCard>

          {/* Health & Clinical Data Card */}
          <div className="lg:col-span-2 space-y-8">

            {/* NEW: Appointment Availability Section for Doctors */}
            {userRole === 'doctor' && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden"
              >
                <GlassCard className="p-8 border-none bg-gradient-to-br from-blue-600/10 to-indigo-600/10 border-blue-200">
                  <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    <div className="flex items-center gap-4">
                      <div className="p-4 bg-blue-100 rounded-2xl text-blue-600 shadow-inner">
                        <CalendarClock className="w-8 h-8" />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-gray-800">Clinic Availability</h3>
                        <p className="text-gray-600">Set your working hours and consultation intervals.</p>
                      </div>
                    </div>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => navigate('/doctor/availability')}
                      className="px-8 py-4 bg-blue-600 text-white rounded-2xl font-bold shadow-lg shadow-blue-200 hover:shadow-blue-300 transition-all flex items-center gap-2 whitespace-nowrap"
                    >
                      <Plus className="w-5 h-5" />
                      Add Slots
                    </motion.button>
                  </div>
                </GlassCard>
              </motion.div>
            )}
            
            {/* Doctor Verification Section */}
            {userRole === 'doctor' && (

              <GlassCard className="p-8 border-l-4 border-l-blue-500">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center">
                    <ShieldCheck className="w-6 h-6 mr-2 text-blue-500" />
                    <h3 className="text-2xl font-bold text-gray-800">Professional Verification</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500 font-medium">Attempts: {currentUser.verification?.attempts || 0} / 3</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* Current Status */}
                  <div className="space-y-4">
                    <div className="p-6 rounded-2xl bg-gray-50 border border-gray-100">
                      <p className="text-sm text-gray-500 uppercase tracking-wider mb-2">Current Status</p>
                      <div className="flex items-center gap-3">
                        {currentUser.isApproved ? (
                          <>
                            <div className="p-2 bg-green-100 rounded-lg text-green-600">
                              <ShieldCheck className="w-6 h-6" />
                            </div>
                            <div>
                              <p className="font-bold text-green-700">Fully Verified</p>
                              <p className="text-xs text-green-600">Clinical features unlocked</p>
                            </div>
                          </>
                        ) : currentUser.verification?.rejection_reason ? (
                          <>
                            <div className="p-2 bg-red-100 rounded-lg text-red-600">
                              <AlertCircle className="w-6 h-6" />
                            </div>
                            <div>
                              <p className="font-bold text-red-700">Verification Rejected</p>
                              <p className="text-xs text-red-600">Action required</p>
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="p-2 bg-amber-100 rounded-lg text-amber-600">
                              <Clock className="w-6 h-6" />
                            </div>
                            <div>
                              <p className="font-bold text-amber-700">Pending Review</p>
                              <p className="text-xs text-amber-600">Awaiting admin approval</p>
                            </div>
                          </>
                        )}
                      </div>
                    </div>

                    {currentUser.verification?.rejection_reason && !currentUser.isApproved && (
                      <div className="p-4 rounded-xl bg-red-50 border border-red-100">
                        <p className="text-sm font-bold text-red-700 mb-1 flex items-center gap-2">
                          <AlertCircle className="w-4 h-4" />
                          Administrator Feedback
                        </p>
                        <p className="text-sm text-red-600 italic">"{currentUser.verification.rejection_reason}"</p>
                      </div>
                    )}
                  </div>

                  {/* Upload Section */}
                  <div className="flex flex-col justify-center">
                    {!currentUser.isApproved && (
                      <div className="space-y-4">
                        <p className="text-sm font-medium text-gray-700">
                          {currentUser.verification?.certificate_url 
                            ? "Update your medical certificate to re-apply for verification."
                            : "Upload your medical license or certificate to unlock clinical features."}
                        </p>
                        <div className="relative group p-6 border-2 border-dashed border-blue-200 rounded-2xl bg-blue-50/30 hover:bg-blue-50/50 transition-colors text-center cursor-pointer">
                          <input 
                            type="file" 
                            disabled={isUploading}
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) handleCertificateUpload(file);
                            }}
                            accept=".pdf,.jpg,.jpeg,.png"
                          />
                          <div className="flex flex-col items-center gap-2">
                            <Upload className={`h-8 w-8 ${isUploading ? 'animate-bounce text-blue-400' : 'text-blue-500'}`} />
                            <p className="font-bold text-blue-700">{isUploading ? 'Uploading...' : 'Click to Upload License'}</p>
                            <p className="text-xs text-blue-400">PDF, JPG, or PNG (Max 5MB)</p>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {currentUser.verification?.certificate_url && (
                      <div className="mt-4 flex items-center gap-2 text-sm text-gray-500 font-medium">
                        <FileText className="w-4 h-4" />
                        <span>Current file: </span>
                        <a 
                          href={currentUser.verification.certificate_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline flex items-center gap-1"
                        >
                          View License <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </GlassCard>
            )}

            <form onSubmit={handleUpdateProfile} className="space-y-8">
              <GlassCard className="p-8">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-2xl font-bold text-gray-800 flex items-center">
                    <HeartPulse className="w-6 h-6 mr-2 text-pink-500" />
                    Health Profile
                  </h3>
                  {!editing ? (
                    <motion.button
                      type="button"
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => setEditing(true)}
                      className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:shadow-lg transition-all"
                    >
                      Edit Profile
                    </motion.button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setEditing(false)}
                      className="text-gray-500 hover:text-gray-700 font-medium"
                    >
                      Cancel
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Age</label>
                    <input
                      type="number"
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      disabled={!editing}
                      className="w-full px-4 py-3 bg-white/50 border border-white/30 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Sex</label>
                    <select
                      value={sex}
                      onChange={(e) => setSex(e.target.value)}
                      disabled={!editing}
                      className="w-full px-4 py-3 bg-white/50 border border-white/30 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    >
                      <option value="">Select Sex</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Weight (kg)</label>
                    <input
                      type="number"
                      value={weight}
                      onChange={(e) => setWeight(e.target.value)}
                      disabled={!editing}
                      className="w-full px-4 py-3 bg-white/50 border border-white/30 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Height (cm)</label>
                    <input
                      type="number"
                      value={height}
                      onChange={(e) => setHeight(e.target.value)}
                      disabled={!editing}
                      className="w-full px-4 py-3 bg-white/50 border border-white/30 rounded-xl outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                    />
                  </div>
                </div>
              </GlassCard>

              {/* Dietary Preferences Card */}
              <GlassCard className="p-8">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-2xl font-bold text-gray-800 flex items-center">
                    <Utensils className="w-6 h-6 mr-2 text-orange-500" />
                    Dietary Preferences
                  </h3>
                  {editing && dietPreference !== 'veg' && (
                    <button 
                      type="button"
                      onClick={() => setShowNonVegModal(true)}
                      className="text-sm font-semibold text-blue-600 hover:text-blue-700 flex items-center bg-blue-50 px-3 py-1.5 rounded-lg"
                    >
                      Select Types <ChevronRight className="w-4 h-4 ml-1" />
                    </button>
                  )}
                </div>

                <div className="space-y-8">
                  {/* Custom Circular Radio Buttons */}
                  <div className="flex flex-wrap gap-6">
                    {[
                      { id: 'veg', label: 'Vegetarian', color: 'bg-emerald-500' },
                      { id: 'non_veg', label: 'Non-Vegetarian', color: 'bg-rose-500' },
                      { id: 'both', label: 'Both / Flexitarian', color: 'bg-amber-500' }
                    ].map((option) => (
                      <label 
                        key={option.id}
                        className={`relative flex items-center gap-3 p-4 rounded-2xl cursor-pointer border-2 transition-all duration-300 min-w-[160px] ${
                          dietPreference === option.id 
                            ? 'border-blue-500 bg-blue-50/50 shadow-md' 
                            : 'border-transparent bg-white/40 hover:bg-white/60'
                        } ${!editing ? 'pointer-events-none' : ''}`}
                      >
                        <input 
                          type="radio" 
                          name="dietPref" 
                          value={option.id}
                          checked={dietPreference === option.id}
                          onChange={(e) => {
                            setDietPreference(e.target.value);
                            if (e.target.value !== 'veg' && editing) {
                              setShowNonVegModal(true);
                            }
                          }}
                          className="hidden"
                        />
                        <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                          dietPreference === option.id ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
                        }`}>
                          {dietPreference === option.id && <Check className="w-4 h-4 text-white" />}
                        </div>
                        <span className={`font-bold transition-colors ${
                          dietPreference === option.id ? 'text-blue-700' : 'text-gray-600'
                        }`}>{option.label}</span>
                      </label>
                    ))}
                  </div>

                  {/* Selected Non-Veg Preferences Chips */}
                  {dietPreference !== 'veg' && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="space-y-3"
                    >
                      <p className="text-sm font-semibold text-gray-500 flex items-center gap-2">
                         Protein Preferences {nonVegPreferences.length === 0 && <span className="text-rose-500 text-xs font-normal">(None selected)</span>}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {nonVegPreferences.map((pref) => (
                          <span key={pref} className="px-3 py-1.5 bg-rose-50 text-rose-600 rounded-full text-xs font-bold border border-rose-100 flex items-center gap-1">
                            {pref}
                            {editing && (
                              <X 
                                className="w-3 h-3 cursor-pointer hover:text-rose-800" 
                                onClick={() => setNonVegPreferences(prev => prev.filter(p => p !== pref))}
                              />
                            )}
                          </span>
                        ))}
                        {editing && (
                          <button 
                            type="button"
                            onClick={() => setShowNonVegModal(true)}
                            className="px-3 py-1.5 bg-gray-100 text-gray-500 rounded-full text-xs font-bold border border-dashed border-gray-300 hover:bg-gray-200 transition-colors"
                          >
                            + Add/Edit
                          </button>
                        )}
                      </div>
                    </motion.div>
                  )}

                  {/* Allergy Section */}
                  <div className="space-y-4 pt-4 border-t border-gray-100">
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-gray-800">Allergies & Sensitivities</h4>
                      <div className="group relative">
                        <Info className="w-4 h-4 text-gray-400 cursor-help" />
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-800 text-white text-[10px] rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          AI will strictly avoid these ingredients in your diet plans.
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2 mb-3">
                      {allergies.map((allergy) => (
                        <motion.span 
                          layout
                          initial={{ scale: 0.8, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          key={allergy} 
                          className="px-3 py-1.5 bg-orange-100 text-orange-700 rounded-full text-xs font-bold border border-orange-200 flex items-center gap-2"
                        >
                          {allergy}
                          {editing && (
                            <X 
                               className="w-4 h-4 cursor-pointer hover:text-orange-900 bg-white/50 rounded-full p-0.5" 
                               onClick={() => setAllergies(prev => prev.filter(a => a !== allergy))}
                            />
                          )}
                        </motion.span>
                      ))}
                      {allergies.length === 0 && <p className="text-sm text-gray-400 italic">No allergies listed.</p>}
                    </div>

                    {editing && (
                      <div className="space-y-4">
                        <div className="flex gap-2">
                          <div className="relative flex-grow">
                            <input
                              type="text"
                              value={allergyInput}
                              onChange={(e) => setAllergyInput(e.target.value)}
                              onKeyDown={(e) => {
                                if ((e.key === 'Enter' || e.key === ',') && allergyInput.trim()) {
                                  e.preventDefault();
                                  const newAllergy = allergyInput.trim().toLowerCase();
                                  if (!allergies.includes(newAllergy)) {
                                    setAllergies([...allergies, newAllergy]);
                                  }
                                  setAllergyInput('');
                                }
                              }}
                              placeholder="Type allergy (e.g. peanuts, dairy)"
                              className="w-full px-4 py-3 bg-white/50 border border-white/30 rounded-xl outline-none focus:ring-2 focus:ring-orange-500 transition-all text-sm pr-12"
                            />
                            {allergyInput.trim() && (
                              <button
                                type="button"
                                onClick={() => {
                                  const newAllergy = allergyInput.trim().toLowerCase();
                                  if (!allergies.includes(newAllergy)) {
                                    setAllergies([...allergies, newAllergy]);
                                  }
                                  setAllergyInput('');
                                }}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors shadow-md"
                              >
                                <Plus className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <span className="text-xs font-semibold text-gray-400 mr-2 flex items-center">Quick Add:</span>
                          {['Peanuts', 'Dairy', 'Soy', 'Gluten', 'Eggs', 'Seafood'].map(item => (
                            <button
                              key={item}
                              type="button"
                              disabled={allergies.includes(item.toLowerCase())}
                              onClick={() => setAllergies([...allergies, item.toLowerCase()])}
                              className={`px-3 py-1 rounded-lg text-[10px] font-bold transition-all ${
                                allergies.includes(item.toLowerCase()) 
                                  ? 'bg-gray-100 text-gray-300 cursor-not-allowed' 
                                  : 'bg-white border border-gray-200 text-gray-600 hover:border-orange-300 hover:text-orange-500'
                              }`}
                            >
                              {item}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Safety Warning */}
                  <div className="bg-blue-50 rounded-2xl p-4 flex gap-3 items-start border border-blue-100 mt-4">
                    <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
                    <p className="text-xs text-blue-700 leading-relaxed italic">
                      <span className="font-bold">Safety Note:</span> Dietary preferences and allergies are used to guide AI recommendations. <strong>Always verify AI recommendations with a clinical professional</strong> before implementation.
                    </p>
                  </div>

                  {/* Save Button for the entire form */}
                  <AnimatePresence>
                    {editing && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        className="pt-6"
                      >
                        <button
                          type="submit"
                          className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-bold shadow-lg hover:shadow-xl transition-all flex items-center justify-center space-x-2"
                        >
                          <Save className="w-5 h-5" />
                          <span>Save All Changes</span>
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </GlassCard>
            </form>

            {/* Non-Veg Selection Modal */}
            <AnimatePresence>
              {showNonVegModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={() => setShowNonVegModal(false)}
                    className="absolute inset-0 bg-black/40 backdrop-blur-sm"
                  />
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: 20 }}
                    className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl overflow-hidden p-8"
                  >
                    <h3 className="text-2xl font-bold text-gray-800 mb-2">Protein Preferences</h3>
                    <p className="text-sm text-gray-500 mb-6">Select the types of non-veg items you consume.</p>
                    
                    <div className="grid grid-cols-2 gap-3 mb-8">
                      {['Chicken', 'Fish', 'Egg', 'Mutton', 'Beef', 'Pork', 'Seafood'].map(pref => (
                        <label 
                          key={pref}
                          className={`flex items-center gap-3 p-4 rounded-2xl cursor-pointer border-2 transition-all ${
                            nonVegPreferences.includes(pref)
                              ? 'border-rose-500 bg-rose-50 text-rose-700'
                              : 'border-gray-100 bg-gray-50 hover:bg-gray-100 text-gray-600'
                          }`}
                        >
                          <input 
                            type="checkbox"
                            className="hidden"
                            checked={nonVegPreferences.includes(pref)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setNonVegPreferences([...nonVegPreferences, pref]);
                              } else {
                                setNonVegPreferences(nonVegPreferences.filter(p => p !== pref));
                              }
                            }}
                          />
                          <div className={`w-5 h-5 rounded-md border flex items-center justify-center ${
                            nonVegPreferences.includes(pref) ? 'bg-rose-500 border-rose-500' : 'border-gray-300'
                          }`}>
                            {nonVegPreferences.includes(pref) && <Check className="w-3 h-3 text-white" />}
                          </div>
                          <span className="font-bold text-sm">{pref}</span>
                        </label>
                      ))}
                    </div>

                    <button
                      onClick={() => setShowNonVegModal(false)}
                      className="w-full py-4 bg-gray-800 text-white rounded-2xl font-bold hover:bg-gray-900 transition-colors"
                    >
                      Confirm Selection
                    </button>
                  </motion.div>
                </div>
              )}
            </AnimatePresence>

            {/* Booked Appointments - Patient Only */}
            {!isProfessional && (
              <GlassCard className="p-8 mb-8">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center">
                    <CalendarClock className="w-6 h-6 mr-2 text-rose-500" />
                    <h3 className="text-2xl font-bold text-gray-800">My Booked Appointments</h3>
                  </div>
                  <button 
                    onClick={() => navigate('/book-appointment')}
                    className="text-sm font-bold text-rose-600 hover:text-rose-700 flex items-center bg-rose-50 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Book New
                  </button>
                </div>

                {loadingAppointments ? (
                  <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-rose-500"></div>
                  </div>
                ) : appointments.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {appointments.map((apt) => (
                      <motion.div
                        key={apt.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="p-5 rounded-2xl bg-white/40 border border-white/20 hover:border-rose-200 transition-all group"
                      >
                        <div className="flex justify-between items-start mb-3">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 rounded-xl bg-rose-100 flex items-center justify-center text-rose-600">
                              <CalendarClock className="w-5 h-5" />
                            </div>
                            <div>
                              <h4 className="font-bold text-gray-800">{apt.reason}</h4>
                              <p className="text-xs text-blue-600 font-semibold flex items-center mb-1">
                                <Stethoscope className="w-3 h-3 mr-1" />
                                {apt.doctor_name}
                              </p>
                              <p className="text-xs text-gray-500 flex items-center">
                                <Clock className="w-3 h-3 mr-1" />
                                {apt.date} at {apt.time}
                              </p>
                            </div>

                          </div>
                          <span className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                            apt.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                            apt.status === 'pending' ? 'bg-orange-100 text-orange-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {apt.status}
                          </span>
                        </div>
                        
                        {apt.mode === 'online' && apt.meeting_link && apt.status === 'confirmed' && (
                          <a
                            href={apt.meeting_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-4 w-full py-2 bg-rose-500 text-white rounded-xl text-xs font-bold flex items-center justify-center hover:bg-rose-600 transition-all shadow-md group-hover:shadow-rose-200"
                          >
                            <ExternalLink className="w-3 h-3 mr-2" />
                            Join Zoom Meeting
                          </a>
                        )}
                        
                        {apt.mode === 'online' && !apt.meeting_link && apt.status === 'confirmed' && (
                          <div className="mt-4 w-full py-2 bg-gray-100 text-gray-500 rounded-xl text-[10px] font-medium text-center border border-dashed border-gray-300">
                            Waiting for meeting link...
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 bg-gray-50/50 rounded-3xl border-2 border-dashed border-gray-200">
                    <CalendarClock className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500 font-medium">No appointments booked yet.</p>
                    <button 
                      onClick={() => navigate('/book-appointment')}
                      className="mt-4 text-blue-600 font-bold hover:underline"
                    >
                      Book your first consultation
                    </button>
                  </div>
                )}
              </GlassCard>
            )}

            {/* Associated Hospitals - Shared Visibility */}

            <GlassCard className="p-8">
              <div className="flex items-center mb-6">
                <Hospital className="w-6 h-6 mr-2 text-blue-500" />
                <h3 className="text-2xl font-bold text-gray-800">Associated Hospitals</h3>
              </div>

              <div className="flex flex-wrap gap-3 mb-6">
                {currentUser.profile?.hospitals?.length > 0 ? (
                  currentUser.profile.hospitals.map((hospital: string, idx: number) => (
                    <div
                      key={idx}
                      className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg font-medium flex items-center"
                    >
                      {hospital}
                      {isProfessional && (
                        <button
                          onClick={() => handleRemoveHospital(currentUser.id, currentUser.profile.hospitals, hospital)}
                          className="ml-2 hover:text-red-500 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500 italic">No hospitals associated yet.</p>
                )}
              </div>

              {isProfessional && (
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newHospital}
                    onChange={(e) => setNewHospital(e.target.value)}
                    placeholder="Add a hospital..."
                    className="flex-grow px-4 py-2 bg-white/50 border border-white/30 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={() => handleAddHospital(currentUser.id, currentUser.profile?.hospitals || [])}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center"
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                </div>
              )}
            </GlassCard>

            {/* Patient Search - Professionals Only */}
            {isProfessional && (
              <GlassCard className="p-8">
                <div className="flex items-center mb-6">
                  <Search className="w-6 h-6 mr-2 text-purple-500" />
                  <h3 className="text-2xl font-bold text-gray-800">Manage Patient Hospital Data</h3>
                </div>

                <div className="flex gap-2 mb-8">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search patients by name or email..."
                    className="flex-grow px-4 py-3 bg-white/50 border border-white/30 rounded-xl outline-none focus:ring-2 focus:ring-purple-500"
                  />
                  <button
                    onClick={handleSearch}
                    disabled={searching}
                    className="px-6 py-3 bg-purple-500 text-white rounded-xl hover:bg-purple-600 transition-colors disabled:opacity-50"
                  >
                    {searching ? "..." : "Search"}
                  </button>
                </div>

                <div className="space-y-4">
                  {searchResults.map((user) => (
                    <motion.div
                      key={user.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="p-4 bg-white/40 border border-white/20 rounded-xl"
                    >
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h4 className="font-bold text-gray-800">{user.name}</h4>
                          <p className="text-sm text-gray-500">{user.email}</p>
                          <div className="mt-2 flex gap-4 text-sm text-gray-600">
                            <span>Age: {user.profile?.age || 'N/A'}</span>
                            <span>Weight: {user.profile?.weight || 'N/A'}kg</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-gray-500 uppercase">Hospitals</p>
                          <div className="flex flex-wrap gap-1 mt-1 justify-end">
                            {user.profile?.hospitals?.map((h: string, i: number) => (
                              <span key={i} className="px-2 py-0.5 bg-gray-100 rounded text-xs">{h}</span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <input
                          id={`hospital-input-${user.id}`}
                          type="text"
                          placeholder="Add hospital association..."
                          className="flex-grow px-3 py-2 bg-white/50 border border-white/30 rounded-lg text-sm"
                        />
                        <button
                          onClick={() => {
                            const input = document.getElementById(`hospital-input-${user.id}`) as HTMLInputElement;
                            if (input.value) {
                              setNewHospital(input.value);
                              handleAddHospital(user.id, user.profile?.hospitals || []);
                              input.value = '';
                            }
                          }}
                          className="px-4 py-2 bg-purple-500 text-white rounded-lg text-sm font-semibold"
                        >
                          Add
                        </button>
                      </div>
                    </motion.div>
                  ))}
                  {searchQuery && searchResults.length === 0 && !searching && (
                    <p className="text-center text-gray-500 italic">No patients found matches.</p>
                  )}
                </div>
              </GlassCard>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Profile;
