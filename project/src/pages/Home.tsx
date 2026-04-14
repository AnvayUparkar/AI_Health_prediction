import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sun as Lung, Activity, ArrowRight, Brain, Heart, Zap, Calendar, HeartPulse, LineChart, Utensils } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';
import GlassCard from '../components/GlassCard';
import FeatureCard from '../components/FeatureCard';
import HealthAnalysisCard from '../components/HealthAnalysisCard';
import AlertMonitoringCard from '../components/AlertMonitoringCard';
import AppointmentManagementCard from '../components/AppointmentManagementCard';

const Home = () => {
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      try {
        setUser(JSON.parse(userData));
      } catch (e) {
        console.error("Failed to parse user data", e);
      }
    }
  }, []);

  const additionalFeatures = [
    {
      icon: Brain,
      title: "Machine Learning Precision",
      description: "Our AI models are trained on thousands of medical cases to provide accurate risk assessments with high confidence scores."
    },
    {
      icon: Heart,
      title: "Comprehensive Health Insights",
      description: "Get detailed analysis covering multiple risk factors including lifestyle, genetics, and environmental exposures."
    },
    {
      icon: Zap,
      title: "Real-time Processing",
      description: "Experience lightning-fast predictions with our optimized algorithms that process your data in milliseconds."
    }
  ];

  const mainServices = [
    {
      icon: Calendar,
      title: "Book Doctor Appointment",
      description: "Schedule consultations with healthcare professionals. Choose between online video consultations or in-person visits at your convenience.",
      gradient: "from-purple-500 to-pink-500",
      hoverColorClass: "group-hover:text-purple-500 group-hover:[text-shadow:0_0_12px_rgba(168,85,247,0.8)]",
      features: ["Online & Offline consultations", "Flexible scheduling", "Experienced doctors"],
      link: "/book-appointment",
      ctaText: "Book Appointment",
      roles: ["doctor", "nurse", "user"],
      glow: "hover:shadow-[0_0_20px_rgba(168,85,247,0.2)]"
    },
    {
      icon: LineChart,
      title: "AI Health Predictions",
      description: "Access our suite of AI-powered health prediction tools. Get instant risk assessments for various conditions based on your health data.",
      gradient: "from-amber-500 to-red-500",
      hoverColorClass: "group-hover:text-amber-500 group-hover:[text-shadow:0_0_12px_rgba(245,158,11,0.8)]",
      features: ["Multiple prediction models", "Instant results", "Comprehensive analysis"],
      link: "/predictions",
      ctaText: "Start Prediction",
      roles: ["doctor", "nurse"], // Restricted to medical staff
      glow: "hover:shadow-[0_0_20px_rgba(245,158,11,0.2)]"
    },
    {
      icon: Utensils,
      title: "Smart Diet Planner",
      description: "Receive personalized diet recommendations based on your health reports. AI-powered nutrition planning tailored to your specific needs.",
      gradient: "from-green-500 to-emerald-500",
      hoverColorClass: "group-hover:text-green-500 group-hover:[text-shadow:0_0_12px_rgba(16,185,129,0.8)]",
      features: ["Personalized meal plans", "Report-based recommendations", "Nutritionist-approved"],
      link: "/report-analyzer",
      ctaText: "Get Diet Plan",
      roles: ["doctor", "nurse", "user"],
      glow: "hover:shadow-[0_0_20px_rgba(16,185,129,0.2)]"
    }
  ];

  // Filter services based on user role
  const visibleServices = mainServices.filter(service =>
    !service.roles || (user && user.role && service.roles.includes(user.role))
  );

  return (
    <div className="relative min-h-screen">
      <AnimatedBackground />

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <motion.h1
              className="text-5xl md:text-7xl font-bold mb-8 leading-tight"
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
                Proactive Health Insights,
              </span>
              <br />
              <span className="bg-gradient-to-r from-indigo-600 via-blue-600 to-purple-600 bg-clip-text text-transparent">
                Powered by AI
              </span>
            </motion.h1>

            <motion.p
              className="text-xl md:text-2xl text-gray-600 max-w-4xl mx-auto leading-relaxed mb-12"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              Leverage the power of machine learning to provide early-stage risk assessment
              for common diseases. Get instant, data-driven insights into your potential health risks
              and take proactive steps towards a healthier life.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
              className="flex flex-col sm:flex-row gap-6 justify-center items-center"
            >
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-2xl font-semibold text-lg shadow-xl hover:shadow-2xl transition-all duration-300"
                onClick={() => window.scrollTo({ top: (document.querySelector('#services') as HTMLElement)?.offsetTop || 0, behavior: 'smooth' })}
              >
                Explore Services
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-4 backdrop-blur-lg bg-white/20 border border-white/30 text-gray-700 rounded-2xl font-semibold text-lg hover:bg-white/30 transition-all duration-300"
              >
                Learn More
              </motion.button>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Main Services Section */}
      <section id="services" className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-6 bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
              Our Healthcare Services
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Comprehensive health solutions powered by AI and expert care
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 gap-8 mb-20">
            {visibleServices.map((service, index) => {
              const IconComponent = service.icon;
              return (
                <GlassCard key={index} className={`p-8 group h-full flex flex-col ${service.glow}`} delay={index * 0.2}>
                  <div className="flex flex-col h-full">
                    <div className="flex items-center space-x-4 mb-6">
                      <motion.div
                        className={`p-4 bg-gradient-to-r ${service.gradient} rounded-2xl`}
                        whileHover={{ scale: 1.1, rotate: 5 }}
                      >
                        <IconComponent className="h-8 w-8 text-white" />
                      </motion.div>
                    </div>

                    <h3 className={`text-2xl font-bold text-gray-800 mb-4 ${service.hoverColorClass} transition-all duration-300`}>
                      {service.title}
                    </h3>

                    <p className="text-gray-600 mb-6 leading-relaxed flex-grow">
                      {service.description}
                    </p>

                    <div className="space-y-3 mb-8">
                      {service.features.map((item, idx) => (
                        <div key={idx} className="flex items-center space-x-3">
                          <div className={`w-2 h-2 bg-gradient-to-r ${service.gradient} rounded-full`}></div>
                          <span className="text-gray-600">{item}</span>
                        </div>
                      ))}
                    </div>

                    <Link to={service.link}>
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        className={`w-full bg-gradient-to-r ${service.gradient} text-white px-6 py-4 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-xl transition-all duration-300`}
                      >
                        <span>{service.ctaText}</span>
                        <ArrowRight className="h-5 w-5" />
                      </motion.button>
                    </Link>
                  </div>
                </GlassCard>
              );
            })}
            <HealthAnalysisCard />
            {(user?.role?.toLowerCase() === 'doctor' || user?.role?.toLowerCase() === 'nurse') && (
              <>
                <AppointmentManagementCard />
                <AlertMonitoringCard />
              </>
            )}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-6 bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
              Why Choose Our Platform?
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Experience the future of healthcare with our cutting-edge AI technology
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-20">
            {additionalFeatures.map((feature, index) => (
              <FeatureCard
                key={index}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
                delay={index * 0.2}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Assessment Cards Section - Restricted to Professionals */}
      {(user?.role?.toLowerCase() === 'doctor' || user?.role?.toLowerCase() === 'nurse') && (
        <section className="relative py-20 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="text-center mb-16"
            >
              <h2 className="text-4xl md:text-5xl font-bold mb-6 bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                Start Your Health Assessment
              </h2>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto">
                Choose from our AI-powered health prediction tools
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-8">
              {/* Lung Cancer Card */}
              <GlassCard className="p-8 group" delay={0}>
                <div className="flex items-center space-x-4 mb-6">
                  <motion.div
                    className="p-4 bg-gradient-to-r from-red-400 to-pink-500 rounded-2xl"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <Lung className="h-8 w-8 text-white" />
                  </motion.div>
                  <h3 className="text-2xl font-bold text-gray-800 group-hover:text-red-500 transition-colors duration-300">
                    Lung Cancer Risk Predictor
                  </h3>
                </div>

                <p className="text-gray-600 mb-6 leading-relaxed">
                  Assess your lung cancer risk based on lifestyle factors, medical history, and environmental exposures.
                  Our AI model analyzes 12 key risk factors to provide comprehensive risk assessment.
                </p>

                <div className="space-y-3 mb-8">
                  {['12 comprehensive risk factors', 'Takes 3-5 minutes to complete', 'Instant AI-powered analysis'].map((item, index) => (
                    <div key={index} className="flex items-center space-x-3">
                      <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"></div>
                      <span className="text-gray-600">{item}</span>
                    </div>
                  ))}
                </div>

                <Link to="/lung-cancer">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="w-full bg-gradient-to-r from-red-500 to-pink-500 text-white px-6 py-4 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-xl transition-all duration-300"
                  >
                    <span>Start Assessment</span>
                    <ArrowRight className="h-5 w-5" />
                  </motion.button>
                </Link>
              </GlassCard>

              {/* Diabetes Card */}
              <GlassCard className="p-8 group" delay={0.2}>
                <div className="flex items-center space-x-4 mb-6">
                  <motion.div
                    className="p-4 bg-gradient-to-r from-green-400 to-emerald-500 rounded-2xl"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <Activity className="h-8 w-8 text-white" />
                  </motion.div>
                  <h3 className="text-2xl font-bold text-gray-800 group-hover:text-green-500 transition-colors duration-300">
                    Diabetes Risk Predictor
                  </h3>
                </div>

                <p className="text-gray-600 mb-6 leading-relaxed">
                  Evaluate your diabetes risk through a comprehensive questionnaire covering symptoms, lifestyle,
                  and health indicators. Get insights into your metabolic health with our trained prediction model.
                </p>

                <div className="space-y-3 mb-8">
                  {['Comprehensive symptom analysis', 'Quick and easy questionnaire', 'Immediate risk assessment'].map((item, index) => (
                    <div key={index} className="flex items-center space-x-3">
                      <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"></div>
                      <span className="text-gray-600">{item}</span>
                    </div>
                  ))}
                </div>

                <Link to="/diabetes">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="w-full bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-4 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-xl transition-all duration-300"
                  >
                    <span>Start Assessment</span>
                    <ArrowRight className="h-5 w-5" />
                  </motion.button>
                </Link>
              </GlassCard>

              {/* Heart Disease Card */}
              <GlassCard className="p-8 group" delay={0.4}>
                <div className="flex items-center space-x-4 mb-6">
                  <motion.div
                    className="p-4 bg-gradient-to-r from-rose-400 to-red-500 rounded-2xl"
                    whileHover={{ scale: 1.1, rotate: 5 }}
                  >
                    <HeartPulse className="h-8 w-8 text-white" />
                  </motion.div>
                  <h3 className="text-2xl font-bold text-gray-800 group-hover:text-rose-500 transition-colors duration-300">
                    Heart Disease Risk Predictor
                  </h3>
                </div>

                <p className="text-gray-600 mb-6 leading-relaxed">
                  Evaluate your cardiovascular risk using our elite ensemble model that analyzes your lifestyle, health markers, and dietary habits.
                </p>

                <div className="space-y-3 mb-8">
                  {['17 comprehensive risk factors', 'Elite Stacking Ensemble Model', 'Highly accurate assessment'].map((item, index) => (
                    <div key={index} className="flex items-center space-x-3">
                      <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"></div>
                      <span className="text-gray-600">{item}</span>
                    </div>
                  ))}
                </div>

                <Link to="/heart-disease">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="w-full bg-gradient-to-r from-rose-500 to-red-500 text-white px-6 py-4 rounded-xl font-semibold flex items-center justify-center space-x-2 hover:shadow-xl transition-all duration-300"
                  >
                    <span>Start Assessment</span>
                    <ArrowRight className="h-5 w-5" />
                  </motion.button>
                </Link>
              </GlassCard>

              {/* AI Health Analysis Card moved to services section */}
            </div>
          </div>
        </section>
      )}

      {/* CTA Section */}
      <section className="relative py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <GlassCard className="p-12">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
            >
              <h2 className="text-4xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Ready to Take Control of Your Health?
              </h2>
              <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
                Choose a service above to begin your journey towards better health awareness and proactive care.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/what-we-do">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="px-8 py-4 backdrop-blur-lg bg-white/30 border border-white/40 text-gray-700 rounded-xl font-semibold hover:bg-white/40 transition-all duration-300"
                  >
                    Learn How It Works
                  </motion.button>
                </Link>
                <Link to="/about">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-semibold hover:shadow-xl transition-all duration-300"
                  >
                    Meet Our Team
                  </motion.button>
                </Link>
              </div>
            </motion.div>
          </GlassCard>
        </div>
      </section>
    </div>
  );
};

export default Home;