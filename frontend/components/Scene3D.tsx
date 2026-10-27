"use client";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, PointerLockControls } from "@react-three/drei";
import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { Box, Scene } from "@/lib/types";

export type Quality = "low" | "balanced" | "high";
type Props = { scene: Scene; mode: "orbit" | "walk"; collide: boolean; speed: number; quality: Quality; resetKey: number; onRoom: (name: string) => void };

function pip(poly: [number, number][], x: number, z: number) {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, zi] = poly[i], [xj, zj] = poly[j];
    if (zi > z !== zj > z && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) inside = !inside;
  }
  return inside;
}

/** Circle-vs-oriented-box push-out in the XZ plane. Box local axes follow three.js rotation.y. */
function resolve(p: THREE.Vector3, boxes: Box[], r: number) {
  for (let it = 0; it < 3; it++) for (const b of boxes) {
    const th = b.rotation_y, c = Math.cos(th), s = Math.sin(th);
    const dx = p.x - b.center[0], dz = p.z - b.center[2];
    const lx = dx * c - dz * s, lz = dx * s + dz * c;
    const hx = b.size[0] / 2, hz = b.size[2] / 2;
    const ox = lx - Math.max(-hx, Math.min(hx, lx)), oz = lz - Math.max(-hz, Math.min(hz, lz));
    const d = Math.hypot(ox, oz);
    let px = 0, pz = 0;
    if (d > 1e-6) { if (d < r) { px = (ox / d) * (r - d); pz = (oz / d) * (r - d); } }
    else { const gx = hx - Math.abs(lx), gz = hz - Math.abs(lz); if (gx < gz) px = Math.sign(lx || 1) * (gx + r); else pz = Math.sign(lz || 1) * (gz + r); }
    if (px || pz) { p.x += px * c + pz * s; p.z += -px * s + pz * c; }
  }
}

function Polygon({ poly, y, color, double = true }: { poly: [number, number][]; y: number; color: string; double?: boolean }) {
  const geo = useMemo(() => { const g = new THREE.ShapeGeometry(new THREE.Shape(poly.map(([x, z]) => new THREE.Vector2(x, z)))); g.rotateX(Math.PI / 2); return g; }, [poly]);
  return <mesh geometry={geo} position={[0, y, 0]} receiveShadow><meshStandardMaterial color={color} side={double ? THREE.DoubleSide : THREE.FrontSide} /></mesh>;
}

function Walker({ scene, collide, speed, resetKey, onRoom }: Omit<Props, "mode" | "quality">) {
  const { camera } = useThree();
  const keys = useRef<Record<string, boolean>>({});
  const live = useRef({ speed, collide }); live.current = { speed, collide };
  const lastRoom = useRef("");
  const solid = useMemo(() => scene.rooms.flatMap((r) => [...r.walls, ...r.glass]), [scene]);

  useEffect(() => {
    const sp = scene.spawn; if (!sp) return;
    camera.rotation.order = "YXZ";
    camera.position.set(...sp.position);
    camera.rotation.set(0, Math.atan2(-sp.look[0], -sp.look[1]), 0);
  }, [scene, resetKey, camera]);

  useEffect(() => {
    const typing = (e: KeyboardEvent) => ["INPUT", "SELECT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName);
    const dn = (e: KeyboardEvent) => { if (!typing(e)) keys.current[e.code] = true; };
    const up = (e: KeyboardEvent) => { keys.current[e.code] = false; };
    window.addEventListener("keydown", dn); window.addEventListener("keyup", up);
    return () => { window.removeEventListener("keydown", dn); window.removeEventListener("keyup", up); };
  }, []);

  const f = useMemo(() => new THREE.Vector3(), []);
  useFrame((_, dt) => {
    if (!document.pointerLockElement) return; // only move while the view is captured: no accidental input
    const k = keys.current;
    const fw = (k.KeyW || k.ArrowUp ? 1 : 0) - (k.KeyS || k.ArrowDown ? 1 : 0);
    const st = (k.KeyD || k.ArrowRight ? 1 : 0) - (k.KeyA || k.ArrowLeft ? 1 : 0);
    if (fw || st) {
      camera.getWorldDirection(f); f.y = 0; f.normalize();
      const mx = f.x * fw + -f.z * st, mz = f.z * fw + f.x * st, len = Math.hypot(mx, mz) || 1;
      const step = Math.min(dt, 0.05) * live.current.speed;
      camera.position.x += (mx / len) * step; camera.position.z += (mz / len) * step;
      if (live.current.collide) {
        const y = camera.position.y, near = solid.filter((b) => b.center[1] + b.size[1] / 2 > y - 1.4 && b.center[1] - b.size[1] / 2 < y + 0.1);
        resolve(camera.position, near, 0.25);
      }
    }
    const here = scene.rooms.find((r) => pip(r.polygon, camera.position.x, camera.position.z))?.name ?? "Outside";
    if (here !== lastRoom.current) { lastRoom.current = here; onRoom(here); }
  });
  return <PointerLockControls />;
}

export default function Scene3D({ scene, mode, collide, speed, quality, resetKey, onRoom }: Props) {
  const b = scene.bounds!;
  const cx = (b.min[0] + b.max[0]) / 2, cz = (b.min[1] + b.max[1]) / 2, size = Math.max(b.max[0] - b.min[0], b.max[1] - b.min[1], 4);
  const shadows = quality !== "low";
  return (
    <Canvas key={mode} shadows={shadows} dpr={quality === "high" ? [1, 2] : quality === "balanced" ? [1, 1.5] : 1}
      camera={{ position: [cx + size * 0.6, size * 0.9, cz + size * 0.9], fov: mode === "walk" ? 70 : 45, near: 0.05, far: Math.max(200, size * 20) }}>
      <color attach="background" args={[mode === "walk" ? "#cfd6d4" : "#dfe3e1"]} />
      <hemisphereLight args={["#ffffff", "#8a8f8c", 0.9]} />
      <directionalLight position={[cx + 6, 12, cz + 4]} intensity={1.1} castShadow={shadows} shadow-mapSize={quality === "high" ? [2048, 2048] : [1024, 1024]} />
      {scene.rooms.map((r) => (
        <group key={r.room_id}>
          <Polygon poly={r.floor.polygon} y={r.floor.y + 0.001} color="#b9a58a" />
          {mode === "walk" && <Polygon poly={r.ceiling.polygon} y={r.ceiling.y} color="#f4f3ef" />}
          {r.walls.map((w) => (
            <mesh key={w.id} position={w.center} rotation-y={w.rotation_y} castShadow={shadows} receiveShadow={shadows}>
              <boxGeometry args={w.size} /><meshStandardMaterial color="#e6e2da" />
            </mesh>))}
          {r.glass.map((w) => (
            <mesh key={w.id} position={w.center} rotation-y={w.rotation_y}><boxGeometry args={w.size} /><meshStandardMaterial color="#9fc4d6" transparent opacity={0.35} /></mesh>))}
        </group>))}
      {mode === "orbit" ? <OrbitControls target={[cx, 0, cz]} maxPolarAngle={Math.PI / 2 - 0.02} /> :
        <Walker scene={scene} collide={collide} speed={speed} resetKey={resetKey} onRoom={onRoom} />}
    </Canvas>
  );
}