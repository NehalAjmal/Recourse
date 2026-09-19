/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['IBM Plex Sans', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
      colors: {
        accent: '#2563eb', // muted blue for interactive elements
      },
      transitionDuration: {
        DEFAULT: '150ms', // exactly 150ms transition
      }
    },
  },
  plugins: [],
}
