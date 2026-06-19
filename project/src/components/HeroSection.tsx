import { useState } from 'react';
import { motion } from 'framer-motion';
import { Search, Heart, Stethoscope, Video } from 'lucide-react';

interface FloatingCardProps {
  icon: React.ReactNode;
  label: string;
  delay: number;
  position: 'left-top' | 'left-middle' | 'left-bottom';
}

const FloatingCard: React.FC<FloatingCardProps> = ({ icon, label, delay, position }) => {
  const positionClasses = {
    'left-top': '-left-16 sm:-left-20 lg:-left-24 top-0 sm:top-4',
    'left-middle': '-left-16 sm:-left-20 lg:-left-24 top-1/3 sm:top-2/5',
    'left-bottom': '-left-16 sm:-left-20 lg:-left-24 top-2/3 sm:top-3/4',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.6, delay }}
      whileHover={{ scale: 1.05 }}
      className={`absolute ${positionClasses[position]} hidden sm:block`}
    >
      <motion.div
        animate={{
          y: [0, -15, 0],
        }}
        transition={{
          duration: 4,
          repeat: Infinity,
          delay: delay * 0.5,
        }}
        className="bg-white/95 rounded-2xl shadow-lg p-3 sm:p-4 w-max border border-healthcare-mint-border/50"
      >
        <div className="flex items-center space-x-2 sm:space-x-3">
          <div className="p-2 sm:p-3 bg-healthcare-mint/15 rounded-full">
            {icon}
          </div>
          <span className="font-semibold text-healthcare-heading text-xs sm:text-sm whitespace-nowrap">
            {label}
          </span>
        </div>
      </motion.div>
    </motion.div>
  );
};

const HeroSection: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8 },
    },
  };

  return (
    <section className="relative min-h-screen pt-40 sm:pt-32 pb-20 px-4 sm:px-6 lg:px-8 overflow-hidden bg-gradient-to-br from-healthcare-light via-healthcare-bg-secondary to-healthcare-light">
      {/* Decorative background shapes */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Soft green circle (bottom-left) */}
        <motion.div
          className="absolute -bottom-32 -left-32 w-96 h-96 rounded-full opacity-5"
          style={{
            background: 'radial-gradient(circle, #4A9B8E, transparent)',
          }}
          animate={{
            y: [0, 20, 0],
            x: [0, 10, 0],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
          }}
        />

        {/* Soft peach/beige curve (bottom-right) */}
        <motion.div
          className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full opacity-3"
          style={{
            background: 'radial-gradient(circle, #FFE8D6, transparent)',
          }}
          animate={{
            y: [0, -20, 0],
            x: [0, -10, 0],
          }}
          transition={{
            duration: 7,
            repeat: Infinity,
          }}
        />
      </div>

      <div className="relative max-w-7xl mx-auto z-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
          {/* Left Side - Content */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-8"
          >
            {/* Headline */}
            <motion.div 
              variants={itemVariants}
              className="text-center lg:text-left max-w-4xl"
            >
              <style>{`
                .premium-gradient-text {
                  background: linear-gradient(
                    90deg,
                    #0F3D4C 0%,
                    #0A6E8C 30%,
                    #2A8BC8 60%,
                    #6A5ACD 80%,
                    #8B3FD1 100%
                  );
                  -webkit-background-clip: text;
                  -webkit-text-fill-color: transparent;
                  background-clip: text;
                  color: transparent;
                }
              `}</style>
              <h1 className="premium-gradient-text text-4xl sm:text-5xl lg:text-6xl font-black leading-none sm:leading-none tracking-tight" style={{ letterSpacing: '-0.03em', lineHeight: '0.95' }}>
                Compassionate Care,
                <div className="flex items-center justify-center lg:justify-start gap-4 mt-2 sm:mt-3">
                  <div className="w-12 sm:w-16 h-1 bg-gradient-to-r from-purple-600 to-purple-500 rounded-full"></div>
                  <span className="text-purple-600 text-4xl sm:text-5xl font-black"></span>
                </div>
                <div className="mt-3 sm:mt-4">a Click Away.</div>
              </h1>
            </motion.div>

            {/* Description */}
            <motion.p
              variants={itemVariants}
              className="text-lg sm:text-xl text-healthcare-text leading-relaxed max-w-lg"
            >
              Connect with top-rated doctors, get instant health predictions, and receive
              personalized care plans—all from the comfort of your home.
            </motion.p>

            {/* Search Bar */}
            <motion.div
              variants={itemVariants}
              className="hidden sm:flex items-center bg-white/90 backdrop-blur-md rounded-full shadow-lg border border-healthcare-mint-border px-4 sm:px-6 py-2 sm:py-3 w-full max-w-md"
            >
              <input
                type="text"
                placeholder="Search doctors or specialties..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 px-4 sm:px-6 py-2 sm:py-3 bg-transparent text-healthcare-heading placeholder-healthcare-text focus:outline-none text-sm sm:text-base"
              />
              <button
                className="p-2 sm:p-3 rounded-full bg-healthcare-mint hover:bg-healthcare-mint-dark transition-colors duration-300"
                aria-label="Search"
                type="button"
              >
                <Search className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
              </button>
            </motion.div>

            {/* CTA Button */}
            <motion.div variants={itemVariants} className="hidden">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="w-full sm:w-auto px-6 sm:px-8 py-3 sm:py-4 bg-healthcare-mint hover:bg-healthcare-mint-dark text-white font-semibold text-base sm:text-lg rounded-full shadow-lg transition-all duration-300"
                type="button"
              >
                See Available Doctors
              </motion.button>
            </motion.div>
          </motion.div>

          {/* Right Side - Doctor Image + Floating Cards */}
          <motion.div
            className="relative h-80 sm:h-96 lg:h-[600px] mt-8 lg:mt-0"
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            {/* Doctor Image Container */}
            <motion.div
              className="absolute inset-0 rounded-3xl overflow-hidden shadow-2xl"
              animate={{
                y: [0, -10, 0],
              }}
              transition={{
                duration: 4,
                repeat: Infinity,
              }}
            >
              {/* Doctor Image */}
              <img
                src="/images/doctor.jpg"
                alt="Professional Doctor"
                className="w-full h-full object-cover"
              />
            </motion.div>

            {/* Floating Card - Primary */}
            <FloatingCard
              icon={<Stethoscope className="h-5 w-5 text-healthcare-mint" />}
              label="Primary"
              delay={0}
              position="left-top"
            />

            {/* Floating Card - Specialist */}
            <FloatingCard
              icon={<Heart className="h-5 w-5 text-healthcare-mint" />}
              label="Specialist"
              delay={0.2}
              position="left-middle"
            />

            {/* Floating Card - Telehealth */}
            <FloatingCard
              icon={<Video className="h-5 w-5 text-healthcare-mint" />}
              label="Telehealth"
              delay={0.4}
              position="left-bottom"
            />
          </motion.div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
