import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Calendar, Video, MapPin, User, Mail, Phone, Clock, CheckCircle, Navigation, Stethoscope, Info } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';
import { getUserLocation, UserLocation } from '../services/geoService';
import { fetchNearbyHealthcare } from '../services/overpassService';
import { processFacilities, HealthcareFacility } from '../services/healthcareProcessor';
import HealthcareMap from '../components/HealthcareMap';
import { getDoctorsByHospital } from '../services/api';

const BookAppointment = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    mode: 'online',
    date: '',
    time: '',
    reason: '',
    facilityId: '',
    doctorId: ''
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // Nearby Healthcare State
  const [facilities, setFacilities] = useState<HealthcareFacility[]>([]);
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Doctors
  const [hospitalDoctors, setHospitalDoctors] = useState<any[]>([]);
  const [fetchingDoctors, setFetchingDoctors] = useState(false);

  useEffect(() => {
    if (!formData.facilityId) {
      setHospitalDoctors([]);
      setFormData(prev => ({ ...prev, doctorId: '' }));
      return;
    }

    const facility = facilities.find(f => String(f.id) === String(formData.facilityId));
    if (facility && facility.name) {
      fetchDoctors(facility.name);
    }
  }, [formData.facilityId]);

  const fetchDoctors = async (hospitalName: string) => {
    setFetchingDoctors(true);
    try {
      const docs = await getDoctorsByHospital(hospitalName);
      setHospitalDoctors(docs || []);
      setFormData(prev => ({ ...prev, doctorId: docs && docs.length > 0 ? docs[0].id : '' }));
    } catch (err) {
      console.error('Failed to fetch doctors', err);
      setHospitalDoctors([]);
      setFormData(prev => ({ ...prev, doctorId: '' }));
    } finally {
      setFetchingDoctors(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Prepare final dropdown string if a facility is selected
    const selectedFacility = facilities.find(f => String(f.id) === String(formData.facilityId));
    
    // Get patient_id from local storage
    const userString = localStorage.getItem('user');
    const currentUser = userString ? JSON.parse(userString) : null;
    
    const bookingData = {
      ...formData,
      selected_doctor: selectedFacility ? `${selectedFacility.name} (${selectedFacility.type})` : '',
      doctor_id: formData.doctorId || null,
      patient_id: currentUser ? currentUser.id : null
    };

    try {
      const response = await fetch('http://localhost:5000/api/appointments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(bookingData),
      });

      if (response.ok) {
        setSubmitted(true);
        setTimeout(() => {
          setSubmitted(false);
          setFormData({
            name: '',
            email: '',
            phone: '',
            mode: 'online',
            date: '',
            time: '',
            reason: '',
            facilityId: '',
            doctorId: ''
          });
        }, 5000);
      }
    } catch (error) {
      console.error('Error booking appointment:', error);
      alert('Failed to book appointment. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleFindNearby = async () => {
    setSearching(true);
    setSearchError(null);
    try {
      // 1. Get current position
      const location = await getUserLocation();
      setUserLocation(location);

      // 2. Check Cache (LocalStorage)
      const cacheKey = `nearby_healthcare_${location.latitude.toFixed(3)}_${location.longitude.toFixed(3)}`;
      const cachedData = localStorage.getItem(cacheKey);
      
      if (cachedData) {
        setFacilities(JSON.parse(cachedData));
        setSearching(false);
        return;
      }

      // 3. Fetch from Overpass if not cached
      const rawData = await fetchNearbyHealthcare(location.latitude, location.longitude);
      const processed = processFacilities(rawData, location.latitude, location.longitude);
      
      if (processed.length === 0) {
        setSearchError('No nearby healthcare facilities found within 5km.');
      } else {
        setFacilities(processed);
        // Cache results for 1 hour approx (storing simplified list)
        localStorage.setItem(cacheKey, JSON.stringify(processed));
      }
    } catch (err: any) {
      setSearchError(err.message || 'Failed to fetch nearby medical facilities.');
    } finally {
      setSearching(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  if (submitted) {
    return (
      <div className="relative min-h-screen flex items-center justify-center">
        <AnimatedBackground />
        <GlassCard className="p-12 max-w-md mx-4">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="text-center"
          >
            <CheckCircle className="h-20 w-20 text-green-500 mx-auto mb-6" />
            <h2 className="text-3xl font-bold text-gray-800 mb-4">Appointment Booked!</h2>
            <p className="text-gray-600">
              We've received your appointment request. You'll receive a confirmation email shortly.
            </p>
          </motion.div>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen pt-20 pb-12">
      <AnimatedBackground />
      
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
            Book Doctor Appointment
          </h1>
          <p className="text-xl text-gray-600">
            Schedule a consultation with our healthcare professionals
          </p>
        </motion.div>

        <GlassCard className="p-8">
          <div className="flex justify-end mb-6">
            <motion.button
              type="button"
              onClick={handleFindNearby}
              disabled={searching}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center space-x-2 bg-blue-50 text-blue-600 px-5 py-2.5 rounded-2xl font-bold border border-blue-100 shadow-sm hover:shadow-md transition-all active:bg-blue-100 disabled:opacity-50"
            >
              <Navigation className={`h-4 w-4 ${searching ? 'animate-pulse' : ''}`} />
              <span>{searching ? 'Locating...' : 'Find Nearby Doctors & Hospitals'}</span>
            </motion.button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Personal Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <User className="h-5 w-5 mr-2 text-blue-500" />
                  Full Name
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-white/50"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <Mail className="h-5 w-5 mr-2 text-blue-500" />
                  Email
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-white/50"
                  placeholder="john@example.com"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <Phone className="h-5 w-5 mr-2 text-blue-500" />
                  Phone Number
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-white/50"
                  placeholder="+1 (555) 000-0000"
                />
              </div>

              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <Stethoscope className="h-5 w-5 mr-2 text-blue-500" />
                  Select Healthcare Professional / Facility
                </label>
                <select
                  name="facilityId"
                  value={formData.facilityId}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-white/50"
                >
                  <option value="">{facilities.length > 0 ? '-- Choose Nearby Specialist --' : 'Locate nearby doctors first'}</option>
                  {facilities.map(f => (
                    <option key={f.id} value={f.id}>
                      {f.name} ({f.type.charAt(0).toUpperCase() + f.type.slice(1)}) - {f.distance.toFixed(1)} km
                    </option>
                  ))}
                </select>
                {facilities.length === 0 && (
                  <p className="mt-1 text-[10px] text-gray-400 font-medium italic pl-1 flex items-center">
                    <Info className="h-3 w-3 mr-1" />
                    Click "Find Nearby" above to populate this list automatically.
                  </p>
                )}
              </div>
            </div>

            {/* Doctor Selection (Conditional) */}
            <AnimatePresence>
              {formData.facilityId && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-6 overflow-hidden"
                >
                  <label className="flex items-center text-gray-700 font-semibold mb-2">
                    <User className="h-5 w-5 mr-2 text-blue-500" />
                    Select Associated Doctor
                  </label>
                  
                  {fetchingDoctors ? (
                    <div className="flex items-center space-x-2 text-sm text-blue-600 bg-blue-50 p-3 rounded-xl border border-blue-100">
                      <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                      <span>Fetching registered doctors for this facility...</span>
                    </div>
                  ) : hospitalDoctors.length > 0 ? (
                    <select
                      name="doctorId"
                      value={formData.doctorId}
                      onChange={handleChange}
                      className="w-full px-4 py-3 rounded-xl border border-blue-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-blue-50/50 shadow-sm"
                    >
                      {hospitalDoctors.map(doc => (
                        <option key={doc.id} value={doc.id}>
                          Dr. {doc.name} {doc.profile?.specialty ? `- ${doc.profile.specialty}` : ''}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="flex items-start space-x-2 text-sm text-gray-500 bg-gray-50 p-3 rounded-xl border border-gray-200">
                      <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
                      <span>
                        No registered doctors on this platform are associated with this facility yet. 
                        Your booking will be sent to the facility's general queue.
                      </span>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {searchError && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="p-4 bg-amber-50 border border-amber-100 text-amber-700 rounded-xl text-sm italic"
              >
                {searchError}
              </motion.div>
            )}

            {/* Appointment Mode */}
            <div>
              <label className="text-gray-700 font-semibold mb-3 block">
                Consultation Mode
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <motion.label
                  whileHover={{ scale: 1.02 }}
                  className={`flex items-center p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    formData.mode === 'online'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-white/50 bg-white/30 hover:border-blue-300 backdrop-blur-sm'
                  }`}
                >
                  <input
                    type="radio"
                    name="mode"
                    value="online"
                    checked={formData.mode === 'online'}
                    onChange={handleChange}
                    className="mr-3"
                  />
                  <Video className="h-6 w-6 mr-3 text-blue-500" />
                  <div>
                    <div className="font-semibold">Online (Video Call)</div>
                    <div className="text-sm text-gray-600">Virtual consultation</div>
                  </div>
                </motion.label>

                <motion.label
                  whileHover={{ scale: 1.02 }}
                  className={`flex items-center p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    formData.mode === 'offline'
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-white/50 bg-white/30 hover:border-blue-300 backdrop-blur-sm'
                  }`}
                >
                  <input
                    type="radio"
                    name="mode"
                    value="offline"
                    checked={formData.mode === 'offline'}
                    onChange={handleChange}
                    className="mr-3"
                  />
                  <MapPin className="h-6 w-6 mr-3 text-blue-500" />
                  <div>
                    <div className="font-semibold">Offline (In-Person)</div>
                    <div className="text-sm text-gray-600">Visit clinic</div>
                  </div>
                </motion.label>
              </div>
            </div>

            {/* Date and Time */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <Calendar className="h-5 w-5 mr-2 text-blue-500" />
                  Preferred Date
                </label>
                <input
                  type="date"
                  name="date"
                  value={formData.date}
                  onChange={handleChange}
                  required
                  min={new Date().toISOString().split('T')[0]}
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-white/50"
                />
              </div>

              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <Clock className="h-5 w-5 mr-2 text-blue-500" />
                  Preferred Time
                </label>
                <select
                  name="time"
                  value={formData.time}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-white/50"
                >
                  <option value="">Select time</option>
                  <option value="09:00">09:00 AM</option>
                  <option value="10:00">10:00 AM</option>
                  <option value="11:00">11:00 AM</option>
                  <option value="14:00">02:00 PM</option>
                  <option value="15:00">03:00 PM</option>
                  <option value="16:00">04:00 PM</option>
                </select>
              </div>
            </div>

            {/* Reason */}
            <div>
              <label className="text-gray-700 font-semibold mb-2 block">
                Reason for Visit
              </label>
              <textarea
                name="reason"
                value={formData.reason}
                onChange={handleChange}
                required
                rows={4}
                className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all resize-none bg-white/50"
                placeholder="Please describe your symptoms or reason for consultation..."
              />
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-6 py-4 rounded-xl font-semibold text-lg shadow-xl hover:shadow-2xl transition-all duration-300 disabled:opacity-50"
            >
              {loading ? 'Booking...' : 'Book Appointment'}
            </motion.button>
          </form>
        </GlassCard>

        <AnimatePresence>
          {(facilities.length > 0 || userLocation) && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="mt-12"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-2xl font-bold text-gray-800">Healthcare Map</h3>
                <div className="flex space-x-4">
                  <div className="flex items-center text-xs text-gray-500">
                    <div className="w-3 h-3 rounded-full bg-blue-500 mr-2 border border-white shadow-sm" />
                    You
                  </div>
                  <div className="flex items-center text-xs text-gray-500">
                    <div className="w-3 h-3 rounded-full bg-green-500 mr-2 border border-white shadow-sm" />
                    Doctor
                  </div>
                  <div className="flex items-center text-xs text-gray-500">
                    <div className="w-3 h-3 rounded-full bg-red-500 mr-2 border border-white shadow-sm" />
                    Hospital
                  </div>
                </div>
              </div>
              <HealthcareMap 
                facilities={facilities} 
                userLocation={userLocation}
                selectedFacilityId={formData.facilityId}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default BookAppointment;