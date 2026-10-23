"""Kiểm thử CSDL phối hợp tần số vệ tinh quốc gia."""
from datetime import date

import pytest

from leo_coord import database as db


@pytest.fixture
def dbpath(tmp_path):
    p = tmp_path / "coord.db"
    db.init_db(p)
    return str(p)


def test_add_and_list_filing(dbpath):
    fid = db.add_filing(dbpath, network_name="VN-LEO-1", administration="VTN",
                        n_sats_filed=648, operator="DemoSat",
                        bands="10.7-12.7 GHz", alt_km=550.0, inc_deg=53.0,
                        status="COORDINATION", biu_deadline="2031-03-01")
    assert fid == 1
    rows = db.list_filings(dbpath)
    assert len(rows) == 1 and rows[0]["network_name"] == "VN-LEO-1"
    with pytest.raises(Exception):
        db.add_filing(dbpath, network_name="VN-LEO-1", administration="VTN",
                      n_sats_filed=10)  # trùng tên


def test_invalid_status_rejected(dbpath):
    with pytest.raises(ValueError):
        db.add_filing(dbpath, network_name="X", administration="VTN",
                      n_sats_filed=10, status="KHONG_HOP_LE")


def test_deployment_and_milestones(dbpath):
    db.add_filing(dbpath, network_name="VN-LEO-1", administration="VTN",
                  n_sats_filed=648, biu_deadline="2024-03-01")
    db.report_deployment(dbpath, "VN-LEO-1", "2025-06-01", 70, source="test")
    db.report_deployment(dbpath, "VN-LEO-1", "2028-12-01", 320, source="test")
    out = db.milestone_status(dbpath, today=date(2030, 1, 1))
    assert len(out) == 1
    ms = out[0]["milestones"]
    assert ms[0]["status"] == "DAT"          # 70 >= 65 trước 2026-03-01
    assert ms[1]["status"] == "TRE_HAN"      # 320 < 324
    assert ms[2]["status"] == "CHUA_DEN_HAN"


def test_deployment_unknown_filing(dbpath):
    with pytest.raises(ValueError):
        db.report_deployment(dbpath, "KHONG_TON_TAI", "2025-01-01", 5)


def test_coordination_cases(dbpath):
    db.add_filing(dbpath, network_name="VN-LEO-1", administration="VTN",
                  n_sats_filed=100)
    cid = db.add_coordination_case(dbpath, "VN-LEO-1", "GSO-KU-105E",
                                   band="10.7-12.7 GHz",
                                   trigger="cung ±6° (Appendix 5)",
                                   notes="test")
    assert cid == 1
    rows = db.list_coordination_cases(dbpath, "VN-LEO-1")
    assert len(rows) == 1 and rows[0]["other_system"] == "GSO-KU-105E"


def test_list_deployments(dbpath):
    db.add_filing(dbpath, network_name="VN-LEO-1", administration="VTN",
                  n_sats_filed=100)
    db.report_deployment(dbpath, "VN-LEO-1", "2025-01-01", 10, source="a")
    db.report_deployment(dbpath, "VN-LEO-1", "2026-01-01", 40, source="b")
    rows = db.list_deployments(dbpath)
    assert [r["n_deployed"] for r in rows] == [40, 10]  # mới nhất trước
    assert rows[0]["network_name"] == "VN-LEO-1"
    assert db.list_deployments(dbpath, "VN-LEO-1")[0]["source"] == "b"
    assert db.list_deployments(dbpath, "KHONG_CO") == []


def test_migration_from_old_schema(tmp_path):
    import sqlite3
    p = tmp_path / "old.db"
    with sqlite3.connect(p) as c:
        c.execute("""CREATE TABLE filings (
          id INTEGER PRIMARY KEY AUTOINCREMENT, network_name TEXT UNIQUE NOT NULL,
          administration TEXT NOT NULL, operator TEXT, bands TEXT,
          n_sats_filed INTEGER NOT NULL, alt_km REAL, inc_deg REAL,
          status TEXT DEFAULT 'API', api_date TEXT, biu_deadline TEXT,
          notes TEXT)""")
        c.execute("INSERT INTO filings (network_name, administration,"
                  " n_sats_filed) VALUES ('OLD-1', 'VTN', 10)")
    db.init_db(str(p))  # phải tự thêm cột App4 + bảng cross_checks
    rows = db.list_filings(str(p))
    assert rows[0]["network_name"] == "OLD-1"
    assert rows[0]["sns_id"] is None
    db.add_filing(str(p), network_name="NEW-1", administration="VTN",
                  n_sats_filed=5, sns_id="110999", notice_type="CR/C",
                  ific_no="3082", receipt_date="2026-09-15")
    by_name = {f["network_name"]: f for f in db.list_filings(str(p))}
    assert by_name["NEW-1"]["sns_id"] == "110999"
    assert by_name["NEW-1"]["notice_type"] == "CR/C"


def test_cross_checks(dbpath):
    db.add_filing(dbpath, network_name="VN-LEO-1", administration="VTN",
                  n_sats_filed=100)
    xid = db.add_cross_check(
        dbpath, "VN-LEO-1", "GSO-KU-105E",
        our_result="Cần phối hợp: cung ±6°, ΔT/T 8,2%",
        official_source="BR IFIC 3082 (CR/C)",
        official_result="BR xác nhận cần phối hợp với GSO-KU-105E",
        agreement="KHOP", checked_date="2026-10-20", checker="P.HTQT")
    assert xid == 1
    rows = db.list_cross_checks(dbpath)
    assert len(rows) == 1 and rows[0]["network_name"] == "VN-LEO-1"
    assert rows[0]["agreement"] == "KHOP"
    with pytest.raises(ValueError):
        db.add_cross_check(dbpath, "VN-LEO-1", "X", agreement="SAI")
    with pytest.raises(ValueError):
        db.add_cross_check(dbpath, "KHONG_CO", "X")


def test_export_csv(dbpath, tmp_path):
    db.add_filing(dbpath, network_name="VN-LEO-1", administration="VTN",
                  n_sats_filed=100)
    out = tmp_path / "filings.csv"
    p = db.export_filings_csv(dbpath, out)
    assert p.exists()
    assert "VN-LEO-1" in p.read_text(encoding="utf-8")
