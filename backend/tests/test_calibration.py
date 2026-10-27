import io
import pytest
from app.geometry import calibration as c, engine as g
from .conftest import PNG


def test_scale_from_reference():
    assert c.scale_from_reference((0, 0), (100, 0), 2.0) == pytest.approx(0.02)
    assert c.scale_from_reference((10, 10), (10, 310), 6.0) == pytest.approx(0.02)


def test_scale_rejects_bad_input():
    with pytest.raises(c.CalibrationError):
        c.scale_from_reference((0, 0), (5, 0), 2.0)   # points too close
    with pytest.raises(c.CalibrationError):
        c.scale_from_reference((0, 0), (100, 0), 0)


def test_snap_makes_walls_straight():
    pts = c.px_to_m([(100, 100), (250, 102), (251, 300), (99, 299)], 0.02)
    snapped = c.snap_coordinates(pts, 0.08)
    assert snapped[0][0] == snapped[3][0] and snapped[1][0] == snapped[2][0]
    assert snapped[0][1] == snapped[1][1] and snapped[2][1] == snapped[3][1]
    assert g.polygon_area(snapped) == pytest.approx(12.0, abs=0.3)


def test_snap_disabled_and_grid():
    pts = [(0.0, 0.0), (1.004, 0.0)]
    assert c.snap_coordinates(pts, 0) == pts
    assert c.round_to_grid([(1.004, 2.996)], 0.01) == [(1.0, 3.0)]


def _setup(client):
    p = client.post("/api/projects", json={"name": "Plan test"}).json()
    a = client.post(f"/api/projects/{p['id']}/assets", data={"category": "floor_plan"}, files={"file": ("plan.png", io.BytesIO(PNG))}).json()
    return p, a


def test_trace_requires_calibration(client):
    p, _ = _setup(client)
    r = client.post(f"/api/projects/{p['id']}/floorplan/trace-room", json={"name": "X", "points_px": [[0, 0], [100, 0], [100, 100]]})
    assert r.status_code == 409


def test_calibrate_trace_and_verify_flow(client):
    p, a = _setup(client); pid = p["id"]
    assert client.get(f"/api/projects/{pid}").json()["status"] == "Floor Plan Uploaded"
    bad = client.put(f"/api/projects/{pid}/floorplan", json={"asset_id": a["id"], "p1": [0, 0], "p2": [3, 0], "real_distance_m": 2, "image_width": 800, "image_height": 600})
    assert bad.status_code == 422
    ok = client.put(f"/api/projects/{pid}/floorplan", json={"asset_id": a["id"], "p1": [0, 0], "p2": [100, 0], "real_distance_m": 2.0, "image_width": 800, "image_height": 600})
    assert ok.status_code == 200 and ok.json()["scale_m_per_px"] == pytest.approx(0.02)
    room = client.post(f"/api/projects/{pid}/floorplan/trace-room", json={"name": "Bedroom", "points_px": [[100, 100], [250, 100], [250, 300], [100, 300]]}).json()
    assert room["area"] == pytest.approx(12.0) and room["dimension_source"] == "user_defined"
    # clockwise clicks are accepted and normalised
    cw = client.post(f"/api/projects/{pid}/floorplan/trace-room", json={"name": "Kitchen", "points_px": [[300, 100], [300, 300], [450, 300], [450, 100]]})
    assert cw.status_code == 201 and cw.json()["area"] == pytest.approx(12.0)
    # a self-crossing outline is rejected and nothing is created
    n = len(client.get(f"/api/projects/{pid}/rooms").json())
    assert client.post(f"/api/projects/{pid}/floorplan/trace-room", json={"name": "Bad", "points_px": [[0, 0], [100, 100], [100, 0], [0, 100]]}).status_code == 422
    assert len(client.get(f"/api/projects/{pid}/rooms").json()) == n
    v = client.post(f"/api/projects/{pid}/verify-floorplan").json()
    assert v["status"] == "Floor Plan Verified"
    assert {r["dimension_source"] for r in client.get(f"/api/projects/{pid}/rooms").json()} == {"verified"}


def test_verify_needs_rooms(client):
    p = client.post("/api/projects", json={"name": "Empty"}).json()
    assert client.post(f"/api/projects/{p['id']}/verify-floorplan").status_code == 409
