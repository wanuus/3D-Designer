"use client";
import { useEffect, useState } from "react";
export default function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  const toggle = () => {
    const next = !dark; setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem("ais-theme", next ? "dark" : "light"); } catch {}
  };
  return <button className="btn w-full justify-center" onClick={toggle} aria-pressed={dark}>{dark ? "Switch to light mode" : "Switch to dark mode"}</button>;
}
