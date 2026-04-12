import React, { useState } from 'react';
import { HeartPulse, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { predict } from '../services/api';

const HeartDisease = () => {
  const [formData, setFormData] = useState({
    General_Health: '',
    Checkup: '',
    Exercise: '',
    Skin_Cancer: '',
    Other_Cancer: '',
    Depression: '',
    Diabetes: '',
    Arthritis: '',
    Age_Category: '',
    Sex: '',
    Smoking_History: '',
    'Height_(cm)': '',
    'Weight_(kg)': '',
    Alcohol_Consumption: '',
    Fruit_Consumption: '',
    Green_Vegetables_Consumption: '',
    FriedPotato_Consumption: ''
  });

  const [result, setResult] = useState<{ prediction: string, confidence: number | null, risk_score?: number | null, threshold?: number | null } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const questions = [
    {
      field: 'General_Health', label: 'How would you rate your general health?', type: 'select', options: [
        { value: 'Excellent', label: 'Excellent' },
        { value: 'Very Good', label: 'Very Good' },
        { value: 'Good', label: 'Good' },
        { value: 'Fair', label: 'Fair' },
        { value: 'Poor', label: 'Poor' }
      ]
    },
    {
      field: 'Checkup', label: 'When was your last medical checkup?', type: 'select', options: [
        { value: 'Within the past year', label: 'Within the past year' },
        { value: 'Within the past 2 years', label: 'Within the past 2 years' },
        { value: 'Within the past 5 years', label: 'Within the past 5 years' },
        { value: '5 or more years ago', label: '5 or more years ago' },
        { value: 'Never', label: 'Never' }
      ]
    },
    { field: 'Exercise', label: 'Do you exercise (physical activity in past 30 days)?', type: 'radio' },
    { field: 'Skin_Cancer', label: 'Have you ever been diagnosed with skin cancer?', type: 'radio' },
    { field: 'Other_Cancer', label: 'Have you ever been diagnosed with any other cancer?', type: 'radio' },
    { field: 'Depression', label: 'Have you been diagnosed with a depressive disorder?', type: 'radio' },
    {
      field: 'Diabetes', label: 'Diabetes status?', type: 'select', options: [
        { value: 'No', label: 'No' },
        { value: 'No, pre-diabetes or borderline diabetes', label: 'No, pre-diabetes or borderline diabetes' },
        { value: 'Yes, but female told only during pregnancy', label: 'Yes, but female told only during pregnancy' },
        { value: 'Yes', label: 'Yes' }
      ]
    },
    { field: 'Arthritis', label: 'Have you been told you have arthritis?', type: 'radio' },
    {
      field: 'Age_Category', label: 'What is your age group?', type: 'select', options: [
        { value: '18-24', label: '18-24' },
        { value: '25-29', label: '25-29' },
        { value: '30-34', label: '30-34' },
        { value: '35-39', label: '35-39' },
        { value: '40-44', label: '40-44' },
        { value: '45-49', label: '45-49' },
        { value: '50-54', label: '50-54' },
        { value: '55-59', label: '55-59' },
        { value: '60-64', label: '60-64' },
        { value: '65-69', label: '65-69' },
        { value: '70-74', label: '70-74' },
        { value: '75-79', label: '75-79' },
        { value: '80+', label: '80+' }
      ]
    },
    {
      field: 'Sex', label: 'What is your biological sex?', type: 'select', options: [
        { value: 'Male', label: 'Male' },
        { value: 'Female', label: 'Female' }
      ]
    },
    { field: 'Smoking_History', label: 'Do you have a smoking history?', type: 'radio' },
    { field: 'Height_(cm)', label: 'What is your height in cm? (e.g. 170)', type: 'number', min: 100, max: 250 },
    { field: 'Weight_(kg)', label: 'What is your weight in kg? (e.g. 70.5)', type: 'number', min: 30, max: 300 },
    { field: 'Alcohol_Consumption', label: 'How many alcoholic drinks per week? (0-30)', type: 'number', min: 0, max: 30 },
    { field: 'Fruit_Consumption', label: 'How many servings of fruit per week? (0-120)', type: 'number', min: 0, max: 120 },
    { field: 'Green_Vegetables_Consumption', label: 'How many servings of green vegetables per week? (0-128)', type: 'number', min: 0, max: 128 },
    { field: 'FriedPotato_Consumption', label: 'How many servings of fried potatoes per week? (0-128)', type: 'number', min: 0, max: 128 }
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
    setErrorMessage(null);
    setResult(null);

    try {
      const data = await predict('heart_disease', formData);

      setResult({
        prediction: data.prediction,
        confidence: data.confidence,
        risk_score: data.risk_score,
        threshold: data.threshold
      });
    } catch (err: any) {
      console.error('Prediction error:', err);
      const errorMsg = err?.response?.data?.error || err?.message || 'Prediction failed. Please try again.';
      setErrorMessage(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const getResultColor = (prediction: string) => {
    if (prediction === 'Lower Risk') return 'text-green-700 bg-green-50 border-green-200';
    if (prediction === 'Higher Risk') return 'text-red-700 bg-red-50 border-red-200';
    return 'text-gray-600 bg-gray-50 border-gray-200';
  };

  const isFormValid = Object.values(formData).every(value => value !== '');

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-rose-50 rounded-2xl">
            <HeartPulse className="h-12 w-12 text-rose-500" />
          </div>
        </div>
        <h1 className="text-4xl font-bold text-gray-900 mb-4">Heart Disease Risk Questionnaire</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">
          Please answer all questions honestly based on your current health status and lifestyle.
          This assessment evaluates your risk factors for cardiovascular disease using our elite stacking ensemble model.
        </p>
      </div>

      <div className="bg-white rounded-2xl shadow-lg p-8">
        <form id="heart-disease-form" onSubmit={handleSubmit} className="space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {questions.map((question) => (
              <div key={question.field} className="space-y-4">
                <label className="block text-sm font-semibold text-gray-900">
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
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-rose-500 focus:border-transparent transition-all duration-200"
                    required
                  />
                )}

                {question.type === 'select' && question.options && (
                  <select
                    id={question.field}
                    name={question.field}
                    value={formData[question.field as keyof typeof formData]}
                    onChange={(e) => handleInputChange(question.field, e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-rose-500 focus:border-transparent transition-all duration-200"
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
                        className="w-4 h-4 text-rose-600 border-gray-300 focus:ring-rose-500"
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
                        className="w-4 h-4 text-rose-600 border-gray-300 focus:ring-rose-500"
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
              className="px-8 py-4 bg-rose-600 text-white rounded-xl font-semibold hover:bg-rose-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center space-x-2 shadow-lg hover:shadow-xl"
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
              <div className="text-sm text-red-600 flex items-center space-x-1 mt-4 bg-red-50 p-4 rounded-lg">
                <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
                <span>Error: {errorMessage}</span>
              </div>
            )}
          </div>
        </form>

        {/* Results */}
        <div id="result">
          {result && (
            <div className={`mt-12 p-8 border-2 rounded-2xl transition-all duration-500 ${getResultColor(result.prediction)}`}>
              <div className="text-center">
                <div className="flex justify-center mb-4">
                  {result.prediction === 'Lower Risk' && <CheckCircle className="h-16 w-16 text-green-600" />}
                  {result.prediction === 'Higher Risk' && <AlertCircle className="h-16 w-16 text-red-600" />}
                </div>

                <h2 className="text-3xl font-bold mb-2">
                  Result: {result.prediction}
                </h2>

                {result.risk_score !== undefined && result.risk_score !== null && (
                  <div className="mt-6 mb-2">
                    <div className="flex justify-between text-sm font-medium mb-1">
                      <span>Risk Score</span>
                      <span>{result.risk_score} / 100</span>
                    </div>
                    {/* Gauge bar */}
                    <div className="relative w-full h-5 bg-gray-200 rounded-full overflow-visible">
                      {/* Filled bar */}
                      <div
                        className={`h-5 rounded-full transition-all duration-700 ${result.prediction === 'Higher Risk' ? 'bg-red-500' : 'bg-green-500'}`}
                        style={{ width: `${result.risk_score}%` }}
                      />
                      {/* Threshold marker */}
                      {result.threshold !== undefined && result.threshold !== null && (
                        <div
                          className="absolute top-0 h-5 flex flex-col items-center"
                          style={{ left: `${result.threshold}%`, transform: 'translateX(-50%)' }}
                        >
                          <div className="w-0.5 h-5 bg-gray-800" />
                        </div>
                      )}
                    </div>
                    {result.threshold !== undefined && result.threshold !== null && (
                      <div className="flex justify-end mt-1">
                        <span className="text-xs text-gray-600 font-medium">▲ Decision threshold: {result.threshold}</span>
                      </div>
                    )}
                    <p className="text-xs text-gray-500 mt-2">
                      {result.risk_score < (result.threshold ?? 50)
                        ? `Your score (${result.risk_score}) is below the decision threshold (${result.threshold}) — classified as Lower Risk.`
                        : `Your score (${result.risk_score}) meets or exceeds the decision threshold (${result.threshold}) — classified as Higher Risk.`
                      }
                    </p>
                  </div>
                )}

                {result.confidence !== null && (
                  <p className="text-sm mb-4 mt-1 text-gray-500">
                    Model confidence: {result.confidence}% away from threshold
                  </p>
                )}

                <div className="bg-white bg-opacity-50 rounded-xl p-6 mt-6">
                  <p className="text-sm leading-relaxed">
                    {result.prediction === 'Lower Risk' &&
                      "Your assessment indicates a lower risk profile for heart disease. Keep up the good work by maintaining a balanced diet, staying physically active, and attending regular preventative check-ups."
                    }
                    {result.prediction === 'Higher Risk' &&
                      "Your assessment indicates a potential higher risk profile for cardiovascular issues. We strongly advise that you consult with a healthcare professional to further evaluate your risk and establish a preventative care plan."
                    }
                  </p>
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

export default HeartDisease;
