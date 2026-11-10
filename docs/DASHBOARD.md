# Giao diện xem sự kiện bằng Streamlit

**Giao diện gọn 05/11/2026:** màn hình chính mặc định chỉ hiện nghi vượt đèn, gồm một ô **Tổng lượt nghi vượt đèn**, tìm biển số, lọc **Tất cả / Đỏ / Vàng** và danh sách bấm xem chi tiết. Đã bỏ loại xe, JSON và các ô thống kê trùng. **Cài đặt** chứa nguồn dữ liệu và lọc ngày; **Nhật ký kiểm tra → Xem tất cả sự kiện** dùng để xem xanh/UNKNOWN và bản ghi cũ. Phân trang chỉ xuất hiện khi quá 25 lượt, ở cuối danh sách; CSV nằm trong **Xuất dữ liệu**.

Mỗi dòng có biển số, thời gian và kết quả. Bấm vào dòng để mở hộp **Chi tiết vi phạm**: ảnh tại vạch, biển số, thời gian, màu đèn. Ảnh gốc và ảnh xe nằm trong mục mở rộng. Đóng bằng dấu X để chọn lượt khác. Tổng đỏ + vàng được tính theo bộ lọc hiện tại; dữ liệu cũ giữ nguyên kết quả đã lưu.

**Bổ sung 03/11/2026:** đã có cột biển số/trạng thái OCR, tìm theo biển không phân biệt hoa thường, xuất CSV và ảnh cắt biển ở chi tiết. Chọn **Video biển số** để xem dữ liệu pipeline mẫu; nhập `29A33185` để xem 1 sự kiện có OCR ổn định. Cách tạo lại dữ liệu và giới hạn ở bước 5 trong [BIEN_SO.md](BIEN_SO.md). Những mục ghi “chưa có OCR” bên dưới là mô tả mốc 02/11.

Chạy PowerShell tại thư mục gốc dự án:

```powershell
.\.venv\Scripts\python.exe -m streamlit run python/dashboard.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Mở `http://127.0.0.1:8501` bằng trình duyệt trên laptop. Giữ PowerShell mở; Ctrl+C để dừng. Nếu cổng bận, thêm `--server.port 8502` rồi mở địa chỉ cổng 8502.

Đây là giao diện local cho laptop, chưa xuất bản hoặc cung cấp tài khoản qua mạng.

## Xem ngay dữ liệu mẫu

1. Nếu chưa có dữ liệu, mở PowerShell khác chạy `.\.venv\Scripts\python.exe python/storage_demo.py`.
2. Trong thanh bên, mở **Cài đặt → Chọn dữ liệu → Demo lưu trữ**.
3. Bấm vào một dòng trong danh sách để mở **Chi tiết vi phạm** và xem ảnh bằng chứng.
4. Ba ảnh gồm ảnh gốc, ảnh có khung và ảnh cắt xe. Cảnh báo trên trang xác định rõ dữ liệu thử.

**Dữ liệu chạy thật** đọc `data/traffic.db`; **Video mẫu** đọc `data/demos/storage_pipeline/traffic.db`. Có thể chọn **Đường dẫn khác** để đọc SQLite khác cùng schema của dự án. Trang không tự tạo dữ liệu hoặc database mới.

## Chức năng

- Một ô tổng nghi vượt đèn đỏ + vàng theo bộ lọc.
- Tìm riêng biển số, không phân biệt hoa/thường; lọc một lần theo Tất cả / Đỏ / Vàng. Lọc ngày và chọn nguồn nằm trong Cài đặt.
- Nhật ký kiểm tra cho phép xem mọi sự kiện và lọc theo loại ghi nhận, gồm chưa xác minh khi mất MQTT.
- Ngày theo phần ngày trong timestamp đã lưu (hiện dùng giờ Bangkok/Vietnam); giá trị ngày mặc định của giao diện dùng Asia/Bangkok.
- Danh sách có phân trang ở cuối khi quá 25 lượt; tổng nghi vượt đèn tính trên toàn bộ kết quả lọc, không chỉ trang hiện tại.
- Tải CSV UTF-8 có BOM cho **trang hiện tại**, không phải toàn bộ database.
- Bấm vào dòng sự kiện để xem thông tin và ảnh trong hộp chi tiết; không hiển thị JSON. Không có ảnh hoặc mất file thì thông báo rõ; không tự tạo lại bằng chứng.
- Nhấn **Làm mới dữ liệu** sau khi chương trình camera thêm sự kiện. Trang không tự chạy camera hay điều khiển LED.
- Biển số và ảnh lấy từ sự kiện đã lưu; thiếu biển thì hiển thị Chưa đọc được. Màu đèn trong chi tiết là màu gắn với sự kiện, không phải bộ theo dõi màu đèn trực tiếp.

## Giới hạn

Giao diện mở SQLite bằng chế độ chỉ đọc và không có nút xóa/sửa sự kiện. Có thể chạy đồng thời với chương trình ghi SQLite, nhưng khi database bị khóa lâu sẽ báo lỗi để thử làm mới. Dữ liệu demo được lưu riêng; lựa chọn đường dẫn tùy chỉnh cần người dùng kiểm tra nguồn. Chưa làm đăng nhập, cloud, đọc nhiều camera, xét duyệt sự kiện hoặc chỉnh OCR.

AppTest kiểm tra tương tác Streamlit không thay thế việc người dùng mở trình duyệt để kiểm tra bố cục, tải CSV và ảnh thực tế.

Kiểm thử ngày 02/11/2026: 6 bài dashboard đạt, gồm filter/ngày local, phân trang/thống kê, tìm kiếm có tham số, chỉ đọc và Streamlit AppTest. Tổng 48 bài đạt. Máy chủ local thử trả HTTP 200, health OK; đã dừng máy chủ kiểm thử sau khi xác nhận. Chạy lại lệnh đầu tài liệu để mở giao diện. `pip check` không thấy xung đột; thư viện Streamlit có cảnh báo deprecation của pandas khi vẽ chart, không ảnh hưởng kết quả kiểm thử.
