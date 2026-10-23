"""Dòng lệnh leo-coord — đánh giá chòm sao LEO/NGSO và quản lý CSDL phối hợp."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import yaml

from .config import load_config
from .orbits import WalkerConstellation
from .coverage import coverage_grid, point_stats, footprint_radius_km
from .pfd import check_downlink_pfd
from .epfd import single_entry_epfd_down
from .coordination import screen_ngso_vs_gso
from .milestones import res35_schedule, evaluate, warehousing_flag
from .report import build_html
from . import database as db


def load_walker(path):
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    w = WalkerConstellation(
        spec.get("name", "LEO"), spec["alt_km"], spec["inc_deg"],
        spec["n_sats"], spec["n_planes"],
        spec.get("phasing", 1), spec.get("kind", "delta"))
    return w, spec


def _ref_points(cfg):
    return [(v["lat"], v["lon"], k) for k, v in
            cfg["vietnam"]["reference_points"].items()]


def build_assessment(w, spec, cfg, gso_lon=105.5, biu_deadline=None,
                     deployments=(), dish_d_m=1.2):
    dl = spec.get("downlink", {})
    band = dl.get("band_ghz", "10.7-12.7")
    lo, hi = (float(x) for x in band.split("-"))
    freq = (lo + hi) / 2.0
    eirp = float(dl.get("eirp_dbw_per_mhz", 10.0))
    pts = _ref_points(cfg)
    min_el = cfg["analysis"]["min_elevation_deg"]

    times = np.arange(0.0, 86400.0, 60.0)
    sat_ecef = w.ecef_positions(times)
    point_rows = []
    for lat, lon, name in pts:
        st = point_stats(sat_ecef, times, lat, lon, min_el)
        point_rows.append({"name": name, **st})
    grid = coverage_grid(w, tuple(cfg["vietnam"]["bbox"].values()),
                         grid_step_deg=1.0, min_elev_deg=min_el,
                         duration_s=43200.0, dt_s=120.0)
    grid_summary = {
        "grid": f"{grid['fraction_covered'].shape[0]}x{grid['fraction_covered'].shape[1]}",
        "mean_fraction": float(grid["fraction_covered"].mean()),
        "min_fraction": float(grid["fraction_covered"].min()),
    }
    pfd = check_downlink_pfd(eirp, freq, w.alt_km, w.size, cfg)
    epfd = single_entry_epfd_down(
        w, eirp, freq, cfg["vietnam"]["reference_points"]["hanoi"]["lat"],
        cfg["vietnam"]["reference_points"]["hanoi"]["lon"], gso_lon,
        dish_d_m=dish_d_m, duration_s=43200.0, dt_s=120.0, cfg=cfg)
    coord = screen_ngso_vs_gso(w, freq, eirp, gso_lon, pts, cfg=cfg,
                               duration_s=43200.0, dt_s=120.0)

    milestones, warehousing = None, None
    if biu_deadline:
        sched = res35_schedule(biu_deadline, w.size)
        ev = evaluate(sched, list(deployments))
        milestones = [{**m, "due": m["due"].isoformat()} for m in ev]
        n_dep = max([n for _, n in deployments], default=0)
        warehousing = warehousing_flag(w.size, n_dep)

    return {
        "name": w.name,
        "fictional": bool(spec.get("fictional", False)),
        "constellation": {
            "alt_km": w.alt_km, "inc_deg": w.inc_deg, "n_sats": w.size,
            "n_planes": w.n_planes, "kind": w.kind,
            "period_min": w.period_s / 60.0,
            "footprint_km": footprint_radius_km(w.alt_km, min_el),
        },
        "downlink": {"band_ghz": band, "freq_ghz": freq,
                     "eirp_dbw_per_mhz": eirp},
        "coverage": {"points": point_rows, "grid_summary": grid_summary,
                     "min_elev_deg": min_el},
        "pfd": pfd,
        "epfd": epfd,
        "coordination": coord,
        "milestones": milestones,
        "warehousing": warehousing,
    }


def cmd_assess(args):
    w, spec = load_walker(args.constellation)
    cfg = load_config(args.config) if args.config else load_config()
    biu = date.fromisoformat(args.biu_deadline) if args.biu_deadline else None
    deps = []
    if args.deployed:
        for item in args.deployed.split(","):
            d, n = item.split(":")
            deps.append((date.fromisoformat(d.strip()), int(n.strip())))
    a = build_assessment(w, spec, cfg, gso_lon=args.gso_lon, biu_deadline=biu,
                         deployments=deps, dish_d_m=args.dish)
    html = build_html(a)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Đã ghi báo cáo: {out}")
    print(f"Phủ sóng TB VN: {a['coverage']['grid_summary']['mean_fraction']*100:.1f}% | "
          f"PFD: {'DAT' if a['pfd']['compliant'] else 'KHONG DAT'} | "
          f"EPFD: {'DAT' if a['epfd']['screening_pass'] else 'KHONG DAT'} | "
          f"Phối hợp: {'CAN' if a['coordination']['coordination_likely_required'] else 'chua thay'}")
    if args.json_out:
        jp = Path(args.json_out)
        jp.write_text(json.dumps(a, indent=2, default=str), encoding="utf-8")
        print(f"Đã ghi JSON: {jp}")


def cmd_coverage(args):
    w, spec = load_walker(args.constellation)
    cfg = load_config()
    min_el = cfg["analysis"]["min_elevation_deg"]
    times = np.arange(0.0, 86400.0, 60.0)
    sat_ecef = w.ecef_positions(times)
    for lat, lon, name in _ref_points(cfg):
        st = point_stats(sat_ecef, times, lat, lon, min_el)
        print(f"{name}: phủ {st['fraction_covered']*100:.1f}%, "
              f"TB {st['mean_sats_visible']:.1f} vệ tinh, "
              f"trống lâu nhất {st['max_gap_min']:.1f} phút")


def cmd_pfd(args):
    r = check_downlink_pfd(args.eirp, args.freq, args.alt, args.n_sats)
    for k in ("freq_ghz", "band", "unit", "pfd", "limit", "x_reduction_db",
              "margin_db", "compliant"):
        print(f"{k}: {r[k]}")


def cmd_epfd(args):
    w, spec = load_walker(args.constellation)
    r = single_entry_epfd_down(
        w, args.eirp, args.freq, args.lat, args.lon, args.gso_lon,
        dish_d_m=args.dish, duration_s=args.duration_h * 3600.0, dt_s=120.0)
    print(f"mẫu hợp lệ: {r['n_valid']}/{r['n_samples']}")
    for k, v in r["percentiles"].items():
        print(f"{k}: {v:.1f} dBW/m2/40kHz")
    print(f"max: {r['max']:.1f}, biên vs Table 22-1A: {r['margin_vs_anchor_db']:.1f} dB, "
          f"{'DAT' if r['screening_pass'] else 'KHONG DAT'}")


def cmd_milestones(args):
    biu = date.fromisoformat(args.biu_deadline)
    sched = res35_schedule(biu, args.n_sats)
    deps = []
    if args.deployed:
        for item in args.deployed.split(","):
            d, n = item.split(":")
            deps.append((date.fromisoformat(d.strip()), int(n.strip())))
    today = date.fromisoformat(args.today) if args.today else None
    for m in evaluate(sched, deps, today):
        print(f"{m['regime']} | {m['percent']}% | hạn {m['due']} | "
              f"cần {m['required_n']} | đã có {m['deployed_n']} | {m['status']}")


def cmd_db(args):
    if args.db_cmd == "init":
        p = db.init_db(args.db)
        print(f"Đã khởi tạo CSDL: {p}")
    elif args.db_cmd == "add-filing":
        fid = db.add_filing(
            args.db, network_name=args.name, administration=args.admin,
            n_sats_filed=args.n_sats, operator=args.operator, bands=args.bands,
            alt_km=args.alt, inc_deg=args.inc, status=args.status,
            api_date=args.api_date, biu_deadline=args.biu_deadline,
            notes=args.notes, sns_id=args.sns_id,
            notice_type=args.notice_type, ific_no=args.ific_no,
            receipt_date=args.receipt_date)
        print(f"Đã thêm hồ sơ id={fid}")
    elif args.db_cmd == "import-brific":
        from .brific import import_file
        stats, report = import_file(args.db, args.file)
        print(f"Đọc {report['n_rows']} dòng; cột khớp: "
              f"{', '.join(report['fields_mapped']) or '(không có)'}")
        print(f"Đã nhập mới: {stats['added']}; bỏ qua (đã có): "
              f"{stats['skipped_existing']}; bỏ qua (thiếu tên): "
              f"{report['n_skipped_no_name']}")
        for e in stats["errors"]:
            print(f"  LỖI: {e}")
    elif args.db_cmd == "add-crosscheck":
        xid = db.add_cross_check(
            args.db, args.name, args.other, our_result=args.our_result,
            official_source=args.official_source,
            official_result=args.official_result, agreement=args.agreement,
            checked_date=args.date, checker=args.checker, notes=args.notes)
        print(f"Đã ghi nhận đối chứng id={xid}")
    elif args.db_cmd == "list-crosschecks":
        for x in db.list_cross_checks(args.db, args.name):
            print(f"{x['id']} | {x['network_name']} <-> {x['other_system']} | "
                  f"{x['agreement']} | {x['official_source']} | "
                  f"{x['checked_date']}")
    elif args.db_cmd == "report-deployment":
        did = db.report_deployment(args.db, args.name, args.date, args.n,
                                   args.source)
        print(f"Đã ghi nhận triển khai id={did}")
    elif args.db_cmd == "list":
        for f in db.list_filings(args.db):
            print(f"{f['network_name']} | {f['administration']} | "
                  f"{f['n_sats_filed']} vs | {f['status']} | BIU {f['biu_deadline']}")
    elif args.db_cmd == "milestones":
        for item in db.milestone_status(args.db):
            print(f"== {item['network_name']}")
            for m in item["milestones"]:
                print(f"  {m['percent']}% hạn {m['due']}: cần {m['required_n']}, "
                      f"đã có {m['deployed_n']} -> {m['status']}")
    elif args.db_cmd == "add-case":
        cid = db.add_coordination_case(args.db, args.name, args.other,
                                       args.band, args.trigger, args.status,
                                       args.notes)
        print(f"Đã thêm vụ việc phối hợp id={cid}")
    elif args.db_cmd == "list-cases":
        for c_ in db.list_coordination_cases(args.db, args.name):
            print(f"{c_['id']} | {c_['other_system']} | {c_['band']} | "
                  f"{c_['trigger']} | {c_['status']}")
    elif args.db_cmd == "export":
        p = db.export_filings_csv(args.db, args.out)
        print(f"Đã xuất: {p}")


def build_parser():
    p = argparse.ArgumentParser(prog="leo-coord",
                                description="Đánh giá chòm sao LEO/NGSO và CSDL phối hợp tần số")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("assess", help="Đánh giá toàn diện và xuất báo cáo HTML")
    a.add_argument("--constellation", required=True)
    a.add_argument("--config", default=None)
    a.add_argument("--gso-lon", type=float, default=105.5)
    a.add_argument("--dish", type=float, default=1.2)
    a.add_argument("--biu-deadline", default=None)
    a.add_argument("--deployed", default=None,
                   help='VD: "2025-06-01:70,2028-12-01:320"')
    a.add_argument("--out", default="out/bao_cao.html")
    a.add_argument("--json-out", default=None)
    a.set_defaults(func=cmd_assess)

    c = sub.add_parser("coverage", help="Thống kê phủ sóng tại các điểm tham chiếu VN")
    c.add_argument("--constellation", required=True)
    c.set_defaults(func=cmd_coverage)

    f = sub.add_parser("pfd", help="Kiểm tra PFD Article 21")
    f.add_argument("--eirp", type=float, required=True)
    f.add_argument("--freq", type=float, required=True)
    f.add_argument("--alt", type=float, required=True)
    f.add_argument("--n-sats", type=int, default=1)
    f.set_defaults(func=cmd_pfd)

    e = sub.add_parser("epfd", help="Sàng lọc EPFD Article 22")
    e.add_argument("--constellation", required=True)
    e.add_argument("--eirp", type=float, required=True)
    e.add_argument("--freq", type=float, required=True)
    e.add_argument("--lat", type=float, default=21.0285)
    e.add_argument("--lon", type=float, default=105.8542)
    e.add_argument("--gso-lon", type=float, default=105.5)
    e.add_argument("--dish", type=float, default=1.2)
    e.add_argument("--duration-h", type=float, default=12.0)
    e.set_defaults(func=cmd_epfd)

    m = sub.add_parser("milestones", help="Lịch và đánh giá mốc Res 35")
    m.add_argument("--biu-deadline", required=True)
    m.add_argument("--n-sats", type=int, required=True)
    m.add_argument("--deployed", default=None)
    m.add_argument("--today", default=None, help="Ngày đánh giá (YYYY-MM-DD)")
    m.set_defaults(func=cmd_milestones)

    d = sub.add_parser("db", help="CSDL phối hợp tần số vệ tinh quốc gia")
    dsub = d.add_subparsers(dest="db_cmd", required=True)
    di = dsub.add_parser("init"); di.add_argument("--db", required=True)
    af = dsub.add_parser("add-filing"); af.add_argument("--db", required=True)
    af.add_argument("--name", required=True); af.add_argument("--admin", required=True)
    af.add_argument("--n-sats", type=int, required=True)
    af.add_argument("--operator", default=""); af.add_argument("--bands", default="")
    af.add_argument("--alt", type=float, default=None); af.add_argument("--inc", type=float, default=None)
    af.add_argument("--status", default="API"); af.add_argument("--api-date", default=None)
    af.add_argument("--biu-deadline", default=None); af.add_argument("--notes", default="")
    af.add_argument("--sns-id", default=""); af.add_argument("--notice-type", default="")
    af.add_argument("--ific-no", default=""); af.add_argument("--receipt-date", default=None)
    ib = dsub.add_parser("import-brific"); ib.add_argument("--db", required=True)
    ib.add_argument("--file", required=True,
                    help="File .csv trích từ SpaceQry/SpaceCap hoặc .mdb (SRS)")
    xc = dsub.add_parser("add-crosscheck"); xc.add_argument("--db", required=True)
    xc.add_argument("--name", required=True); xc.add_argument("--other", required=True)
    xc.add_argument("--our-result", default=""); xc.add_argument("--official-source", default="")
    xc.add_argument("--official-result", default="")
    xc.add_argument("--agreement", default="CHUA_RO", choices=["KHOP", "LECH", "CHUA_RO"])
    xc.add_argument("--date", default=None); xc.add_argument("--checker", default="")
    xc.add_argument("--notes", default="")
    lx = dsub.add_parser("list-crosschecks"); lx.add_argument("--db", required=True)
    lx.add_argument("--name", default=None)
    rd = dsub.add_parser("report-deployment"); rd.add_argument("--db", required=True)
    rd.add_argument("--name", required=True); rd.add_argument("--date", required=True)
    rd.add_argument("--n", type=int, required=True); rd.add_argument("--source", default="")
    li = dsub.add_parser("list"); li.add_argument("--db", required=True)
    ms = dsub.add_parser("milestones"); ms.add_argument("--db", required=True)
    ac = dsub.add_parser("add-case"); ac.add_argument("--db", required=True)
    ac.add_argument("--name", required=True); ac.add_argument("--other", required=True)
    ac.add_argument("--band", default=""); ac.add_argument("--trigger", default="")
    ac.add_argument("--status", default="MO"); ac.add_argument("--notes", default="")
    lc = dsub.add_parser("list-cases"); lc.add_argument("--db", required=True)
    lc.add_argument("--name", default=None)
    ex = dsub.add_parser("export"); ex.add_argument("--db", required=True)
    ex.add_argument("--out", required=True)
    d.set_defaults(func=cmd_db)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
