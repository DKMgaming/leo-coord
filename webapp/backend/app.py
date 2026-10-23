"""Web app leo_coord — API đánh giá chòm sao LEO/NGSO + quản lý tài liệu tham luận.

Chạy từ thư mục gốc dự án:
    .venv/bin/uvicorn webapp.backend.app:app --host 0.0.0.0 --port 8000

- Tab 1: các chức năng chính (phủ sóng, PFD, EPFD, phối hợp, milestone)
  + dữ liệu quỹ đạo cho bản đồ số 3D ở frontend.
- Tab 2: thư viện tham luận — upload/tải/xóa file Word, Excel, PDF, PPTx.
- Tab 3: CSDL phối hợp tần số vệ tinh quốc gia (SQLite) — hồ sơ đăng ký,
  báo cáo triển khai thực tế, vụ việc phối hợp, trạng thái mốc Res 35.
"""
from __future__ import annotations

import json
import math
import sqlite3
import uuid
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from leo_coord import __version__
from leo_coord.config import load_config
from leo_coord.orbits import WalkerConstellation, enu_angles
from leo_coord.coverage import coverage_grid, point_stats, footprint_radius_km
from leo_coord.pfd import check_downlink_pfd
from leo_coord.epfd import single_entry_epfd_down
from leo_coord.coordination import screen_ngso_vs_gso
from leo_coord.milestones import res35_schedule, evaluate, warehousing_flag
from leo_coord import database as coorddb

BASE = Path(__file__).resolve().parent.parent
FRONTEND = BASE / "frontend"
DATA = BASE / "data"
UPLOADS = DATA / "uploads"
DB_PATH = DATA / "thamluan.db"

ALLOWED_EXT = {".doc", ".docx", ".xls", ".xlsx", ".pdf", ".ppt", ".pptx"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB / file
MAX_SATS = 2400  # giới hạn an toàn cho mô phỏng web

# thư mục dữ liệu tài liệu — tạo ngay khi nạp app
DATA.mkdir(parents=True, exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="leo_coord web app", version=__version__)
CFG = load_config()


# ---------------------------------------------------------------- helpers
def _jsonable(o):
    if isinstance(o, dict):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


def _constellation(body: dict) -> WalkerConstellation:
    n = int(body.get("n_sats", 120))
    if n < 1 or n > MAX_SATS:
        raise HTTPException(400, f"Số vệ tinh phải trong [1, {MAX_SATS}]")
    return WalkerConstellation(
        body.get("name", "LEO-WEB"),
        float(body.get("alt_km", 550.0)),
        float(body.get("inc_deg", 53.0)),
        n,
        int(body.get("n_planes", 6)),
        int(body.get("phasing", 1)),
        body.get("kind", "delta"))


def _band(body: dict):
    band = body.get("band_ghz", "10.7-12.7")
    lo, hi = (float(x) for x in band.split("-"))
    return band, (lo + hi) / 2.0


def _ref_points():
    return [(v["lat"], v["lon"], k) for k, v in
            CFG["vietnam"]["reference_points"].items()]


# ---------------------------------------------------------------- API: meta
@app.get("/api/health")
def health():
    return {"ok": True, "version": __version__}


@app.get("/api/meta")
def meta():
    return _jsonable({
        "vietnam_bbox": CFG["vietnam"]["bbox"],
        "reference_points": CFG["vietnam"]["reference_points"],
        "min_elevation_deg": CFG["analysis"]["min_elevation_deg"],
        "coordination_arcs": CFG["coordination"]["arcs"],
        "pfd_source": CFG["pfd"]["table_source"],
        "epfd_anchor": CFG["epfd"]["single_entry"]["never_exceed_dbw_m2_40khz"],
    })


# ---------------------------------------------------------------- API: tab 1
@app.post("/api/assess")
def assess(body: dict):
    """Đánh giá toàn diện một chòm sao (giống CLI assess)."""
    w = _constellation(body)
    band, freq = _band(body)
    eirp = float(body.get("eirp_dbw_per_mhz", 10.0))
    gso_lon = float(body.get("gso_lon", 105.5))
    dish = float(body.get("dish_d_m", 1.2))
    min_el = CFG["analysis"]["min_elevation_deg"]
    pts = _ref_points()

    times = np.arange(0.0, 86400.0, 60.0)
    sat_ecef = w.ecef_positions(times)
    point_rows = []
    for lat, lon, name in pts:
        point_rows.append({"name": name,
                           **point_stats(sat_ecef, times, lat, lon, min_el)})

    grid = coverage_grid(w, tuple(CFG["vietnam"]["bbox"].values()),
                         grid_step_deg=1.0, min_elev_deg=min_el,
                         duration_s=43200.0, dt_s=120.0)
    pfd = check_downlink_pfd(eirp, freq, w.alt_km, w.size, CFG)
    epfd = single_entry_epfd_down(
        w, eirp, freq,
        CFG["vietnam"]["reference_points"]["hanoi"]["lat"],
        CFG["vietnam"]["reference_points"]["hanoi"]["lon"],
        gso_lon, dish_d_m=dish, duration_s=43200.0, dt_s=120.0, cfg=CFG)
    coord = screen_ngso_vs_gso(w, freq, eirp, gso_lon, pts, cfg=CFG,
                               duration_s=43200.0, dt_s=120.0)

    milestones, warehousing = None, None
    if body.get("biu_deadline"):
        biu = date.fromisoformat(body["biu_deadline"])
        deps = [(date.fromisoformat(d), int(n))
                for d, n in body.get("deployed") or []]
        ev = evaluate(res35_schedule(biu, w.size), deps)
        milestones = [{**m, "due": m["due"].isoformat()} for m in ev]
        n_dep = max([n for _, n in deps], default=0)
        warehousing = warehousing_flag(w.size, n_dep)

    return _jsonable({
        "name": w.name,
        "constellation": {
            "alt_km": w.alt_km, "inc_deg": w.inc_deg, "n_sats": w.size,
            "n_planes": w.n_planes, "kind": w.kind,
            "period_min": w.period_s / 60.0,
            "footprint_km": footprint_radius_km(w.alt_km, min_el)},
        "downlink": {"band_ghz": band, "freq_ghz": freq,
                     "eirp_dbw_per_mhz": eirp},
        "coverage": {
            "points": point_rows,
            "grid_summary": {
                "mean_fraction": float(grid["fraction_covered"].mean()),
                "min_fraction": float(grid["fraction_covered"].min())},
            "min_elev_deg": min_el},
        "pfd": pfd, "epfd": epfd, "coordination": coord,
        "milestones": milestones, "warehousing": warehousing,
    })


@app.post("/api/tracks")
def tracks(body: dict):
    """Vệt quỹ đạo ECEF (km) cho bản đồ 3D — mỗi vệ tinh 1 vòng quỹ đạo."""
    w = _constellation(body)
    n_samples = int(body.get("samples", 90))
    times = np.linspace(0.0, w.period_s, n_samples, endpoint=False)
    pos = w.ecef_positions(times)  # (T, S, 3)
    tracks_out = np.transpose(pos, (1, 0, 2)).round(1).tolist()
    return _jsonable({
        "period_s": w.period_s,
        "n_sats": w.size,
        "n_planes": w.n_planes,
        "tracks": tracks_out,
    })


@app.post("/api/coverage-map")
def coverage_map(body: dict):
    """Lưới phủ sóng để phủ lên bản đồ 3D (khu vực VN)."""
    w = _constellation(body)
    min_el = CFG["analysis"]["min_elevation_deg"]
    grid = coverage_grid(w, tuple(CFG["vietnam"]["bbox"].values()),
                         grid_step_deg=1.0, min_elev_deg=min_el,
                         duration_s=43200.0, dt_s=120.0)
    cells = []
    for i, la in enumerate(grid["lats"]):
        for j, lo in enumerate(grid["lons"]):
            cells.append({"lat": float(la), "lon": float(lo),
                          "fraction": float(grid["fraction_covered"][i, j])})
    return {"cells": cells, "min_elev_deg": min_el}


@app.post("/api/visible-sats")
def visible_sats(body: dict):
    """Vệ tinh khả kiến tại một điểm mặt đất ở thời điểm t (click trên bản đồ)."""
    w = _constellation(body)
    lat = float(body["lat"])
    lon = float(body["lon"])
    t = float(body.get("t_s", 0.0))
    min_el = float(body.get("min_elev_deg",
                            CFG["analysis"]["min_elevation_deg"]))
    pos = w.ecef_positions(np.array([t]))[0]  # (S, 3)
    az, el, rng = enu_angles(pos, lat, lon)
    idx = np.where(el >= min_el)[0]
    order = idx[np.argsort(el[idx])[::-1]]
    sats = [{"name": w.sat_names[int(i)],
             "elevation_deg": float(el[i]),
             "azimuth_deg": float(az[i]),
             "range_km": float(rng[i])} for i in order[:25]]
    return _jsonable({"lat": lat, "lon": lon, "t_s": t,
                      "min_elev_deg": min_el,
                      "n_visible": int(len(idx)),
                      "satellites": sats})


# ---------------------------------------------------------------- API: tab 2 (tham luận)
def _db():
    DATA.mkdir(parents=True, exist_ok=True)
    UPLOADS.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '',
        filename TEXT NOT NULL, stored_name TEXT NOT NULL, ext TEXT,
        size_bytes INTEGER, uploaded_at TEXT)""")
    return c


@app.get("/api/docs")
def list_docs():
    with _db() as c:
        rows = c.execute(
            "SELECT id, title, description, filename, ext, size_bytes,"
            " uploaded_at FROM documents ORDER BY uploaded_at DESC").fetchall()
    return {"documents": [dict(r) for r in rows]}


@app.post("/api/docs")
async def upload_doc(title: str = Form(...), description: str = Form(""),
                     file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Chỉ nhận file Word/Excel/PDF/PowerPoint "
                                 "(.doc, .docx, .xls, .xlsx, .pdf, .ppt, .pptx)")
    doc_id = uuid.uuid4().hex
    stored = f"{doc_id}{ext}"
    dest = UPLOADS / stored
    size = 0
    with dest.open("wb") as fh:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "File vượt quá 50 MB")
            fh.write(chunk)
    now = (datetime.now(timezone.utc) + timedelta(hours=7)).strftime(
        "%Y-%m-%dT%H:%M:%S+07:00")
    with _db() as c:
        c.execute("INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                  (doc_id, title.strip() or file.filename, description.strip(),
                   file.filename, stored, ext, size, now))
    return {"id": doc_id, "filename": file.filename, "size_bytes": size}


@app.get("/api/docs/{doc_id}/download")
def download_doc(doc_id: str):
    with _db() as c:
        row = c.execute("SELECT * FROM documents WHERE id=?",
                        (doc_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Không tìm thấy tài liệu")
    path = UPLOADS / row["stored_name"]
    if not path.exists():
        raise HTTPException(404, "File không còn trên đĩa")
    return FileResponse(path, filename=row["filename"])


@app.delete("/api/docs/{doc_id}")
def delete_doc(doc_id: str):
    with _db() as c:
        row = c.execute("SELECT * FROM documents WHERE id=?",
                        (doc_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Không tìm thấy tài liệu")
        c.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    (UPLOADS / row["stored_name"]).unlink(missing_ok=True)
    return {"deleted": doc_id}


# ---------------------------------------------------------------- API: tab 3 (CSDL phối hợp)
def _coord_path():
    """Đường dẫn CSDL phối hợp (dùng chung với CLI `leo-coord db`)."""
    p = DATA / "coord.db"
    coorddb.init_db(p)  # idempotent — tạo bảng nếu chưa có
    return p


def _opt_float(v):
    return None if v in (None, "") else float(v)


@app.get("/api/db/filings")
def db_list_filings():
    return {"filings": coorddb.list_filings(_coord_path())}


@app.post("/api/db/filings")
def db_add_filing(body: dict):
    try:
        fid = coorddb.add_filing(
            _coord_path(),
            network_name=str(body["network_name"]).strip(),
            administration=str(body["administration"]).strip(),
            n_sats_filed=int(body["n_sats_filed"]),
            operator=str(body.get("operator", "") or ""),
            bands=str(body.get("bands", "") or ""),
            alt_km=_opt_float(body.get("alt_km")),
            inc_deg=_opt_float(body.get("inc_deg")),
            status=str(body.get("status", "API") or "API"),
            api_date=body.get("api_date") or None,
            biu_deadline=body.get("biu_deadline") or None,
            notes=str(body.get("notes", "") or ""))
    except sqlite3.IntegrityError:
        raise HTTPException(400, "Tên mạng vệ tinh đã tồn tại trong CSDL")
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(400, f"Dữ liệu hồ sơ không hợp lệ: {e}")
    return {"id": fid}


@app.get("/api/db/deployments")
def db_list_deployments(network_name: str = None):
    return {"deployments": coorddb.list_deployments(_coord_path(), network_name)}


@app.post("/api/db/deployments")
def db_report_deployment(body: dict):
    try:
        did = coorddb.report_deployment(
            _coord_path(), str(body["network_name"]), str(body["report_date"]),
            int(body["n_deployed"]), str(body.get("source", "") or ""))
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(400, str(e))
    return {"id": did}


@app.get("/api/db/cases")
def db_list_cases():
    path = _coord_path()
    names = {f["id"]: f["network_name"] for f in coorddb.list_filings(path)}
    cases = coorddb.list_coordination_cases(path)
    for c in cases:
        c["network_name"] = names.get(c["filing_id"], "?")
    return {"cases": cases}


@app.post("/api/db/cases")
def db_add_case(body: dict):
    try:
        cid = coorddb.add_coordination_case(
            _coord_path(), str(body["network_name"]),
            str(body["other_system"]), str(body.get("band", "") or ""),
            str(body.get("trigger", "") or ""),
            str(body.get("status", "MO") or "MO"),
            str(body.get("notes", "") or ""))
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(400, str(e))
    return {"id": cid}


@app.get("/api/db/milestones")
def db_milestones():
    out = []
    for item in coorddb.milestone_status(_coord_path()):
        ms = [{**m, "due": m["due"].isoformat()} for m in item["milestones"]]
        out.append({"network_name": item["network_name"], "milestones": ms})
    return {"networks": out}


@app.get("/api/db/export.csv")
def db_export_csv():
    out = DATA / "filings_export.csv"
    coorddb.export_filings_csv(_coord_path(), out)
    return FileResponse(out, filename="ho_so_phoi_hop.csv",
                        media_type="text/csv")


# ---------------------------------------------------------------- static
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
