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
          50: '#FFFDF5',
          100: '#FEF9E7',
          200: '#FDF0C8',
          300: '#FCE49E',
          400: '#FAD56C',
          500: '#F59E0B', // Primary Warm Amber Gold
          600: '#D97706',
          700: '#B45309',
          800: '#92400E',
          900: '#78350F',
          yellow: '#F59E0B',
          gold: '#EAB308',
          lightYellow: '#FEF3C7',
          subtleYellow: '#FFFBEB',
          cream: '#FCFBF7',
          canvas: '#F7F6F0',
          card: '#FFFFFF',
          border: '#EAE6DB',
          borderSubtle: '#F3EFE6',
          slate: {
            900: '#0F172A',
            800: '#1E293B',
            700: '#334155',
            600: '#475569',
            500: '#64748B',
            400: '#94A3B8',
          }
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Consolas', 'monospace'],
        display: ['"Outfit"', '"Plus Jakarta Sans"', 'sans-serif'],
      },
      boxShadow: {
        'warm-sm': '0 1px 3px rgba(217, 119, 6, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)',
        'warm-md': '0 4px 12px rgba(217, 119, 6, 0.08), 0 2px 4px rgba(0, 0, 0, 0.03)',
        'warm-lg': '0 10px 25px -3px rgba(217, 119, 6, 0.10), 0 4px 6px -2px rgba(0, 0, 0, 0.03)',
        'warm-xl': '0 20px 35px -4px rgba(217, 119, 6, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.04)',
        'glow-yellow': '0 0 20px rgba(245, 158, 11, 0.35)',
        'tactile': '0 3px 0 #D97706, 0 4px 10px rgba(217, 119, 6, 0.25)',
        'tactile-pressed': '0 1px 0 #D97706, 0 2px 4px rgba(217, 119, 6, 0.2)',
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.25s ease-out forwards',
        'slide-up': 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      }
    },
  },
  plugins: [],
}
