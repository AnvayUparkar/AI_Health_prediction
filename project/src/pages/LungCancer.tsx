import React, { useState, useEffect } from 'react';
import { Sun as Lung, AlertCircle, CheckCircle, Clock } from 'lucide-react';

const LungCancer = () => {
  // Default features that match the backend model
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

  const [features, setFeatures] = useState<string[]>(DEFAULT_FEATURES);
  const [formData, setFormData] = useState<Record<string, string>>(
    Object.fromEntries(DEFAULT_FEATURES.map(f => [f, '']))
  );
  
  const [result, setResult] = useState<{prediction: string, confidence: string} | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Build questions dynamically from `features`
  const buildQuestion = (field: string) => {
    const f = field.toLowerCase();
    if (f.includes('age')) {
      return { 
        field, 
        label: 'What is your current age?', 
        type: 'number', 
        min: 1, 
        max: 120 
      };
    }
    if (f.includes('gender')) {
      return { 
        field, 
        label: 'Gender', 
        type: 'select', 
        options: [
          { value: '1', label: 'Male' }, 
          { value: '2', label: 'Female' }
        ] 
      };
    }
    // Default to small-range sliders for other ordinal features
    return { 
      field, 
      label: field, 
      type: 'range', 
      min: 1, 
      max: 3 
    };
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
    setResult(null);
    
    // Prepare payload - only send features that are in the backend's expected list
    const payload = Object.fromEntries(
      Object.entries(formData)
        .filter(([key]) => features.includes(key))
        .filter(([_, value]) => value !== '') // Only send non-empty values
    );
    
    try {
      const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5000';
      
      // Use the new unified prediction endpoint
      const response = await fetch(`${API_URL}/api/predict`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          type: 'lung_cancer',
          features: payload
        })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        // Show backend error in UI
        console.error('Prediction error:', data);
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
    const pred = prediction.toLowerCase();
    if (pred.includes('low') || pred === 'no') {
      return 'text-health-low bg-green-50 border-green-200';
    }
    if (pred.includes('medium') || pred.includes('moderate')) {
      return 'text-health-medium bg-yellow-50 border-yellow-200';
    }
    if (pred.includes('high') || pred === 'yes') {
      return 'text-health-high bg-red-50 border-red-200';
    }
    return 'text-gray-600 bg-gray-50 border-gray-200';
  };

  const getResultMessage = (prediction: string) => {
    const pred = prediction.toLowerCase();
    if (pred.includes('low') || pred === 'no') {
      return "Your assessment indicates a lower risk profile. Continue maintaining healthy lifestyle choices and regular check-ups with your healthcare provider.";
    }
    if (pred.includes('medium') || pred.includes('moderate')) {
      return "Your assessment indicates a moderate risk profile. Consider discussing these results with your healthcare provider and explore preventive measures.";
    }
    if (pred.includes('high') || pred === 'yes') {
      return "Your assessment indicates a higher risk profile. We strongly recommend consulting with a healthcare professional for further evaluation and guidance.";
    }
    return "Please consult with a healthcare professional to discuss your results.";
  };

  const isFormValid = features.every(f => (formData[f] ?? '') !== '');

  // Fetch model info from backend to align field names at runtime
  useEffect(() => {
    const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:5000';
    
    const fetchModelInfo = async () => {
      try {
        const res = await fetch(`${API_URL}/api/model-info`);
        if (res.ok) {
          const data = await res.json();
          if (data.lung_cancer_features && Array.isArray(data.lung_cancer_features)) {
            console.log('Loaded lung cancer features from backend:', data.lung_cancer_features);
            setFeatures(data.lung_cancer_features);
            
            // Update form data with new features
            setFormData(prev => {
              const updated = { ...prev };
              data.lung_cancer_features.forEach((f: string) => {
                if (!(f in updated)) {
                  updated[f] = '';
                }
              });
              return updated;
            });
          }
        }
      } catch (error) {
        console.warn('Could not fetch model info, using default features:', error);
        // Keep using default features
      }
    };

    fetchModelInfo();
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
                    value={formData[question.field]}
                    onChange={(e) => handleInputChange(question.field, e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-health-primary focus:border-transparent transition-all duration-200"
                    required
                  />
                )}
                
                {question.type === 'select' && question.options && (
                  <select
                    id={question.field}
                    name={question.field}
                    value={formData[question.field]}
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
                      value={formData[question.field] || question.min}
                      onChange={(e) => handleInputChange(question.field, e.target.value)}
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
                      required
                    />
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>{question.min}</span>
                      <span className="font-medium text-health-primary">
                        {formData[question.field] || question.min}
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
                    {getResultColor(result.prediction).includes('green') && 
                      <CheckCircle className="h-16 w-16 text-health-low" />
                    }
                    {getResultColor(result.prediction).includes('yellow') && 
                      <AlertCircle className="h-16 w-16 text-health-medium" />
                    }
                    {getResultColor(result.prediction).includes('red') && 
                      <AlertCircle className="h-16 w-16 text-health-high" />
                    }
                  </div>
                  
                  <h2 className="text-3xl font-bold mb-2">
                    Risk Level: {result.prediction}
                  </h2>
                  
                  {result.confidence && (
                    <p className="text-xl mb-4">
                      Confidence: {result.confidence}%
                    </p>
                  )}
                  
                  <div className="bg-white bg-opacity-50 rounded-xl p-6 mt-6">
                    <p className="text-sm leading-relaxed">
                      {getResultMessage(result.prediction)}
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