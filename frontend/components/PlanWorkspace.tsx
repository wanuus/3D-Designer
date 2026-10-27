"use client";
import { useMemo, useState } from "react";
import { API, api, patch, post } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Asset, FloorPlan, Room } from "@/lib/types";
import { Empty, ErrorNote, Field } from "./ui";

type Pt = [number, number];
type Mode = "view" | "calibrate" | "trace";

export default function PlanWorkspace({ projectId, rooms, onChange }: { projectId: string; rooms: Room[]; onChange: () => void }) {
  const assets = useAsync(() => api<Asset[]>(`/api/projects/${projectId}/assets?category=floor_plan`), [projectId]);
  const fp = useAsync(() => api<FloorPlan | null>(`/api/projects/${projectId}/floorplan`), [projectId]);
  const tasks = useAsync(() => api<any[]>(`/api/ai/tasks?project_id=${projectId}`), [projectId]);
  const [assetId, setAssetId] = useState<string>("");
  const [mode, setMode] = useState<Mode>("view");
  const [pts, setPts] = useState<Pt[]>([]);
  const [size, setSize] = useState<[number, number]>([1000, 700]);
  const [zoom, setZoom] = useState(100);
  const [real, setReal] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const images = (assets.data ?? []).filter((a) => a.mime.startsWith("image/"));
  const asset = images.find((a) => a.id === (assetId || fp.data?.asset_id)) ?? images[0];
  const scale = fp.data?.scale_m_per_px ?? null;
  const [W, H] = fp.data && asset && fp.data.asset_id === asset.id ? [fp.data.image_width, fp.data.image_height] : size;
  const unit = W / 220; // marker size in image pixels, so it looks the same at any resolution

  // Lengths the OCR step has already read from this plan (offered as one-click calibration values)
  const ocrLengths = useMemo(() => {
    const out = new Set<number>();
    for (const t of tasks.data ?? []) if (t.task_type === "floorplan_ocr" && t.status === "completed" && t.input?.asset_id === asset?.id)
      for (const x of t.result?.texts ?? []) if (x.length_m && x.length_m > 0.3 && x.length_m < 30) out.add(Math.round(x.length_m * 1000) / 1000);
    return [...out].slice(0, 8);
  }, [tasks.data, asset?.id]);

  const fail = (e: any) => { setErr(e.message); setMsg(null); };
  const reset = (m: Mode) => { setMode(m); setPts([]); setErr(null); setMsg(null); setReal(""); setName(""); };
  const toImg = (e: React.MouseEvent<SVGSVGElement>): Pt | null => {
    const svg = e.currentTarget, p = svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY;
    const m = svg.getScreenCTM(); if (!m) return null; const q = p.matrixTransform(m.inverse()); return [Math.round(q.x * 10) / 10, Math.round(q.y * 10) / 10];
  };
  const click = (e: React.MouseEvent<SVGSVGElement>) => {
    if (mode === "view") return; const p = toImg(e); if (!p) return;
    if (mode === "calibrate") setPts((a) => (a.length >= 2 ? [p] : [...a, p])); else setPts((a) => [...a, p]);
  };
  const dist = (a: Pt, b: Pt) => Math.hypot(a[0] - b[0], a[1] - b[1]);

  async function saveCalibration() {
    try {
      await api(`/api/projects/${projectId}/floorplan`, { method: "PUT", body: JSON.stringify({ asset_id: asset!.id, p1: pts[0], p2: pts[1], real_distance_m: +real, image_width: W, image_height: H }) });
      await fp.reload(); reset("view"); setMsg("Scale saved. You can now trace rooms.");
    } catch (e) { fail(e); }
  }
  async function saveRoom() {
    try {
      await post(`/api/projects/${projectId}/floorplan/trace-room`, { name, points_px: pts });
      reset("view"); setMsg(`Room added. Check its size in "Rooms" and adjust if needed.`); onChange();
    } catch (e) { fail(e); }
  }
  async function verify() {
    if (!confirm("Confirm that every room's measurements match the real apartment? The 3D model will treat them as verified.")) return;
    try { await post(`/api/projects/${projectId}/verify-floorplan`); setMsg("Floor plan marked as verified."); onChange(); } catch (e) { fail(e); }
  }

  if (assets.loading) return <p className="text-sm text-muted">Loading…</p>;
  if (!asset) return <Empty>Upload a floor plan image (PNG, JPG or WebP) in the <b>Files</b> tab first. PDFs and DXF files cannot be traced yet: export them to PNG.</Empty>;

  const polyPx = (r: Room) => (scale ? r.polygon.map(([x, y]) => [x / scale, y / scale] as Pt) : []);
  const D = scale && pts.length ? pts : [];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 items-center">
        {images.length > 1 && <select className="input !w-auto" value={asset.id} onChange={(e) => { setAssetId(e.target.value); reset("view"); }} aria-label="Floor plan file">{images.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select>}
        <button className={`btn ${mode === "calibrate" ? "btn-primary" : ""}`} onClick={() => reset("calibrate")}>1. {scale ? "Recalibrate" : "Set scale"}</button>
        <button className={`btn ${mode === "trace" ? "btn-primary" : ""}`} disabled={!scale} onClick={() => reset("trace")} title={scale ? "" : "Set the scale first"}>2. Trace a room</button>
        <button className="btn" disabled={!rooms.length} onClick={verify}>3. Mark floor plan verified</button>
        <label className="text-sm flex items-center gap-2 ml-auto">Zoom <input type="range" min={60} max={300} value={zoom} onChange={(e) => setZoom(+e.target.value)} /> {zoom}%</label>
      </div>
      <ErrorNote msg={err} />{msg && <p className="text-sm text-accent">{msg}</p>}

      {mode === "calibrate" && <div className="panel p-3 space-y-3 text-sm">
        <p>Click <b>two points</b> on the plan whose real distance you know (for example the two ends of a dimensioned wall), then enter that distance.
          {scale && " Recalibrating moves where existing rooms appear on the plan; it does not change their sizes."}</p>
        {pts.length === 2 && <div className="flex flex-wrap items-end gap-3">
          <Field label={`Real distance between the points (m) · ${dist(pts[0], pts[1]).toFixed(0)} px apart`}><input className="input" type="number" step="0.001" min="0.1" value={real} onChange={(e) => setReal(e.target.value)} /></Field>
          <button className="btn btn-primary" disabled={!(+real > 0)} onClick={saveCalibration}>Save scale</button></div>}
        {pts.length === 2 && ocrLengths.length > 0 && <p className="text-xs text-muted">Lengths read from this plan by OCR (AI-estimated, check them): {ocrLengths.map((v) => <button key={v} className="btn !py-0 !px-1.5 mx-0.5" onClick={() => setReal(String(v))}>{v} m</button>)}</p>}
      </div>}
      {mode === "trace" && <div className="panel p-3 space-y-3 text-sm">
        <p>Click each <b>inside corner</b> of the room in order (the inner face of the walls). Near-straight walls are straightened automatically and measurements rounded to 1 cm. {pts.length} corner{pts.length === 1 ? "" : "s"} placed.</p>
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Room name"><input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Bedroom 1" /></Field>
          <button className="btn" disabled={!pts.length} onClick={() => setPts((a) => a.slice(0, -1))}>Undo corner</button>
          <button className="btn btn-primary" disabled={pts.length < 3 || !name.trim()} onClick={saveRoom}>Create room</button>
          <button className="btn" onClick={() => reset("view")}>Cancel</button></div>
      </div>}

      <div className="panel overflow-auto max-h-[70vh]">
        <div className="relative" style={{ width: `${zoom}%` }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={`${API}/api/assets/${asset.id}/file`} alt="Floor plan" className="block w-full select-none" draggable={false}
            onLoad={(e) => { const i = e.currentTarget; if (i.naturalWidth) setSize([i.naturalWidth, i.naturalHeight]); }} />
          <svg viewBox={`0 0 ${W} ${H}`} className={`absolute inset-0 w-full h-full ${mode === "view" ? "" : "cursor-crosshair"}`} onClick={click} role="img" aria-label="Plan overlay">
            {scale && rooms.map((r) => {
              const P = polyPx(r); const cx = P.reduce((s, p) => s + p[0], 0) / P.length, cy = P.reduce((s, p) => s + p[1], 0) / P.length;
              return <g key={r.id}>
                <polygon points={P.map((p) => p.join(",")).join(" ")} fill="rgb(46 107 94 / 0.18)" stroke="rgb(46 107 94)" strokeWidth={unit * 0.5} />
                {r.openings.map((o) => { const a = P[o.edge_index], b = P[(o.edge_index + 1) % P.length], L = dist(a, b) || 1, ux = (b[0] - a[0]) / L, uy = (b[1] - a[1]) / L, s0 = o.offset / scale, s1 = (o.offset + o.width) / scale;
                  return <line key={o.id} x1={a[0] + ux * s0} y1={a[1] + uy * s0} x2={a[0] + ux * s1} y2={a[1] + uy * s1} stroke={o.kind === "window" ? "#3b82c4" : "#c0792b"} strokeWidth={unit * 1.4} />; })}
                <text x={cx} y={cy} textAnchor="middle" fontSize={unit * 4} fill="rgb(27 34 38)" stroke="white" strokeWidth={unit * 0.8} paintOrder="stroke">{r.name} · {r.area.toFixed(1)} m²</text>
              </g>;
            })}
            {mode === "calibrate" && pts.map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r={unit * 1.2} fill="#d33" />)}
            {mode === "calibrate" && pts.length === 2 && <line x1={pts[0][0]} y1={pts[0][1]} x2={pts[1][0]} y2={pts[1][1]} stroke="#d33" strokeWidth={unit * 0.6} />}
            {mode === "trace" && <>
              {pts.length > 1 && <polyline points={pts.map((p) => p.join(",")).join(" ")} fill="none" stroke="#d33" strokeWidth={unit * 0.6} />}
              {pts.map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r={unit * 1.1} fill={i === 0 ? "#2a7" : "#d33"} />)}
              {D.map((p, i) => i > 0 && <text key={`l${i}`} x={(p[0] + D[i - 1][0]) / 2} y={(p[1] + D[i - 1][1]) / 2 - unit * 1.5} fontSize={unit * 3.2} textAnchor="middle" fill="#d33" stroke="white" strokeWidth={unit * 0.6} paintOrder="stroke">{(dist(p, D[i - 1]) * scale!).toFixed(2)} m</text>)}
            </>}
          </svg>
        </div>
      </div>
      <p className="text-xs text-muted">{scale ? `Scale: 1 px = ${(scale * 1000).toFixed(2)} mm (from a ${fp.data!.ref_real_m} m reference).` : "No scale yet: lengths on the plan are unknown until you set one."} Doors are orange and windows blue on the overlay; add or change them in the Rooms tab.</p>
    </div>
  );
}
