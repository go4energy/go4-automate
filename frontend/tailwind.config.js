/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,js}'],
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
          muted: '#6B7280',
          'dark-bg': '#0F172A',
          'dark-surface': '#1E293B',
          'dark-border': '#334155'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif']
      },
      keyframes: {
        moveVertical: {
          '0%, 100%': { transform: 'translateY(-50%)' },
          '50%': { transform: 'translateY(50%)' }
        },
        moveHorizontal: {
          '0%, 100%': { transform: 'translateX(-50%) translateY(-10%)' },
          '50%': { transform: 'translateX(50%) translateY(10%)' }
        },
        moveOrbit: {
          '0%': { transform: 'translate(0, -30%)' },
          '25%': { transform: 'translate(30%, 0)' },
          '50%': { transform: 'translate(0, 30%)' },
          '75%': { transform: 'translate(-30%, 0)' },
          '100%': { transform: 'translate(0, -30%)' }
        },
        moveDrift: {
          '0%, 100%': { transform: 'translate(-25%, 15%)' },
          '33%': { transform: 'translate(25%, -15%)' },
          '66%': { transform: 'translate(15%, 25%)' }
        }
      },
      animation: {
        first: 'moveVertical 30s ease infinite',
        second: 'moveOrbit 25s ease infinite reverse',
        third: 'moveDrift 35s ease infinite',
        fourth: 'moveHorizontal 30s ease infinite',
        fifth: 'moveOrbit 20s linear infinite'
      }
    }
  },
  plugins: [
    require('@tailwindcss/typography')
  ]
}
