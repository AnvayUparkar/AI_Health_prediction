import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sun as Lung, Activity, ArrowRight } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';

const Predictions = () => {
  const predictionModels = [
    {
      icon: Lung,
      title: "Lung Cancer Risk Predictor",
      description: "Assess your lung cancer risk based on lifestyle factors, medical history, and environmental exposures. Our AI model analyzes 12 key risk factors to provide comprehensive risk assessment.",
      gradient: "from-red-400 to-pink-500",
      hoverColor: "red-500",
      features: ['12 comprehensive risk factors', 'Takes 3-5 minutes to complete', 'Instant AI-powered analysis'],
      link: "/lung-cancer",
      accuracy: "94%"
    },
    {
      icon: Activity,
      title: "Diabetes Risk Predictor",
      description: "Evaluate your diabetes risk through a comprehensive questionnaire covering symptoms, lifestyle, and health indicators. Get insights into your metabolic health with our trained prediction model.",
      gradient: "from-green-400 to-emerald-500",
      hoverColor: "green-500",
      features: ['Comprehensive symptom analysis', 'Quick and easy questionnaire', 'Immediate risk assessment'],
      link: "/diabetes",
      accuracy: "92%"
    }
  ];

  return (
    <div className="relative min-h-screen pt-20 pb-12">
      <AnimatedBackground />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            AI Health Predictions
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Select a prediction model to assess your health risks using advanced machine learning algorithms
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
          {predictionModels.map((model, index) => {
            const IconComponent = model.icon;
            return (
              <GlassCard key={index} className="p-8 group" delay={index * 0.2}>
                <div className="flex items-center space-x-4 mb-6">
                  <motion.div 
                    className={`p-4 bg-gradient-to-r ${model.gradient} rounded-2xl relative`}
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <IconComponent className="h-8 w-8 text-white" />
                    <div className="absolute -top-2 -right-2 bg-white rounded-full px-2 py-1 text-xs font-bold text-gray-800 shadow-lg">
                      {model.accuracy}
                    </div>
                  </motion.div>
                  <h3 className={`text-2xl font-bold text-gray-800 group-hover:text-${model.hoverColor} transition-colors duration-300`}>
                    {model.title}
                  </h3>
                </div>
                
                <p className="text-gray-600 mb-6 leading-relaxed">
                  {model.description}
                </p>
                
                <div className="space-y-3 mb-8">
                  {model.features.map((item, idx) => (
                    <div key={idx} className="flex items-center space-x-3">
                      <div className={`w-2 h-2 bg-gradient-to-r ${model.gradient} rounded-full`}></div>
                      <span className="text-gray-600">{item}</span>
                    </div>
                  ))}
                </div>
                
                <Link to={model.link}>
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className={`w-full bg-gradient-to-r ${model.gradient} text-white px-6 py-4 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-xl transition-all duration-300`}
                  >
                    <span>Start Assessment</span>
                    <ArrowRight className="h-5 w-5" />
                  </motion.button>
                </Link>
              </GlassCard>
            );
          })}
        </div>

        {/* Information Section */}
        <GlassCard className="p-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-6">How Our Predictions Work</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-4xl font-bold text-purple-600 mb-2">1</div>
              <h3 className="font-semibold text-lg mb-2">Input Your Data</h3>
              <p className="text-gray-600">Answer questions about your health, lifestyle, and medical history</p>
            </div>
            <div>
              <div className="text-4xl font-bold text-purple-600 mb-2">2</div>
              <h3 className="font-semibold text-lg mb-2">AI Analysis</h3>
              <p className="text-gray-600">Our trained models process your data using advanced algorithms</p>
            </div>
            <div>
              <div className="text-4xl font-bold text-purple-600 mb-2">3</div>
              <h3 className="font-semibold text-lg mb-2">Get Results</h3>
              <p className="text-gray-600">Receive your risk assessment with confidence scores and recommendations</p>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
};

export default Predictions;