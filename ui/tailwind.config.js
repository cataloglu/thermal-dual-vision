/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B1020',
        surface1: '#111A2E',
        surface2: '#17223A',
        border: '#22304A',
        text: '#E6EAF2',
        muted: '#9AA6BF',
        accent: '#5B8CFF',
        success: '#2ECC71',
        warning: '#F5A524',
        error: '#FF4D4F',
        info: '#3B82F6',
      },
    },
  },
  plugins: [],
}
