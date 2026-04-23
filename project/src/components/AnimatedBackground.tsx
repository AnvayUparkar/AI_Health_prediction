import React from 'react';
import { motion } from 'framer-motion';

const AnimatedBackground = () => {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none -z-10">

      {/* Mesh Glows - Perfected to match the reference screenshot */}
      <div
        className="absolute -top-[10%] -left-[10%] w-[70%] h-[70%] rounded-full blur-[120px] opacity-[0.2]"
        style={{ background: 'radial-gradient(circle, var(--bg-icon-teal), transparent 70%)' }}
      />
      <div
        className="absolute top-[10%] -right-[10%] w-[60%] h-[60%] rounded-full blur-[120px] opacity-[0.15]"
        style={{ background: 'radial-gradient(circle, var(--bg-icon-purple), transparent 70%)' }}
      />
      <div
        className="absolute -bottom-[20%] right-[10%] w-[50%] h-[50%] rounded-full blur-[100px] opacity-[0.1]"
        style={{ background: 'radial-gradient(circle, var(--bg-icon-orange), transparent 70%)' }}
      />

      {/* Subtle Animated Particles */}
      {[...Array(12)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1.5 h-1.5 bg-brand rounded-full opacity-[0.1]"
          initial={{
            x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1000),
            y: Math.random() * (typeof window !== 'undefined' ? window.innerHeight : 1000),
          }}
          animate={{
            x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1000),
            y: Math.random() * (typeof window !== 'undefined' ? window.innerHeight : 1000),
          }}
          transition={{
            duration: Math.random() * 40 + 30,
            repeat: Infinity,
            repeatType: "reverse",
            ease: "linear",
          }}
        />
      ))}

      {/* Elegant Floating Blobs */}
      <motion.div
        className="absolute top-1/4 left-[5%] w-64 h-64 rounded-full opacity-[0.05] blur-3xl"
        style={{ background: 'var(--bg-primary-gradient)' }}
        animate={{
          y: [0, -40, 0],
          scale: [1, 1.1, 1],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />

      <motion.div
        className="absolute bottom-1/4 right-[5%] w-72 h-72 rounded-full opacity-[0.04] blur-3xl"
        style={{ background: 'linear-gradient(135deg, var(--secondary), var(--accent-pink))' }}
        animate={{
          y: [0, 50, 0],
          scale: [1, 1.15, 1],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
    </div>
  );
};

export default AnimatedBackground;