# Thử vượt vạch và đèn MQTT giả lập

Không cần ESP32 đèn hoặc LED cho bài thử này. ESP32-CAM quay màn hình đang phát video; một bảng điều khiển trên laptop gửi màu đèn giả lập qua MQTT. Giữ nguyên Mosquitto/MQTT, ByteTrack và logic phân loại hiện có; không nạp firmware.

## Chạy bằng hai lệnh

PowerShell ở thư mục gốc dự án, dùng hai terminal:

```powershell
# Phát video nguồn, chậm 0.5 lần và lặp lại
.\.venv\Scripts\python.exe -u -B python/play_plate_video.py --speed 0.5

# Mở bảng đèn giả lập và camera/chọn vạch
.\.venv\Scripts\python.exe -u -B python/traffic_demo.py --camera-url http://10.82.212.69/capture --auto-start
```

Đã chạy hai cửa sổ này trên máy trong phiên làm việc. Địa chỉ camera có thể đổi theo Wi-Fi; điền lại trong bảng điều khiển rồi nhấn **Mở camera / chọn lại vạch**. Cần Mosquitto đã cài trên máy (hiện có tại `C:/Program Files/mosquitto/mosquitto.exe`). Bộ chạy tự tạo broker riêng chỉ nghe loopback trên cổng tạm, không dùng cổng/tài khoản broker LAN của ESP32.

## 1. Căn camera và đặt vạch

1. Hướng camera vào **video ô tô nguồn**, không quay cửa sổ preview nhận diện. Ảnh camera kiểm tra ban đầu trong phiên này chỉ thấy trần/đèn sáng, chưa phải cảnh xe.
2. Đóng các tab/cửa sổ khác đang đọc stream ESP32-CAM. Kết nối camera thật trong phiên có lúc trả ảnh 320×240, có lúc timeout; cần nguồn và Wi-Fi ổn định. Có thể tăng VGA trên trang camera nếu vẫn giữ tốc độ phù hợp.
3. Trong cửa sổ chọn vạch, hình camera cập nhật liên tục trước click đầu tiên. Căn góc đến khi thấy xe rõ; có thể nhấn Space ở cửa sổ video nguồn để tạm dừng lúc căn.
4. Click hai đầu vạch **từ trái sang phải** trên mặt đường trong ảnh. Click đầu tiên đóng băng hình; R xóa các điểm và tiếp tục xem camera. Enter xác nhận, Q hủy.
5. Đặt vạch nơi xe sẽ đi qua sau khi bắt đầu theo dõi, không đặt ngay trên xe đã qua. Mặc định xét chiều từ phía trên xuống phía dưới vạch.

Điểm theo dõi là giữa cạnh dưới bbox xe, không phải vùng biển số. Không cần train model cho vạch.

## 2. Kiểm tra xanh trước

- Bảng điều khiển khởi động màu **Xanh**. Chờ ít nhất 2 giây sau khi kết nối/màu đổi để có lịch sử heartbeat.
- Cho xe đi qua vạch: cần có crossing, màu GREEN và `no_red_light_evidence` nếu dữ liệu đèn liên tục.
- Nếu chỉ muốn kiểm tra vạch nhanh, bỏ chọn **Đọc biển số** trước khi mở camera; không yêu cầu có OCR mới ghi sự kiện qua vạch.

## 3. Thử đỏ và mất trạng thái

| Thao tác | Kết quả mong đợi khi xe đi đúng chiều qua vạch |
| --- | --- |
| Nhấn Đỏ, chờ >=2 giây rồi cho xe qua | RED / nghi vượt đèn đỏ trong bài mô phỏng |
| Nhấn Xanh, chờ >=2 giây rồi cho xe qua | GREEN / không có bằng chứng đèn đỏ |
| Nhấn Ngừng gửi, chờ hết timeout 1.5 giây | UNKNOWN / chưa xác minh |
| Xe chưa đổi phía qua vạch | Không tạo crossing |

Đổi màu sát lúc xe qua vạch có thể cho **chưa xác minh** vì chính sách cần một màu liên tục và khoảng dự phòng 0.5 giây. Đây là hành vi bảo thủ, không ép thành đỏ. Không dùng màu đèn nhìn thấy bên trong video làm trạng thái MQTT.

Video lặp lại/cắt cảnh không phải chuyển động liên tục ngoài thực tế. Khi kiểm tra chính xác một lượt, có thể Q dừng tracking, đưa video về trước khi xe tới vạch, rồi mở lại camera/chọn vạch. Không coi thay đổi cảnh đột ngột hoặc ID nhảy là bằng chứng vi phạm.

## 4. Xem bản ghi

- Mở Streamlit như trước và chọn nguồn **Camera + đèn giả lập**.
- Chọn **Tất cả sự kiện** để thấy cả xanh/UNKNOWN; chế độ **Nghi vi phạm** chỉ thấy các bản ghi nghi đỏ.
- Nhấn **Làm mới dữ liệu** sau khi xe qua vạch.
- Database: `data/demos/live_simulation/traffic.db`.
- Ảnh: `data/demos/live_simulation/evidence/`; log crossing và camera/broker cùng vùng demo.
- Mọi bản ghi đều có `simulation: true`, ảnh có nhãn SIMULATION, giao diện cảnh báo dữ liệu thử. Không ghi vào `data/traffic.db` thật; ảnh quét biển đơn lẻ trong `data/plates/` không được nhập thành vi phạm.

Q ở cửa sổ camera để dừng tracking; đóng bảng đèn để dừng publisher và broker do bảng đó tạo. Muốn chọn vạch mới, Q cửa sổ camera cũ rồi nhấn nút mở camera lại. Đóng bảng khi camera còn chạy sẽ kết thúc tiến trình camera; nên Q trước để đóng bình thường.

Nếu camera mất ảnh tạm thời, chương trình thử đọc lại tối đa 3 lần. Lịch sử crossing/OCR được xóa tại chỗ mất ảnh, tránh suy ra xe đi qua vạch trong đoạn không quan sát được. Khi hết lượt thử, kiểm tra camera rồi bấm mở lại; xem `camera_<phiên>.log` nếu chưa có hình.

## Kiểm thử thực tế phần mềm ngày 03/11/2026

- 82 kiểm thử toàn repo đạt trước khi thêm xử lý mất ảnh; thêm 1 bài hồi quy mất ảnh camera đạt sau đó. Kiểm thử nguồn đèn dùng broker Mosquitto thật: đổi xanh/đỏ/vàng, hết heartbeat về UNKNOWN, tự dọn broker riêng.
- Chạy YOLO/ByteTrack + HTTP camera giả lập từ video Việt Nam + MQTT thật trong ba lượt: xanh có 1 crossing `no_red_light_evidence`, đỏ có 1 crossing `suspected_red_light`, ngừng gửi có 1 crossing `unverified`. Tất cả đều lưu `simulation: true` vào database riêng.
- Báo cáo kiểm thử nằm trong `data/demos/live_simulation_validation/report.json`; đây là kiểm thử HTTP/video fixture, không thay thế camera vật lý quay màn hình.
- Camera vật lý đã trả ảnh nhưng chưa xác nhận người dùng đã căn camera vào video, chọn vạch và hoàn tất ba tình huống. Bộ điều khiển và video đã được mở để thực hiện bước này.

Đây là bài kiểm thử phần mềm với đèn giả lập, chưa xác nhận hệ thống đèn ESP32 thật hoặc độ trễ phơi sáng/MQTT của mô hình hoàn chỉnh.
