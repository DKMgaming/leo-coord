"""Cơ sở dữ liệu phối hợp tần số vệ tinh quốc gia (SQLite).

Lưu trữ: hồ sơ đăng ký mạng vệ tinh (filings), số liệu triển khai thực tế
(deployments), các vụ việc phối hợp quốc tế (coordination_cases).
Tích hợp đánh giá mốc Res 35 để phát hiện "xí phần" tài nguyên quỹ đạo.
"""
from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path

from .milestones import res35_schedule, evaluate

SCHEMA = """
CREATE TABLE IF NOT EXISTS filings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  network_name TEXT UNIQUE NOT NULL,
  administration TEXT NOT NULL,
  operator TEXT,
  bands TEXT,
  n_sats_filed INTEGER NOT NULL,
  alt_km REAL,
  inc_deg REAL,
  status TEXT DEFAULT 'API',
  api_date TEXT,
  biu_deadline TEXT,
  sns_id TEXT,
  notice_type TEXT,
  ific_no TEXT,
  receipt_date TEXT,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS deployments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filing_id INTEGER NOT NULL REFERENCES filings(id),
  report_date TEXT NOT NULL,
  n_deployed INTEGER NOT NULL,
  source TEXT
);
CREATE TABLE IF NOT EXISTS coordination_cases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filing_id INTEGER NOT NULL REFERENCES filings(id),
  other_system TEXT NOT NULL,
  band TEXT,
  trigger TEXT,
  status TEXT DEFAULT 'MO',
  notes TEXT
);
CREATE TABLE IF NOT EXISTS cross_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filing_id INTEGER NOT NULL REFERENCES filings(id),
  other_system TEXT NOT NULL,
  our_result TEXT,
  official_source TEXT,
  official_result TEXT,
  agreement TEXT DEFAULT 'CHUA_RO',
  checked_date TEXT,
  checker TEXT,
  notes TEXT
);
"""

VALID_STATUS = {"API", "COORDINATION", "NOTIFICATION", "MIFR", "BIU"}
VALID_AGREEMENT = {"KHOP", "LECH", "CHUA_RO"}

# Cột bổ sung theo Appendix 4 / SpaceCap cho CSDL tạo từ phiên bản cũ
_FILING_EXTRA_COLUMNS = {
    "sns_id": "TEXT", "notice_type": "TEXT",
    "ific_no": "TEXT", "receipt_date": "TEXT",
}


def init_db(path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(p) as c:
        c.executescript(SCHEMA)
        # migration: thêm cột App4 còn thiếu vào bảng filings cũ (idempotent)
        cols = {r[1] for r in c.execute("PRAGMA table_info(filings)")}
        for name, typ in _FILING_EXTRA_COLUMNS.items():
            if name not in cols:
                c.execute(f"ALTER TABLE filings ADD COLUMN {name} {typ}")
    return p


def _connect(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def add_filing(path, *, network_name, administration, n_sats_filed,
               operator="", bands="", alt_km=None, inc_deg=None,
               status="API", api_date=None, biu_deadline=None, notes="",
               sns_id="", notice_type="", ific_no="",
               receipt_date=None) -> int:
    if status not in VALID_STATUS:
        raise ValueError(f"status phải thuộc {sorted(VALID_STATUS)}")
    with _connect(path) as c:
        cur = c.execute(
            """INSERT INTO filings (network_name, administration, operator, bands,
               n_sats_filed, alt_km, inc_deg, status, api_date, biu_deadline,
               sns_id, notice_type, ific_no, receipt_date, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (network_name, administration, operator, bands, n_sats_filed,
             alt_km, inc_deg, status, api_date, biu_deadline,
             sns_id, notice_type, ific_no, receipt_date, notes))
        return cur.lastrowid


def report_deployment(path, network_name, report_date, n_deployed, source="") -> int:
    with _connect(path) as c:
        row = c.execute("SELECT id FROM filings WHERE network_name=?",
                        (network_name,)).fetchone()
        if row is None:
            raise ValueError(f"Không tìm thấy hồ sơ '{network_name}'")
        cur = c.execute(
            "INSERT INTO deployments (filing_id, report_date, n_deployed, source)"
            " VALUES (?,?,?,?)",
            (row["id"], report_date, n_deployed, source))
        return cur.lastrowid


def list_filings(path) -> list:
    with _connect(path) as c:
        return [dict(r) for r in
                c.execute("SELECT * FROM filings ORDER BY network_name")]


def list_deployments(path, network_name=None) -> list:
    """Lịch sử báo cáo triển khai (kèm tên mạng), báo cáo mới nhất trước."""
    q = """SELECT d.*, f.network_name FROM deployments d
           JOIN filings f ON d.filing_id = f.id"""
    with _connect(path) as c:
        if network_name:
            rows = c.execute(q + " WHERE f.network_name=?"
                             " ORDER BY d.report_date DESC, d.id DESC",
                             (network_name,))
        else:
            rows = c.execute(q + " ORDER BY d.report_date DESC, d.id DESC")
        return [dict(r) for r in rows]


def add_coordination_case(path, network_name, other_system, band="",
                          trigger="", status="MO", notes="") -> int:
    with _connect(path) as c:
        row = c.execute("SELECT id FROM filings WHERE network_name=?",
                        (network_name,)).fetchone()
        if row is None:
            raise ValueError(f"Không tìm thấy hồ sơ '{network_name}'")
        cur = c.execute(
            """INSERT INTO coordination_cases
               (filing_id, other_system, band, trigger, status, notes)
               VALUES (?,?,?,?,?,?)""",
            (row["id"], other_system, band, trigger, status, notes))
        return cur.lastrowid


def list_coordination_cases(path, network_name=None) -> list:
    with _connect(path) as c:
        if network_name:
            q = """SELECT cc.* FROM coordination_cases cc JOIN filings f
                   ON cc.filing_id = f.id WHERE f.network_name=? ORDER BY cc.id"""
            rows = c.execute(q, (network_name,))
        else:
            rows = c.execute("SELECT * FROM coordination_cases ORDER BY id")
        return [dict(r) for r in rows]


def milestone_status(path, today: date = None) -> list:
    """Đánh giá mốc Res 35 cho mọi hồ sơ có biu_deadline."""
    today = today or date.today()
    out = []
    with _connect(path) as c:
        filings = c.execute(
            "SELECT * FROM filings WHERE biu_deadline IS NOT NULL").fetchall()
        for f in filings:
            deps = c.execute(
                "SELECT report_date, n_deployed FROM deployments WHERE filing_id=?"
                " ORDER BY report_date", (f["id"],)).fetchall()
            sched = res35_schedule(date.fromisoformat(f["biu_deadline"]),
                                   f["n_sats_filed"])
            ev = evaluate(sched,
                          [(date.fromisoformat(d["report_date"]), d["n_deployed"])
                           for d in deps], today)
            out.append({"network_name": f["network_name"], "milestones": ev})
    return out


def add_cross_check(path, network_name, other_system, our_result="",
                    official_source="", official_result="",
                    agreement="CHUA_RO", checked_date=None, checker="",
                    notes="") -> int:
    """Ghi nhận một lần đối chứng kết quả sàng lọc của leo_coord với
    kết quả chính thức của BR (BR IFIC / SpaceQry / BR-SIS)."""
    if agreement not in VALID_AGREEMENT:
        raise ValueError(f"agreement phải thuộc {sorted(VALID_AGREEMENT)}")
    with _connect(path) as c:
        row = c.execute("SELECT id FROM filings WHERE network_name=?",
                        (network_name,)).fetchone()
        if row is None:
            raise ValueError(f"Không tìm thấy hồ sơ '{network_name}'")
        cur = c.execute(
            """INSERT INTO cross_checks
               (filing_id, other_system, our_result, official_source,
                official_result, agreement, checked_date, checker, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (row["id"], other_system, our_result, official_source,
             official_result, agreement, checked_date, checker, notes))
        return cur.lastrowid


def list_cross_checks(path, network_name=None) -> list:
    """Danh sách đối chứng (kèm tên mạng), mới nhất trước."""
    q = """SELECT cc.*, f.network_name FROM cross_checks cc
           JOIN filings f ON cc.filing_id = f.id"""
    with _connect(path) as c:
        if network_name:
            rows = c.execute(q + " WHERE f.network_name=? ORDER BY cc.id DESC",
                             (network_name,))
        else:
            rows = c.execute(q + " ORDER BY cc.id DESC")
        return [dict(r) for r in rows]


def export_filings_csv(path, csv_path) -> Path:
    rows = list_filings(path)
    p = Path(csv_path)
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys() if rows else ["id"])
        w.writeheader()
        w.writerows(rows)
    return p
