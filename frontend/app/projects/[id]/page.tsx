"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { API, api, del, fmtBytes, patch, post } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Asset, PROJECT_STATUSES, Project, Room } from "@/lib/types";
import PlanWorkspace from "@/components/PlanWorkspace";
import RoomCard from "@/components/RoomCard";
import SceneView from "@/components/SceneView";
import { Empty, ErrorNote, Field } from "@/components/ui";

const CATS: [string, string][] = [["floor_plan", "Floor plan"], ["room_reference", "Room reference"], ["furniture_reference", "Furniture reference"], ["material_texture", "Material texture"], ["model_3d", "3D model (GLB)"], ["render_image", "Rendered image"], ["walkthrough_video", "Walkthrough video"]];
type Tab = "plan" | "rooms" | "3d" | "assets";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>(); const router = useRouter();
  const [tab, setTab] = useState<Tab>("rooms"); const [err, setErr] = useState<string | null>(null); const [version, setVersion] = useState(0);
  const proj = useAsync(() => api<Project>(`/api/projects/${id}`), [id, version]);
  const rooms = useAsync(() => api<Room[]>(`/api/projects/${id}/rooms`), [id, version]);
  const settings = useAsync(() => api("/api/settings"), []);
  const refresh = () => setVersion((v) => v + 1);
  const p = proj.data;
  if (proj.error) return <div><ErrorNote msg={proj.error} /><Link href="/projects" className="underline text-sm">Back to projects</Link></div>;
  if (!p) return <p className="text-sm text-muted">Loading…</p>;

  const t = p.wall_thickness;
  const nextX = rooms.data?.length ? Math.max(...rooms.data.flatMap((r) => r.polygon.map((q) => q[0]))) + t : 0;
  const baseY = rooms.data?.length ? Math.min(...rooms.data.flatMap((r) => r.polygon.map((q) => q[1]))) : 0;
  async function addRoom(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); const f = new FormData(e.currentTarget); const form = e.currentTarget; setErr(null);
    const w = +f.get("w")!, l = +f.get("l")!, x = +f.get("x")!, y = +f.get("y")!;
    try { await post(`/api/projects/${id}/rooms`, { name: f.get("name"), polygon: [[x, y], [x + w, y], [x + w, y + l], [x, y + l]], ceiling_height: +f.get("h")! }); form.reset(); refresh(); }
    catch (x: any) { setErr(x.message); }
  }
  const guard = async (fn: () => Promise<any>) => { setErr(null); try { await fn(); refresh(); } catch (x: any) { setErr(x.message); } };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap justify-between gap-3 items-start">
        <div><Link href="/projects" className="text-xs text-muted underline">Projects</Link><h1 className="text-3xl mt-1">{p.name}</h1>
          <p className="text-sm text-muted">{p.client_name || "No client set"}{p.location ? ` · ${p.location}` : ""}</p></div>
        <div className="flex flex-wrap gap-2 items-center">
          <select aria-label="Project status" className="input !w-auto" value={p.status} onChange={(e) => guard(() => patch(`/api/projects/${id}`, { status: e.target.value }))}>{PROJECT_STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
          <button className="btn" onClick={() => guard(async () => { const d = await post<Project>(`/api/projects/${id}/duplicate`); router.push(`/projects/${d.id}`); })}>Duplicate</button>
          <button className="btn btn-danger" onClick={() => confirm(`Permanently delete "${p.name}", its rooms and ALL its uploaded files?`) && guard(async () => { await del(`/api/projects/${id}`); router.push("/projects"); })}>Delete</button>
        </div>
      </header>
      <ErrorNote msg={err || rooms.error} />
      <div role="tablist" className="flex gap-1 border-b border-line">
        {([["plan", "Floor plan"], ["rooms", "Rooms"], ["3d", "3D model"], ["assets", "Files"]] as [Tab, string][]).map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`px-4 py-2 text-sm -mb-px border-b-2 ${tab === k ? "border-accent text-ink" : "border-transparent text-muted hover:text-ink"}`}>{label}</button>))}
      </div>

      {tab === "plan" && <PlanWorkspace projectId={id} rooms={rooms.data ?? []} onChange={refresh} />}

      {tab === "rooms" && <div className="space-y-4">
        <p className="text-sm text-muted max-w-2xl">Enter each room&apos;s interior size from your plan. These measurements drive the 3D model exactly; mark them verified once you have checked them. Place neighbouring rooms {t.toFixed(2)} m apart so they share one wall.</p>
        <form onSubmit={addRoom} key={`${rooms.data?.length}-${settings.data?.ceiling_height}`} className="panel p-4 grid grid-cols-2 md:grid-cols-6 gap-3 items-end">
          <Field label="Room name"><input name="name" required className="input" placeholder="Bedroom 1" /></Field>
          <Field label="Width (m)"><input name="w" type="number" step="0.01" min="0.5" required defaultValue="3" className="input" /></Field>
          <Field label="Length (m)"><input name="l" type="number" step="0.01" min="0.5" required defaultValue="4" className="input" /></Field>
          <Field label="Position X (m)"><input name="x" type="number" step="0.01" defaultValue={nextX} className="input" /></Field>
          <Field label="Position Y (m)"><input name="y" type="number" step="0.01" defaultValue={baseY} className="input" /></Field>
          <Field label="Ceiling (m)"><input name="h" type="number" step="0.01" min="1.6" defaultValue={settings.data?.ceiling_height ?? 2.7} className="input" /></Field>
          <button className="btn btn-primary justify-center col-span-2 md:col-span-6 md:w-40">Add room</button>
        </form>
        {rooms.data?.length === 0 && <Empty>No rooms yet. Add the first room above, then add its doors and windows.</Empty>}
        {rooms.data?.map((r) => <RoomCard key={r.id + r.polygon.join()} room={r} onChange={refresh} />)}
        <div className="panel p-4 flex items-end gap-3 max-w-sm"><Field label="Wall thickness (m)"><input type="number" step="0.01" min="0.05" max="1" className="input" defaultValue={p.wall_thickness} onBlur={(e) => +e.target.value !== p.wall_thickness && guard(() => patch(`/api/projects/${id}`, { wall_thickness: +e.target.value }))} /></Field></div>
      </div>}

      {tab === "3d" && <SceneView projectId={id} version={version} />}
      {tab === "assets" && <Files projectId={id} rooms={rooms.data ?? []} />}
    </div>
  );
}

function Files({ projectId, rooms }: { projectId: string; rooms: Room[] }) {
  const [trash, setTrash] = useState(false); const [err, setErr] = useState<string | null>(null); const [msg, setMsg] = useState<string | null>(null);
  const [v, setV] = useState(0);
  const list = useAsync(() => api<Asset[]>(`/api/projects/${projectId}/assets?include_deleted=${trash}`), [projectId, trash, v]);
  const usage = useAsync(() => api("/api/storage/usage"), [v]);
  const act = async (fn: () => Promise<any>, ok?: string) => { setErr(null); setMsg(null); try { await fn(); setV((n) => n + 1); if (ok) setMsg(ok); } catch (e: any) { setErr(e.message); } };
  async function upload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form = e.currentTarget; const fd = new FormData(form); if (!fd.get("room_id")) fd.delete("room_id");
    await act(async () => { await api(`/api/projects/${projectId}/assets`, { method: "POST", body: fd }); form.reset(); }, "Uploaded.");
  }
  const analyze = (a: Asset, task_type: string) => act(() => post("/api/ai/tasks", { task_type, asset_id: a.id }), "Task queued. Follow it in the AI task center.");
  const shown = list.data?.filter((a) => trash ? !!a.deleted_at : !a.deleted_at) ?? [];
  return (
    <div className="space-y-4">
      <form onSubmit={upload} className="panel p-4 grid md:grid-cols-4 gap-3 items-end">
        <Field label="Type"><select name="category" className="input">{CATS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></Field>
        <Field label="Room (optional)"><select name="room_id" className="input"><option value="">Whole apartment</option>{rooms.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select></Field>
        <Field label="File"><input name="file" type="file" required className="input" /></Field>
        <button className="btn btn-primary justify-center">Upload</button>
      </form>
      <ErrorNote msg={err || list.error} />{msg && <p className="text-sm text-accent">{msg}</p>}
      <div className="flex justify-between items-center text-sm text-muted">
        <span>All projects use {usage.data ? fmtBytes(usage.data.active_bytes) : "…"}{usage.data?.trash_bytes ? ` · ${fmtBytes(usage.data.trash_bytes)} in trash` : ""}</span>
        <label className="flex items-center gap-2"><input type="checkbox" checked={trash} onChange={(e) => setTrash(e.target.checked)} /> Show trash</label>
      </div>
      {shown.length === 0 && <Empty>{trash ? "Trash is empty." : "No files yet. Upload a floor plan or a room reference image."}</Empty>}
      <div className="grid md:grid-cols-2 gap-3">
        {shown.map((a) => (
          <div key={a.id} className="panel p-3 flex gap-3">
            {a.mime.startsWith("image/") && !a.deleted_at ? /* eslint-disable-next-line @next/next/no-img-element */ <img src={`${API}/api/assets/${a.id}/file`} alt={a.name} className="w-24 h-24 object-cover rounded border border-line" /> : <div className="w-24 h-24 rounded border border-line grid place-items-center text-xs text-muted">{a.mime.split("/")[1]}</div>}
            <div className="flex-1 min-w-0 space-y-1.5">
              <p className="truncate text-sm font-medium" title={a.name}>{a.name}</p>
              <p className="text-xs text-muted">{CATS.find((c) => c[0] === a.category)?.[1]} · {fmtBytes(a.size_bytes)}</p>
              <div className="flex flex-wrap gap-1.5">
                {!a.deleted_at && a.category === "room_reference" && <button className="btn !py-0.5" onClick={() => analyze(a, "reference_analysis")}>Analyze with AI</button>}
                {!a.deleted_at && a.category === "floor_plan" && <><button className="btn !py-0.5" onClick={() => analyze(a, "floorplan_preprocess")}>Detect lines</button><button className="btn !py-0.5" onClick={() => analyze(a, "floorplan_ocr")}>Read dimensions</button></>}
                {a.deleted_at ? <button className="btn !py-0.5" onClick={() => act(() => post(`/api/assets/${a.id}/restore`))}>Restore</button> : <a className="btn !py-0.5" href={`${API}/api/assets/${a.id}/file`} download>Download</a>}
                {!a.deleted_at && <button className="btn !py-0.5" onClick={() => act(() => del(`/api/assets/${a.id}`))}>Move to trash</button>}
                <button className="btn btn-danger !py-0.5" onClick={() => confirm(`Permanently delete "${a.name}" from disk? This cannot be undone.`) && act(() => del(`/api/assets/${a.id}?permanent=true`))}>Delete forever</button>
              </div>
            </div>
          </div>))}
      </div>
    </div>
  );
}
