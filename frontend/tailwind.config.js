/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        crimson: {
          50: '#FDF2F4',
          100: '#FCE7EB',
          200: '#F9D0D8',
          300: '#F4A9B8',
          400: '#EC778E',
          500: '#DE4567',
          600: '#C52649',
          700: '#A41A39',
          800: '#8A1731',
          900: '#73172D', // Primary matte crimson
          950: '#410815',
        },
        warm: {
          50: '#FAF8F5',  // Background soft warm
          100: '#F5F2ED',
          200: '#EAE5DC',
          300: '#DDD5C7',
          800: '#2A2927',
          900: '#1A1918',
        },
        charcoal: {
          50: '#F6F6F7',
          100: '#E7E7E9',
          200: '#D1D1D5',
          300: '#B0B0B8',
          400: '#888894',
          500: '#6D6D7A',
          600: '#575762',
          700: '#46464F',
          800: '#26262B',
          900: '#18181B', // Dark charcoal text
          950: '#0E0E10',
        }
      },
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'sans-serif'
        ],
        serif: [
          'Newsreader',
          'Merriweather',
          'Georgia',
          'serif'
        ]
      },
      boxShadow: {
        'subtle': '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        'premium': '0 4px 20px -2px rgba(24, 24, 27, 0.06), 0 2px 6px -1px rgba(24, 24, 27, 0.03)',
        'crimson-glow': '0 4px 24px -2px rgba(138, 23, 49, 0.15)',
      }
    },
  },
  plugins: [],
}
