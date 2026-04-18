import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ShieldCheck, Mail, Lock, AlertCircle, ArrowRight } from 'lucide-react';
import { login } from '../services/api';

const AdminLogin = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect if already logged in as admin
    const userStr = localStorage.getItem('user');
    if (userStr) {
      try {
        const user = JSON.parse(userStr);
        if (user.role === 'admin') navigate('/manage-doctors');
      } catch (e) {}
    }
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await login(email, password);
      if (res.user.role !== 'admin') {
        throw new Error('Access denied: You do not have administrator privileges.');
      }
      localStorage.setItem('token', res.access_token);
      localStorage.setItem('user', JSON.stringify(res.user));
      navigate('/manage-doctors');
    } catch (err: any) {
      setError(err.message || 'Verification failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen pt-28 pb-20 flex items-center justify-center px-4 bg-gradient-to-br from-slate-50 to-blue-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md w-full"
      >
        <div className="bg-white/70 backdrop-blur-xl p-8 rounded-3xl shadow-2xl border border-white/50">
          <div className="text-center mb-10">
            <div className="inline-flex p-4 rounded-2xl bg-indigo-600 shadow-lg shadow-indigo-200 mb-6 text-white">
              <ShieldCheck className="h-8 w-8" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 bg-gradient-to-r from-indigo-700 to-purple-600 bg-clip-text text-transparent">
              Admin Gateway
            </h1>
            <p className="text-gray-500 mt-2 font-medium">Restricted Administrative Access</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-700 ml-1">Admin Email</label>
              <div className="relative group">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 group-focus-within:text-indigo-500 transition-colors" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-white border border-gray-100 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 outline-none shadow-sm transition-all text-gray-800"
                  placeholder="admin@healthcare.com"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-gray-700 ml-1">Security Key</label>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 group-focus-within:text-indigo-500 transition-colors" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-12 pr-4 py-3.5 rounded-2xl bg-white border border-gray-100 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 outline-none shadow-sm transition-all text-gray-800"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-3 p-4 rounded-2xl bg-red-50 border border-red-100 text-red-600 text-sm"
              >
                <AlertCircle className="h-5 w-5 shrink-0" />
                <span className="font-medium">{error}</span>
              </motion.div>
            )}

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              disabled={loading}
              type="submit"
              className="w-full py-4 rounded-2xl bg-gradient-to-r from-indigo-700 to-purple-700 text-white font-bold shadow-xl shadow-indigo-200 hover:shadow-indigo-300 transition-all flex items-center justify-center gap-2 group disabled:opacity-70"
            >
              {loading ? 'Verifying...' : 'Authenticate'}
              <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </motion.button>
          </form>

          <p className="mt-8 text-center text-sm text-gray-400">
            Forgot credentials? Contact system support.
          </p>
        </div>
      </motion.div>
    </div>
  );
};

export default AdminLogin;
