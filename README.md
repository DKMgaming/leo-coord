# leo_coord — Phần mềm hỗ trợ quản lý tần số & quỹ đạo chòm sao vệ tinh LEO/NGSO

Phần mềm phân tích kỹ thuật phục vụ nhiệm vụ **"Xây dựng Chiến lược quản lý tần số,
quỹ đạo vệ tinh chòm sao tầm thấp (LEO) và phối hợp quốc tế về tần số vũ trụ"**
(Cục Tần số vô tuyến điện — cơ quan thường trực Ủy ban Vũ trụ Việt Nam;
Phòng Hợp tác và Phối hợp tần số quốc tế chủ trì).

Phần mềm gồm hai phần dùng chung một engine tính toán:

1. **Engine + CLI** — mô hình chòm sao, phân tích phủ sóng, kiểm tra PFD/EPFD,
   sàng lọc phối hợp quốc tế, theo dõi mốc triển khai, CSDL phối hợp quốc gia.
2. **Web app 3 tab** — Tab 1: các chức năng chính + **bản đồ số 3D (CesiumJS)**;
   Tab 2: tham luận & tài liệu đính kèm (Word/Excel/PDF/PowerPoint);
   Tab 3: CSDL phối hợp tần số vệ tinh quốc gia (hồ sơ đăng ký, triển khai
   thực tế, vụ việc phối hợp).

## Chức năng engine

| Module | Nội dung |
|---|---|
| `orbits.py` | Chòm sao Walker (star/delta), lan truyền quỹ đạo tròn, nạp TLE/SGP4; tính góc ngẩng, phương vị, cự ly trạm–vệ tinh |
| `coverage.py` | Phân tích phủ sóng trên lưới lãnh thổ Việt Nam + 3 điểm tham chiếu (Hà Nội, Đà Nẵng, TP.HCM): tỉ lệ thời gian phủ, số vệ tinh trung bình, khoảng trống tối đa |
| `pfd.py` | Kiểm tra PFD theo RR Article 21 (Table 21-4), gồm hệ số giảm X cho chòm sao lớn (≥51 vệ tinh) |
| `epfd.py` | Sàng lọc EPFD đơn điểm theo RR Article 22 (đường bao S.465) — **chỉ là sàng lọc rút gọn, không thay thế phần mềm S.1503 của ITU BR** |
| `coordination.py` | Xác định nhu cầu phối hợp: RR Article 9, cung Appendix 5, tiêu chí ΔT/T > 6% của Appendix 8 |
| `milestones.py` | Mốc triển khai Res 35 (WRC-19, sửa đổi WRC-23): 10%/50%/100% tại +2/+5/+7 năm sau thời hạn 7 năm; lịch FCC; cảnh báo nguy cơ "xí phần" (warehousing) |
| `database.py` | CSDL phối hợp tần số vệ tinh quốc gia (SQLite): hồ sơ đăng ký, triển khai thực tế, vụ việc phối hợp |
| `report.py` | Xuất báo cáo đánh giá dạng HTML tiếng Việt |

Mọi ngưỡng quy định (ITU/FCC) đều nằm trong `configs/leo_coord.yaml` dạng
versioned — **không hard-code trong mã nguồn**.

## Web app

### Tab 1 — Chức năng chính + Bản đồ số 3D

- Form nhập tham số chòm sao (độ cao, góc nghiêng, số vệ tinh, số mặt phẳng,
  kiểu Walker, băng tần, EIRP, kinh độ vệ tinh GSO, lịch triển khai) + 2 mẫu sẵn.
- Thẻ kết quả: phủ sóng Việt Nam, PFD (Article 21), EPFD (Article 22),
  phối hợp quốc tế, mốc Res 35, chống "xí phần".
- Bản đồ số 3D dùng **CesiumJS**: **địa hình thật** (ArcGIS World Elevation),
  **3 lớp ảnh nền chuyển đổi được** (ảnh vệ tinh Esri / bản đồ đường
  OpenStreetMap / nền tối CARTO), vệ tinh bay theo thời gian mô phỏng
  (chạy/tạm dừng, tốc độ 1–1000×), vành quỹ đạo theo mặt phẳng, lớp phủ sóng,
  điểm tham chiếu Việt Nam, vệ tinh GSO + vành GEO, bật/tắt từng lớp.
- **Click vào điểm bất kỳ trên quả cầu** để tra cứu vệ tinh đang khả kiến tại
  đúng thời điểm mô phỏng: tên vệ tinh, góc ngẩng, phương vị, cự ly
  (API `/api/visible-sats`).

### Tab 2 — Tham luận & Tài liệu

- Tải lên / danh sách / tải xuống / xóa tài liệu đính kèm: `.doc`, `.docx`,
  `.xls`, `.xlsx`, `.pdf`, `.ppt`, `.pptx` (tối đa 50 MB/file).
- Lưu trữ tại `webapp/data/` (không đưa lên git).

### Tab 3 — CSDL phối hợp quốc gia

- Form nhập **hồ sơ đăng ký** (tên mạng, cơ quan đăng ký, nhà khai thác, băng
  tần, số vệ tinh, trạng thái API/COORDINATION/NOTIFICATION/MIFR/BIU, hạn BIU),
  **báo cáo triển khai thực tế** theo ngày, và **vụ việc phối hợp** với hệ
  thống khác.
- Bảng quản lý: danh sách hồ sơ (kèm số vệ tinh đã triển khai mới nhất), lịch
  sử triển khai, danh sách vụ việc, trạng thái mốc Res 35 từng hồ sơ, nút
  **xuất CSV**.
- Dùng chung file SQLite `webapp/data/coord.db` với CLI (`leo-coord db ...`).

### API chính (FastAPI)

| Endpoint | Mô tả |
|---|---|
| `GET /api/health`, `GET /api/meta` | Trạng thái, cấu hình & ngưỡng hiện hành |
| `POST /api/assess` | Đánh giá toàn diện một chòm sao |
| `POST /api/tracks` | Quỹ đạo mẫu hóa cho bản đồ 3D |
| `POST /api/coverage-map` | Lưới phủ sóng cho lớp overlay |
| `POST /api/visible-sats` | Vệ tinh khả kiến tại điểm + thời điểm chỉ định |
| `GET/POST /api/docs`, `GET /api/docs/{id}/download`, `DELETE /api/docs/{id}` | Quản lý tài liệu tham luận |
| `GET/POST /api/db/filings` | Danh sách / thêm hồ sơ đăng ký |
| `GET/POST /api/db/deployments` | Lịch sử / báo cáo triển khai thực tế |
| `GET/POST /api/db/cases` | Danh sách / thêm vụ việc phối hợp |
| `GET /api/db/milestones`, `GET /api/db/export.csv` | Trạng thái mốc Res 35; xuất CSV hồ sơ |

Tài liệu API tương tác có tại `/docs` khi server đang chạy. Chi tiết thêm:
`webapp/README.md`.

## Lưu ý quan trọng

- Đây là công cụ **hỗ trợ phân tích, sàng lọc**. Mọi kết luận cấp phép hay phối
  hợp chính thức phải dựa trên văn bản ITU/FCC hiện hành và phần mềm của ITU BR
  (SpaceCap, GIMS, S.1503).
- Các giá trị giới hạn ITU/FCC trong `configs/leo_coord.yaml` hiện ở trạng thái
  `index-sourced-2026-10-19` (tra cứu từ nguồn mở trên mạng) — **cần đối chiếu
  văn bản gốc trước khi dùng chính thức**.
- Toàn bộ dữ liệu trong `data/demo/` đều là **HƯ CẤU** và được gắn nhãn rõ ràng.

## Cài đặt

Yêu cầu Python ≥ 3.10.

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
# thêm cho web app:
.venv/bin/pip install fastapi "uvicorn[standard]" python-multipart httpx
```

## Chạy nhanh

### CLI

```bash
.venv/bin/leo-coord assess --constellation data/demo/constellation_demo.yaml --report out/bao_cao.html
.venv/bin/leo-coord coverage   # thống kê phủ sóng tại 3 điểm VN
.venv/bin/leo-coord pfd        # kiểm tra PFD Article 21
.venv/bin/leo-coord epfd       # sàng lọc EPFD Article 22
.venv/bin/leo-coord milestones # lịch & đánh giá mốc Res 35
.venv/bin/leo-coord db init --db data/coord.db   # CSDL phối hợp quốc gia
```

### Web app

```bash
.venv/bin/uvicorn webapp.backend.app:app --host 0.0.0.0 --port 8000
# mở http://localhost:8000
```

Bản đồ 3D tải CesiumJS và các tile ảnh nền/địa hình qua mạng (CDN + dịch vụ
công cộng miễn phí); nếu không có mạng, các chức năng tính toán vẫn hoạt động.

## Kiểm thử

```bash
.venv/bin/python -m pytest   # 61 test
```

## Cấu trúc thư mục

```
leo_coord/            mã nguồn engine (orbits, coverage, pfd, epfd,
                      coordination, milestones, database, report, cli, config)
configs/              leo_coord.yaml — mọi ngưỡng kỹ thuật, có version
data/demo/            chòm sao demo HƯ CẤU
docs/nghien-cuu-quoc-te/  báo cáo nghiên cứu quốc tế (FCC, ITU, 8 quốc gia,
                      bền vững không gian, khung pháp lý Việt Nam, 3 nhóm giải pháp)
webapp/               backend FastAPI + frontend (HTML/CSS/JS + CesiumJS)
tests/                kiểm thử pytest (engine + web app)
```

## Lịch sử phiên bản

- **2026-10-19** — Engine + CLI (8 module), báo cáo nghiên cứu quốc tế.
- **2026-10-20** — Web app 2 tab (FastAPI + bản đồ 3D); nâng cấp bản đồ lên
  CesiumJS (địa hình thật, chuyển lớp ảnh nền) + click tra cứu vệ tinh khả kiến.
- **2026-10-23** — Thêm Tab 3: CSDL phối hợp quốc gia trên web (hồ sơ đăng ký,
  triển khai thực tế, vụ việc phối hợp, mốc Res 35, xuất CSV); README viết lại.
