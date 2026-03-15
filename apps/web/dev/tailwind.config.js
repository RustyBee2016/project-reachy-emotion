/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          pink:    '#D4166A',
          magenta: '#E91E8C',
          purple:  '#7B2FF7',
          violet:  '#6820D0',
          cyan:    '#00B4D8',
          sky:     '#0EA5E9',
        },
        dark: {
          900: '#06060F',
          800: '#080818',
          700: '#0D0D20',
          600: '#111128',
          500: '#161630',
          400: '#1E1E3E',
          300: '#282850',
        },
        surface: {
          DEFAULT: '#0F1025',
          hover:   '#161638',
          border:  'rgba(123,47,247,0.25)',
          glow:    'rgba(123,47,247,0.10)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
        'gradient-brand-r': 'linear-gradient(135deg, #00B4D8 0%, #7B2FF7 50%, #D4166A 100%)',
        'gradient-dark': 'linear-gradient(180deg, #080818 0%, #0D0D20 100%)',
        'gradient-card': 'linear-gradient(145deg, rgba(123,47,247,0.08) 0%, rgba(0,180,216,0.04) 100%)',
        'gradient-hero': 'radial-gradient(ellipse 80% 60% at 50% -10%, rgba(123,47,247,0.35) 0%, transparent 60%), radial-gradient(ellipse 40% 30% at 10% 70%, rgba(212,22,106,0.20) 0%, transparent 50%), linear-gradient(180deg, #06060F 0%, #080818 100%)',
        'gradient-glow': 'radial-gradient(ellipse 60% 40% at 50% 50%, rgba(123,47,247,0.15) 0%, transparent 70%)',
      },
      boxShadow: {
        'brand': '0 0 40px rgba(123,47,247,0.25)',
        'brand-sm': '0 0 20px rgba(123,47,247,0.15)',
        'pink': '0 0 30px rgba(212,22,106,0.20)',
        'cyan': '0 0 30px rgba(0,180,216,0.20)',
        'card': '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'signal': 'signal 2s ease-in-out infinite',
        'fade-up': 'fadeUp 0.6s ease-out forwards',
        'glow-pulse': 'glowPulse 3s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        signal: {
          '0%': { opacity: '0.3', transform: 'scale(0.95)' },
          '50%': { opacity: '1', transform: 'scale(1.02)' },
          '100%': { opacity: '0.3', transform: 'scale(0.95)' },
        },
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(24px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        glowPulse: {
          '0%, 100%': { boxShadow: '0 0 20px rgba(123,47,247,0.2)' },
          '50%': { boxShadow: '0 0 40px rgba(123,47,247,0.4)' },
        },
      },
    },
  },
  plugins: [],
}
