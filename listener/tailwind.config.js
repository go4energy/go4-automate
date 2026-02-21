/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        go4: {
          primary: '#0ea5e9',
          'primary-dark': '#0284c7',
          'primary-light': '#38bdf8',
          secondary: '#1A1A2E',
          accent: '#16213E',
          surface: '#F8F9FA',
          muted: '#6B7280'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif']
      }
    }
  },
  plugins: []
}
