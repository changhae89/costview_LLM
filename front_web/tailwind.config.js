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
        primary:        '#0D9488',
        'primary-accent': '#5EEAD4',
        navy:           '#1A2332',
        'navy-light':   '#243044',
        seafoam:        '#A8DADC',
        up:             '#D85A30',
        down:           '#1D9E75',
        neutral:        '#B4B2A9',
        surface:        '#F4F7FA',
      },
    },
  },
  plugins: [],
}
