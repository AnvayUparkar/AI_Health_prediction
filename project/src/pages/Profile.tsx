import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Mail, Shield, Scale, Ruler, Users, Search, Hospital, Save, Plus, X, HeartPulse, Stethoscope, Activity, Heart, Edit } from 'lucide-react';
import GlassCard from '../components/GlassCard';
import AnimatedBackground from '../components/AnimatedBackground';
import { getProfile, updateProfile, searchUsers, updatePatientProfile } from '../services/api';
import toast from 'react-hot-toast';

const Profile = () => {
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);

  // Profile Form States
  const [age, setAge] = useState('');
  const [sex, setSex] = useState('');
  const [weight, setWeight] = useState('');
  const [height, setHeight] = useState('');

  // Doctor/Nurse Search States
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [newHospital, setNewHospital] = useState('');

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
    } catch (error) {
      console.error("Failed to fetch profile", error);
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const profileData: any = { sex };

      if (age && !isNaN(parseInt(age))) profileData.age = parseInt(age);
      if (weight && !isNaN(parseFloat(weight))) profileData.weight = parseFloat(weight);
      if (height && !isNaN(parseFloat(height))) profileData.height = parseFloat(height);

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
            <GlassCard className="p-8">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-2xl font-bold text-gray-800 flex items-center">
                  <HeartPulse className="w-6 h-6 mr-2 text-pink-500" />
                  Health Profile
                </h3>
                {!editing ? (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setEditing(true)}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-semibold hover:shadow-lg transition-all"
                  >
                    Edit Profile
                  </motion.button>
                ) : (
                  <button
                    onClick={() => setEditing(false)}
                    className="text-gray-500 hover:text-gray-700 font-medium"
                  >
                    Cancel
                  </button>
                )}
              </div>

              <form onSubmit={handleUpdateProfile} className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-600 block">Age</label>
                  <div className="relative">
                    <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="number"
                      disabled={!editing}
                      value={age}
                      onChange={(e) => setAge(e.target.value)}
                      placeholder="Enter age"
                      className="w-full pl-10 pr-4 py-3 bg-white/50 border border-white/30 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all disabled:opacity-50"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-600 block">Sex</label>
                  <select
                    disabled={!editing}
                    value={sex}
                    onChange={(e) => setSex(e.target.value)}
                    className="w-full px-4 py-3 bg-white/50 border border-white/30 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all disabled:opacity-50"
                  >
                    <option value="">Select Sex</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-600 block">Weight (kg)</label>
                  <div className="relative">
                    <Scale className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="number"
                      step="0.1"
                      disabled={!editing}
                      value={weight}
                      onChange={(e) => setWeight(e.target.value)}
                      placeholder="Enter weight"
                      className="w-full pl-10 pr-4 py-3 bg-white/50 border border-white/30 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all disabled:opacity-50"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-gray-600 block">Height (cm)</label>
                  <div className="relative">
                    <Ruler className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="number"
                      disabled={!editing}
                      value={height}
                      onChange={(e) => setHeight(e.target.value)}
                      placeholder="Enter height"
                      className="w-full pl-10 pr-4 py-3 bg-white/50 border border-white/30 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all disabled:opacity-50"
                    />
                  </div>
                </div>

                <AnimatePresence>
                  {editing && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="md:col-span-2"
                    >
                      <button
                        type="submit"
                        className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-bold shadow-lg hover:shadow-xl transition-all flex items-center justify-center space-x-2"
                      >
                        <Save className="w-5 h-5" />
                        <span>Save Profile Data</span>
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </form>
            </GlassCard>

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
