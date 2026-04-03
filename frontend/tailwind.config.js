/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['Space Grotesk', 'monospace'],
      },
      colors: {
        sc_bg: '#06080d',
        sc_card: '#0b0f17',
        sc_elevated: '#101520',
        sc_cyan: '#00d4ff',
        sc_orange: '#ff6b35',
        sc_green: '#4ade80',
        sc_yellow: '#ffd60a',
        sc_purple: '#c084fc',
        sc_red: '#fb7185',
        sc_gray: '#64748b'
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
      }
    },
  },
  plugins: [],
}
