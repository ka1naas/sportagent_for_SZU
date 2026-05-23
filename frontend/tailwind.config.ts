import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#f4f8f6",
        foreground: "#10221b",
        primary: {
          DEFAULT: "#256f63",
          foreground: "#f7fffd",
        },
        secondary: {
          DEFAULT: "#dff2ec",
          foreground: "#21463e",
        },
        card: "#ffffff",
        border: "#d9e7e1",
        muted: "#6c857d",
        accent: "#8dd3c2",
      },
      boxShadow: {
        soft: "0 16px 40px rgba(16, 34, 27, 0.08)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.5rem",
      },
    },
  },
  plugins: [],
};

export default config;
