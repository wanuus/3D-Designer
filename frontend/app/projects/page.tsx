"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, post } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { PROJECT_STATUSES, Project } from "@/lib/types";
import { Empty, ErrorNote, Field } from "@/components/ui";

export default function Projects() {
  const router = useRouter();
  const [q, setQ] = useState(""); const [status, setStatus] = useState(""); const [sort, setSort] = useState("updated");
  const [err, setErr] = useState<string | null>(null);
  const list = useAsync(() => api<Project[]>(`/api/projects?q=${encodeURIComponent(q)}&status=${encodeURIComponent(status)}&sort=${sort}`), [q, status, sort]);
  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); const f = new FormData(e.currentTarget); setErr(null);
    try { const p = await post<Project>("/api/projects", { name: f.get("name"), client_name: f.get("client_name"), location: f.get("location") }); router.push(`/projects/${p.id}`); }
    catch (x: any) { setErr(x.message); }
  }
  return (
    <div className="space-y-8">
      <h1 className="text-3xl">Projects</h1>
      <form onSubmit={create} className="panel p-4 grid md:grid-cols-4 gap-3 items-end">
        <Field label="Project name"><input name="name" required className="input" placeholder="Apartment A" /></Field>
        <Field label="Client"><input name="client_name" className="input" /></Field>
        <Field label="Location (optional)"><input name="location" className="input" /></Field>
        <button className="btn btn-primary justify-center">Create project</button>
      </form>
      <ErrorNote msg={err || list.error} />
      <div className="flex gap-3 flex-wrap">
        <input className="input max-w-xs" placeholder="Search by project or client" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search projects" />
        <select className="input max-w-[14rem]" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status"><option value="">Active statuses</option>{PROJECT_STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
        <select className="input max-w-[10rem]" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort"><option value="updated">Recently updated</option><option value="created">Newest</option><option value="name">Name</option></select>
      </div>
      {list.data?.length === 0 && <Empty>No projects match. Create one above.</Empty>}
      <div className="grid md:grid-cols-2 gap-3">
        {list.data?.map((p) => (
          <Link key={p.id} href={`/projects/${p.id}`} className="panel p-4 hover:border-accent transition-colors block">
            <div className="flex justify-between gap-2"><h2 className="text-lg">{p.name}</h2><span className="badge">{p.status}</span></div>
            <p className="text-sm text-muted mt-1">{p.client_name || "No client set"}{p.location ? ` · ${p.location}` : ""} · {p.room_count} room{p.room_count === 1 ? "" : "s"}</p>
          </Link>))}
      </div>
    </div>
  );
}
