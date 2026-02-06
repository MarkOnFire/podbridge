/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Podbridge brand colors
        'pod-teal': '#0d9488',
        'pod-amber': '#d97706',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
