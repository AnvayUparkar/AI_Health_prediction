import React, { useState, useEffect } from 'react';
import { Sun as Lung, AlertCircle, CheckCircle, Clock } from 'lucide-react';

const LungCancer = () => {
  // Default feature list used if backend /model-info cannot be reached
  const DEFAULT_FEATURES = [
    'Gender',
    'Age',
    'Smoking',
    'Yellow fingers',
    'Anxiety',
    'Peer_pressure',
    'Chronic Disease',
    'Fatigue',
    'Allergy',
    'Wheezing',
    'Alcohol',
    'Coughing',
    'Shortness of Breath',
    'Swallowing Difficulty',
    'Chest Pain'
  ];

  // Features will be fetched from backend /model-info if available so frontend keys
  // always match the model's expected feature names.
  const [features, setFeatures] = useState<string[]>(DEFAULT_FEATURES);

  const [formData, setFormData] = useState<Record<string, string>>(
    Object.fromEntries(DEFAULT_FEATURES.map(f => [f, '']))
  );
  
  const [result, setResult] = useState<{prediction: string, confidence: string} | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Build questions dynamically from `features` so the frontend always matches backend
  const buildQuestion = (field: string) => {
    const f = field.toLowerCase();
    if (f.includes('age')) return { field, label: 'What is your current age?', type: 'number', min: 1, max: 120 };
    if (f.includes('gender')) return { field, label: `${field}`, type: 'select', options: [{ value: '1', label: 'Male' }, { value: '2', label: 'Female' }] };
    // default to small-range sliders for other ordinal features
    return { field, label: `${field}`, type: 'range', min: 1, max: 3 };
  };

  const questions = features.map(buildQuestion);

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    // Only send features present in backend
    const payload = Object.fromEntries(
      Object.entries(formData).filter(([key]) => features.includes(key))
    );
    try {
      const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5000';
      const response = await fetch(`${API_URL}/predict_lung_cancer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        // Show backend error in UI
        setResult(null);
        alert(data.error || 'Prediction failed. Please check your inputs and try again.');
        return;
      }
      setResult(data);
    } catch (error: any) {
      console.error('Prediction error:', error);
      alert(error.message || 'Prediction failed. Please try again or check if the backend server is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const getResultColor = (prediction: string) => {
    switch (prediction) {
      case 'Low': return 'text-health-low bg-green-50 border-green-200';
      case 'Medium': return 'text-health-medium bg-yellow-50 border-yellow-200';
      case 'High': return 'text-health-high bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const isFormValid = features.every(f => (formData[f] ?? '') !== '');

  // Fetch model-info from backend to align field names at runtime
  useEffect(() => {
    const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5000';
    // Helper: parse CSV header line into feature list (exclude target columns)
    const parseCsvHeader = async (csvUrl: string) => {
      try {
        const res = await fetch(csvUrl);
        if (!res.ok) throw new Error('CSV fetch failed');
        const text = await res.text();
        const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
        if (!lines.length) return null;
        const header = lines[0].split(',').map(h => h.trim());
        const excluded = new Set(['Level', 'Level_encoded', 'Level_encoded ']);
        const features = header.filter(h => !excluded.has(h));
        return features;
      } catch (e) {
        return null;
      }
    };

    // New behavior: prefer the local CSV header first, then fallback to backend /model-info.
    (async () => {
      // Try CSV first (preferred)
      try {
        const csvName = encodeURI('cancer patient data sets.csv');
        const csvUrl = `${window.location.origin}/${csvName}`;
        const csvFeatures = await parseCsvHeader(csvUrl);
        if (csvFeatures && csvFeatures.length) {
          setFeatures(csvFeatures);
          setFormData(prev => {
            const copy = { ...prev };
            csvFeatures.forEach((f: string) => { if (!(f in copy)) copy[f] = ''; });
            return copy;
          });
          return; // done
        }
      } catch (e) {
        // continue to try model-info
      }

      // CSV not available or failed — try backend /model-info
      try {
        const res = await fetch(`${API_URL}/model-info`);
        if (res.ok) {
          const json = await res.json();
          const mf = json?.model_feature_order && json.model_feature_order.length ? json.model_feature_order
            : (json?.lung_cancer_features_from_dataset && json.lung_cancer_features_from_dataset.length ? json.lung_cancer_features_from_dataset : null);
          if (mf) {
            setFeatures(mf);
            setFormData(prev => {
              const copy = { ...prev };
              mf.forEach((f: string) => { if (!(f in copy)) copy[f] = ''; });
              return copy;
            });
            return;
          }
        }
      } catch (e) {
        // ignore; will keep defaults
      }
    })();
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-red-50 rounded-2xl">
            <Lung className="h-12 w-12 text-red-500" />
          </div>
        </div>
        <h1 className="text-4xl font-bold text-health-text mb-4">Lung Cancer Risk Questionnaire</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Please answer all questions honestly for the most accurate assessment. This evaluation 
          considers multiple risk factors including lifestyle, environmental, and genetic factors.
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-8">
        <form id="lung-cancer-form" onSubmit={handleSubmit} className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {questions.map((question) => (
              <div key={question.field} className="space-y-3">
                <label 
                  htmlFor={question.field}
                  className="block text-sm font-semibold text-health-text"
                >
                  {question.label}
                </label>
                
                {question.type === 'number' && (
                  <input
                    type="number"
                    id={question.field}
                    name={question.field}
                    min={question.min}
                    max={question.max}
                    value={formData[question.field as keyof typeof formData]}
                    onChange={(e) => handleInputChange(question.field, e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-health-primary focus:border-transparent transition-all duration-200"
                    required
                  />
                )}
                
                {question.type === 'select' && question.options && (
                  <select
                    id={question.field}
                    name={question.field}
                    value={formData[question.field as keyof typeof formData]}
                    onChange={(e) => handleInputChange(question.field, e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-health-primary focus:border-transparent transition-all duration-200"
                    required
                  >
                    <option value="">Select an option</option>
                    {question.options.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                )}
                
                {question.type === 'range' && (
                  <div className="space-y-2">
                    <input
                      type="range"
                      id={question.field}
                      name={question.field}
                      min={question.min}
                      max={question.max}
                      value={formData[question.field as keyof typeof formData]}
                      onChange={(e) => handleInputChange(question.field, e.target.value)}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                      required
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>{question.min}</span>
                      <span className="font-medium text-health-primary">
                        {formData[question.field as keyof typeof formData] || question.min}
                      </span>
                      <span>{question.max}</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="flex flex-col items-center space-y-4 pt-8 border-t border-gray-200">
            <button
              type="submit"
              disabled={!isFormValid || isLoading}
              className="px-8 py-4 bg-health-primary text-white rounded-xl font-semibold hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center space-x-2"
            >
              {isLoading ? (
                <>
                  <Clock className="h-5 w-5 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <span>Predict My Risk</span>
              )}
            </button>
            
            {!isFormValid && (
              <p className="text-sm text-gray-500 flex items-center space-x-1">
                <AlertCircle className="h-4 w-4" />
                <span>Please complete all fields to get your prediction</span>
              </p>
            )}
          </div>
        </form>

        {/* Results */}
        <div id="result">
          {result && (
            <div className="mt-12 p-8 border-2 rounded-2xl transition-all duration-500 animate-fade-in">
              <div className={`${getResultColor(result.prediction)}`}>
                <div className="text-center">
                  <div className="flex justify-center mb-4">
                    {result.prediction === 'Low' && <CheckCircle className="h-16 w-16 text-health-low" />}
                    {result.prediction === 'Medium' && <AlertCircle className="h-16 w-16 text-health-medium" />}
                    {result.prediction === 'High' && <AlertCircle className="h-16 w-16 text-health-high" />}
                  </div>
                  
                  <h2 className="text-3xl font-bold mb-2">
                    Risk Level: {result.prediction}
                  </h2>
                  
                  <p className="text-xl mb-4">
                    Confidence: {result.confidence}%
                  </p>
                  
                  <div className="bg-white bg-opacity-50 rounded-xl p-6 mt-6">
                    <p className="text-sm leading-relaxed">
                      {result.prediction === 'Low' && 
                        "Your assessment indicates a lower risk profile. Continue maintaining healthy lifestyle choices and regular check-ups with your healthcare provider."
                      }
                      {result.prediction === 'Medium' && 
                        "Your assessment indicates a moderate risk profile. Consider discussing these results with your healthcare provider and explore preventive measures."
                      }
                      {result.prediction === 'High' && 
                        "Your assessment indicates a higher risk profile. We strongly recommend consulting with a healthcare professional for further evaluation and guidance."
                      }
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mt-8 bg-yellow-50 border border-yellow-200 rounded-xl p-6">
        <div className="flex items-start space-x-3">
          <AlertCircle className="h-6 w-6 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-yellow-800 mb-2">Medical Disclaimer</h3>
            <p className="text-sm text-yellow-700">
              This tool is for educational purposes only and is not a substitute for professional medical advice. 
              Please consult a doctor for any health concerns or before making any medical decisions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LungCancer;