import io, json
from sqlalchemy import create_engine, text
from app import config
from .conftest import PNG


def mk_project(c, **kw):
    r = c.post("/api/projects", json={"name": "Apt A", "client_name": "Nour", **kw}); assert r.status_code == 201, r.text
    return r.json()


def mk_room(c, pid, w=3, l=4, name="Bedroom"):
    poly = [[0, 0], [w, 0], [w, l], [0, l]]
    r = c.post(f"/api/projects/{pid}/rooms", json={"name": name, "polygon": poly}); assert r.status_code == 201, r.text
    return r.json()


def test_project_crud_search_duplicate_archive(client):
    p = mk_project(client)
    assert client.get(f"/api/projects/{p['id']}").json()["name"] == "Apt A"
    mk_room(client, p["id"])
    assert client.get("/api/projects", params={"q": "Nour"}).status_code == 200
    d = client.post(f"/api/projects/{p['id']}/duplicate").json()
    assert d["room_count"] == 1 and d["name"].endswith("(copy)")
    client.patch(f"/api/projects/{d['id']}", json={"status": "Archived"})
    ids = [x["id"] for x in client.get("/api/projects").json()]
    assert d["id"] not in ids and p["id"] in ids
    assert client.patch(f"/api/projects/{p['id']}", json={"status": "Nope"}).status_code == 422
    assert client.delete(f"/api/projects/{d['id']}").status_code == 204
    assert client.get(f"/api/projects/{d['id']}").status_code == 404


def test_room_dimensions_and_manual_correction(client):
    p = mk_project(client)
    r = mk_room(client, p["id"])
    assert abs(r["area"] - 12) < 1e-9
    r2 = client.patch(f"/api/rooms/{r['id']}", json={"polygon": [[0, 0], [3.5, 0], [3.5, 4], [0, 4]], "dimension_source": "verified"}).json()
    assert abs(r2["area"] - 14) < 1e-9 and r2["dimension_source"] == "verified"
    bad = client.post(f"/api/projects/{p['id']}/rooms", json={"name": "Bad", "polygon": [[0, 0], [2, 2], [2, 0], [0, 2]]})
    assert bad.status_code == 422


def test_clockwise_polygon_is_normalised(client):
    p = mk_project(client)
    r = client.post(f"/api/projects/{p['id']}/rooms", json={"name": "CW", "polygon": [[0, 0], [0, 4], [3, 4], [3, 0]]}).json()
    assert abs(r["area"] - 12) < 1e-9


def test_openings_validation_and_scene(client):
    p = mk_project(client)
    r = mk_room(client, p["id"])
    ok = client.post(f"/api/rooms/{r['id']}/openings", json={"kind": "door", "edge_index": 0, "offset": 1, "width": 0.9, "height": 2.1, "is_entrance": True})
    assert ok.status_code == 201
    assert client.post(f"/api/rooms/{r['id']}/openings", json={"kind": "door", "edge_index": 0, "offset": 2.5, "width": 0.9, "height": 2.1}).status_code == 422
    # shrinking the room so the door no longer fits must be rejected and leave the room untouched
    assert client.patch(f"/api/rooms/{r['id']}", json={"polygon": [[0, 0], [1.5, 0], [1.5, 4], [0, 4]]}).status_code == 422
    assert abs(client.get(f"/api/projects/{p['id']}/rooms").json()[0]["area"] - 12) < 1e-9
    scene = client.get(f"/api/projects/{p['id']}/scene").json()
    assert scene["spawn"]["from"] == "entrance" and len(scene["rooms"][0]["walls"]) >= 5


def test_asset_upload_validation_trash_and_video_preservation(client):
    p = mk_project(client); pid = p["id"]
    up = lambda cat, name, data: client.post(f"/api/projects/{pid}/assets", data={"category": cat}, files={"file": (name, io.BytesIO(data))})
    assert up("room_reference", "evil.exe", b"MZ").status_code == 422
    assert up("room_reference", "fake.png", b"not a png").status_code == 422
    assert up("room_reference", "../../etc/x.png", PNG).status_code == 201  # name sanitised, never used as a path
    ref = up("room_reference", "room.png", PNG).json()
    video = up("walkthrough_video", "tour.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64).json()
    # delete ALL reference images permanently; final video must survive and stay downloadable
    for a in client.get(f"/api/projects/{pid}/assets", params={"category": "room_reference"}).json():
        assert client.delete(f"/api/assets/{a['id']}", params={"permanent": True}).status_code == 204
    assert client.get(f"/api/assets/{ref['id']}/file").status_code == 404
    assert client.get(f"/api/assets/{video['id']}/file").status_code == 200
    # trash is recoverable
    client.delete(f"/api/assets/{video['id']}")
    assert video["id"] not in [a["id"] for a in client.get(f"/api/projects/{pid}/assets").json()]
    assert client.post(f"/api/assets/{video['id']}/restore").status_code == 200
    assert client.get(f"/api/assets/{video['id']}/file").status_code == 200


def test_ai_failure_is_reported_and_data_preserved(client, tmp_path, monkeypatch):
    cfg = {"mode": "local-only", "providers": {"ollama_vision": {"host": "http://127.0.0.1:9"}},
           "tasks": {"reference_analysis": {"provider": "ollama_vision", "options": {"model": "qwen2.5vl:3b"}}}}
    f = tmp_path / "p.json"; f.write_text(json.dumps(cfg)); monkeypatch.setenv("AIS_PROVIDER_CONFIG", str(f))
    p = mk_project(client); mk_room(client, p["id"])
    a = client.post(f"/api/projects/{p['id']}/assets", data={"category": "room_reference"}, files={"file": ("r.png", io.BytesIO(PNG))}).json()
    t = client.post("/api/ai/tasks", json={"task_type": "reference_analysis", "asset_id": a["id"]}).json()
    t = [x for x in client.get("/api/ai/tasks").json() if x["id"] == t["id"]][0]
    assert t["status"] == "failed" and "Ollama is not reachable" in t["error"]
    assert client.get(f"/api/projects/{p['id']}/rooms").json()  # project data intact
    assert client.post(f"/api/ai/tasks/{t['id']}/retry").status_code == 202


def test_unintegrated_provider_never_fakes_results(client):
    prov = {x["name"]: x for x in client.get("/api/ai/providers").json()["providers"]}
    assert prov["triposr"]["available"] is False and prov["sam2"]["available"] is False


def test_persistence_across_connections(client):
    p = mk_project(client, name="Persist me")
    eng = create_engine(config.DATABASE_URL)  # a brand-new connection, as after an app restart
    with eng.connect() as conn:
        assert conn.execute(text("select count(*) from projects where id=:i"), {"i": p["id"]}).scalar() == 1


def test_settings_and_dashboard(client):
    assert client.put("/api/settings", json={"theme": "dark", "bogus": 1}).json()["theme"] == "dark"
    assert client.get("/api/settings").json()["theme"] == "dark"
    assert "total_projects" in client.get("/api/dashboard").json()
