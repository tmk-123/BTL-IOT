# Nhật ký quyết định kỹ thuật

## Cập nhật 15/11/2026 — dashboard cloud có đăng nhập

- Người dùng xác nhận đưa dashboard lên VPS, đọc cloud, đăng nhập và dùng trên điện thoại.
- Giữ Streamlit và giao diện hiện tại thay vì viết lại frontend/app native, giảm phạm vi thay đổi và giữ chức năng local. Thêm API lọc, tổng hợp và phân trang trên PostgreSQL; dashboard nhận metadata/ảnh qua API bằng khóa chỉ đọc.
- Cân nhắc đăng nhập trong Streamlit hoặc bảo vệ tại reverse proxy. Chọn Caddy Basic Authentication qua HTTPS để bảo vệ đồng thời giao diện, media và WebSocket; một tài khoản xem chung cho giai đoạn demo. Đánh đổi: hộp đăng nhập do trình duyệt hiển thị, chưa có logout trong app hay tài khoản cá nhân.
- Dùng `/traffic/` trên domain HTTPS có sẵn, giữ route `/iot-api/` và Jenkins. Streamlit chạy user riêng, chỉ nghe loopback; không dùng khóa ghi của laptop và không mở cổng 8501 ra Internet.
- Bổ sung bố cục màn hình hẹp. Xem hướng dẫn và phạm vi xác minh tại [CLOUD.md](CLOUD.md).

## Cập nhật 14/11/2026 — lưu trữ cloud trên VPS đã có

- Người dùng xác nhận triển khai PostgreSQL + thư mục ảnh + API nhận đồng bộ, Caddy HTTPS, laptop tiếp tục nhận diện và lưu local khi mất mạng.
- Cân nhắc Supabase (database và object storage quản lý sẵn) hoặc VPS hiện có (tự vận hành). Chọn VPS vì đã truy cập được, còn tài nguyên và có Caddy HTTPS; đánh đổi là tự quản lý sao lưu, cập nhật và quyền truy cập.
- Giữ SQLite làm nguồn local, thêm tiến trình đồng bộ độc lập để mạng không chặn pipeline nhận diện. Sổ xác nhận SQLite riêng; retry theo event_id, không ghi đè cùng ID với nội dung khác.
- PostgreSQL lưu JSONB sự kiện và chỉ mục thời gian/biển số; ảnh content-addressed lưu ngoài database. API và ảnh yêu cầu bearer token; source URL và đường dẫn ảnh local được loại khỏi bản gửi.
- Dùng đường dẫn `/iot-api/` trên hostname HTTPS hiện có; chỉ thêm route Caddy, giữ catch-all Jenkins. Chưa triển khai dashboard điện thoại hay đưa MQTT/AI lên VPS.
- Sao lưu database và ảnh hằng ngày trên cùng VPS, giữ khoảng 7 ngày; chưa thay thế backup ngoài máy chủ. Xem [CLOUD.md](CLOUD.md).
- Xem xét object storage/managed database khi ảnh tăng nhiều, cần độ sẵn sàng cao, nhiều thiết bị hoặc vận hành dài hạn.

## Cập nhật 05/11/2026 — demo không lọc chiều

- Người dùng yêu cầu bỏ chiều vì demo một chiều. Đặt mặc định `expected_direction`/`--violation-direction` là `both`: mọi lần đổi phía qua đoạn vạch được phân loại theo màu đèn, không loại lượt vì hướng đi. Giữ kiểm tra crossing thật, dữ liệu đèn liên tục và timeout như trước.
- Bản ghi cũ giữ nguyên; không gán lại màu đèn hoặc xóa lịch sử. Khi đưa xe quay về qua vạch đỏ/vàng vẫn có thể ghi thêm lượt, nên nhấc xe về vị trí xuất phát ngoài khung hình nếu chỉ muốn minh họa một chiều.

## Cập nhật 05/11/2026 — tối ưu FPS camera snapshot

- Đo riêng camera/YOLO/OCR trên máy i7-6600U: HD quality 4 tạo JPEG khoảng 114 KB, tải ảnh khoảng 0,45 giây; VGA quality 12 còn khoảng 19 KB và 0,24 giây trong lần đo này. Giữ YOLO imgsz 640 vì 416/320 bỏ sót xe mô hình ở cả 8 ảnh đối chiếu.
- Thêm `--async-snapshot` tùy chọn để lấy ảnh đồng thời với xử lý AI, chỉ giữ ảnh mới nhất. Tránh bỏ qua lượt chạy YOLO/tracking hoặc dùng lại OCR cũ như quan sát mới. Timestamp theo thời điểm nhận ảnh; cờ gián đoạn không bị mất khi frame lỗi bị ảnh mới ghi đè, nên crossing/OCR vẫn reset sau mất ảnh.
- Giữ nguyên timeout MQTT và logic phân loại. Đổi độ phân giải cần chọn lại vạch. Tốc độ đo là thử nhanh trên cảnh/mạng hiện tại, không phải cam kết FPS hay độ chính xác.

## Cập nhật 05/11/2026 — gộp bộ đếm nghi vượt đèn đỏ/vàng

- Người dùng yêu cầu lượt qua lúc vàng cũng được tính và chọn một bộ đếm nghi vượt đèn chung cho đỏ/vàng. Giữ riêng `suspected_red_light` / `suspected_yellow_light` trong bản ghi để không mất màu đèn thực tế, thay cho phương án ghi vàng thành RED.
- Áp dụng cùng điều kiện crossing đúng chiều và một màu liên tục trong toàn khoảng xét có dự phòng 0,5 giây. Xanh không tăng bộ đếm; đổi màu, mất heartbeat hoặc thiếu lịch sử vẫn chưa xác minh. Đây là chính sách demo để xem lại bằng chứng, chưa mô hình hóa mọi ngoại lệ của đèn vàng.
- Camera hiển thị tổng đỏ + vàng; dashboard Nghi vi phạm và chỉ số tổng gồm cả hai. Sự kiện nghi vàng tự lưu ảnh như nghi đỏ. Không đổi nhãn dữ liệu cũ hoặc thay firmware/MQTT; chỉ lượt mới sau khi khởi động lại detector dùng chính sách mới.

Cập nhật: **01/11/2026**. File tổng hợp lựa chọn đã xác nhận và đề xuất còn mở; xem [định hướng dự án](DINH_HUONG_DU_AN.md) để theo dõi tiến độ.

Trạng thái: **BẮT BUỘC**, **ĐÃ CHỐT**, **ĐÃ THỐNG NHẤT HƯỚNG**, **ĐỀ XUẤT/CHƯA CHỐT**. Chốt hướng công nghệ không đồng nghĩa đã chọn phiên bản cụ thể hay đã kiểm thử thành công.

## D-00 — Arduino IDE: BẮT BUỘC

- Ghi nhận từ tài liệu dự án trước đây, giữ nguyên ngày 12/10/2026.
- Dùng Arduino IDE để viết, biên dịch và nạp firmware ESP32.
- Không chuyển công cụ nạp sang PlatformIO khi chưa có yêu cầu thay đổi từ người dùng.

## D-01 — MQTT cho trạng thái đèn: ĐÃ CHỐT

- Bổ sung 03/11: người dùng chưa có đèn, yêu cầu chạy mô phỏng. Thêm bảng Tk điều khiển đèn MQTT giả lập, broker chỉ loopback/cổng tạm/topic và device riêng cho mỗi phiên, không sửa broker LAN hoặc firmware. So với giả màu trực tiếp trong detector, cách này kiểm tra được luồng MQTT/heartbeat/UNKNOWN thật.
- `vehicle_detector.py --simulation` gắn cờ và nhãn lên ảnh, mặc định lưu vùng `data/demos/live_simulation`, từ chối database production. Dùng topic `demo/` hoặc device `simulation-` bắt buộc có cờ này. Giữ chặn MQTT realtime ghép video file; video chỉ được đưa qua HTTP trong bài fixture rõ ràng hoặc do camera thật quay màn hình.
- Bộ chọn vạch camera có cập nhật hình trực tiếp trước click đầu tiên, sau đó đóng băng để chọn hai đầu; R căn lại. Khi snapshot lỗi tạm thời, xóa lịch sử crossing/OCR trước khi thử lại, không nối chuyển động qua đoạn mất quan sát. Chi tiết và bằng chứng ở [MO_PHONG_KHONG_DEN.md](MO_PHONG_KHONG_DEN.md).

- Lịch sử: nhật ký Git ghi chốt ngày 12/10/2026; người dùng xác nhận lại ngày 01/11/2026.
- Cân nhắc: HTTP polling, HTTP đẩy trạng thái, MQTT.
- Quyết định: ESP32 điều khiển đèn publish MQTT; Mosquitto trên laptop; Python subscribe.
- Lý do: phù hợp môn IoT, gửi ngay khi đổi đèn, có heartbeat và Last Will hỗ trợ phát hiện mất kết nối.
- Đánh đổi: cần broker, tài khoản và cấu hình mạng LAN; firmware hiện publish QoS 0.
- Cấu hình hiện có: `traffic/inter1/light/state` cho JSON, `traffic/inter1/light/status` cho online/offline. Hợp đồng payload: [firmware README](../firmware/esp32_traffic_light/README.md).
- Điều kiện xem xét lại: mạng demo không cho thiết bị kết nối hoặc không chạy được broker. HTTP chỉ là phương án dự phòng cần thống nhất lại, không tự thay MQTT.

## D-02 — Camera HTTP và OpenCV: ĐÃ CHỐT CHO BƯỚC HIỆN TẠI

- Ngày: 01/11/2026, theo yêu cầu triển khai Camera → Python của người dùng.
- ESP32-CAM phát MJPEG qua HTTP/Wi-Fi tại `http://<IP>:81/stream`; Python/OpenCV trên laptop nhận hình, hiển thị và lưu JPG.
- MQTT chỉ mang trạng thái đèn trong kiến trúc hiện tại.
- Lý do: dùng tiếp firmware camera đã test, nối trực tiếp với phần xử lý ảnh trên laptop.
- Đánh đổi: chất lượng và tốc độ phụ thuộc nguồn camera, Wi-Fi, độ phân giải; cần kiểm thử thật.
- Xem xét lại cấu hình khi hình giật, trễ hoặc không đủ rõ để nhận dạng.

## D-03 — YOLO bản nhỏ và ByteTrack: ĐÃ THỐNG NHẤT HƯỚNG

- Ngày: 01/11/2026; người dùng đồng ý đề xuất trong cuộc trao đổi hiện tại.
- Cân nhắc: model phát hiện xe phù hợp và tracking ByteTrack/SORT.
- Hướng triển khai: thử YOLO bản nhỏ + ByteTrack trên hình camera thật.
- Lý do: phù hợp luồng phát hiện xe rồi theo dõi ID qua nhiều frame; bắt đầu với model nhỏ để đánh giá tốc độ laptop.
- Chưa chốt: phiên bản YOLO, trọng số, ngưỡng confidence và tốc độ/độ chính xác chấp nhận được.
- Trước khi chọn model: kiểm tra tương thích môi trường, giấy phép mã nguồn/trọng số/dataset và kết quả thực tế. Thay model khi chất lượng hoặc tốc độ không đạt.

## D-04 — SQLite và ảnh riêng: ĐÃ THỐNG NHẤT HƯỚNG

- Ngày: 01/11/2026; người dùng đồng ý đề xuất.
- Cân nhắc: SQLite hoặc MySQL.
- Chọn SQLite cho bản local; ảnh lưu trong thư mục, database lưu đường dẫn cùng thông tin sự kiện.
- Lý do: triển khai đơn giản trên laptop, không cần server database riêng.
- Đánh đổi: cần quản lý nhất quán file ảnh và bản ghi; đánh giá lại khi có nhiều máy cùng ghi hoặc yêu cầu MySQL từ môn học.

## D-05 — Streamlit local: ĐÃ THỐNG NHẤT HƯỚNG

- Ngày: 01/11/2026; người dùng đồng ý đề xuất.
- Cân nhắc: Streamlit hoặc Flask/FastAPI cùng frontend.
- Chọn Streamlit cho bản đầu: danh sách sự kiện, ảnh, bộ lọc và thống kê.
- Lý do: ưu tiên hoàn thành giao diện tra cứu local bằng Python.
- Đánh đổi: mức tùy biến giao diện và API; đánh giá lại nếu có yêu cầu mobile/API/giao diện vượt khả năng bản đầu.

## D-06 — Biển số và OCR: CHƯA CHỐT

- Tự lưu 03/11 theo yêu cầu người dùng: camera scanner mặc định lưu vào `data/plates/` ngay khi detector thấy biển, không đợi OCR đồng thuận và không cần S. Mỗi track lưu một lần ban đầu, thêm đúng một bộ ảnh xác nhận trong cùng thư mục khi có đồng thuận; không ghi đè ảnh ban đầu hoặc lưu mỗi frame. `--no-auto-save` tắt và `--output` đổi nơi lưu. ID mất/đổi hoặc phiên mới có thể lưu lại cùng biển. Ảnh/video offline và database sự kiện giữ luồng riêng như trước.

- Bổ sung 03/11/2026 theo yêu cầu lấy model/train để test camera: triển khai bản thử FastALPR 0.4.0, detector YOLOv9-t-384 ONNX và OCR CCT-XS-v2-global, CPU trong `.venv-alpr`; chưa chốt model cuối. [Nguồn, giấy phép và cách chạy](BIEN_SO.md).
- So với train mới hoặc ghép YOLO với EasyOCR/PaddleOCR/Tesseract, bộ ONNX có sẵn giúp test ngay trên CPU/Python 3.13 khi chưa có dữ liệu gán nhãn. Đánh đổi là chưa đánh giá biển Việt Nam/hai dòng; đổi model hoặc fine-tune sau khi có ảnh thật. Giữ nguyên luồng xe/tracking/MQTT/SQLite/Streamlit hiện có.
- Mã nguồn mang MIT; quyền weights detector/dữ liệu nguồn chưa được tác giả làm rõ hoàn toàn. Chỉ cache local, không đưa weights vào repo.
- Bổ sung test video 03/11: thêm `--video` đọc file tuần tự và xuất MP4/JSONL, không bỏ frame như luồng camera. Giữ thời gian video riêng, không ghép với trạng thái đèn MQTT hiện tại. Giữ OCR thô theo frame; chưa suy tần suất chuỗi thành số xe hoặc tự chốt biển theo đa số.
- Bổ sung ổn định OCR 03/11: công cụ ALPR riêng ghép bbox biển theo IoU hai chiều tốt nhất (>=0.15), tách ID khi mơ hồ, hết hạn sau 0.5 giây. Cân nhắc dùng ID xe ByteTrack hiện có; để bước tích hợp vì môi trường ALPR hiện chỉ có detector biển. Không thay ByteTrack trong luồng xe/vượt vạch.
- Chọn bỏ phiếu theo chuỗi nguyên vẹn trong 15 quan sát gần nhất (gồm cả lần OCR không hợp lệ), ít nhất 5 phiếu và tỷ lệ >=60%; confidence ký tự thấp nhất >=0.8. Lọc dạng chuỗi thường gặp ở biển Việt Nam, không tự thay O/0/B/8. Đây là heuristic thử nghiệm, chưa bao quát mọi loại biển.
- Nếu không đủ bằng chứng hiện PENDING; phiếu cũ hết hiệu lực theo cửa sổ. Khi mất track hoặc khung chồng lấn không rõ thì tạo ID mới. So với giữ chữ lần đầu hay đa số toàn video, cách này giảm truyền chữ cũ sang biển mới; vẫn có thể nhầm ID hoặc đồng thuận trên chuỗi sai. Log giữ raw và stable riêng; `last_consensus` trong tracks.json là lịch sử, không phải kết quả hiện hành ở mọi frame. `--raw-ocr` tắt ổn định để đối chiếu.
- Tích hợp sự kiện 03/11: thêm `--plate-ocr` vào luồng YOLO/ByteTrack hiện có, chạy detector biển trên frame và chỉ ghép khi >=90% diện tích biển nằm trong đúng một bbox xe. Nhiều xe nhận cùng biển hoặc nhiều biển trong một xe thì đánh dấu mơ hồ, xóa phiếu đang tích lũy. Mỗi ID xe có cửa sổ OCR riêng; mất ID quá `--plate-max-gap` (mặc định 0.5 giây) thì xóa. Giữ ByteTrack cho xe; lớp theo dõi biển riêng chỉ phục vụ ổn định OCR bên trong ID xe.
- Sửa PENDING 03/11 theo ảnh người dùng: bộ lọc cũ loại `80441NN02` vì buộc chữ đứng sau đúng hai số. Bỏ ràng buộc vị trí chữ, dùng kiểm tra chuỗi OCR sơ bộ 6–12 ký tự, ít nhất 4 số và 1–4 chữ; không coi đây là xác thực định dạng pháp lý. Giữ ngưỡng confidence 0.8 và bỏ phiếu 5 lần/60%. Log/overlay bổ sung lý do chờ, confidence ký tự thấp nhất và nguyên nhân loại từng quan sát; không hạ ngưỡng để ép có kết quả.
- Chụp kết quả OCR hiện tại đúng lúc crossing, không dùng đồng thuận xuất hiện trong tương lai hoặc tự đổi UNKNOWN thành RED. SQLite thêm cột nullable biển/trạng thái/tỷ lệ phiếu/ảnh bằng ALTER TABLE, giữ schema/dữ liệu cũ; dashboard đọc được cả database cũ chưa nâng cấp mà không sửa file. Ảnh biển cùng transaction bằng chứng hiện có; giữ policy chỉ lưu ảnh nghi đỏ hoặc `--save-all-evidence` khi thử.

- Cập nhật: 01/11/2026.
- Cần thử model phát hiện biển số và OCR trên ảnh thật, gồm biển số xe máy hai dòng nếu thuộc phạm vi demo.
- Phương án khảo sát: EasyOCR, PaddleOCR hoặc Tesseract; chưa cài/chọn mặc định một công cụ.
- Đề xuất: so sánh khả năng đọc, tốc độ, tương thích và giấy phép trước khi chốt.
- Giữ ảnh, kết quả thô và độ tin cậy khi có; không đọc được biển số vẫn giữ sự kiện để kiểm tra.

## D-07 — Đồng bộ thời gian: ĐỀ XUẤT

- Kế thừa hướng đề xuất cũ; cập nhật 01/11/2026, chưa có xác nhận chốt.
- Dùng đồng hồ laptop, suy ra thời điểm chuyển đèn từ thời điểm nhận và `ms_in_state`; cần đánh giá sai số truyền hình/mạng trước khi kết luận vượt đèn.
- Heartbeat firmware hiện là 1 giây. Ngưỡng hết hạn 1,5 giây là đề xuất cần kiểm thử và cấu hình được.
- Mất kết nối, offline hoặc trạng thái hết hạn: UNKNOWN. Nguyên tắc này giữ theo yêu cầu độ tin cậy của dự án.
- Đánh giá lại nếu cần NTP/RTC hoặc đồng bộ log từ nhiều thiết bị.

## D-08 — Môi trường local: HIỆN ĐÃ TRIỂN KHAI

- Cập nhật: 01/11/2026.
- Python 3.13 trên máy hiện tại, `.venv` và `requirements.txt`; OpenCV đã cài cho bước nhận hình.
- Đây là môi trường đã dùng, chưa phải cam kết mọi thư viện AI/OCR đều tương thích.
- Đề xuất tiếp tục local, chưa thêm Docker/cloud. Đổi phiên bản Python khi kiểm tra thư viện sau này cho thấy cần thiết.

## D-09 — GPIO và bố trí board: CHƯA XÁC NHẬN MẠCH THẬT

- Cập nhật: 01/11/2026.
- Firmware đèn hiện dùng GPIO đỏ 25, vàng 26, xanh 27, active-HIGH; chu kỳ xanh 10 giây, vàng 3 giây, đỏ 10 giây.
- Đây là cấu hình mẫu cho ESP32 DevKit, chưa được người dùng xác nhận đấu dây và kiểm thử.
- Camera và đèn có sketch riêng. Trước khi ghép phải xác nhận board, nguồn, chân thực tế; không dùng GPIO mẫu của DevKit cho ESP32-CAM khi chưa kiểm tra xung đột.

## Cập nhật thử nghiệm 02/11/2026 — nhận diện xe

- Người dùng yêu cầu triển khai nhận diện xe; thử Ultralytics YOLOv8n pretrained COCO, chưa chốt trọng số cuối cùng. Model lớn hơn được cân nhắc nhưng để sau khi đo bản nano trên CPU.
- Thêm đầu vào video/ảnh local và camera HTTP; tiếp tục dùng `/capture` vì `/stream` đã kết nối TCP nhưng không trả dữ liệu. Người dùng đã xác nhận lưu ảnh từ `/capture`.
- Môi trường máy hiện tại đã cài Python 3.12, thay cho ghi nhận Python 3.13 trước đây.
- Mã nguồn/trọng số Ultralytics: AGPL-3.0 hoặc Enterprise; nguồn và điều khoản dữ liệu được liên kết tại [YOLO.md](YOLO.md). Không tự thay giấy phép repository.
- Chỉ triển khai detection; ByteTrack, crossing và OCR để các mốc sau. Đánh giá lại model/confidence khi có xe mô hình và video của nhóm.

## Cập nhật tiếp 02/11/2026 — ByteTrack và vạch dừng

- Theo yêu cầu làm mốc tiếp theo, dùng ByteTrack đã thống nhất, cấu hình Ultralytics `bytetrack.yaml` và `persist=True`. Không đổi sang tracker khác.
- Thêm `--track` vào chương trình có sẵn, không tạo luồng đọc camera thứ hai. LAP được khai báo trong requirements để cài trước.
- Vạch là đoạn thẳng cấu hình theo tỷ lệ ảnh, dùng tâm đáy bbox làm điểm kiểm tra. So với chỉ kiểm tra bbox chạm vạch, yêu cầu đổi phía qua nhiều frame để xác định lượt qua. Deadband mặc định 5 pixel và giới hạn gap 5 frame là cấu hình thử, có thể thay qua CLI.
- JSONL ghi sự kiện crossing với ID phiên chạy và ID xe; đây là log tạm trước SQLite, không thay quyết định D-04. Trạng thái đèn luôn UNKNOWN, chưa phân loại vi phạm. Thời điểm ghi là frame xác nhận, chưa có đồng bộ video/đèn.
- Kiểm thử và giới hạn được ghi tại [TRACKING.md](TRACKING.md); cần đánh giá lại gap/deadband/góc quay trên dữ liệu thật và khi có xe mô hình.

## Cập nhật tiếp 02/11/2026 — nhận đèn MQTT và phân loại crossing

- Theo yêu cầu làm mốc tiếp theo, giữ giao thức MQTT và firmware hiện có. Thêm Paho MQTT 2.x cho Python, sử dụng callback API VERSION2, reconnect/resubscribe tự động. Tài liệu chính thức: https://eclipse.dev/paho/clients/python/docs/ .
- Dùng monotonic trên laptop để quản lý độ mới và lịch sử trạng thái; không suy từ đồng hồ chạy video ghi sẵn sang đèn hiện tại. Timeout 1.5 giây là mặc định thử có thể cấu hình, chưa chốt sau đo thực tế.
- Chỉ phân loại nghi vượt đèn đỏ nếu khoảng từ điểm ổn định trước vạch tới frame xác nhận, mở rộng 0.5 giây phía trước, có dữ liệu đỏ liên tục và đúng chiều. Khác với chỉ lấy màu đèn lúc xử lý xong, cách này tránh dùng màu mới cho frame cũ trong nhiều tình huống; chưa thay thế đồng bộ phơi sáng camera/đèn. Khoảng dự phòng 0.5 giây cũng là cấu hình thử.
- Từ chối retained state, dữ liệu sai, trạng thái thiếu/hết hạn; disconnect/offline về UNKNOWN, reconnect cần trạng thái mới. History giới hạn 1000 bản tin; khoảng không còn lịch sử không được xác nhận.
- Giữ JSONL cho log tạm, thêm assessment; SQLite/OCR là mốc sau. MQTT topic thật không dùng cho simulator: demo dùng `demo/inter1/light`, broker thử chỉ loopback:18884. Không thay đổi xác thực broker LAN hay cấu hình firewall tự động.
- 28 kiểm thử đạt, trong đó 1 bài broker Mosquitto thật; chi tiết tại [CHECKLIST.md](../CHECKLIST.md). Không sửa/nạp firmware, chưa xác nhận camera/ESP32 đèn chạy chung.

## Cách sửa nhật ký

### Bổ sung 02/11/2026 — logic đèn đỏ có giải thích

- Giữ chính sách nghi vi phạm dựa trên crossing đúng chiều và đỏ liên tục; đưa việc mở rộng khoảng thời gian/lý do vào `assess_crossing` để camera và demo dùng cùng hàm.
- JSONL bổ sung `assessment_reason`, không đổi giao thức MQTT, firmware hay kiến trúc lưu trữ.
- Thêm demo 14 tình huống theo thời gian giả lập, không giả làm kiểm thử camera/ESP32 thật. 33 unittest đạt; video YOLO/ByteTrack tổng hợp vẫn ghi 1 crossing UNKNOWN/unverified khi không có nguồn đèn.
- Kiểm tra trên phần cứng và hiệu chỉnh thời gian vẫn để chưa hoàn thành trong CHECKLIST.md.

Ghi ngày, vấn đề, phương án cân nhắc, kết luận, lý do, đánh đổi và điều kiện xem xét lại. Đánh dấu rõ nội dung người dùng đã xác nhận; giữ phần chưa quyết định ở trạng thái đề xuất.

## Bổ sung 02/11/2026 — SQLite và ảnh bằng chứng

- Theo yêu cầu làm mốc tiếp theo, triển khai D-04: SQLite qua sqlite3 sẵn trong Python, JPEG riêng và đường dẫn trong database. Không thêm server database hay thay firmware.
- Mọi crossing được lưu metadata; mặc định chỉ suspected_red_light lưu ba ảnh (gốc/có khung/cắt xe). `--save-all-evidence` phục vụ kiểm thử, giữ nguyên kết quả phân loại.
- SQLite là dữ liệu chính, JSONL tiếp tục làm log phụ. event_id khóa duy nhất bảo đảm ghi lại cùng ID không thêm bản ghi/ảnh; không khử trùng giữa phiên khác nhau hoặc ID tracking bị đổi.
- Ghi ảnh tạm rồi đổi tên thư mục trước khi commit; lỗi ghi/INSERT thông thường rollback và dọn file do lần gọi đó tạo. Chưa bảo đảm giao dịch xuyên SQLite/filesystem khi mất điện; đường dẫn ảnh tuyệt đối cần điều chỉnh khi di chuyển dữ liệu. Chi tiết tại STORAGE.md.
- Đã thử 9 tests storage và video YOLO/ByteTrack 41 frame: 1 crossing UNKNOWN, 3 ảnh khi bật lưu mọi crossing. Tổng bộ kiểm thử 42 bài đạt; chưa xác nhận trường hợp đỏ trên camera/LED thật.

## Bổ sung 02/11/2026 — Streamlit xem dữ liệu local

- Triển khai D-05 bằng Streamlit, dùng lại SQLite/ảnh của D-04; local-only theo hướng kiến trúc đã thống nhất, không publish Sites/cloud hay thay firmware.
- Làm giao diện tra cứu trước OCR vì dữ liệu sự kiện/ảnh đã sẵn sàng kiểm tra; model biển số và OCR vẫn chưa chốt/triển khai. Không thêm biển số giả vào giao diện.
- SQLite mở mode=ro, truy vấn có tham số, bộ lọc và thống kê cùng transaction đọc. Phân trang, CSV chỉ trang đang xem, refresh thủ công để tránh cache dữ liệu cũ.
- 6 kiểm thử dashboard đạt gồm Streamlit AppTest; máy chủ local HTTP 200/health OK. Tổng 48 bài đạt. Chưa kiểm tra trực quan bằng trình duyệt hoặc cùng luồng camera/đèn thật.
- API/kiểm thử theo tài liệu chính thức: https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest .
