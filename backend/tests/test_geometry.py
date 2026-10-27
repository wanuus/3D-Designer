import math
import pytest
from app.geometry import engine as g
from app.geometry.dimensions import parse_dimension, parse_pair

T = 0.12


def room(poly=None, **kw):
    return {"id": "r1", "name": "Bedroom", "polygon": poly or g.rect_polygon(3, 4), "ceiling_height": 2.7, **kw}


def inner_point(piece, poly):
    """Point on the room-facing side of a wall piece (should lie on the polygon edge line)."""
    th = piece["rotation_y"]
    dx, dz = math.cos(th), -math.sin(th)
    nx, nz = dz, -dx
    cx, _, cz = piece["center"]
    return cx - nx * piece["size"][2] / 2, cz - nz * piece["size"][2] / 2


def test_real_dimensions_3x4():
    r = g.build_room(room(), [], T)
    poly = [tuple(p) for p in r["polygon"]]
    assert [round(g.edge_length(poly, i), 9) for i in range(4)] == [3, 4, 3, 4]
    assert r["area"] == pytest.approx(12.0, abs=1e-9)
    assert len(r["walls"]) == 4
    # every wall's inner face lies exactly on the verified polygon edge
    for w in r["walls"]:
        px, pz = inner_point(w, poly)
        sx, sy = poly[w["edge"]]
        ex, ey = poly[(w["edge"] + 1) % 4]
        L = math.hypot(ex - sx, ey - sy)
        dist = abs((ex - sx) * (pz - sy) - (ey - sy) * (px - sx)) / L
        assert dist < 1e-9
    # opposite inner faces are exactly 4 m (edges 0/2) and 3 m (edges 1/3) apart
    z = {w["edge"]: inner_point(w, poly) for w in r["walls"]}
    assert abs(z[2][1] - z[0][1]) == pytest.approx(4.0, abs=1e-9)
    assert abs(z[1][0] - z[3][0]) == pytest.approx(3.0, abs=1e-9)


def test_interior_independent_of_wall_thickness():
    a = g.build_room(room(), [], 0.08)
    b = g.build_room(room(), [], 0.30)
    assert a["polygon"] == b["polygon"] and a["area"] == b["area"]


def test_floor_and_ceiling_heights():
    r = g.build_room(room(floor_level=0.5), [], T)
    assert r["floor"]["y"] == 0.5 and r["ceiling"]["y"] == pytest.approx(3.2)


def test_door_and_window_cut_openings():
    ops = [
        {"id": "d", "kind": "door", "edge_index": 0, "offset": 1.0, "width": 0.9, "height": 2.1, "sill": 0, "is_entrance": True},
        {"id": "w", "kind": "window", "edge_index": 2, "offset": 0.5, "width": 1.5, "height": 1.2, "sill": 0.9},
    ]
    r = g.build_room(room(), ops, T)
    # no wall piece may occupy the door's span below its top
    for w in r["walls"]:
        if w["edge"] == 0:
            u0, u1 = w["u"]; y0, y1 = w["y"]
            overlaps_span = u0 < 1.9 - 1e-9 and u1 > 1.0 + 1e-9
            if overlaps_span:
                assert y0 >= 2.1 - 1e-9
    assert len(r["glass"]) == 1
    assert r["glass"][0]["y"] == [0.9, pytest.approx(2.1)]
    # total wall area on edge 0 = full wall minus door hole (plus the t corner extension)
    area0 = sum((w["u"][1] - w["u"][0]) * (w["y"][1] - w["y"][0]) for w in r["walls"] if w["edge"] == 0)
    assert area0 == pytest.approx((3 + T) * 2.7 - 0.9 * 2.1)


def test_spawn_at_entrance_faces_inward():
    ops = [{"id": "d", "kind": "door", "edge_index": 0, "offset": 1.0, "width": 0.9, "height": 2.1, "is_entrance": True}]
    scene = g.build_scene([{**room(), "openings": ops}], T)
    sp = scene["spawn"]
    assert sp["from"] == "entrance"
    assert sp["look"] == [0.0, 1.0] or tuple(round(v, 6) for v in sp["look"]) == (0.0, 1.0)
    assert sp["position"][1] == g.EYE_HEIGHT
    assert 0 < sp["position"][2] < 4  # inside the room


@pytest.mark.parametrize("bad", [
    {"kind": "door", "edge_index": 0, "offset": 2.5, "width": 0.9, "height": 2.1},   # past end of wall
    {"kind": "door", "edge_index": 9, "offset": 0.1, "width": 0.9, "height": 2.1},   # no such wall
    {"kind": "window", "edge_index": 0, "offset": 0.1, "width": 1, "height": 2.0, "sill": 1.0},  # above ceiling
    {"kind": "gate", "edge_index": 0, "offset": 0.1, "width": 1, "height": 2.0},
])
def test_invalid_openings_rejected(bad):
    with pytest.raises(g.GeometryError):
        g.build_room(room(), [bad], T)


def test_overlapping_openings_rejected():
    ops = [{"kind": "door", "edge_index": 0, "offset": 0.2, "width": 1.0, "height": 2.1},
           {"kind": "window", "edge_index": 0, "offset": 1.0, "width": 1.0, "height": 1.0, "sill": 1.0}]
    with pytest.raises(g.GeometryError):
        g.build_room(room(), ops, T)


def test_invalid_polygons():
    with pytest.raises(g.GeometryError):
        g.validate_polygon([(0, 0), (1, 0)])
    with pytest.raises(g.GeometryError):
        g.validate_polygon([(0, 0), (2, 2), (2, 0), (0, 2)])  # bow-tie
    with pytest.raises(g.GeometryError):
        g.build_room(room(poly=g.rect_polygon(3, 4)[::-1]), [], T)  # clockwise


def test_l_shaped_room_area():
    poly = [(0, 0), (5, 0), (5, 2), (2, 2), (2, 4), (0, 4)]
    assert g.polygon_area(poly) == pytest.approx(14.0)
    r = g.build_room(room(poly=poly), [], T)
    assert len(r["walls"]) == 6


def test_normalize_ccw():
    cw = g.rect_polygon(3, 4)[::-1]
    assert g.signed_area(g.normalize_ccw(cw)) > 0


def test_dimension_parsing():
    assert parse_dimension("3.00 m") == pytest.approx(3.0)
    assert parse_dimension("3000 mm") == pytest.approx(3.0)
    assert parse_dimension("350 cm") == pytest.approx(3.5)
    assert parse_dimension("3,5 m") == pytest.approx(3.5)
    assert parse_dimension("3000", default_unit="mm") == pytest.approx(3.0)
    assert parse_dimension("3.2", default_unit="m") == pytest.approx(3.2)
    assert parse_dimension("10'6\"") == pytest.approx(3.2004)
    assert parse_dimension("BEDROOM") is None
    assert parse_pair("3.0 x 4.0 m") == (pytest.approx(3.0), pytest.approx(4.0))
    assert parse_pair("3000x4000", default_unit="mm") == (pytest.approx(3.0), pytest.approx(4.0))
