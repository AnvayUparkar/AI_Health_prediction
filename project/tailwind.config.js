/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        'inter': ['Inter', 'sans-serif'],
      },
      colors: {
        'health': {
          'bg': '#F8F9FA',
          'primary': '#3B82F6',
          'text': '#1F2937',
          'low': '#10B981',
          'medium': '#F59E0B',
          'high': '#EF4444',
        },
        'truthshield': {
          'primary': {
            DEFAULT: '#00D1FF',
            hover: '#00A3C4',
          },
          'purple': '#A855F7',
          'neutral': {
            main: '#1E293B',
            body: '#64748B',
            border: '#E2E8F0',
            surface: '#F8FAFC',
          },
          'accent': {
            blue: '#06B6D4',
            pink: '#D946EF',
            orange: '#F97316',
            yellow: '#EAB308',
          }
        }
      },
      textColor: {
        'heading': '#1E293B',
        'body': '#64748B',
        'muted': '#94A3B8',
        'brand': '#00D1FF',
        'contrast': '#FFFFFF',
        'accent': '#9333EA',
      },
      backgroundImage: {
        'hero-gradient': 'linear-gradient(90deg, #1E293B 0%, #A855F7 100%)',
        'primary-gradient': 'linear-gradient(135deg, #00D1FF 0%, #00B4D8 100%)',
        'text-hero': 'linear-gradient(90deg, #1E3A8A 0%, #6D28D9 100%)',
        'brand-gradient': 'linear-gradient(90deg, #0EA5A4 0%, #1E3A8A 100%)',
        'main-mesh': 'linear-gradient(135deg, #e0f2fe 0%, #f8fafc 50%, #faf5ff 100%)',
      },
      borderRadius: {
        'button': '50px',
        'card': '24px',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        }
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
};