/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
      colors: {
        primary:          '#F97316',
        'primary-accent': '#FED7AA',
        'primary-dark':   '#EA580C',
        surface:          '#FFF7ED',
        up:               '#EF4444',
        down:             '#22C55E',
        neutral:          '#9CA3AF',
        warning:          '#F59E0B',
        series3:          '#6366F1',
        series4:          '#EC4899',
      },
    },
  },
  plugins: [],
}
