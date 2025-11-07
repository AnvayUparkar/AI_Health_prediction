import React from 'react';
import { Heart, Shield, Users } from 'lucide-react';

const Footer = () => {
  return (
    <footer className="bg-white border-t border-gray-200 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <div className="p-2 bg-health-primary rounded-lg">
                <Heart className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-bold text-health-text">AI Health Predictor</span>
            </div>
            <p className="text-gray-600 text-sm leading-relaxed">
              Empowering proactive healthcare through AI-driven risk assessment and early detection insights.
            </p>
          </div>

          {/* Features */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-health-text">Our Focus</h3>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Shield className="h-4 w-4 text-health-primary" />
                <span className="text-sm text-gray-600">Privacy & Security</span>
              </div>
              <div className="flex items-center space-x-2">
                <Heart className="h-4 w-4 text-health-primary" />
                <span className="text-sm text-gray-600">Accurate Predictions</span>
              </div>
              <div className="flex items-center space-x-2">
                <Users className="h-4 w-4 text-health-primary" />
                <span className="text-sm text-gray-600">User-Friendly Design</span>
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-health-text">Important Notice</h3>
            <div className="text-sm text-gray-600 leading-relaxed">
              <p className="mb-2">
                This tool is for educational purposes only and is not a substitute for professional medical advice.
              </p>
              <p className="font-medium text-health-primary">
                Please consult a doctor for any health concerns.
              </p>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200 mt-8 pt-8 text-center">
          <p className="text-sm text-gray-600">
            © 2025 AI Health Predictor. Created with ❤️ for better health awareness.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;