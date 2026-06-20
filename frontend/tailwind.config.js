/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dark theme palette: slate for surfaces, with semantic accent colors.
        surface: {
          DEFAULT: '#0f172a', // slate-900
          card: '#1e293b',    // slate-800
          hover: '#334155',   // slate-700
          border: '#334155',  // slate-700
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
