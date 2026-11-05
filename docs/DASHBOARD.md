# Giao diện xem sự kiện bằng Streamlit

**Bổ sung 03/11/2026:** đã có cột biển số/trạng thái OCR, tìm theo biển không phân biệt hoa thường, xuất CSV và ảnh cắt biển ở chi tiết. Chọn **Video biển số** để xem dữ liệu pipeline mẫu; nhập `29A33185` để xem 1 sự kiện có OCR ổn định. Cách tạo lại dữ liệu và giới hạn ở bước 5 trong [BIEN_SO.md](BIEN_SO.md). Những mục ghi “chưa có OCR” bên dưới là mô tả mốc 02/11.

Chạy PowerShell tại thư mục gốc dự án:

```powershell
.\.venv\Scripts\python.exe -m streamlit run python/dashboard.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Mở `http://127.0.0.1:8501` bằng trình duyệt trên laptop. Giữ PowerShell mở; Ctrl+C để dừng. Nếu cổng bận, thêm `--server.port 8502` rồi mở địa chỉ cổng 8502.

Đây là giao diện local cho laptop, chưa xuất bản hoặc cung cấp tài khoản qua mạng.

## Xem ngay dữ liệu mẫu

1. Nếu chưa có dữ liệu, mở PowerShell khác chạy `.\.venv\Scripts\python.exe python/storage_demo.py`.
2. Trong thanh bên của giao diện, chọn **Demo lưu trữ**.
3. Xem bảng, chọn một sự kiện trong mục **Chi tiết và ảnh bằng chứng**.
4. Ba ảnh gồm ảnh gốc, ảnh có khung và ảnh cắt xe. Cảnh báo trên trang xác định rõ dữ liệu thử.

**Dữ liệu chạy thật** đọc `data/traffic.db`; **Video mẫu** đọc `data/demos/storage_pipeline/traffic.db`. Có thể chọn **Đường dẫn khác** để đọc SQLite khác cùng schema của dự án. Trang không tự tạo dữ liệu hoặc database mới.

## Chức năng

- Thống kê tổng sự kiện, nghi vượt đèn đỏ, chưa xác minh và không có bằng chứng đỏ theo bộ lọc.
- Lọc kết quả phân loại, loại xe, màu đèn, ngày ghi nhận; tìm chuỗi trong ID sự kiện/ID xe/nguồn.
- Ngày theo phần ngày trong timestamp đã lưu (hiện dùng giờ Bangkok/Vietnam); giá trị ngày mặc định của giao diện dùng Asia/Bangkok.
- Bảng có phân trang; số liệu thống kê/biểu đồ tính trên toàn bộ kết quả lọc, không chỉ trang hiện tại.
- Tải CSV UTF-8 có BOM cho **trang hiện tại**, không phải toàn bộ database.
- Chọn sự kiện để xem ba ảnh và JSON chi tiết. Không có ảnh hoặc mất file thì thông báo rõ; không tự tạo lại bằng chứng.
- Nhấn **Làm mới dữ liệu** sau khi chương trình camera thêm sự kiện. Trang không tự chạy camera hay điều khiển LED.
- Không có OCR/biển số ở mốc này, không tạo kết quả biển số giả. Màu đèn hiển thị là màu gắn với sự kiện đã lưu, không phải bộ theo dõi màu đèn trực tiếp.

## Giới hạn

Giao diện mở SQLite bằng chế độ chỉ đọc và không có nút xóa/sửa sự kiện. Có thể chạy đồng thời với chương trình ghi SQLite, nhưng khi database bị khóa lâu sẽ báo lỗi để thử làm mới. Dữ liệu demo được lưu riêng; lựa chọn đường dẫn tùy chỉnh cần người dùng kiểm tra nguồn. Chưa làm đăng nhập, cloud, đọc nhiều camera, xét duyệt sự kiện hoặc chỉnh OCR.

AppTest kiểm tra tương tác Streamlit không thay thế việc người dùng mở trình duyệt để kiểm tra bố cục, tải CSV và ảnh thực tế.

Kiểm thử ngày 02/11/2026: 6 bài dashboard đạt, gồm filter/ngày local, phân trang/thống kê, tìm kiếm có tham số, chỉ đọc và Streamlit AppTest. Tổng 48 bài đạt. Máy chủ local thử trả HTTP 200, health OK; đã dừng máy chủ kiểm thử sau khi xác nhận. Chạy lại lệnh đầu tài liệu để mở giao diện. `pip check` không thấy xung đột; thư viện Streamlit có cảnh báo deprecation của pandas khi vẽ chart, không ảnh hưởng kết quả kiểm thử.
