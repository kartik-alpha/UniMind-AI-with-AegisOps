/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0B0F19',
          800: '#111827',
          700: '#1E293B',
        },
        obsidian: {
          900: '#080D1E',
          800: '#0B1120',
          700: '#131B2E',
        },
      },
      animation: {
        fadeIn: 'fadeIn 0.3s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        'glow-cyan': '0 0 15px rgba(6, 182, 212, 0.15), 0 0 3px rgba(6, 182, 212, 0.1)',
      },
    },
  },
  plugins: [],
}
