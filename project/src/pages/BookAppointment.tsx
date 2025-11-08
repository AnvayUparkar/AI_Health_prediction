import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Video, MapPin, User, Mail, Phone, Clock, CheckCircle } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';

const BookAppointment = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    mode: 'online',
    date: '',
    time: '',
    reason: ''
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('http://localhost:5000/api/appointments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
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
            reason: ''
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
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Personal Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <User className="h-5 w-5 mr-2" />
                  Full Name
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <Mail className="h-5 w-5 mr-2" />
                  Email
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                  placeholder="john@example.com"
                />
              </div>
            </div>

            <div>
              <label className="flex items-center text-gray-700 font-semibold mb-2">
                <Phone className="h-5 w-5 mr-2" />
                Phone Number
              </label>
              <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                required
                className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                placeholder="+1 (555) 000-0000"
              />
            </div>

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
                      : 'border-gray-300 hover:border-blue-300'
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
                      : 'border-gray-300 hover:border-blue-300'
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
                  <Calendar className="h-5 w-5 mr-2" />
                  Preferred Date
                </label>
                <input
                  type="date"
                  name="date"
                  value={formData.date}
                  onChange={handleChange}
                  required
                  min={new Date().toISOString().split('T')[0]}
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                />
              </div>

              <div>
                <label className="flex items-center text-gray-700 font-semibold mb-2">
                  <Clock className="h-5 w-5 mr-2" />
                  Preferred Time
                </label>
                <select
                  name="time"
                  value={formData.time}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
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
                className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all resize-none"
                placeholder="Please describe your symptoms or reason for consultation..."
              />
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-6 py-4 rounded-xl font-semibold text-lg shadow-xl hover:shadow-2xl transition-all duration-300 disabled:opacity-50"
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