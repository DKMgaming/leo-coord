# Ánh xạ trường dữ liệu leo_coord ↔ Appendix 4 / SpaceCap / SNS

Tài liệu này căn chỉnh CSDL phối hợp quốc gia của `leo_coord` (Tab 3 + CLI)
với khung dữ liệu hồ sơ vệ tinh của ITU — để số liệu quản lý nội bộ chuyển
sang quy trình chính thức (SpaceCap → BR) không bị lệch khái niệm.

> Phạm vi: ánh xạ ở mức khái niệm/trường dữ liệu. Mã mục chi tiết của
> Appendix 4 và cấu trúc SNS chuẩn nằm trong Preface của BR IFIC (Section III)
> — đối chiếu bản hiện hành khi làm hồ sơ thật.

## 1. Ánh xạ trường hồ sơ (bảng `filings`)

| Trường leo_coord | Khái niệm Appendix 4 / SNS | Vai trò trong SpaceCap | Ghi chú |
|---|---|---|---|
| `network_name` | Tên mạng vệ tinh (satellite network) | Định danh thông báo | Duy nhất trong CSDL nội bộ |
| `administration` | Cơ quan thông báo (notifying administration), mã ADM | Thông tin chung của notice | VD: VTN |
| `operator` | Cơ quan khai thác / operating agency | Thông tin liên hệ khai thác | |
| `sns_id` | SNS Notice ID | Mã định danh hồ sơ trên SNS / ITU Space Explorer | Tra cứu trực tiếp trên Space Explorer bằng ID này |
| `notice_type` | Loại thông báo: API/A, CR/C, CR/D, CR/E, CR/F, NOTIFICATION... | Quyết định mẫu nhập liệu trong SpaceCap | |
| `ific_no` | Số BR IFIC nơi đăng Special Section/Part tương ứng | Tham chiếu ấn phẩm chính thức | VD: 3082 |
| `receipt_date` | Ngày BR nhận hồ sơ (date of receipt) | Mốc tính các thời hạn luật định | Khác ngày API bên dưới |
| `api_date` | Ngày thông tin công bố trước (API) | Giai đoạn Section I, Article 9 | |
| `biu_deadline` | Hạn đưa vào sử dụng (bringing into use, No. 11.44/11.48) | Đầu vào tính mốc Res 35 | leo_coord tự đánh giá 10/50/100% |
| `status` | Giai đoạn xử lý: API → COORDINATION → NOTIFICATION → MIFR (BIU là mốc sự kiện) | Theo dõi vòng đời hồ sơ | Tập giá trị cố định trong `database.VALID_STATUS` |
| `bands` | Băng tần của mạng (tổng hợp từ các nhóm tần số App4) | Chi tiết nằm ở cấp assignment/group trong SpaceCap | leo_coord chỉ lưu dạng tổng hợp |
| `n_sats_filed` | Số vệ tinh trong hồ sơ NGSO | Thuộc dữ liệu đặc tính quỹ đạo | NGSO: kèm `alt_km`, `inc_deg` |
| `alt_km`, `inc_deg` | Đặc tính quỹ đạo danh định (độ cao, nghiêng) | Phần orbital characteristics của notice NGSO | GSO: độ cao ~35.786 km, nghiêng ~0 |

## 2. Quy trình chính thức (để định vị vai trò của leo_coord)

1. **SpaceCap** — thu thập notice điện tử (dữ liệu Appendix 4).
2. **BRSIS-Validation** — kiểm tra tính hợp lệ của notice ngay trong SpaceCap
   trước khi gửi.
3. **GIMS** — dữ liệu đồ họa kèm theo (biểu đồ bức xạ ăng-ten, vùng dịch vụ,
   đường biên phối hợp). leo_coord **không** lưu dữ liệu này; bản đồ 3D và lớp
   phủ sóng của leo_coord chỉ phục vụ sàng lọc nội bộ.
4. **BR xử lý & công bố** trên BR IFIC (Space): API/A → CR/C (+ CR/D, CR/E,
   CR/F) → Part I-S/II-S/III-S; kết luận kiểm tra (findings) theo các điều
   khoản liên quan của Article 11.
5. **SpaceCom** — cơ quan quản lý gửi/ghi nhận góp ý đối với các Special
   Section (CR/C, API/A...) trong thời hạn quy định; các mốc này nên được ghi
   vào `coordination_cases` của leo_coord để theo dõi nội bộ.
6. **ITU Space Explorer / SNS** — tra cứu trạng thái hồ sơ (cần tài khoản
   TIES của cơ quan thành viên); `sns_id` trong leo_coord là khóa tra cứu.

## 3. Đối chứng kết quả phối hợp (bảng `cross_checks`)

Mỗi bản ghi đối chứng gồm: kết quả sàng lọc của leo_coord (`our_result`),
nguồn chính thức (`official_source` — số BR IFIC, ngày chạy SpaceQry/BR-SIS),
kết luận chính thức (`official_result`) và mức khớp (`agreement`:
KHOP / LECH / CHUA_RO). Mọi trường hợp LECH phải được phân tích nguyên nhân
và ghi vào `notes` — đây là cơ chế hiệu chuẩn độ tin cậy của tầng sàng lọc,
không thay đổi nguyên tắc: **kết luận chính thức thuộc về BR**.
