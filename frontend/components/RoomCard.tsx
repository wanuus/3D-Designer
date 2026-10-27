"use client";
import { useState } from "react";
import { del, patch, post } from "@/lib/api";
import { DIM_LABEL, ROOM_STATUSES, Room } from "@/lib/types";
import { ErrorNote, Field } from "./ui";

const edgeLen = (p: [number, number][], i: number) => Math.hypot(p[(i + 1) % p.length][0] - p[i][0], p[(i + 1) % p.length][1] - p[i][1]);
function rectSize(r: Room) {
  const p = r.polygon; if (p.length !== 4) return null;
  const a = edgeLen(p, 0), b = edgeLen(p, 1);
  const rect = Math.abs(p[0][0] - p[1][0]) < 1e-9 || Math.abs(p[0][1] - p[1][1]) < 1e-9;
  return rect && Math.abs(a * b - r.area) < 1e-6 ? { w: a, l: b, x: Math.min(...p.map((q) => q[0])), y: Math.min(...p.map((q) => q[1])) } : null;
}

export default function RoomCard({ room, onChange }: { room: Room; onChange: () => void }) {
  const [open, setOpen] = useState(false); const [err, setErr] = useState<string | null>(null); const [edit, setEdit] = useState(false);
  const rs = rectSize(room);
  const run = async (fn: () => Promise<any>) => { setErr(null); try { await fn(); onChange(); return true; } catch (e: any) { setErr(e.message); return false; } };
  const saveSize = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget); const w = +f.get("w")!, l = +f.get("l")!, x = rs!.x, y = rs!.y;
    run(async () => { await patch(`/api/rooms/${room.id}`, { polygon: [[x, y], [x + w, y], [x + w, y + l], [x, y + l]], dimension_source: "user_defined" }); setEdit(false); });
  };
  const addOpening = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget); const form = e.currentTarget; const kind = String(f.get("kind"));
    run(async () => { await post(`/api/rooms/${room.id}/openings`, { kind, edge_index: +f.get("edge")!, offset: +f.get("offset")!, width: +f.get("width")!, height: +f.get("height")!, sill: +f.get("sill")!, is_entrance: f.get("entrance") === "on" }); form.reset(); });
  };
  return (
    <div className="panel p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-lg">{room.name}</h3>
          <p className="text-sm text-muted">{rs ? `${rs.w.toFixed(2)} × ${rs.l.toFixed(2)} m · ` : ""}{room.area.toFixed(2)} m² · ceiling {room.ceiling_height.toFixed(2)} m · <span className="badge">{DIM_LABEL[room.dimension_source]}</span></p>
        </div>
        <div className="flex gap-2 items-center">
          <select aria-label="Room status" className="input !w-auto" value={room.status} onChange={(e) => run(() => patch(`/api/rooms/${room.id}`, { status: e.target.value }))}>{ROOM_STATUSES.map((s) => <option key={s}>{s}</option>)}</select>
          <input aria-label="Progress percent" type="number" min={0} max={100} className="input !w-16" defaultValue={room.progress} onBlur={(e) => +e.target.value !== room.progress && run(() => patch(`/api/rooms/${room.id}`, { progress: Math.max(0, Math.min(100, +e.target.value)) }))} />%
        </div>
      </div>
      <div className="h-1.5 bg-line rounded"><div className="h-1.5 bg-accent rounded" style={{ width: `${room.progress}%` }} /></div>
      <ErrorNote msg={err} />
      <div className="flex flex-wrap gap-2">
        {room.dimension_source !== "verified" && <button className="btn" onClick={() => run(() => patch(`/api/rooms/${room.id}`, { dimension_source: "verified" }))}>Mark dimensions verified</button>}
        {rs ? <button className="btn" onClick={() => setEdit(!edit)}>Edit size</button> : <span className="text-xs text-muted self-center">Size editing is available for rectangular rooms.</span>}
        <button className="btn" onClick={() => setOpen(!open)} aria-expanded={open}>Doors &amp; windows ({room.openings.length})</button>
        <button className="btn btn-danger" onClick={() => confirm(`Delete room "${room.name}" and its doors and windows?`) && run(() => del(`/api/rooms/${room.id}`))}>Delete room</button>
      </div>
      {edit && rs && <form onSubmit={saveSize} className="grid grid-cols-3 gap-3 items-end">
        <Field label="Width (m)"><input name="w" type="number" step="0.01" min="0.5" defaultValue={rs.w} className="input" /></Field>
        <Field label="Length (m)"><input name="l" type="number" step="0.01" min="0.5" defaultValue={rs.l} className="input" /></Field>
        <button className="btn btn-primary justify-center">Save size</button></form>}
      {open && <div className="space-y-3 border-t border-line pt-3">
        {room.openings.map((o) => <div key={o.id} className="flex justify-between text-sm gap-2">
          <span>{o.kind === "door" && o.is_entrance ? "Entrance door" : o.kind[0].toUpperCase() + o.kind.slice(1)} · wall {o.edge_index + 1} · at {o.offset.toFixed(2)} m · {o.width.toFixed(2)} × {o.height.toFixed(2)} m{o.sill ? ` · sill ${o.sill.toFixed(2)} m` : ""}</span>
          <button className="text-danger underline" onClick={() => run(() => del(`/api/openings/${o.id}`))}>Remove</button></div>)}
        <form onSubmit={addOpening} className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
          <Field label="Type"><select name="kind" className="input"><option value="door">Door</option><option value="window">Window</option><option value="opening">Open passage</option></select></Field>
          <Field label="Wall"><select name="edge" className="input">{room.polygon.map((_, i) => <option key={i} value={i}>Wall {i + 1} ({edgeLen(room.polygon, i).toFixed(2)} m)</option>)}</select></Field>
          <Field label="Distance from wall start (m)"><input name="offset" type="number" step="0.01" min="0" defaultValue="0.5" className="input" /></Field>
          <Field label="Width (m)"><input name="width" type="number" step="0.01" min="0.1" defaultValue="0.9" className="input" /></Field>
          <Field label="Height (m)"><input name="height" type="number" step="0.01" min="0.1" defaultValue="2.1" className="input" /></Field>
          <Field label="Sill height (m)"><input name="sill" type="number" step="0.01" min="0" defaultValue="0" className="input" /></Field>
          <label className="text-sm flex items-center gap-2 pb-2"><input name="entrance" type="checkbox" /> Apartment entrance</label>
          <button className="btn btn-primary justify-center">Add</button>
        </form>
        <p className="text-xs text-muted">Walls are numbered in drawing order, counter-clockwise from the room&apos;s first corner. Windows usually need a sill height of about 0.9 m and a height of about 1.2 m.</p>
      </div>}
    </div>
  );
}
