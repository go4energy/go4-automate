/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js}'
  ],
  theme: {
    extend: {
      colors: {
        go4: {
          primary: '#FF6600',
          'primary-dark': '#E55A00',
          'primary-light': '#FF8533',
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
