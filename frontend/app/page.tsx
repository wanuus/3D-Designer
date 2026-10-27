"use client";
import Link from "next/link";
import { api, fmtBytes } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Project } from "@/lib/types";
import { Empty, ErrorNote } from "@/components/ui";

export default function Dashboard() {
  const stats = useAsync(() => api("/api/dashboard"), []);
  const projects = useAsync(() => api<Project[]>("/api/projects"), []);
  const s = stats.data;
  const cells = s ? [["Projects", s.total_projects], ["In progress", s.active_projects], ["Completed", s.completed_projects], ["Archived", s.archived_projects], ["Rooms not started", s.rooms_pending_design], ["Storage used", fmtBytes(s.storage_bytes)]] : [];
  return (
    <div className="space-y-8">
      <header><h1 className="text-3xl">Studio</h1><p className="text-muted text-sm mt-1">Everything here is stored on this computer.</p></header>
      <ErrorNote msg={stats.error || projects.error} />
      <dl className="grid grid-cols-2 md:grid-cols-6 gap-px bg-line border border-line rounded-md overflow-hidden">
        {cells.map(([k, v]) => <div key={k as string} className="bg-surface p-4"><dt className="text-xs text-muted">{k}</dt><dd className="font-display text-2xl mt-1">{v as any}</dd></div>)}
      </dl>
      <section>
        <div className="flex items-baseline justify-between mb-3"><h2 className="text-xl">Recent projects</h2><Link className="text-sm underline" href="/projects">All projects</Link></div>
        {projects.data && projects.data.length === 0 && <Empty>No projects yet. <Link className="underline" href="/projects">Create your first apartment project</Link> to begin.</Empty>}
        <div className="grid md:grid-cols-2 gap-3">
          {projects.data?.slice(0, 6).map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="panel p-4 hover:border-accent transition-colors block">
              <div className="flex justify-between gap-2"><h3 className="text-lg">{p.name}</h3><span className="badge">{p.status}</span></div>
              <p className="text-sm text-muted mt-1">{p.client_name || "No client set"} · {p.room_count} room{p.room_count === 1 ? "" : "s"}</p>
            </Link>))}
        </div>
      </section>
    </div>
  );
}
