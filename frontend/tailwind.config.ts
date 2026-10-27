import type { Config } from "tailwindcss";
const c = (v: string) => `rgb(var(--${v}) / <alpha-value>)`;
export default {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: { bg: c("bg"), surface: c("surface"), raised: c("raised"), line: c("line"), ink: c("ink"), muted: c("muted"), accent: c("accent"), danger: c("danger") },
    fontFamily: { display: ["ui-serif", "'New York'", "Georgia", "serif"], sans: ["ui-sans-serif", "-apple-system", "system-ui", "sans-serif"] },
  } },
  plugins: [],
} satisfies Config;
