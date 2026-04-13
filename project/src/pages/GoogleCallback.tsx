import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Loader, CheckCircle, XCircle } from 'lucide-react';
import api from '../services/api';

const GoogleCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Completing Google authentication...');
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      if (!code) {
        setStatus('error');
        setMessage('Authorization code not found. Please try again.');
        return;
      }

      try {
        const response = await api.post('/api/auth/google/callback', { code });
        if (response.data.success) {
          // If the backend returned a new token (login flow), store it
          if (response.data.token) {
            localStorage.setItem('token', response.data.token);
            localStorage.setItem('user', JSON.stringify(response.data.user || {}));
            // Dispatch storage event for navbar/app to detect login
            window.dispatchEvent(new Event('storage'));
          }

          setStatus('success');
          setMessage('Google account linked successfully! Redirecting...');
          setTimeout(() => navigate('/'), 2000);
        } else {
          setStatus('error');
          setMessage(response.data.error || 'Failed to link Google account.');
        }
      } catch (err: any) {
        setStatus('error');
        setMessage(err.response?.data?.error || 'A server error occurred during authentication.');
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-md w-full p-8 bg-white rounded-2xl shadow-xl text-center"
      >
        {status === 'loading' && (
          <div className="flex flex-col items-center">
            <Loader className="h-12 w-12 text-blue-500 animate-spin mb-4" />
            <h2 className="text-xl font-bold text-gray-800">{message}</h2>
          </div>
        )}

        {status === 'success' && (
          <div className="flex flex-col items-center">
            <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
            <h2 className="text-xl font-bold text-gray-800">{message}</h2>
          </div>
        )}

        {status === 'error' && (
          <div className="flex flex-col items-center">
            <XCircle className="h-12 w-12 text-red-500 mb-4" />
            <h2 className="text-xl font-bold text-gray-800">{message}</h2>
            <button
              onClick={() => navigate('/login')}
              className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Back to Login
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default GoogleCallback;
