# Logic nghi vượt đèn đỏ

Chạy thử không cần camera, YOLO, ESP32 hoặc broker:

```powershell
.\.venv\Scripts\python.exe python/red_light_demo.py
```

Chương trình chạy 14 tình huống với vị trí xe và bản tin đèn giả lập theo cùng một trục thời gian. Mỗi dòng PASS nghĩa là kết quả đúng với tình huống đặt ra. Báo cáo có chi tiết sự kiện ở `data/demos/red_light_logic.json`. Demo này kiểm tra logic, chưa xác nhận nhận diện xe hay độ trễ của phần cứng thật.

## Điều kiện đánh dấu

Xe phải có ID theo dõi, điểm đáy khung xe chuyển từ trước vạch sang sau vạch và đi đúng chiều xét vi phạm. Đèn phải đỏ liên tục, bản tin còn hiệu lực trong toàn khoảng từ vị trí ổn định trước vạch đến frame xác nhận qua vạch, có thêm khoảng dự phòng `--timing-margin` (mặc định 0.5 giây) ở phía trước.

| Tình huống | Kết quả |
| --- | --- |
| Qua vạch đúng chiều, đỏ liên tục | `suspected_red_light` — nghi vượt đèn đỏ |
| Qua vạch, xanh/vàng liên tục | `no_red_light_evidence` — không có bằng chứng đỏ |
| Đèn đổi màu trong khoảng qua vạch hoặc thiếu/hết hạn dữ liệu | `unverified` — chưa xác minh |
| Qua vạch chiều ngược | `not_applicable_direction` — không xét chiều này |
| Dừng trước vạch, chỉ rung gần vạch | Không có sự kiện qua vạch |
| Xe đã ở sau vạch rồi đèn mới đỏ | Không tạo sự kiện mới chỉ vì đổi màu |
| Qua lúc xanh rồi đèn mới đỏ | Giữ kết quả lần qua lúc xanh, không gán lại thành vi phạm |
| Cùng xe tiếp tục đi sau một lần qua | Không ghi lặp cho mỗi frame |
| Đổi ID giữa hai phía vạch | Không suy diễn hai ID là cùng xe |

JSONL khi chạy camera bổ sung `assessment_reason` để biết vì sao có kết quả, ví dụ `continuous_red_during_crossing`, `opposite_direction`, `missing_stale_or_changing_light`, `no_light_source`. Khi không có sự kiện qua vạch thì không tạo bản ghi phân loại.

Chiều mặc định: vạch vẽ trái sang phải, xe đi trên xuống dưới. Đổi bằng `--violation-direction positive_to_negative` khi cần. Khi xe quay lại rồi thực hiện lượt qua mới, có thể ghi sự kiện mới; không bảo đảm chống trùng giữa các ID khác nhau.

## Chạy thật

Chuẩn bị broker và ESP32 đèn theo [MQTT_PYTHON.md](MQTT_PYTHON.md), kiểm tra camera gửi ảnh được, rồi chạy:

```powershell
.\.venv\Scripts\python.exe python/vehicle_detector.py --source http://10.82.212.69/capture --snapshot --select-line --mqtt-host 127.0.0.1 --mqtt-user laptop
```

Thay IP camera nếu đổi; nhập mật khẩu MQTT khi được hỏi. Bấm hai đầu vạch rồi Enter. Màn hình hiển thị Light, Crossings, Suspected red-light; log nằm trong `data/detections/`.

Chưa đồng bộ thời điểm phơi sáng camera và đồng hồ ESP32. Khoảng dự phòng 0.5 giây cần đánh giá thực tế, không bù được mọi độ trễ. Kết quả vẫn là nghi vi phạm để kiểm tra lại. Không tự đọc màu LED từ ảnh; màu đèn lấy từ MQTT.

## Bằng chứng kiểm thử

33 bài unittest đạt ngày 02/11/2026, gồm 5 bài mới cho chính sách phân loại (trong đó một bài chạy 14 tình huống), các bài vạch/đèn và tích hợp Mosquitto thật. Kiểm tra phần cứng và cảnh giao thông thật vẫn chưa hoàn thành. Không sửa firmware ở bước này.
