"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { ErrorNote, Field } from "@/components/ui";

export default function Settings() {
  const s = useAsync(() => api("/api/settings"), []);
  const [msg, setMsg] = useState<string | null>(null); const [err, setErr] = useState<string | null>(null);
  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); const f = new FormData(e.currentTarget); setErr(null);
    try { await api("/api/settings", { method: "PUT", body: JSON.stringify({ ceiling_height: +f.get("ceiling_height")!, quality: f.get("quality"), walk_speed: +f.get("walk_speed")! }) }); setMsg("Saved."); s.reload(); }
    catch (x: any) { setErr(x.message); }
  }
  if (!s.data) return <ErrorNote msg={s.error} />;
  return (
    <div className="space-y-6 max-w-md"><h1 className="text-3xl">Settings</h1>
      <form onSubmit={save} className="panel p-4 space-y-4">
        <Field label="Default ceiling height for new rooms (m)"><input name="ceiling_height" type="number" step="0.01" min="1.6" defaultValue={s.data.ceiling_height} className="input" /></Field>
        <Field label="3D quality"><select name="quality" defaultValue={s.data.quality} className="input"><option value="low">Low (fastest)</option><option value="balanced">Balanced</option><option value="high">High (shadows, sharper)</option></select></Field>
        <Field label="Walking speed (m/s)"><input name="walk_speed" type="number" step="0.1" min="0.5" max="4" defaultValue={s.data.walk_speed} className="input" /></Field>
        <ErrorNote msg={err} />{msg && <p className="text-sm text-accent">{msg}</p>}
        <button className="btn btn-primary">Save settings</button>
      </form>
      <p className="text-sm text-muted">Theme is switched from the sidebar and remembered in this browser. All measurements are in metres. AI providers are configured in <code>config/providers.json</code>.</p>
    </div>
  );
}
