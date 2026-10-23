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
| `coverage.py` | Phân tích phủ sóng trên lưới lãnh thổ Việt Nam + 5 điểm tham chiếu (Hà Nội, Việt Trì, Trạm Kiểm soát vệ tinh Bắc Ninh, Đà Nẵng, TP.HCM): tỉ lệ thời gian phủ, số vệ tinh trung bình, khoảng trống tối đa |
| `pfd.py` | Kiểm tra PFD theo RR Article 21 (Table 21-4), gồm hệ số giảm X cho chòm sao lớn (≥51 vệ tinh) |
| `epfd.py` | Sàng lọc EPFD đơn điểm theo RR Article 22 (đường bao S.465) — **chỉ là sàng lọc rút gọn, không thay thế phần mềm S.1503 của ITU BR** |
| `coordination.py` | Xác định nhu cầu phối hợp: RR Article 9, cung Appendix 5, tiêu chí ΔT/T > 6% của Appendix 8 |
| `milestones.py` | Mốc triển khai Res 35 (WRC-19, sửa đổi WRC-23): 10%/50%/100% tại +2/+5/+7 năm sau thời hạn 7 năm; lịch FCC; cảnh báo nguy cơ "xí phần" (warehousing) |
| `database.py` | CSDL phối hợp tần số vệ tinh quốc gia (SQLite): hồ sơ đăng ký (kèm trường Appendix 4: SNS ID, loại thông báo, số BR IFIC, ngày BR nhận), triển khai thực tế, vụ việc phối hợp, bản ghi đối chứng với BR |
| `brific.py` | Nhập dữ liệu hồ sơ từ nguồn ITU: file CSV trích từ SpaceQry/SpaceCap/Space Explorer hoặc file .mdb SRS của BR IFIC (ánh xạ cột SNS, chuẩn hóa trạng thái/ngày tháng) |
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
- **Nhập dữ liệu BR IFIC**: tải lên file CSV trích từ SpaceQry/SpaceCap/
  Space Explorer để nhập hàng loạt hồ sơ (file .mdb SRS nhập qua CLI).
- **Đối chứng kết quả phối hợp**: ghi nhận kết luận chính thức của BR
  (BR IFIC, SpaceQry/BR-SIS) và mức khớp với kết quả sàng lọc của leo_coord.
- Trường hồ sơ căn chỉnh theo Appendix 4 / SpaceCap — xem
  `docs/app4-spacecap-mapping.md`.
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
| `GET/POST /api/db/crosschecks` | Bản ghi đối chứng kết quả phối hợp với BR |
| `POST /api/db/import` | Nhập hồ sơ từ file CSV trích BR IFIC/SpaceQry/SpaceCap |

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

## Quản trị cấu hình — cập nhật `configs/leo_coord.yaml` sau khi đối chiếu dữ liệu ITU

Mọi ngưỡng quy định đều nằm trong `configs/leo_coord.yaml` (không hard-code
trong mã nguồn). Trạng thái xác minh được ghi **theo từng mục** (trường
`status`/`source` của từng bảng) và một dòng tổng ở đầu file
(`verification_status`). Quản trị viên chỉ cập nhật file này theo quy trình
sau — **không sửa giá trị khi chưa có văn bản gốc trong tay**.

### Bước 1 — Chuẩn bị nguồn đối chiếu chính thức

- Thể lệ Vô tuyến (RR) bản hiện hành: Article 21 (Table 21-4), Article 22
  (Table 22-1A, 22-1B, 22-2...), Resolution 35 (bản sửa đổi mới nhất),
  Appendix 5 (Table 5-1), Appendix 8, các điều khoản 9.7A/9.7B.
- BR IFIC (Space) + Preface (cấu trúc SNS, mã trạng thái hồ sơ); khuyến nghị
  ITU-R liên quan (S.1503, S.1714...). Quy định FCC (47 CFR Part 25) chỉ khi
  đối chiếu riêng phần FCC.
- Ghi rõ **ấn bản/năm** của từng văn bản dùng để đối chiếu.

### Bước 2 — Đối chiếu từng mục và lập bảng chênh lệch

Đối chiếu lần lượt: `pfd.bands`, `epfd` (điểm không-vượt-quá và đường cong
Table 22-1A đầy đủ), `coordination.arcs`, `coordination.pfd_triggers_9_7`,
`coordination.delta_T_over_T_trigger_percent`, `milestones.marks`.
Lập bảng: *mục — giá trị hiện tại — giá trị văn bản gốc — chênh lệch — căn cứ
(số điều/bảng)*. Các mục hiện đang gắn cờ chưa rõ phải được xử lý dứt điểm ở
bước này, ví dụ: mức −202 dB(W/m²/40kHz) trong ghi chú của ngưỡng 9.7A/9.7B,
hai ngưỡng gắn `index-sourced-verify` (17.8–18.6 GHz, 19.7–20.2 GHz) và
đường cong mask đầy đủ của Table 22-1A. Mục nào chưa đối chiếu được thì
**giữ nguyên** giá trị và cờ trạng thái — không tự suy đoán để điền.

### Bước 3 — Cập nhật file

1. Sửa giá trị của đúng mục đã đối chiếu; đổi `status` của mục đó từ
   `index-sourced` thành `verified` và bổ sung căn cứ ngay tại chỗ, ví dụ:

   ```yaml
   - freq_ghz: "10.7-11.7"
     delta_le_5: -150.0
     status: "verified"   # RR 2024, Article 21, Table 21-4; doi chieu 2026-11-02, Nguyen Van A
   ```

2. Cập nhật `updated` ở đầu file thành ngày sửa; chỉ khi **mọi** mục đều đã
   `verified` mới đổi `verification_status` tổng thành
   `verified-itu-<YYYY-MM-DD>`. Tăng `version` nếu thay đổi làm đổi kết quả
   đánh giá trên diện rộng.
3. Không đổi cấu trúc khóa (tên trường) — mã nguồn và test phụ thuộc vào đó.

### Bước 4 — Kiểm tra tác động trước khi dùng

```bash
.venv/bin/python -m pytest            # toàn bộ test phải qua (hiện 68 test)
.venv/bin/leo-coord assess --constellation data/demo/constellation_demo.yaml --report out/truoc-sau.html
```

- Nếu test đỏ vì gắn với giá trị cũ: **dừng lại** — xác minh thay đổi là đúng
  văn bản gốc rồi mới sửa test, và ghi rõ trong commit. Không sửa test cho
  khớp một cách máy móc.
- So sánh kết quả đánh giá trước/sau (biên PFD, kết luận phối hợp, mốc
  Res 35) với chòm sao demo để chắc chắn thay đổi đúng ý đồ.

### Bước 5 — Lưu hồ sơ và phân quyền

- Commit với thông điệp nêu rõ mục đã sửa + căn cứ, ví dụ:
  `config: doi chieu PFD Table 21-4 theo RR 2024 (verified)`.
- Lưu bảng đối chiếu của Bước 2 tại `docs/doi-chieu-config-<YYYY-MM-DD>.md`.
- Người sửa và người duyệt phải là **hai người khác nhau**; bản đã duyệt mới
  được dùng cho đánh giá phục vụ công việc chính thức.

### Mục không thuộc đối chiếu ITU

- `vietnam.reference_points` (tọa độ các trạm tham chiếu): cập nhật theo số
  liệu đo đạc/quyết định của cơ quan, ghi nguồn riêng — không lấy từ ITU.
- `analysis` (góc ngẩng tối thiểu, bước lưới, bước thời gian): tham số mô
  phỏng nội bộ, quản trị viên chỉnh theo yêu cầu phân tích, không cần đối
  chiếu ITU nhưng phải ghi lý do khi thay đổi.

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
.venv/bin/python -m pytest   # 68 test
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
  Bổ sung: nhập dữ liệu BR IFIC (CSV/.mdb SRS), trường hồ sơ Appendix 4
  (SNS ID, loại thông báo, số BR IFIC), đối chứng kết quả phối hợp với BR.
