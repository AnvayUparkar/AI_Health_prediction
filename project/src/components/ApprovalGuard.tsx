import React from 'react';
import { ShieldAlert, Clock, Lock } from 'lucide-react';
import { motion } from 'framer-motion';

interface ApprovalGuardProps {
  user: any;
  children: React.ReactNode;
}

const ApprovalGuard: React.FC<ApprovalGuardProps> = ({ user, children }) => {
  const isDoctor = user?.role?.toLowerCase() === 'doctor';
  const isApproved = user?.isApproved === true;

  if (isDoctor && !isApproved) {
    return (
      <div className="relative">
        {/* Blured Content Overlay */}
        <div className="filter blur-sm pointer-events-none select-none">
          {children}
        </div>

        {/* Lock Overlay */}
        <div className="absolute inset-0 z-50 flex items-center justify-center p-6 bg-white/30 backdrop-blur-[2px] rounded-3xl border border-white/50 shadow-2xl overflow-hidden">
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-md w-full bg-white/90 backdrop-blur-xl p-8 rounded-3xl shadow-2xl border border-blue-100 text-center"
          >
            <div className="mb-6 relative inline-block">
              <div className="absolute inset-0 bg-blue-100 rounded-full animate-ping opacity-25" />
              <div className="relative bg-gradient-to-br from-blue-500 to-indigo-600 p-4 rounded-full shadow-lg">
                <ShieldAlert className="h-10 w-10 text-white" />
              </div>
            </div>
            
            <h2 className="text-2xl font-bold text-gray-800 mb-3">Verification Pending</h2>
            <p className="text-gray-600 mb-8 leading-relaxed">
              Your doctor account is currently under review by our medical administration team. 
              Core clinical features will be unlocked once your credentials are verified.
            </p>

            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-blue-50/50 rounded-2xl border border-blue-100">
                <Clock className="h-5 w-5 text-blue-500" />
                <span className="text-sm text-blue-700 font-medium text-left">
                  Verification usually takes 24-48 hours.
                </span>
              </div>
              
              <div className="flex items-center gap-3 p-4 bg-amber-50/50 rounded-2xl border border-amber-100">
                <Lock className="h-5 w-5 text-amber-500" />
                <span className="text-sm text-amber-700 font-medium text-left">
                  Feature access restricted for patient safety.
                </span>
              </div>
            </div>

            <p className="mt-8 text-xs text-gray-400 font-medium uppercase tracking-wider">
              Secure Medical Environment
            </p>
          </motion.div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default ApprovalGuard;
