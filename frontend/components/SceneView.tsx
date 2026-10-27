"use client";
import dynamic from "next/dynamic";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Scene } from "@/lib/types";
import { Empty, ErrorNote } from "./ui";
import type { Quality } from "./Scene3D";
const Scene3D = dynamic(() => import("./Scene3D"), { ssr: false, loading: () => <div className="h-full grid place-items-center text-sm text-muted">Loading 3D view…</div> });

export default function SceneView({ projectId, version }: { projectId: string; version: number }) {
  const sc = useAsync(() => api<Scene>(`/api/projects/${projectId}/scene`), [projectId, version]);
  const settings = useAsync(() => api("/api/settings"), []);
  const [mode, setMode] = useState<"orbit" | "walk">("orbit");
  const [collide, setCollide] = useState(true);
  const [room, setRoom] = useState("");
  const [reset, setReset] = useState(0);
  const [quality, setQuality] = useState<Quality | "">("");
  const [speed, setSpeed] = useState<number | null>(null);
  const q = (quality || settings.data?.quality || "balanced") as Quality;
  const sp = speed ?? settings.data?.walk_speed ?? 1.4;
  if (sc.error) return <ErrorNote msg={sc.error} />;
  if (!sc.data) return <p className="text-sm text-muted">Building 3D model…</p>;
  if (!sc.data.rooms.length) return <Empty>Add at least one room to generate the 3D model.</Empty>;
  const unverified = Object.entries(sc.data.dimension_sources).filter(([, v]) => v !== "verified").length;
  const bd = sc.data.bounds!;
  const biggest = Math.max(bd.max[0] - bd.min[0], bd.max[1] - bd.min[1]);
  return (
    <div className="space-y-3">
      {biggest > 30 && <p role="alert" className="text-sm text-danger border border-danger/40 rounded px-3 py-2">The model is {biggest.toFixed(0)} m wide. If your apartment is smaller, a size was probably typed in cm or mm. All sizes must be in metres (3.5, not 350). Fix it in the Rooms tab, or re-trace the room in the Floor plan tab.</p>}
      <div className="flex flex-wrap items-center gap-3">
        <div role="group" aria-label="View mode" className="flex gap-1">
          <button className={`btn ${mode === "orbit" ? "btn-primary" : ""}`} onClick={() => setMode("orbit")}>Overview</button>
          <button className={`btn ${mode === "walk" ? "btn-primary" : ""}`} onClick={() => setMode("walk")}>Walk through</button>
        </div>
        <label className="text-sm flex items-center gap-1.5">Quality
          <select className="input !w-auto" value={q} onChange={(e) => setQuality(e.target.value as Quality)}><option value="low">Low</option><option value="balanced">Balanced</option><option value="high">High</option></select></label>
        {mode === "walk" && <>
          <label className="text-sm flex items-center gap-1.5">Speed <input type="range" min={0.5} max={4} step={0.1} value={sp} onChange={(e) => setSpeed(+e.target.value)} /> {sp.toFixed(1)} m/s</label>
          <label className="text-sm flex items-center gap-1.5"><input type="checkbox" checked={collide} onChange={(e) => setCollide(e.target.checked)} /> Wall collision</label>
          <button className="btn" onClick={() => setReset((n) => n + 1)}>Back to entrance</button>
        </>}
      </div>
      {unverified > 0 && <p className="text-xs text-muted">{unverified} room{unverified > 1 ? "s have" : " has"} dimensions that are not marked verified. The 3D model uses them exactly as entered.</p>}
      <div className="relative h-[60vh] min-h-[360px] panel overflow-hidden">
        <Scene3D scene={sc.data} mode={mode} collide={collide} speed={sp} quality={q} resetKey={reset} onRoom={setRoom} />
        {mode === "walk" && <div className="absolute left-3 top-3 bg-surface/90 border border-line rounded px-3 py-1.5 text-xs pointer-events-none">
          <div>Room: <b>{room || "…"}</b></div><div className="text-muted">Click the view to look around · W A S D or arrows to walk · Esc to release</div></div>}
      </div>
    </div>
  );
}