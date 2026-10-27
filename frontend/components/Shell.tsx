"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import ThemeToggle from "./ThemeToggle";
const NAV = [["/", "Dashboard"], ["/projects", "Projects"], ["/ai", "AI task center"], ["/settings", "Settings"]];
export default function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="min-h-screen md:flex">
      <aside className="md:w-56 md:fixed md:inset-y-0 border-b md:border-b-0 md:border-r border-line bg-surface p-4 flex md:flex-col gap-4">
        <Link href="/" className="font-display text-xl leading-tight">Interior<br className="hidden md:block" /> Studio</Link>
        <nav className="flex md:flex-col gap-1 md:mt-6 flex-1">
          {NAV.map(([href, label]) => {
            const active = href === "/" ? path === "/" : path.startsWith(href);
            return <Link key={href} href={href} aria-current={active ? "page" : undefined}
              className={`rounded px-3 py-1.5 text-sm transition-colors ${active ? "bg-accent text-bg" : "hover:bg-raised"}`}>{label}</Link>;
          })}
        </nav>
        <div className="hidden md:block"><ThemeToggle /></div>
      </aside>
      <main className="md:ml-56 flex-1 p-6 md:p-10 max-w-6xl">{children}</main>
    </div>
  );
}
