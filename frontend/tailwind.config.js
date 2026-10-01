/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "primary": "#041539",
        "on-primary": "#ffffff",
        "primary-container": "#1b2a4e",
        "on-primary-container": "#8392bc",
        "inverse-primary": "#b7c6f2",
        "primary-fixed": "#dae2ff",
        "primary-fixed-dim": "#b7c6f2",
        "on-primary-fixed": "#091a3d",
        "on-primary-fixed-variant": "#37466b",

        "secondary": "#006a6a",
        "on-secondary": "#ffffff",
        "secondary-container": "#90efef",
        "on-secondary-container": "#006e6e",
        "secondary-fixed": "#93f2f2",
        "secondary-fixed-dim": "#76d6d5",
        "on-secondary-fixed": "#002020",
        "on-secondary-fixed-variant": "#004f4f",

        "accent": "#F97316",
        "accent-hover": "#EA580C",

        "tertiary": "#241400",
        "on-tertiary": "#ffffff",
        "tertiary-container": "#402600",
        "on-tertiary-container": "#b48c5b",
        "tertiary-fixed": "#ffddb7",
        "tertiary-fixed-dim": "#ebbf89",
        "on-tertiary-fixed": "#2a1700",
        "on-tertiary-fixed-variant": "#5f4117",

        "error": "#ba1a1a",
        "on-error": "#ffffff",
        "error-container": "#ffdad6",
        "on-error-container": "#93000a",

        "background": "#f8f9ff",
        "on-background": "#0b1c30",

        "surface": "#f8f9ff",
        "surface-dim": "#cbdbf5",
        "surface-bright": "#f8f9ff",
        "surface-variant": "#d3e4fe",
        "on-surface": "#0b1c30",
        "on-surface-variant": "#45464e",

        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#eff4ff",
        "surface-container": "#e5eeff",
        "surface-container-high": "#dce9ff",
        "surface-container-highest": "#d3e4fe",

        "inverse-surface": "#213145",
        "inverse-on-surface": "#eaf1ff",

        "outline": "#75777f",
        "outline-variant": "#c5c6cf",
        "surface-tint": "#4f5d85",
      },
      borderRadius: {
        "DEFAULT": "0.125rem",
        "sm": "0.125rem",
        "md": "0.375rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "2xl": "1rem",
        "full": "9999px"
      },
      spacing: {
        "unit": "8px",
        "gutter": "24px",
        "margin-mobile": "16px",
        "margin-desktop": "40px",
        "container-max": "1200px",
      },
      fontFamily: {
        "display": ["Newsreader", "Georgia", "serif"],
        "headline": ["Newsreader", "Georgia", "serif"],
        "body": ["Inter", "system-ui", "-apple-system", "sans-serif"],
        "label": ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      boxShadow: {
        "card": "0 4px 20px 0px rgba(4, 21, 57, 0.04)",
        "glass": "0 8px 32px 0 rgba(4, 21, 57, 0.05)",
        "subtle": "0 4px 20px rgba(4, 21, 57, 0.04)",
      }
    },
  },
  plugins: [],
}
