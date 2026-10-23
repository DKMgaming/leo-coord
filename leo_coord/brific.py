"""Nhập dữ liệu hồ sơ vệ tinh từ nguồn ITU BR vào CSDL phối hợp quốc gia.

Nguồn dữ liệu thật (do cơ quan quản lý nắm giữ, không tải tự do):
- CSDL SRS (srsXXXX.mdb, từ BR IFIC 2841 tách thành srsXXXX_part1of2.mdb +
  srsXXXX_part2of2.mdb) — chỉ phát hành trong BR IFIC (Space Services)
  DVD-ROM / bản trực tuyến có thuê bao của BR.
- Bản trích CSV từ SpaceQry / SpaceCap / ITU Space Explorer.

Module này nhận:
- file .csv trích ra từ các hệ trên (hoặc từ mdb-export), hoặc
- file .mdb SRS — đọc bằng thư viện tùy chọn `access-parser`
  (pip install "leo-coord[brific]") hoặc công cụ `mdb-export` (mdbtools)
  nếu có trên máy.

Ánh xạ cột: tên trường SNS/SRS chuẩn nằm trong Preface của BR (Section III);
bảng COLUMN_MAP dưới đây gồm các bí danh thường gặp và CHỈ mang tính khởi đầu —
khi chạy lần đầu với dữ liệu thật, hãy đối chiếu cột thực tế (hàm parse_rows
báo cáo rõ cột nào đã khớp, cột nào chưa) rồi bổ sung bí danh nếu cần.
"""
from __future__ import annotations

import csv
import re
import subprocess
from datetime import datetime
from pathlib import Path

from . import database as db

# field của leo_coord -> các bí danh cột trong bản trích SNS/SRS
COLUMN_MAP = {
    "network_name": ["ntwk_name", "sat_name", "network_name", "name",
                     "sat_network_name", "network"],
    "administration": ["adm", "adm_code", "administration", "admin",
                       "adm_name", "notifying_adm"],
    "operator": ["operator", "op_name", "operator_name"],
    "bands": ["bands", "freq_band", "band", "frequency_band"],
    "n_sats_filed": ["n_sats", "num_sats", "no_sats", "n_sats_filed",
                     "num_sat", "no_of_sats"],
    "alt_km": ["alt_km", "altitude", "alt", "apogee_km"],
    "inc_deg": ["inc_deg", "inclination", "inc", "incl_deg"],
    "status": ["status", "stage", "ntc_stage", "filing_status"],
    "api_date": ["api_date", "d_api", "date_api"],
    "biu_deadline": ["biu_deadline", "d_biu", "date_biu", "biu_date"],
    "sns_id": ["sns_id", "ntc_id", "notice_id", "sns_notice_id"],
    "notice_type": ["notice_type", "ntc_type", "type_of_notice"],
    "ific_no": ["ific_no", "br_ific", "ific", "ific_number"],
    "receipt_date": ["receipt_date", "d_rcv", "date_receipt", "date_of_receipt"],
}

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y")


def _norm_key(k) -> str:
    return re.sub(r"[^a-z0-9]", "", str(k).lower())


_ALIAS_TO_FIELD = {}
for _field, _aliases in COLUMN_MAP.items():
    _ALIAS_TO_FIELD[_norm_key(_field)] = _field
    for _a in _aliases:
        _ALIAS_TO_FIELD[_norm_key(_a)] = _field


def _parse_date(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.split(" ")[0]  # bỏ phần giờ nếu có
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_int(v, default=None):
    if v is None or str(v).strip() == "":
        return default
    try:
        return int(float(str(v).replace(",", "").replace(" ", "")))
    except ValueError:
        return default


def _parse_float(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def _map_status(v):
    """Chuẩn hóa giai đoạn hồ sơ về tập trạng thái của leo_coord."""
    s = str(v or "").upper()
    if "MIFR" in s or "MASTER" in s:
        return "MIFR"
    if "NOTIF" in s:
        return "NOTIFICATION"
    if "BIU" in s:
        return "BIU"
    if "COORD" in s or s.startswith("CR/"):
        return "COORDINATION"
    return "API"


def parse_rows(rows):
    """Chuẩn hóa danh sách dict thô -> (records, report).

    records: list dict đúng tham số của database.add_filing.
    report: {columns_found, fields_mapped, n_rows, n_skipped_no_name}.
    """
    records, skipped = [], 0
    fields_mapped = set()
    columns_found = set()
    for raw in rows:
        norm = {}
        for k, v in raw.items():
            columns_found.add(str(k))
            field = _ALIAS_TO_FIELD.get(_norm_key(k))
            if field and (v is not None and str(v).strip() != ""):
                norm[field] = v
                fields_mapped.add(field)
        name = str(norm.get("network_name", "") or "").strip()
        if not name:
            skipped += 1
            continue
        records.append({
            "network_name": name,
            "administration": str(norm.get("administration", "") or "").strip()
                              or "UNKNOWN",
            "operator": str(norm.get("operator", "") or "").strip(),
            "bands": str(norm.get("bands", "") or "").strip(),
            "n_sats_filed": _parse_int(norm.get("n_sats_filed"), default=1),
            "alt_km": _parse_float(norm.get("alt_km")),
            "inc_deg": _parse_float(norm.get("inc_deg")),
            "status": _map_status(norm.get("status")),
            "api_date": _parse_date(norm.get("api_date")),
            "biu_deadline": _parse_date(norm.get("biu_deadline")),
            "sns_id": str(norm.get("sns_id", "") or "").strip(),
            "notice_type": str(norm.get("notice_type", "") or "").strip(),
            "ific_no": str(norm.get("ific_no", "") or "").strip(),
            "receipt_date": _parse_date(norm.get("receipt_date")),
        })
    report = {"columns_found": sorted(columns_found),
              "fields_mapped": sorted(fields_mapped),
              "n_rows": len(rows), "n_skipped_no_name": skipped}
    return records, report


def read_csv(path):
    """Đọc file CSV trích từ SpaceQry/SpaceCap/Space Explorer/mdb-export."""
    p = Path(path)
    text = p.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return [dict(r) for r in csv.DictReader(text.splitlines(), dialect=dialect)]


def read_mdb(path, table=None):
    """Đọc bảng mạng vệ tinh từ file .mdb (SRS) — cần access-parser hoặc mdbtools."""
    p = Path(path)
    try:
        from access_parser import AccessParser
    except ImportError:
        AccessParser = None
    if AccessParser is not None:
        try:
            parser = AccessParser(str(p))
            tables = list(parser.catalog.keys())
            use = table or _pick_network_table(parser, tables)
            if use is None:
                raise RuntimeError(
                    f"Không tìm thấy bảng chứa tên mạng vệ tinh trong {tables}")
            data = parser.parse_table(use)
            cols = list(data.keys())
            n = len(next(iter(data.values()))) if cols else 0
            return [{c: data[c][i] for c in cols} for i in range(n)]
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Không đọc được file MDB bằng access-parser: {e}")
    # dự phòng: mdb-export của mdbtools
    try:
        tables = subprocess.run(["mdb-tables", "-1", str(p)],
                                capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        tables = None
    if tables is not None and tables.returncode == 0:
        names = [t.strip() for t in tables.stdout.splitlines() if t.strip()]
        use = table or (names[0] if names else None)
        if use:
            out = subprocess.run(["mdb-export", str(p), use],
                                 capture_output=True, text=True, timeout=600)
            if out.returncode == 0:
                return [dict(r) for r in
                        csv.DictReader(out.stdout.splitlines())]
    raise RuntimeError(
        "Chưa có công cụ đọc MDB trên máy này. Cài thư viện tùy chọn "
        "(pip install access-parser) hoặc mdbtools, hoặc trích file CSV từ "
        "SpaceCap/SpaceQry rồi nhập bằng file .csv.")


def _pick_network_table(parser, tables):
    name_keys = {_norm_key(a) for a in COLUMN_MAP["network_name"]}
    for t in tables:
        try:
            data = parser.parse_table(t)
        except Exception:
            continue
        if name_keys & {_norm_key(c) for c in data.keys()}:
            return t
    return None


def import_records(db_path, records, source_label):
    """Nạp records vào CSDL; bỏ qua mạng đã tồn tại. Trả thống kê."""
    stats = {"added": 0, "skipped_existing": 0, "errors": []}
    existing = {f["network_name"] for f in db.list_filings(db_path)}
    for rec in records:
        if rec["network_name"] in existing:
            stats["skipped_existing"] += 1
            continue
        try:
            note = f"Nhập từ {source_label}"
            rec = {**rec, "notes": note}
            db.add_filing(db_path, **rec)
            existing.add(rec["network_name"])
            stats["added"] += 1
        except Exception as e:  # lỗi 1 dòng không chặn cả đợt nhập
            stats["errors"].append(f"{rec['network_name']}: {e}")
    return stats


def import_file(db_path, file_path, source_label=None):
    """Nhập từ file .csv hoặc .mdb. Trả (stats, parse_report)."""
    p = Path(file_path)
    label = source_label or p.name
    if p.suffix.lower() == ".mdb":
        rows = read_mdb(p)
    elif p.suffix.lower() in (".csv", ".txt", ".tsv"):
        rows = read_csv(p)
    else:
        raise ValueError("Chỉ nhận file .csv hoặc .mdb (SRS)")
    records, report = parse_rows(rows)
    stats = import_records(db_path, records, label)
    return stats, report
