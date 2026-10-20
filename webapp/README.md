# Web app leo_coord

Giao diện web cho phần mềm `leo_coord` — chạy trên cùng engine Python đã kiểm thử
(49 test pytest), không tính lại bằng JavaScript.

## Hai tab chính

- **Tab 1 — Chức năng chính + Bản đồ số 3D (CesiumJS):** nhập tham số chòm sao,
  chạy đánh giá (phủ sóng Việt Nam, PFD Article 21, EPFD Article 22, sàng lọc
  phối hợp, mốc Res 35), đồng thời xem vệ tinh bay theo thời gian thực trên
  quả cầu 3D với **địa hình thật** (ArcGIS World Elevation) và **lớp ảnh nền
  chuyển đổi được** (ảnh vệ tinh Esri / bản đồ đường OSM / nền tối).
  **Click vào điểm bất kỳ** trên quả cầu để tra cứu vệ tinh đang khả kiến
  (góc ngẩng, phương vị, cự ly) tại đúng thời điểm mô phỏng.
- **Tab 2 — Tham luận & Tài liệu:** đăng tải, tải về, xóa các file đính kèm
  Word (.doc/.docx), Excel (.xls/.xlsx), PDF (.pdf), PowerPoint (.ppt/.pptx),
  tối đa 50 MB/file. File lưu tại `webapp/data/uploads/`, metadata tại
  `webapp/data/thamluan.db`.

## Chạy

```bash
cd ~/workspace/leo_coord
.venv/bin/pip install -e ".[dev]" fastapi "uvicorn[standard]" python-multipart
.venv/bin/uvicorn webapp.backend.app:app --host 0.0.0.0 --port 8000
```

Mở trình duyệt: http://localhost:8000 — tài liệu API tự động: http://localhost:8000/docs

Bản đồ 3D dùng thư viện CesiumJS 1.118 qua CDN (cần mạng khi mở trang); nếu không
tải được CDN, các chức năng tính toán vẫn hoạt động bình thường. Ảnh nền Esri/OSM/Carto
và địa hình ArcGIS là dịch vụ công cộng miễn phí, cần mạng để tải tile.

## Cấu trúc

- `backend/app.py` — FastAPI: `/api/assess`, `/api/tracks`, `/api/coverage-map`,
  `/api/docs` (GET/POST), `/api/docs/{id}/download`, `/api/docs/{id}` (DELETE)
- `frontend/` — `index.html`, `styles.css`, `app.js` (Three.js)
- `data/` — uploads + SQLite (tạo tự động khi chạy)
