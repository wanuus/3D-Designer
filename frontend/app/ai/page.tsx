"use client";
import { useEffect } from "react";
import { api, post } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { ErrorNote, Empty } from "@/components/ui";

const COLORS: Record<string, string> = { completed: "text-accent", failed: "text-danger", running: "text-ink", queued: "text-muted", cancelled: "text-muted" };

export default function AICenter() {
  const prov = useAsync(() => api("/api/ai/providers"), []);
  const tasks = useAsync(() => api<any[]>("/api/ai/tasks"), []);
  useEffect(() => { const t = setInterval(() => tasks.reload(), 3000); return () => clearInterval(t); }, [tasks.reload]); // eslint-disable-line
  const act = async (path: string) => { try { await post(path); tasks.reload(); } catch (e: any) { alert(e.message); } };
  return (
    <div className="space-y-8">
      <header><h1 className="text-3xl">AI task center</h1>
        <p className="text-sm text-muted mt-1">Mode: <b>{prov.data?.mode ?? "…"}</b>. Nothing leaves this computer in local-only mode. One AI job runs at a time to protect memory. Providers are chosen in <code>config/providers.json</code>.</p></header>
      <ErrorNote msg={prov.error || tasks.error} />
      <section><h2 className="text-xl mb-3">Providers</h2>
        <div className="panel divide-y divide-line">
          {prov.data?.providers.map((p: any) => (
            <div key={p.name} className="p-3 grid md:grid-cols-[12rem_1fr] gap-2">
              <div><p className="font-medium">{p.name}</p><p className={`text-xs ${p.available ? "text-accent" : "text-danger"}`}>{p.available ? "Ready" : "Not ready"}</p></div>
              <div className="text-sm"><p>{p.detail}</p>
                <p className="text-xs text-muted mt-1">Tasks: {p.tasks.join(", ")} · {p.execution} · model {p.model_id} · ~{p.est_memory_gb ?? "?"} GB RAM · license: {p.license || "unknown"}</p>
                {p.notes && <p className="text-xs text-muted">{p.notes}</p>}</div>
            </div>))}
        </div></section>
      <section><h2 className="text-xl mb-3">Tasks</h2>
        {tasks.data?.length === 0 && <Empty>No AI tasks yet. Upload a floor plan or room photo in a project&apos;s Files tab and choose an AI action.</Empty>}
        <div className="space-y-3">
          {tasks.data?.map((t) => (
            <div key={t.id} className="panel p-3 space-y-2">
              <div className="flex flex-wrap justify-between gap-2"><p className="text-sm"><b>{t.task_type}</b> <span className="text-muted">· {t.provider || "pending"} {t.model}</span></p>
                <span className={`text-sm ${COLORS[t.status]}`}>{t.status}</span></div>
              {t.error && <p role="alert" className="text-sm text-danger">{t.error}</p>}
              {t.started_at && t.finished_at && <p className="text-xs text-muted">Took {((+new Date(t.finished_at) - +new Date(t.started_at)) / 1000).toFixed(1)} s</p>}
              {t.result && <details><summary className="text-sm cursor-pointer">View result</summary><pre className="text-xs overflow-auto max-h-72 mt-2 p-2 bg-bg rounded">{JSON.stringify(t.result, null, 2)}</pre></details>}
              <div className="flex gap-2">{["failed", "cancelled"].includes(t.status) && <button className="btn !py-0.5" onClick={() => act(`/api/ai/tasks/${t.id}/retry`)}>Retry</button>}
                {t.status === "queued" && <button className="btn !py-0.5" onClick={() => act(`/api/ai/tasks/${t.id}/cancel`)}>Cancel</button>}</div>
            </div>))}
        </div></section>
    </div>
  );
}
