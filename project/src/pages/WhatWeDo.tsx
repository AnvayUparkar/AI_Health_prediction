import { Search, FileText, Brain, Shield, Clock, CheckCircle } from 'lucide-react';

const WhatWeDo = () => {
  const steps = [
    {
      number: '01',
      icon: <Search className="h-8 w-8" />,
      title: 'Select a Predictor',
      description: 'Choose the disease you want to assess from our available health prediction models.',
      details: ['Lung Cancer Risk Assessment', 'Diabetes Risk Evaluation', 'More conditions coming soon']
    },
    {
      number: '02',
      icon: <FileText className="h-8 w-8" />,
      title: 'Answer the Questionnaire',
      description: 'Fill out a short, confidential questionnaire based on well-known risk factors.',
      details: ['Evidence-based questions', 'Takes 3-5 minutes', 'Completely confidential']
    },
    {
      number: '03',
      icon: <Brain className="h-8 w-8" />,
      title: 'Get Your AI-Powered Result',
      description: 'Our trained model analyzes your answers in real-time and provides an instant risk assessment with a confidence score.',
      details: ['Instant analysis', 'Confidence percentage', 'Clear risk categorization']
    }
  ];

  const features = [
    {
      icon: <Shield className="h-6 w-6" />,
      title: 'Privacy Protected',
      description: 'Your data is processed locally and never stored or shared with third parties.'
    },
    {
      icon: <Clock className="h-6 w-6" />,
      title: 'Real-Time Processing',
      description: 'Get your results instantly without any waiting time or complex procedures.'
    },
    {
      icon: <CheckCircle className="h-6 w-6" />,
      title: 'Scientifically Validated',
      description: 'Our models are trained on validated medical datasets and established risk factors.'
    }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="text-4xl md:text-5xl font-bold text-health-text mb-6">How It Works</h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
          Our AI-powered health prediction process is designed to be simple, fast, and reliable. 
          Here's how we help you understand your health risks in just three easy steps.
        </p>
      </div>

      {/* Steps Section */}
      <div className="mb-20">
        {steps.map((step, index) => (
          <div key={index} className="mb-16 last:mb-0">
            <div className={`grid grid-cols-1 lg:grid-cols-2 gap-12 items-center ${
              index % 2 === 1 ? 'lg:grid-flow-col-dense' : ''
            }`}>
              {/* Content */}
              <div className={index % 2 === 1 ? 'lg:col-start-2' : ''}>
                <div className="flex items-center space-x-4 mb-6">
                  <span className="text-4xl font-bold text-health-primary">{step.number}</span>
                  <div className="p-3 bg-blue-50 rounded-xl text-health-primary">
                    {step.icon}
                  </div>
                </div>
                <h2 className="text-3xl font-bold text-health-text mb-4">{step.title}</h2>
                <p className="text-lg text-gray-600 leading-relaxed mb-6">{step.description}</p>
                <ul className="space-y-3">
                  {step.details.map((detail, detailIndex) => (
                    <li key={detailIndex} className="flex items-center space-x-3">
                      <CheckCircle className="h-5 w-5 text-health-low flex-shrink-0" />
                      <span className="text-gray-600">{detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              {/* Visual */}
              <div className={`${index % 2 === 1 ? 'lg:col-start-1 lg:row-start-1' : ''}`}>
                <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-2xl p-8 h-80 flex items-center justify-center">
                  <div className="text-center">
                    <div className="p-6 bg-white rounded-full shadow-lg mb-4 mx-auto w-fit">
                      <div className="text-health-primary">
                        {step.icon}
                      </div>
                    </div>
                    <h3 className="text-xl font-semibold text-health-text">{step.title}</h3>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div className="flex justify-center mt-12">
                <div className="w-px h-16 bg-gradient-to-b from-health-primary to-transparent"></div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Features Grid */}
      <div className="mb-16">
        <h2 className="text-3xl font-bold text-health-text text-center mb-12">Why Choose Our Platform?</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div key={index} className="bg-white rounded-xl shadow-lg p-6 text-center hover:shadow-xl transition-shadow duration-300">
              <div className="p-3 bg-blue-50 rounded-xl text-health-primary mx-auto w-fit mb-4">
                {feature.icon}
              </div>
              <h3 className="text-xl font-bold text-health-text mb-3">{feature.title}</h3>
              <p className="text-gray-600 leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Disclaimer Section */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-8">
        <div className="flex items-start space-x-4">
          <div className="p-2 bg-yellow-100 rounded-lg flex-shrink-0">
            <Shield className="h-6 w-6 text-yellow-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-yellow-800 mb-3">Important Disclaimer</h3>
            <p className="text-yellow-700 leading-relaxed">
              <strong>This tool is for educational purposes only and is not a substitute for professional medical advice.</strong> 
              {' '}The predictions provided by our AI models should not be used as the sole basis for making medical decisions. 
              Always consult with qualified healthcare professionals for proper diagnosis, treatment, and medical guidance. 
              If you have concerns about your health, please seek immediate medical attention.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WhatWeDo;