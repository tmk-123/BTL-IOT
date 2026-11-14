# Lưu trữ cloud trên VPS

Triển khai đêm 14–15/11/2026 (giờ Việt Nam). Người dùng xác nhận PostgreSQL + thư mục ảnh + API HTTPS trên VPS hiện có.

## Luồng dữ liệu

ESP32-CAM và MQTT tiếp tục gửi về Python trên laptop. `EventStore` vẫn ghi SQLite và ảnh local như trước. `python/cloud_sync.py` chạy riêng, chỉ đọc `data/traffic.db`, gửi metadata và ảnh tới VPS. Không chạy AI hay chuyển MQTT lên VPS.

- API: `https://jenkins.tienichnhanong.com/iot-api`.
- Kiểm tra dịch vụ: `/health` (không trả dữ liệu sự kiện).
- PostgreSQL: database `traffic_iot`, role hệ thống `traffic-iot`, xác thực peer qua Unix socket.
- Ảnh VPS: `/var/lib/traffic-iot/evidence/`, không phục vụ file công khai.
- Mã API: `/opt/traffic-iot/api.py`; systemd: `traffic-iot.service`; chỉ nghe `127.0.0.1:8765`.
- Caddy chuyển riêng `/iot-api/*` tới API; các đường dẫn Jenkins hiện tại được giữ lại. Cấu hình Caddy trước thay đổi có bản sao trong `/etc/caddy/`.

## Dashboard trên điện thoại và máy tính — 15/11/2026

Mở **https://jenkins.tienichnhanong.com/traffic/** bằng Chrome, Safari hoặc trình duyệt điện thoại. Trình duyệt hiện hộp đăng nhập; tài khoản là `giamsat`, mật khẩu được lưu riêng trong `data/dashboard_access.txt` trên laptop. Không gửi file này vào Git hoặc chia sẻ công khai. Bản cấu hình truy cập máy chủ ở `/etc/traffic-iot/dashboard_access.json` (quyền 600).

Sau đăng nhập có thể tìm biển số, lọc đỏ/vàng, xem chi tiết và ảnh, lọc ngày trong Cài đặt, mở Nhật ký kiểm tra để xem mọi sự kiện, phân trang và tải CSV của trang đang xem. Bấm nút mở thanh bên trên điện thoại để thấy Làm mới dữ liệu, Cài đặt và Nhật ký kiểm tra. Trang đọc dữ liệu đã đồng bộ trên VPS; laptop tắt vẫn xem được dữ liệu cũ. Muốn có sự kiện mới thì laptop và tiến trình nhận diện/đồng bộ phải hoạt động. Nhấn **Làm mới dữ liệu** để cập nhật danh sách.

Dashboard dùng chung mã `python/dashboard.py` với chế độ cloud qua biến môi trường; bản local giữ lựa chọn SQLite và dữ liệu demo. Bản VPS không hiện đường dẫn SQLite hay bộ chọn nguồn local. Giao diện có CSS cho màn hình nhỏ và các ô Streamlit tự xếp dọc khi hẹp.

### Bảo vệ truy cập

- Caddy yêu cầu HTTP Basic Authentication qua HTTPS trên toàn bộ `/traffic/*`, bao gồm static assets, media, tải CSV và WebSocket. Mật khẩu lưu dưới dạng hash trong Caddy; không đưa mật khẩu vào URL.
- Đây là một tài khoản xem chung cho nhóm, chưa có quản lý nhiều tài khoản, phân quyền cá nhân hoặc nút đăng xuất riêng. Trình duyệt có thể nhớ đăng nhập trong phiên; trên thiết bị dùng chung nên dùng cửa sổ riêng tư và đóng toàn bộ cửa sổ đó sau khi xem.
- Dashboard chạy bằng user `traffic-dashboard`, chỉ nghe loopback `127.0.0.1:8501`, không mở cổng Streamlit ra Internet.
- Khóa `IOT_READ_TOKEN` riêng chỉ đọc API/ảnh; không gửi ra trình duyệt và không được dùng để upload. Khóa ghi của laptop được giữ nguyên.
- File môi trường: `/etc/traffic-iot/dashboard.env`, systemd `traffic-dashboard.service`, mã trên VPS `/opt/traffic-iot/dashboard/`. Môi trường Python giao diện tách khỏi API và không cài YOLO/OCR trên VPS.

Kiểm tra hoặc khởi động lại trên VPS:

```sh
systemctl status traffic-dashboard --no-pager
journalctl -u traffic-dashboard -n 30 --no-pager
systemctl restart traffic-dashboard
```

Đổi mật khẩu cần cập nhật `/etc/traffic-iot/dashboard_access.json`, tạo hash mới bằng `caddy hash-password`, cập nhật khối auth của `/traffic/*`, chạy `caddy validate` rồi reload Caddy. Script cấu hình chỉ tạo tài khoản ban đầu, không tự thay mật khẩu/hash trên mỗi lần chạy.

## Chạy đồng bộ

Thông tin kết nối tại `data/cloud_sync.json`, bị Git bỏ qua và giới hạn quyền đọc. Không đưa nội dung file này vào báo cáo, chat hay Git. Token máy chủ ở `/etc/traffic-iot/api.env` và `/etc/traffic-iot/client.json`, quyền 600.

Chạy một lượt từ thư mục dự án:

```powershell
.\.venv\Scripts\python.exe python/cloud_sync.py --once
```

Chạy liên tục ở cửa sổ hiện tại:

```powershell
.\.venv\Scripts\python.exe python/cloud_sync.py
```

Cài/bật tác vụ nền tự chạy khi đăng nhập Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/install_cloud_sync.ps1
```

Tác vụ `BTL-IoT-CloudSync` chạy khi laptop bật, người dùng đăng nhập và không bị sleep; kiểm tra log tại `data/cloud_sync.log` (xoay vòng). Dừng bằng `Stop-ScheduledTask -TaskName BTL-IoT-CloudSync`; vô hiệu hóa tự chạy bằng `Disable-ScheduledTask -TaskName BTL-IoT-CloudSync`.

`data/cloud_sync.db` là sổ xác nhận gửi thành công, độc lập SQLite chính. Xóa sổ này làm gửi lại nhưng API chống trùng theo event_id; không cần xóa để khắc phục mất mạng. Không chạy nhiều bản đồng bộ thủ công đồng thời với tác vụ nền.

## Tính nhất quán và bảo vệ dữ liệu

- Chu kỳ mặc định 15 giây sau khi kết thúc mỗi lượt quét; mạng lỗi giữ nguyên dữ liệu và thử lại.
- Chỉ xác nhận local sau khi API đã commit PostgreSQL. Mất phản hồi sau commit thì gửi lại an toàn.
- Cùng event_id và nội dung trả thành công mà không thêm bản ghi. Cùng ID nhưng nội dung khác trả 409 để kiểm tra thủ công.
- Ảnh thiếu/ngoài thư mục cấu hình/quá 5 MiB không được đánh dấu hoàn tất; xem log và khôi phục ảnh local trước khi gửi lại.
- API giới hạn request 32 MB; JPEG tối đa 5 MiB/ảnh. Ảnh lưu theo hash ID và hash nội dung, không dùng tên đường dẫn từ laptop.
- Token nằm trong Authorization header; API đọc dữ liệu và ảnh cũng yêu cầu token. Khóa laptop có quyền đọc/ghi, khóa dashboard riêng chỉ đọc; chưa có phân quyền nhiều người hay quản lý thiết bị.
- URL camera và đường dẫn ảnh local không được đưa vào metadata cloud; source đổi thành `edge-camera`. Bản ghi local giữ nguyên.
- API lưu ảnh trước commit database; mất điện có thể để lại file ảnh mồ côi, nhưng không đánh dấu đồng bộ thành công trước commit. Chưa có công cụ dọn ảnh mồ côi.

## Sao lưu và vận hành

`traffic-iot-backup.timer` chạy hằng ngày khoảng 03:00 UTC (10:00 Việt Nam), lưu PostgreSQL dump và toàn bộ ảnh tại `/var/backups/traffic-iot/`, giữ khoảng 7 ngày. Đây là bản khôi phục trên cùng VPS, chưa chống được mất toàn bộ VPS/ổ đĩa. Laptop vẫn giữ bản dữ liệu gốc; nên bổ sung bản sao ngoài VPS khi vận hành lâu dài.

Kiểm tra trên VPS:

```sh
systemctl status traffic-iot --no-pager
journalctl -u traffic-iot -n 30 --no-pager
systemctl list-timers traffic-iot-backup.timer
```

Khôi phục cần giải nén snapshot, dùng `pg_restore` vào database thử và đối chiếu đường dẫn ảnh trước khi thay database đang chạy. Chưa cung cấp tự động khôi phục đè dữ liệu.

## Phạm vi

Đã triển khai lưu trữ, đồng bộ và dashboard HTTPS có đăng nhập để xem trên điện thoại/máy tính. Chỉ đồng bộ nguồn `data/traffic.db` được cấu hình, không tự nhập nguồn `data/demos/`. Camera, MQTT và AI tiếp tục chạy tại laptop.

## Kết quả xác minh 15/11/2026

- Đồng bộ 85/85 sự kiện local, không lỗi; xác nhận PostgreSQL có 85 sự kiện và 318 file ảnh có hash khớp nội dung.
- Thử API thực qua HTTPS: health, từ chối thiếu token, ghi sự kiện, gửi trùng không thêm bản ghi, từ chối cùng ID khác nội dung, tải ảnh có token, từ chối ảnh sai. Sự kiện thử được dọn sau kiểm tra.
- Jenkins `/login` vẫn trả HTTP 200 sau khi thêm route.
- Tác vụ Windows `BTL-IoT-CloudSync` đang chạy; các chu kỳ sau báo không còn dữ liệu chờ.
- Đã tạo snapshot đầu tiên khoảng 16 MB gồm database dump và ảnh, bật timer hằng ngày. Chưa thử khôi phục toàn bộ snapshot sang database khác.
- Kiểm thử mất mạng/gửi lại dùng lỗi mạng giả lập trong unit test, chưa ngắt Internet vật lý khi chạy camera.
- Dashboard VPS đọc 85 sự kiện, tổng nghi vượt đèn 25 tại thời điểm kiểm tra. Streamlit AppTest dùng API thật kiểm tra bộ lọc màu, tìm kiếm, hộp chi tiết/ảnh và nhật ký; kiểm tra HTTP xác nhận từ chối thiếu/sai mật khẩu và WebSocket nâng cấp thành công khi đăng nhập.
- Bổ sung 5 kiểm thử client/UI cloud và chạy lại 13 kiểm thử dashboard local, đều đạt. Chưa xác minh trực quan trong Chrome hoặc điện thoại thật: công cụ Computer Use dừng vì không xác định được URL hiện tại đủ chắc chắn để kiểm tra chính sách.

Tài liệu chính thức: [Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [Caddy handle_path](https://caddyserver.com/docs/caddyfile/directives/handle_path), [Caddy request_body](https://caddyserver.com/docs/caddyfile/directives/request_body).
