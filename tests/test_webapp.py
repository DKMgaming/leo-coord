"""Kiểm thử API web app (FastAPI TestClient)."""
import pytest
from fastapi.testclient import TestClient

import webapp.backend.app as appmod


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setattr(appmod, "DATA", data)
    monkeypatch.setattr(appmod, "UPLOADS", data / "uploads")
    monkeypatch.setattr(appmod, "DB_PATH", data / "thamluan.db")
    data.mkdir(parents=True, exist_ok=True)
    (data / "uploads").mkdir(parents=True, exist_ok=True)
    return TestClient(appmod.app)


SMALL = {"name": "T", "alt_km": 550, "inc_deg": 53, "n_sats": 12,
         "n_planes": 3, "kind": "delta", "band_ghz": "10.7-12.7",
         "eirp_dbw_per_mhz": 10, "gso_lon": 105.5, "dish_d_m": 1.2}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    assert "coordination_arcs" in r.json()


def test_assess_small(client):
    body = {**SMALL, "biu_deadline": "2024-03-01",
            "deployed": [["2025-06-01", 2]]}
    r = client.post("/api/assess", json=body)
    assert r.status_code == 200
    a = r.json()
    assert a["constellation"]["n_sats"] == 12
    f = a["coverage"]["points"][0]["fraction_covered"]
    assert 0.0 <= f <= 1.0
    assert set(a["pfd"]) >= {"pfd", "limit", "margin_db", "compliant"}
    assert a["milestones"][0]["status"] == "DAT"  # 2 >= ceil(12*10%) = 2


def test_assess_rejects_too_many_sats(client):
    r = client.post("/api/assess", json={**SMALL, "n_sats": 99999})
    assert r.status_code == 400


def test_tracks(client):
    r = client.post("/api/tracks",
                    json={**SMALL, "n_sats": 6, "samples": 12})
    assert r.status_code == 200
    t = r.json()
    assert t["n_sats"] == 6 and len(t["tracks"]) == 6
    assert len(t["tracks"][0]) == 12 and len(t["tracks"][0][0]) == 3


def test_visible_sats(client):
    body = {**SMALL, "n_sats": 12, "lat": 21.0285, "lon": 105.8542,
            "t_s": 0.0}
    r = client.post("/api/visible-sats", json=body)
    assert r.status_code == 200
    d = r.json()
    assert d["n_visible"] >= 0
    els = [s["elevation_deg"] for s in d["satellites"]]
    assert els == sorted(els, reverse=True)  # sắp xếp giảm dần theo ngẩng
    assert all(s["elevation_deg"] >= d["min_elev_deg"] for s in d["satellites"])
    assert all(0.0 <= s["azimuth_deg"] < 360.0 for s in d["satellites"])


def test_coverage_map(client):
    r = client.post("/api/coverage-map", json={**SMALL, "n_sats": 6})
    assert r.status_code == 200
    cells = r.json()["cells"]
    assert len(cells) > 0
    assert all(0.0 <= c["fraction"] <= 1.0 for c in cells)


def test_docs_flow(client):
    # upload
    r = client.post("/api/docs",
                    data={"title": "Tham luận A", "description": "mô tả"},
                    files={"file": ("bao-cao.docx", b"noi dung test",
                                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert r.status_code == 200
    doc_id = r.json()["id"]
    # list
    docs = client.get("/api/docs").json()["documents"]
    assert len(docs) == 1 and docs[0]["title"] == "Tham luận A"
    # download
    dl = client.get(f"/api/docs/{doc_id}/download")
    assert dl.status_code == 200 and dl.content == b"noi dung test"
    # từ chối đuôi file lạ
    bad = client.post("/api/docs", data={"title": "x"},
                      files={"file": ("a.exe", b"x", "application/octet-stream")})
    assert bad.status_code == 400
    # xóa
    assert client.delete(f"/api/docs/{doc_id}").status_code == 200
    assert client.get("/api/docs").json()["documents"] == []
