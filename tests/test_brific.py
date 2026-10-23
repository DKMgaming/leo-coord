"""Kiểm thử module nhập dữ liệu BR IFIC/SRS (dữ liệu kiểm thử là HƯ CẤU)."""
import pytest

from leo_coord import database as db
from leo_coord import brific

ROWS = [
    {"SAT_NAME": "DEMO-NGSO-1", "ADM": "VTN", "OPERATOR": "DemoSat",
     "N_SATS": "648", "ALT_KM": "550", "INC": "53", "STAGE": "CR/C",
     "D_BIU": "01/03/2031", "NTC_ID": "110123", "NTC_TYPE": "CR/C",
     "IFIC_NO": "3082", "D_RCV": "15/09/2026"},
    {"SAT_NAME": "DEMO-GSO-1", "ADM": "VTN", "STAGE": "MIFR", "N_SATS": "1"},
    {"ADM": "VTN", "STAGE": "API/A"},  # thiếu tên -> bỏ qua
]


def test_parse_rows_aliases_and_mapping():
    records, report = brific.parse_rows(ROWS)
    assert report["n_rows"] == 3 and report["n_skipped_no_name"] == 1
    r = records[0]
    assert r["network_name"] == "DEMO-NGSO-1"
    assert r["administration"] == "VTN"
    assert r["n_sats_filed"] == 648
    assert r["alt_km"] == 550.0 and r["inc_deg"] == 53.0
    assert r["status"] == "COORDINATION"       # CR/C -> COORDINATION
    assert r["biu_deadline"] == "2031-03-01"  # dd/mm/yyyy -> ISO
    assert r["receipt_date"] == "2026-09-15"
    assert r["sns_id"] == "110123" and r["notice_type"] == "CR/C"
    assert r["ific_no"] == "3082"
    assert records[1]["status"] == "MIFR"
    assert "network_name" in report["fields_mapped"]


def test_import_file_csv_end_to_end(tmp_path):
    csv_path = tmp_path / "extract.csv"
    lines = [",".join(ROWS[0].keys())]
    for r in ROWS[:2]:
        lines.append(",".join(str(r.get(k, "")) for k in ROWS[0].keys()))
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    dbp = str(tmp_path / "coord.db")
    db.init_db(dbp)
    stats, _ = brific.import_file(dbp, csv_path)
    assert stats["added"] == 2 and stats["skipped_existing"] == 0
    # nhập lại -> bỏ qua toàn bộ vì đã tồn tại
    stats2, _ = brific.import_file(dbp, csv_path)
    assert stats2["added"] == 0 and stats2["skipped_existing"] == 2
    rows = db.list_filings(dbp)
    assert rows[0]["notes"].startswith("Nhập từ")


def test_read_mdb_without_valid_file(tmp_path):
    fake = tmp_path / "fake.mdb"
    fake.write_bytes(b"day khong phai file access")
    with pytest.raises(RuntimeError):
        brific.read_mdb(fake)


def test_import_rejects_unknown_suffix(tmp_path):
    f = tmp_path / "data.xlsx"
    f.write_bytes(b"x")
    with pytest.raises(ValueError):
        brific.import_file(str(tmp_path / "c.db"), f)
