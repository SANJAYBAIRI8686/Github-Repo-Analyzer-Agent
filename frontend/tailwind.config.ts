import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"]
  ,
  theme: {
    extend: {
      colors: {
        ink: "#0b1020",
        panel: "#121a31",
        panelSoft: "#18213d",
        accent: "#ff7a18",
        accent2: "#19d3ff",
        muted: "#9aa7c7",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(255,122,24,0.12), 0 20px 60px rgba(0,0,0,0.35)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular"],
      },
      backgroundImage: {
        aurora: "radial-gradient(circle at top left, rgba(255,122,24,0.24), transparent 34%), radial-gradient(circle at top right, rgba(25,211,255,0.14), transparent 26%), linear-gradient(180deg, #07101f 0%, #0b1020 100%)",
      },
    },
  },
  plugins: [],
};

export default config;