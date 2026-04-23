import React, { useState, useEffect } from 'react';



import { motion, AnimatePresence } from 'framer-motion';
import { 
  Calendar, Video, MapPin, User, Mail, Phone, Clock, 
  CheckCircle, Navigation, Stethoscope, Info, Search, 
  Globe, ChevronRight, ChevronDown, AlertCircle 
} from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';
import { getUserLocation, UserLocation } from '../services/geoService';
import { fetchNearbyHealthcare } from '../services/overpassService';
import { processFacilities, HealthcareFacility } from '../services/healthcareProcessor';
import HealthcareMap from '../components/HealthcareMap';
import { getDoctorsByHospital, searchHospitals, bookSubSlot, getDoctorAvailability } from '../services/api';
import toast from 'react-hot-toast';





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
    doctorId: '',
    subSlot: null as any // Added to store sub-slot info
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  
  // Nearby Healthcare State
  const [facilities, setFacilities] = useState<HealthcareFacility[]>([]);
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Search States
  const [localSearch, setLocalSearch] = useState('');
  const [globalSearch, setGlobalSearch] = useState('');
  const [globalSuggestions, setGlobalSuggestions] = useState<any[]>([]);
  const [isGlobalSearching, setIsGlobalSearching] = useState(false);

  // Doctors
  const [hospitalDoctors, setHospitalDoctors] = useState<any[]>([]);
  const [fetchingDoctors, setFetchingDoctors] = useState(false);
  const [addressSearch, setAddressSearch] = useState('');
  const [isSearchingAddress, setIsSearchingAddress] = useState(false);

  // Slot Availability States
  const [availability, setAvailability] = useState<any[]>([]);
  const [isAvailabilityLoading, setIsAvailabilityLoading] = useState(false);
  const [expandedHour, setExpandedHour] = useState<string | null>(null);


  // Fetch availability when doctor or date changes
  useEffect(() => {
    if (formData.doctorId && formData.date) {
      fetchAvailability();
    } else {
      setAvailability([]);
      setFormData(prev => ({ ...prev, time: '', subSlot: null }));
    }
  }, [formData.doctorId, formData.date]);

  const fetchAvailability = async () => {
    setIsAvailabilityLoading(true);
    try {
      const data = await getDoctorAvailability(formData.doctorId, formData.date);
      setAvailability(data.slots || []);
      // Auto-expand first available hour if none expanded
      if (data.slots && data.slots.length > 0 && !expandedHour) {
        const firstAvailable = data.slots.find((s: any) => s.remaining > 0);
        if (firstAvailable) setExpandedHour(firstAvailable.hour);
      }
    } catch (error) {
      console.error('Fetch error:', error);
      toast.error('Failed to load doctor availability');
    } finally {
      setIsAvailabilityLoading(false);
    }
  };



  useEffect(() => {
    if (!formData.facilityId) {
      setHospitalDoctors([]);
      if (!formData.subSlot) { // Don't clear if we just came from slot picker
        setFormData(prev => ({ ...prev, doctorId: '' }));
      }
      return;
    }

    const facility = facilities.find(f => String(f.id) === String(formData.facilityId));
    if (facility && facility.name) {
      fetchDoctors(facility.name);
    }

  }, [formData.facilityId]);

  // Global Search Debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      if (globalSearch.length >= 3) {
        performGlobalSearch(globalSearch);
      } else {
        setGlobalSuggestions([]);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [globalSearch]);

  const performGlobalSearch = async (query: string) => {
    setIsGlobalSearching(true);
    try {
      const results = await searchHospitals(query);
      setGlobalSuggestions(results || []);
    } catch (err) {
      console.error('Global search failed', err);
    } finally {
      setIsGlobalSearching(false);
    }
  };

  const handleGlobalSelection = (hospital: any) => {
    // Convert global hospital to HealthcareFacility format
    const newFacility: HealthcareFacility = {
      id: `global-${hospital.id}`,
      name: hospital.name,
      type: 'hospital',
      lat: hospital.lat,
      lon: hospital.lon,
      distance: 0, // We could calculate this if userLocation exists
      address: hospital.address,
      isGlobal: true // Flag to identify as global (no SOS)
    };

    if (userLocation) {
        // Calculate distance for UI consistency
        const R = 6371;
        const dLat = (hospital.lat - userLocation.latitude) * Math.PI / 180;
        const dLon = (hospital.lon - userLocation.longitude) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(userLocation.latitude * Math.PI / 180) * Math.cos(hospital.lat * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        newFacility.distance = R * c;
    }

    // Add to facilities if not already there
    setFacilities(prev => {
        const exists = prev.find(f => f.id === newFacility.id);
        return exists ? prev : [newFacility, ...prev];
    });

    setFormData(prev => ({ ...prev, facilityId: String(newFacility.id) }));
    setGlobalSearch('');
    setGlobalSuggestions([]);
  };

  // Re-fetch nearby facilities when location changes
  useEffect(() => {
    if (userLocation) {
      fetchNearbyFacilities(userLocation.latitude, userLocation.longitude);
    }
  }, [userLocation?.latitude, userLocation?.longitude]);

  const fetchNearbyFacilities = async (lat: number, lon: number) => {
    setSearching(true);
    setSearchError(null);
    try {
      const rawData = await fetchNearbyHealthcare(lat, lon);
      const processed = processFacilities(rawData, lat, lon);
      if (processed.length === 0) {
        setSearchError('No nearby healthcare facilities found within 5km.');
      } else {
        setFacilities(processed);
        // Expose to window for legacy support if needed
        (window as any).nearbyHospitals = processed;
      }
    } catch (err: any) {
      setSearchError(err.message || 'Failed to fetch medical facilities.');
    } finally {
      setSearching(false);
    }
  };

  // Local filtering
  const filteredFacilities = facilities.filter(f => 
    f.name.toLowerCase().includes(localSearch.toLowerCase())
  );

  const handleAddressSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addressSearch.trim()) return;
    
    setIsSearchingAddress(true);
    try {
      const resp = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(addressSearch)}&limit=1`);
      const data = await resp.json();
      if (data && data.length > 0) {
        const { lat, lon } = data[0];
        setUserLocation({ latitude: parseFloat(lat), longitude: parseFloat(lon) });
      } else {
        setSearchError('Address not found. Please try a different location.');
      }
    } catch (err) {
      console.error('Address search failed', err);
    } finally {
      setIsSearchingAddress(false);
    }
  };

  const fetchDoctors = async (hospitalName: string) => {
    setFetchingDoctors(true);
    setSearchError(null);
    
    // CLEAR OLD DOCTORS before fetching new ones
    setHospitalDoctors([]);
    if (!formData.subSlot) {
      setFormData(prev => ({ ...prev, doctorId: '' }));
    }

    try {
      // Fetch doctors ONLY for the selected hospital by name
      // Backend matches against User.hospitals JSON field (role='doctor')
      const docs = await getDoctorsByHospital(hospitalName);
      setHospitalDoctors(docs || []);
      
      // SAFETY CHECK
      if (!docs || docs.length === 0) {
        setSearchError("No doctors available for this hospital");
      } else {
        setSearchError(null);
        if (!formData.doctorId) {
          setFormData(prev => ({ ...prev, doctorId: docs[0].id }));
        }
      }
    } catch (err) {
      console.error('Failed to fetch doctors', err);
    } finally {
      setFetchingDoctors(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const selectedFacility = facilities.find(f => String(f.id) === String(formData.facilityId));
    
    const userString = localStorage.getItem('user');
    const currentUser = userString ? JSON.parse(userString) : null;
    
    const bookingData = {
      ...formData,
      selected_doctor: selectedFacility ? `${selectedFacility.name} (${selectedFacility.type})` : '',
      doctor_id: formData.doctorId || null,
      patient_id: currentUser ? currentUser.id : null,
      is_global: selectedFacility?.isGlobal || false
    };

    try {
      // IF SUB-SLOT IS SELECTED, use the specialized booking API first
      if (formData.subSlot && formData.doctorId && currentUser?.id) {
        await bookSubSlot({
          doctorId: formData.doctorId,
          date: formData.date,
          slot: formData.subSlot,
          userId: currentUser.id
        });
      }

      // Record the appointment in the main SQL database as well
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
            doctorId: '',
            subSlot: null
          });
        }, 5000);
      }
    } catch (error: any) {
      console.error('Error booking appointment:', error);
      toast.error(error.response?.data?.error || 'Failed to book appointment. Please try again.');
    } finally {
      setLoading(false);
    }
  };


  const handleFindNearby = async () => {
    setSearching(true);
    setSearchError(null);
    try {
      const location = await getUserLocation(15000); // 15s timeout
      setUserLocation(location);
    } catch (err: any) {
      setSearchError(err.message || 'Failed to fetch location automatically.');
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
          <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
            <form onSubmit={handleAddressSearch} className="flex-1 w-full relative">
              <input
                type="text"
                placeholder="Search your area (e.g. Airoli, Navi Mumbai)"
                value={addressSearch}
                onChange={(e) => setAddressSearch(e.target.value)}
                className="w-full pl-10 pr-24 py-2.5 rounded-2xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-white/70"
              />
              <MapPin className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <button
                type="submit"
                disabled={isSearchingAddress}
                className="absolute right-1.5 top-1.5 bg-blue-600 text-white px-4 py-1.5 rounded-xl text-xs font-bold hover:bg-blue-700 disabled:opacity-50"
              >
                {isSearchingAddress ? '...' : 'Set Location'}
              </button>
            </form>

            <motion.button
              type="button"
              onClick={handleFindNearby}
              disabled={searching}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center space-x-2 bg-blue-50 text-blue-600 px-5 py-2.5 rounded-2xl font-bold border border-blue-100 shadow-sm hover:shadow-md transition-all active:bg-blue-100 disabled:opacity-50 w-full md:w-auto justify-center"
            >
              <Navigation className={`h-4 w-4 ${searching ? 'animate-pulse' : ''}`} />
              <span>{searching ? 'Locating...' : 'Auto Detect'}</span>
            </motion.button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="bg-blue-50/30 p-4 rounded-2xl border border-blue-100/50 mb-6">
              <div className="flex items-center space-x-2 mb-3 text-blue-800">
                <Info className="h-4 w-4" />
                <span className="text-sm font-bold uppercase tracking-wider">Step 1: Locate Facilities</span>
              </div>
              <HealthcareMap 
                facilities={facilities} 
                userLocation={userLocation}
                selectedFacilityId={formData.facilityId}
                onLocationChange={(loc) => setUserLocation(loc)}
              />
              <p className="mt-3 text-[11px] text-gray-500 italic text-center">
                Map markers update automatically. Drag the blue pin to refine your location.
              </p>
            </div>

            {/* Premium Search Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              <div className="relative group">
                <label className="flex items-center text-[11px] font-bold text-blue-600 uppercase tracking-widest mb-1.5 ml-1">
                   <Search className="h-3 w-3 mr-1" /> Local Search (5km)
                </label>
                <input
                  type="text"
                  id="localSearch"
                  placeholder="Filter nearby hospitals..."
                  value={localSearch}
                  onChange={(e) => setLocalSearch(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-blue-100 bg-blue-50/30 focus:bg-white focus:ring-2 focus:ring-blue-200 transition-all text-sm shadow-sm placeholder:text-blue-300"
                />
              </div>

              <div className="relative group">
                <label className="flex items-center text-[11px] font-bold text-cyan-600 uppercase tracking-widest mb-1.5 ml-1">
                   <Globe className="h-3 w-3 mr-1" /> Global Search
                </label>
                <div className="relative">
                  <input
                    type="text"
                    id="globalSearch"
                    placeholder="Search any hospital worldwide..."
                    value={globalSearch}
                    onChange={(e) => setGlobalSearch(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-cyan-100 bg-cyan-50/30 focus:bg-white focus:ring-2 focus:ring-cyan-200 transition-all text-sm shadow-sm placeholder:text-cyan-300"
                  />
                  {isGlobalSearching && (
                    <div className="absolute right-3 top-3.5 h-4 w-4 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                  )}
                </div>

                {/* Suggestions Dropdown */}
                <AnimatePresence>
                  {globalSuggestions.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute z-20 mt-2 w-full bg-white rounded-2xl shadow-2xl border border-gray-100 overflow-hidden backdrop-blur-xl"
                    >
                      <div className="p-2 max-h-[250px] overflow-y-auto">
                        {globalSuggestions.map((h, idx) => (
                          <div
                            key={h.id || idx}
                            onClick={() => handleGlobalSelection(h)}
                            className="p-3 hover:bg-gradient-to-r hover:from-cyan-50 hover:to-blue-50 cursor-pointer rounded-xl transition-all group flex items-start space-x-3 border border-transparent hover:border-cyan-100 mb-1"
                          >
                            <div className="bg-cyan-100 p-2 rounded-lg text-cyan-600 group-hover:bg-cyan-600 group-hover:text-white transition-colors mt-0.5">
                              <MapPin className="h-4 w-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="font-bold text-gray-800 text-sm truncate">{h.name}</div>
                              <div className="text-[10px] text-gray-500 truncate">{h.address}</div>
                            </div>
                            <ChevronRight className="h-4 w-4 text-gray-300 group-hover:text-cyan-500 self-center" />
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

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
                  Select Healthcare Facility
                </label>
                <select
                  name="facilityId"
                  value={formData.facilityId}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all bg-white/50 shadow-sm"
                >
                  <option value="">{filteredFacilities.length > 0 ? '-- Choose Selection --' : 'No matches found'}</option>
                  {filteredFacilities.map(f => (
                    <option key={f.id} value={f.id}>
                      {f.isGlobal ? '🌍 ' : ''}{f.name} ({f.type.charAt(0).toUpperCase() + f.type.slice(1)}) - {f.distance >= 1 ? `${f.distance.toFixed(1)} km` : `${(f.distance*1000).toFixed(0)} m`}
                    </option>
                  ))}
                </select>
                {facilities.length === 0 && !searching && (
                  <p className="mt-1 text-[10px] text-amber-600 font-medium italic pl-1 flex items-center">
                    <Info className="h-3 w-3 mr-1" />
                    Click "Auto Detect" or search above to find nearby specialists.
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

              <div className="md:col-span-2">
                <label className="flex items-center text-gray-700 font-semibold mb-3">
                  <Clock className="h-5 w-5 mr-2 text-blue-500" />
                  Select Consultation Time
                </label>
                
                {formData.doctorId && formData.date ? (
                  <div className="space-y-4">
                    {isAvailabilityLoading ? (
                      <div className="flex flex-col items-center justify-center py-10 bg-white/40 rounded-2xl border border-dashed border-gray-200">
                        <div className="w-8 h-8 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mb-3" />
                        <p className="text-xs text-gray-500 font-medium">Checking live availability...</p>
                      </div>
                    ) : availability.length > 0 ? (
                      <div className="grid grid-cols-1 gap-3">
                        {availability.map((hourSlot) => {
                          const isFull = hourSlot.remaining === 0;
                          const isExpanded = expandedHour === hourSlot.hour;
                          const hasSelectedInThisHour = formData.subSlot && hourSlot.subSlots.some((s: any) => s.start === formData.subSlot.start);

                          return (
                            <div key={hourSlot.hour} className={`rounded-2xl border transition-all overflow-hidden ${hasSelectedInThisHour ? 'border-blue-500 bg-blue-50/30' : 'border-gray-100 bg-white/50'}`}>
                              <button
                                type="button"
                                onClick={() => !isFull && setExpandedHour(isExpanded ? null : hourSlot.hour)}
                                disabled={isFull}
                                className={`w-full p-4 flex items-center justify-between text-left ${isFull ? 'opacity-40 cursor-not-allowed' : 'hover:bg-blue-50/20'}`}
                              >
                                <div className="flex items-center gap-3">
                                  <div className={`p-2 rounded-lg ${isFull ? 'bg-gray-200 text-gray-500' : 'bg-blue-100 text-blue-600'}`}>
                                    <Clock className="w-4 h-4" />
                                  </div>
                                  <div>
                                    <h4 className="font-bold text-gray-800 text-sm">{hourSlot.hour}</h4>
                                    <p className={`text-[10px] font-bold ${isFull ? 'text-gray-400' : 'text-blue-500'}`}>
                                      {isFull ? 'FULLY BOOKED' : `${hourSlot.remaining} / ${hourSlot.total} slots remaining`}
                                    </p>
                                  </div>
                                </div>
                                {!isFull && (
                                  <motion.div animate={{ rotate: isExpanded ? 180 : 0 }}>
                                    <ChevronDown className="w-4 h-4 text-gray-400" />
                                  </motion.div>
                                )}
                              </button>

                              <AnimatePresence>
                                {isExpanded && (
                                  <motion.div
                                    initial={{ height: 0 }}
                                    animate={{ height: 'auto' }}
                                    exit={{ height: 0 }}
                                    className="overflow-hidden bg-white/30 border-t border-gray-100"
                                  >
                                    <div className="p-4 grid grid-cols-2 sm:grid-cols-3 gap-2">
                                      {hourSlot.subSlots.map((sub: any, idx: number) => {
                                        const isSelected = formData.subSlot?.start === sub.start && formData.subSlot?.end === sub.end;
                                        return (
                                          <button
                                            key={idx}
                                            type="button"
                                            disabled={sub.isBooked}
                                            onClick={() => setFormData(prev => ({ 
                                              ...prev, 
                                              time: `${sub.start} - ${sub.end}`, 
                                              subSlot: sub 
                                            }))}
                                            className={`p-2.5 rounded-xl border-2 text-xs font-bold transition-all ${
                                              sub.isBooked
                                                ? 'bg-gray-50 border-gray-50 text-gray-300 cursor-not-allowed'
                                                : isSelected
                                                  ? 'bg-blue-600 border-blue-600 text-white shadow-md'
                                                  : 'bg-white border-white hover:border-blue-200 text-gray-600 shadow-sm'
                                            }`}
                                          >
                                            {sub.start}
                                          </button>
                                        );
                                      })}
                                    </div>
                                  </motion.div>
                                )}
                              </AnimatePresence>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="p-8 text-center bg-amber-50/50 rounded-2xl border border-amber-100">
                        <AlertCircle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
                        <p className="text-sm text-amber-800 font-bold">No Slots Set</p>
                        <p className="text-xs text-amber-600 mt-1">This doctor hasn't configured availability for this date.</p>
                      </div>
                    )}
                    
                    {formData.subSlot && (
                      <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-4 bg-green-50 border border-green-200 rounded-xl flex items-center gap-3"
                      >
                        <div className="p-2 bg-green-500 text-white rounded-lg">
                          <CheckCircle className="w-4 h-4" />
                        </div>
                        <div>
                          <p className="text-[10px] font-black text-green-600 uppercase tracking-widest">Selected Appointment</p>
                          <p className="text-sm font-bold text-green-800">{formData.date} @ {formData.subSlot.start} - {formData.subSlot.end}</p>
                        </div>
                      </motion.div>
                    )}
                  </div>
                ) : (
                  <div className="p-10 text-center bg-gray-50 rounded-2xl border-2 border-gray-200 border-dashed text-gray-400">
                    <Clock className="w-8 h-8 mx-auto mb-3 opacity-20" />
                    <p className="text-sm font-medium">Select a doctor and date above to view available time slots.</p>
                  </div>
                )}
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
      </div>
    </div>
  );
};

export default BookAppointment;