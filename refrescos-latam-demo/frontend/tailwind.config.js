/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dark navy surface palette.
        ink: {
          900: "#0d1117",
          800: "#111827",
          700: "#161b22",
          600: "#1f2733",
          border: "#2a3441",
        },
        accent: {
          cyan: "#22d3ee",
          blue: "#3b82f6",
          amber: "#fbbf24",
          green: "#22c55e",
          red: "#ef4444",
          purple: "#a855f7",
        },
      },
    },
  },
  plugins: [],
};
