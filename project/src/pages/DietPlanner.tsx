import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Upload, FileText, Loader, Utensils, Apple, Coffee, Drumstick, CheckCircle } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';
import { getProfile } from '../services/api';

interface MealItem {
  item: string;
  explanation: string;
  nutrients?: {
    p: number;
    f: number;
    c: number;
  };
}

interface DietPlan {
  breakfast: MealItem[];
  lunch: MealItem[];
  dinner: MealItem[];
  snacks: MealItem[];
}

const DietPlanner = () => {
  const [file, setFile] = useState<File | null>(null);
  const [healthData, setHealthData] = useState({
    age: '',
    weight: '',
    height: '',
    activityLevel: 'moderate',
    dietaryPreference: 'none',
    healthConditions: ''
  });

  useEffect(() => {
    const fetchProfileData = async () => {
      try {
        const data = await getProfile();
        if (data && data.profile) {
          setHealthData((prev: any) => ({
            ...prev,
            age: data.profile.age?.toString() || prev.age,
            weight: data.profile.weight?.toString() || prev.weight,
            height: data.profile.height?.toString() || prev.height,
            dietaryPreference: data.profile.diet_preference || prev.dietaryPreference,
            healthConditions: data.profile.allergies?.join(', ') || prev.healthConditions
          }));
        }
      } catch (err) {
        console.error('Failed to fetch profile for auto-population', err);
      }
    };
    fetchProfileData();
  }, []);

  const [loading, setLoading] = useState(false);
  const [dietPlan, setDietPlan] = useState<DietPlan | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setHealthData({
      ...healthData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('http://localhost:5000/api/generate-diet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          patient_data: {
            ...healthData,
            glucose: healthData.healthConditions.toLowerCase().includes('diabetes') ? 140 : 100,
            bp: healthData.healthConditions.toLowerCase().includes('pressure') ? '140/90' : '120/80',
          }
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setDietPlan(data.diet_plan);
      } else {
        alert('Failed to generate diet plan. Please try again.');
      }
    } catch (error) {
      console.error('Error generating diet plan:', error);
      alert('Failed to generate diet plan. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (dietPlan) {
    return (
      <div className="relative min-h-screen pt-20 pb-12">
        <AnimatedBackground />
        
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="text-center mb-8">
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                Your Personalized Diet Plan
              </h1>
              <p className="text-xl text-gray-600">
                AI-generated nutrition plan based on your health profile
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <GlassCard className="p-6">
                <div className="flex items-center mb-4">
                  <Coffee className="h-6 w-6 text-yellow-500 mr-3" />
                  <h3 className="text-2xl font-bold text-gray-800">Breakfast</h3>
                </div>
                <ul className="space-y-4">
                  {dietPlan.breakfast.map((item, idx) => (
                    <li key={idx}>
                      <div className="flex items-start">
                        <span className="text-green-500 mr-2 font-bold">• {item.item}</span>
                      </div>
                      <p className="text-sm text-gray-600 ml-4 italic mt-1 border-l-2 border-green-200 pl-3">
                        {item.explanation}
                      </p>
                    </li>
                  ))}
                </ul>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center mb-4">
                  <Drumstick className="h-6 w-6 text-orange-500 mr-3" />
                  <h3 className="text-2xl font-bold text-gray-800">Lunch</h3>
                </div>
                <ul className="space-y-4">
                  {dietPlan.lunch.map((item, idx) => (
                    <li key={idx}>
                      <div className="flex items-start">
                        <span className="text-orange-500 mr-2 font-bold">• {item.item}</span>
                      </div>
                      <p className="text-sm text-gray-600 ml-4 italic mt-1 border-l-2 border-orange-200 pl-3">
                        {item.explanation}
                      </p>
                    </li>
                  ))}
                </ul>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center mb-4">
                  <Utensils className="h-6 w-6 text-red-500 mr-3" />
                  <h3 className="text-2xl font-bold text-gray-800">Dinner</h3>
                </div>
                <ul className="space-y-4">
                  {dietPlan.dinner.map((item, idx) => (
                    <li key={idx}>
                      <div className="flex items-start">
                        <span className="text-red-500 mr-2 font-bold">• {item.item}</span>
                      </div>
                      <p className="text-sm text-gray-600 ml-4 italic mt-1 border-l-2 border-red-200 pl-3">
                        {item.explanation}
                      </p>
                    </li>
                  ))}
                </ul>
              </GlassCard>

              <GlassCard className="p-6">
                <div className="flex items-center mb-4">
                  <Apple className="h-6 w-6 text-green-500 mr-3" />
                  <h3 className="text-2xl font-bold text-gray-800">Snacks</h3>
                </div>
                <ul className="space-y-4">
                  {dietPlan.snacks.map((item, idx) => (
                    <li key={idx}>
                      <div className="flex items-start">
                        <span className="text-emerald-500 mr-2 font-bold">• {item.item}</span>
                      </div>
                      <p className="text-sm text-gray-600 ml-4 italic mt-1 border-l-2 border-emerald-200 pl-3">
                        {item.explanation}
                      </p>
                    </li>
                  ))}
                </ul>
              </GlassCard>
            </div>

            <div className="text-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setDietPlan(null)}
                className="px-8 py-4 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-semibold hover:shadow-xl transition-all duration-300"
              >
                Create New Plan
              </motion.button>
            </div>
          </motion.div>
        </div>
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
          <h1 className="text-5xl font-bold mb-6 bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
            Smart Diet Planner
          </h1>
          <p className="text-xl text-gray-600">
            Get personalized nutrition recommendations based on your health profile
          </p>
        </motion.div>

        <GlassCard className="p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* File Upload */}
            <div>
              <label className="text-gray-700 font-semibold mb-3 block">
                Upload Health Report (Optional)
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-green-500 transition-colors">
                <input
                  type="file"
                  id="file-upload"
                  onChange={handleFileChange}
                  accept=".pdf,.jpg,.jpeg,.png"
                  className="hidden"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  {file ? (
                    <div className="flex items-center justify-center">
                      <FileText className="h-8 w-8 text-green-500 mr-3" />
                      <span className="text-gray-700">{file.name}</span>
                    </div>
                  ) : (
                    <div>
                      <Upload className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                      <p className="text-gray-600">Click to upload or drag and drop</p>
                      <p className="text-sm text-gray-500 mt-2">PDF, JPG, PNG up to 10MB</p>
                    </div>
                  )}
                </label>
              </div>
            </div>

            {/* Health Data */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="text-gray-700 font-semibold mb-2 block">Age</label>
                <input
                  type="number"
                  name="age"
                  value={healthData.age}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-green-500 focus:ring-2 focus:ring-green-200 transition-all"
                  placeholder="25"
                />
              </div>

              <div>
                <label className="text-gray-700 font-semibold mb-2 block">Weight (kg)</label>
                <input
                  type="number"
                  name="weight"
                  value={healthData.weight}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-green-500 focus:ring-2 focus:ring-green-200 transition-all"
                  placeholder="70"
                />
              </div>

              <div>
                <label className="text-gray-700 font-semibold mb-2 block">Height (cm)</label>
                <input
                  type="number"
                  name="height"
                  value={healthData.height}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-green-500 focus:ring-2 focus:ring-green-200 transition-all"
                  placeholder="170"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="text-gray-700 font-semibold mb-2 block">Activity Level</label>
                <select
                  name="activityLevel"
                  value={healthData.activityLevel}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-green-500 focus:ring-2 focus:ring-green-200 transition-all"
                >
                  <option value="sedentary">Sedentary</option>
                  <option value="light">Light Activity</option>
                  <option value="moderate">Moderate Activity</option>
                  <option value="active">Very Active</option>
                  <option value="extreme">Extremely Active</option>
                </select>
              </div>

              <div>
                <label className="text-gray-700 font-semibold mb-2 block">Dietary Preference</label>
                <select
                  name="dietaryPreference"
                  value={healthData.dietaryPreference}
                  onChange={handleInputChange}
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-green-500 focus:ring-2 focus:ring-green-200 transition-all"
                >
                  <option value="none">No Preference</option>
                  <option value="vegetarian">Vegetarian</option>
                  <option value="vegan">Vegan</option>
                  <option value="keto">Keto</option>
                  <option value="paleo">Paleo</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-gray-700 font-semibold mb-2 block">
                Health Conditions & Allergies
              </label>
              <textarea
                name="healthConditions"
                value={healthData.healthConditions}
                onChange={handleInputChange}
                rows={4}
                className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-green-500 focus:ring-2 focus:ring-green-200 transition-all resize-none"
                placeholder="e.g., Diabetes, High blood pressure, Lactose intolerance..."
              />
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-4 rounded-xl font-semibold text-lg shadow-xl hover:shadow-2xl transition-all duration-300 disabled:opacity-50 flex items-center justify-center"
            >
              {loading ? (
                <>
                  <Loader className="animate-spin h-5 w-5 mr-2" />
                  Generating Your Diet Plan...
                </>
              ) : (
                'Generate Diet Plan'
              )}
            </motion.button>
          </form>
        </GlassCard>
      </div>
    </div>
  );
};

export default DietPlanner;