# Camera → Python

Giữ firmware camera đã test trên board. Khi cần nạp lại, mở `firmware/testCamera/testCamera.ino` trong Arduino IDE và giữ thiết lập board đã test (model hiện chọn AI Thinker).

Wi-Fi chuyển sang `secrets.h` riêng ở mỗi sketch, giữ thông tin cũ trên máy và bỏ qua bởi Git. Trên máy khác, copy `secrets.example.h` thành `secrets.h` rồi điền Wi-Fi 2,4 GHz. Không nạp testWiFi khi cần stream camera.

Mở Serial Monitor 115200, reset camera và lấy IP từ dòng Camera Ready. Laptop và camera phải cùng mạng, cho phép kết nối giữa các thiết bị. Mở thử `http://<IP_CAMERA>:81/stream`, rồi đóng tab stream trước khi chạy Python để giảm tải.

## Cài đặt và chạy

PowerShell tại thư mục gốc dự án:

```powershell
cd D:\Ki1_4\IOT\BTL
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe python/camera_viewer.py --url http://192.168.1.10:81/stream
```

Thay IP ví dụ bằng IP thật. Không cần activate môi trường khi gọi trực tiếp Python như trên.

- Click cửa sổ video để nhận phím.
- `S`: lưu ảnh JPG gốc vào `data/snapshots/`, không có chữ FPS chèn lên ảnh.
- `Q`, Escape, đóng cửa sổ hoặc Ctrl+C: thoát, giải phóng kết nối.
- Thêm `--output "D:\thu_muc_anh"` để đổi nơi lưu.
- FPS là tốc độ nhận/xử lý trên laptop, không đo độ trễ truyền hình.
- Mất stream: báo lỗi và thoát sau timeout đọc, cấu hình 5 giây; kiểm tra rồi chạy lại.

## Kiểm tra hoàn thành

1. Xem liên tục 5–10 phút, di chuyển vật để kiểm tra hình cập nhật.
2. Nhấn S vài lần, kiểm tra thông báo Saved và mở các ảnh JPG.
3. Nhấn Q, chạy lại để kiểm tra kết nối lại.
4. Tắt nguồn camera, kiểm tra chương trình báo mất stream.

Nếu không mở được: kiểm tra IP mới, nguồn, Wi-Fi, cổng 81 và đóng stream khác.
Nếu `/capture` vẫn trả ảnh nhưng `:81/stream` bị timeout, có thể tạm lấy từng ảnh liên tiếp:

```powershell
.\.venv\Scripts\python.exe python/camera_viewer.py --snapshot --url http://<IP_CAMERA>/capture
```

Chế độ này vẫn hỗ trợ S lưu ảnh và Q thoát, nhưng không phải stream MJPEG và không xác nhận stream đã hoạt động ổn định.
Firmware khởi động ở QVGA 320×240; chỉnh ánh sáng, góc quay và độ phân giải trên trang camera nếu cần. Bước này chưa bảo đảm chất lượng đọc biển số.

Chương trình hiện chưa có AI hoặc kết luận vi phạm. Bước tiếp theo là nhận diện xe.
