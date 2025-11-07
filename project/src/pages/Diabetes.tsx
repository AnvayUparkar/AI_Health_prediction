import React, { useState } from 'react';
import { Activity, AlertCircle, CheckCircle, Clock } from 'lucide-react';

const Diabetes = () => {
  const [formData, setFormData] = useState({
    Age: '',
    Gender: '',
    Polyuria: '',
    Polydipsia: '',
    'sudden weight loss': '',
    weakness: '',
    Polyphagia: '',
    'Genital thrush': '',
    'visual blurring': '',
    Itching: '',
    Irritability: '',
    'delayed healing': '',
    'partial paresis': '',
    'muscle stiffness': '',
    Alopecia: '',
    Obesity: ''
  });
  
  const [result, setResult] = useState<{prediction: string, confidence: string} | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const questions = [
    { field: 'Age', label: 'What is your current age?', type: 'number', min: 1, max: 120 },
    { field: 'Gender', label: 'What is your gender?', type: 'select', options: [
      { value: 'Male', label: 'Male' },
      { value: 'Female', label: 'Female' }
    ]},
    { field: 'Polyuria', label: 'Do you experience excessive urination?', type: 'radio' },
    { field: 'Polydipsia', label: 'Do you experience excessive thirst?', type: 'radio' },
    { field: 'sudden weight loss', label: 'Have you experienced sudden weight loss?', type: 'radio' },
    { field: 'weakness', label: 'Do you experience weakness or fatigue?', type: 'radio' },
    { field: 'Polyphagia', label: 'Do you experience excessive hunger?', type: 'radio' },
    { field: 'Genital thrush', label: 'Do you experience genital thrush?', type: 'radio' },
    { field: 'visual blurring', label: 'Do you experience visual blurring?', type: 'radio' },
    { field: 'Itching', label: 'Do you experience itching?', type: 'radio' },
    { field: 'Irritability', label: 'Do you experience irritability?', type: 'radio' },
    { field: 'delayed healing', label: 'Do you experience delayed healing of wounds?', type: 'radio' },
    { field: 'partial paresis', label: 'Do you experience partial paresis (muscle weakness)?', type: 'radio' },
    { field: 'muscle stiffness', label: 'Do you experience muscle stiffness?', type: 'radio' },
    { field: 'Alopecia', label: 'Do you experience hair loss (alopecia)?', type: 'radio' },
    { field: 'Obesity', label: 'Are you considered obese?', type: 'radio' }
  ];

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null); // Clear previous errors
    
    try {
      const response = await fetch('http://localhost:5000/predict_diabetes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Prediction failed');
      }

      const result = await response.json();
      setResult(result);
    } catch (error) {
      console.error('Prediction error:', error);
      setErrorMessage((error as Error).message || 'Prediction failed. Please try again or check if the backend server is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const getResultColor = (prediction: string) => {
    switch (prediction) {
      case 'Negative': return 'text-health-low bg-green-50 border-green-200';
      case 'Positive': return 'text-health-high bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const isFormValid = Object.values(formData).every(value => value !== '');

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-green-50 rounded-2xl">
            <Activity className="h-12 w-12 text-green-500" />
          </div>
        </div>
        <h1 className="text-4xl font-bold text-health-text mb-4">Diabetes Risk Questionnaire</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Please answer all questions honestly based on your current symptoms and health status. 
          This assessment evaluates your risk factors for diabetes.
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-8">
        <form id="diabetes-form" onSubmit={handleSubmit} className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {questions.map((question, index) => (
              <div key={question.field} className="space-y-4">
                <label className="block text-sm font-semibold text-health-text">
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
                
                {question.type === 'radio' && (
                  <div className="flex space-x-6">
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        id={`${question.field}-yes`}
                        name={question.field}
                        value="Yes"
                        checked={formData[question.field as keyof typeof formData] === 'Yes'}
                        onChange={(e) => handleInputChange(question.field, e.target.value)}
                        className="w-4 h-4 text-health-primary border-gray-300 focus:ring-health-primary"
                        required
                      />
                      <span className="text-sm text-gray-700">Yes</span>
                    </label>
                    <label className="flex items-center space-x-2 cursor-pointer">
                      <input
                        type="radio"
                        id={`${question.field}-no`}
                        name={question.field}
                        value="No"
                        checked={formData[question.field as keyof typeof formData] === 'No'}
                        onChange={(e) => handleInputChange(question.field, e.target.value)}
                        className="w-4 h-4 text-health-primary border-gray-300 focus:ring-health-primary"
                        required
                      />
                      <span className="text-sm text-gray-700">No</span>
                    </label>
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
            {errorMessage && (
              <p className="text-sm text-red-500 flex items-center space-x-1 mt-4">
                <AlertCircle className="h-4 w-4 text-red-500" />
                <span>Error: {errorMessage}</span>
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
                    {result.prediction === 'Negative' && <CheckCircle className="h-16 w-16 text-health-low" />}
                    {result.prediction === 'Positive' && <AlertCircle className="h-16 w-16 text-health-high" />}
                  </div>
                  
                  <h2 className="text-3xl font-bold mb-2">
                    Result: {result.prediction === 'Positive' ? 'Higher Risk' : 'Lower Risk'}
                  </h2>
                  
                  <p className="text-xl mb-4">
                    Confidence: {result.confidence}%
                  </p>
                  
                  <div className="bg-white bg-opacity-50 rounded-xl p-6 mt-6">
                    <p className="text-sm leading-relaxed">
                      {result.prediction === 'Negative' && 
                        "Your assessment indicates a lower risk for diabetes. Continue maintaining a healthy lifestyle with regular exercise and a balanced diet."
                      }
                      {result.prediction === 'Positive' && 
                        "Your assessment indicates a higher risk for diabetes. We recommend consulting with a healthcare professional for proper screening and guidance on preventive measures."
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

export default Diabetes;