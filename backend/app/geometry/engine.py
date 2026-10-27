"""Deterministic 2D -> 3D architectural geometry.

Conventions
-----------
* Units are metres. Room polygons are the *interior clear boundary* (finished
  wall faces), counter-clockwise, in apartment plan coordinates (x, y).
* Plan (x, y) maps to world (x, z). World +Y is up.
* Walls are extruded *outward* from each polygon edge, so the interior
  dimensions of a room never change when wall thickness changes.
* Adjacent rooms that share a partition should be placed with a gap equal to
  the wall thickness, so both rooms' walls coincide exactly.
No AI is involved here: the same input always yields the same geometry.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

Point = tuple[float, float]
EPS = 1e-9
EYE_HEIGHT = 1.6
MIN_EDGE = 0.05
OPENING_KINDS = {"door", "window", "opening"}


class GeometryError(ValueError):
    pass


def signed_area(poly: Sequence[Point]) -> float:
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def polygon_area(poly: Sequence[Point]) -> float:
    return abs(signed_area(poly))


def polygon_centroid(poly: Sequence[Point]) -> Point:
    a = signed_area(poly)
    if abs(a) < EPS:
        return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
    cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        f = x1 * y2 - x2 * y1
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    return (cx / (6 * a), cy / (6 * a))


def edge_vector(poly: Sequence[Point], i: int) -> Point:
    x1, y1 = poly[i]
    x2, y2 = poly[(i + 1) % len(poly)]
    return (x2 - x1, y2 - y1)


def edge_length(poly: Sequence[Point], i: int) -> float:
    return math.hypot(*edge_vector(poly, i))


def _orient(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _cross(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    d1, d2 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    d3, d4 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    return ((d1 > EPS and d2 < -EPS) or (d1 < -EPS and d2 > EPS)) and (
        (d3 > EPS and d4 < -EPS) or (d3 < -EPS and d4 > EPS)
    )


def is_simple(poly: Sequence[Point]) -> bool:
    n = len(poly)
    for i in range(n):
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or (i + 1) % n == j:
                continue
            if _cross(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                return False
    return True


def rect_polygon(width: float, length: float, x: float = 0.0, y: float = 0.0) -> list[Point]:
    if width <= 0 or length <= 0:
        raise GeometryError("Width and length must be positive.")
    return [(x, y), (x + width, y), (x + width, y + length), (x, y + length)]


def to_points(raw: Any) -> list[Point]:
    try:
        return [(float(p[0]), float(p[1])) for p in raw]
    except (TypeError, ValueError, IndexError) as exc:
        raise GeometryError("Polygon must be a list of [x, y] numbers.") from exc


def validate_polygon(poly: Sequence[Point]) -> None:
    if len(poly) < 3:
        raise GeometryError("A room needs at least 3 corners.")
    for i in range(len(poly)):
        if edge_length(poly, i) < MIN_EDGE:
            raise GeometryError(f"Wall {i} is shorter than {MIN_EDGE} m; check for duplicate corners.")
    if not is_simple(poly):
        raise GeometryError("Room outline crosses itself.")
    if polygon_area(poly) < 0.25:
        raise GeometryError("Room area is below 0.25 m2.")


def normalize_ccw(poly: Sequence[Point]) -> list[Point]:
    pts = list(poly)
    return pts[::-1] if signed_area(pts) < 0 else pts


def validate_openings(poly: Sequence[Point], openings: Sequence[dict], ceiling_height: float) -> None:
    by_edge: dict[int, list[dict]] = {}
    for o in openings:
        label = o.get("id") or o.get("kind", "opening")
        if o["kind"] not in OPENING_KINDS:
            raise GeometryError(f"{label}: unknown kind '{o['kind']}'.")
        i = int(o["edge_index"])
        if not 0 <= i < len(poly):
            raise GeometryError(f"{label}: wall {i} does not exist (room has {len(poly)} walls).")
        w, h, s, off = float(o["width"]), float(o["height"]), float(o.get("sill", 0)), float(o["offset"])
        if w <= 0 or h <= 0 or s < 0 or off < 0:
            raise GeometryError(f"{label}: width/height must be positive; offset and sill cannot be negative.")
        L = edge_length(poly, i)
        if off + w > L + 1e-6:
            raise GeometryError(f"{label}: extends past the end of wall {i} ({off + w:.3f} m > {L:.3f} m).")
        if s + h > ceiling_height + 1e-6:
            raise GeometryError(f"{label}: top ({s + h:.2f} m) is above the ceiling ({ceiling_height:.2f} m).")
        by_edge.setdefault(i, []).append(o)
    for i, items in by_edge.items():
        items.sort(key=lambda o: float(o["offset"]))
        for a, b in zip(items, items[1:]):
            if float(b["offset"]) < float(a["offset"]) + float(a["width"]) - 1e-6:
                raise GeometryError(f"Two openings overlap on wall {i}.")


def build_room(room: dict, openings: Sequence[dict], wall_thickness: float = 0.12) -> dict:
    poly = to_points(room["polygon"])
    validate_polygon(poly)
    if signed_area(poly) <= 0:
        raise GeometryError("Room outline must be counter-clockwise.")
    H = float(room.get("ceiling_height", 2.7))
    if H <= 1.5:
        raise GeometryError("Ceiling height must be above 1.5 m.")
    t = float(wall_thickness)
    if t <= 0:
        raise GeometryError("Wall thickness must be positive.")
    base = float(room.get("floor_level", 0.0))
    rid = room.get("id", "room")
    validate_openings(poly, openings, H)

    edge_openings: dict[int, list[dict]] = {}
    for o in openings:
        edge_openings.setdefault(int(o["edge_index"]), []).append(o)

    walls: list[dict] = []
    glass: list[dict] = []
    info: list[dict] = []
    n = len(poly)
    for i in range(n):
        sx, sy = poly[i]
        L = edge_length(poly, i)
        dx, dy = edge_vector(poly, i)
        dx, dy = dx / L, dy / L
        nx, ny = dy, -dx  # outward normal for a CCW polygon
        rot = -math.atan2(dy, dx)
        count = 0

        def box(u0: float, u1: float, y0: float, y1: float, kind: str, thick: float, idx: int) -> dict:
            um = (u0 + u1) / 2
            return {
                "id": f"{rid}-{kind}{i}-{idx}", "kind": kind, "room_id": rid, "edge": i,
                "center": [sx + dx * um + nx * t / 2, base + (y0 + y1) / 2, sy + dy * um + ny * t / 2],
                "size": [u1 - u0, y1 - y0, thick], "rotation_y": rot, "u": [u0, u1], "y": [y0, y1],
            }

        cursor = -t  # first wall piece extends back by t to close the outer corner
        for o in sorted(edge_openings.get(i, []), key=lambda o: float(o["offset"])):
            off, w, h, s = float(o["offset"]), float(o["width"]), float(o["height"]), float(o.get("sill", 0))
            if off - cursor > 1e-6:
                walls.append(box(cursor, off, 0, H, "wall", t, count)); count += 1
            if s > 1e-6:
                walls.append(box(off, off + w, 0, s, "wall", t, count)); count += 1
            if H - (s + h) > 1e-6:
                walls.append(box(off, off + w, s + h, H, "wall", t, count)); count += 1
            um = off + w / 2
            if o["kind"] == "window":
                g = box(off, off + w, s, s + h, "glass", 0.02, count); count += 1
                glass.append(g)
            info.append({
                "id": o.get("id"), "kind": o["kind"], "edge": i, "width": w, "height": h, "sill": s,
                "is_entrance": bool(o.get("is_entrance", False)),
                "center": [sx + dx * um + nx * t / 2, base + s + h / 2, sy + dy * um + ny * t / 2],
                "inward": [-nx, -ny], "rotation_y": rot,
            })
            cursor = off + w
        if L - cursor > 1e-6:
            walls.append(box(cursor, L, 0, H, "wall", t, count))

    return {
        "room_id": rid, "name": room.get("name", ""), "polygon": [list(p) for p in poly],
        "ceiling_height": H, "floor_level": base, "area": polygon_area(poly),
        "walls": walls, "glass": glass, "openings": info,
        "floor": {"polygon": [list(p) for p in poly], "y": base},
        "ceiling": {"polygon": [list(p) for p in poly], "y": base + H},
    }


def build_scene(rooms: Sequence[dict], wall_thickness: float = 0.12) -> dict:
    """rooms: dicts with room fields plus an 'openings' list."""
    built = [build_room(r, r.get("openings", []), wall_thickness) for r in rooms]
    xs = [p[0] for r in built for p in r["polygon"]]
    zs = [p[1] for r in built for p in r["polygon"]]
    bounds = {"min": [min(xs) - wall_thickness, min(zs) - wall_thickness],
              "max": [max(xs) + wall_thickness, max(zs) + wall_thickness]} if built else None
    return {"wall_thickness": wall_thickness, "rooms": built, "bounds": bounds, "spawn": _spawn(built)}


def _spawn(built: Sequence[dict]) -> dict | None:
    if not built:
        return None
    doors = [(r, o) for r in built for o in r["openings"] if o["kind"] == "door"]
    pick = next(((r, o) for r, o in doors if o["is_entrance"]), doors[0] if doors else None)
    if pick:
        r, o = pick
        ix, iz = o["inward"]
        cx, _, cz = o["center"]
        return {"position": [cx + ix * 0.8, r["floor_level"] + EYE_HEIGHT, cz + iz * 0.8], "look": [ix, iz],
                "from": "entrance" if o["is_entrance"] else "first_door"}
    r = built[0]
    cx, cy = polygon_centroid([tuple(p) for p in r["polygon"]])
    return {"position": [cx, r["floor_level"] + EYE_HEIGHT, cy], "look": [0.0, -1.0], "from": "room_center"}
