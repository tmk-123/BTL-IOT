# Test camera nhận dạng biển số

**04/11/2026 — biển trong cửa sổ xe:** khi bật `vehicle_detector.py --plate-ocr`,
OCR nay chạy trên toàn ảnh kể cả khi YOLO không có ID xe. Khung biển và kết quả
đồng thuận vẫn hiển thị; lúc không có xe theo dõi, màn hình báo crossing chưa khả dụng.
Đồng thuận toàn ảnh chỉ phục vụ xem; OCR lưu vào sự kiện vẫn phải ghép riêng với
ID xe, không kế thừa phiếu của biển chưa ghép. Kiểm thử ghép/không ghép/reset đạt;
7 ảnh camera thật đọc `29A22222`, đạt đồng thuận ở ảnh thứ 5 trong lần thử này.

**Tự lưu khi phát hiện biển (03/11):** chế độ camera hiện bật tự lưu mặc định vào `data/plates/`, không cần nhấn S. Đóng scanner cũ và chạy lại để nạp thay đổi. `--output` đổi thư mục chung; `--no-auto-save` tắt tự lưu nếu muốn chỉ dùng S. Chế độ ảnh/video vẫn lưu như trước ở `data/plate_tests/`.

Mỗi track biển xuất hiện tạo một thư mục thời gian chứa `frame.jpg`, `annotated.jpg`, `plate_0.jpg`, `result.json` và `event.json`, kể cả OCR còn PENDING. Khi lần đầu đạt đồng thuận, lưu thêm bộ ảnh/JSON trong thư mục con `confirmed/` của cùng lần xuất hiện; giữ nguyên ảnh ban đầu. `event.json` ghi trạng thái và chỉ tới kết quả đã xác nhận nếu có. Dòng trạng thái báo `Auto-save: ON` và báo tên lần lưu gần nhất. Không có biển thì không tự lưu; cùng ID không lưu ở từng frame. Mất tracking rồi nhận lại ID mới hoặc khởi động lại chương trình có thể tạo thư mục mới cho cùng biển; chưa khử trùng qua phiên. S vẫn lưu thủ công thêm một bộ ảnh vào cùng thư mục gốc.

**Sửa lỗi PENDING ngày 03/11:** chuỗi `80441NN02` trong ảnh người dùng đã bị bộ lọc định dạng cũ loại dù OCR đọc đúng. Đã bỏ ràng buộc chữ phải đứng sau đúng hai số: hiện kiểm tra sơ bộ chuỗi 6–12 ký tự, có ít nhất 4 số và 1–4 chữ, không tự xác thực biển hợp pháp. Ngưỡng confidence và số phiếu giữ nguyên. Overlay/JSON bổ sung lý do `low_confidence`, `unsupported_layout`, `empty_ocr`, `not_enough_matches`, `readings_disagree`, cùng confidence ký tự thấp nhất. Đây là phiên bản thay thế mô tả regex hẹp ở bước 4 phía dưới.

`#16` là ID track biển, không phải tiến độ nhận dạng. `(0/15)` nghĩa 15 quan sát gần nhất chưa có phiếu được chấp nhận; chờ thêm không giải quyết được trường hợp toàn bộ quan sát bị bộ lọc loại. Đóng cửa sổ scanner cũ và chạy lại để nạp code mới. Kiểm thử hồi quy chuỗi `80-441 NN-02`, vị trí chữ khác và lý do pending đạt; tổng 19 bài ALPR/ghép xe liên quan đạt.

Cập nhật 03/11/2026. Chạy local CPU: camera → tìm biển số → OCR → hiện khung/chữ → lưu ảnh và JSON. Đây là công cụ test riêng, chưa ghép OCR vào sự kiện crossing/SQLite/Streamlit.

## ESP32-CAM quay video đang phát trên màn hình (03/11/2026)

Người dùng chọn dùng camera thật quay màn hình, không cho AI đọc trực tiếp file video trong bài thử này. Đã kết nối được camera tại `http://10.82.212.69/capture` và đổi Frame Size từ 320×240 sang VGA 640×480 qua API camera, không sửa/nạp firmware. Giá trị enum VGA được đọc từ trang điều khiển của chính camera, không giả định giữa các phiên bản firmware. Sau khi reset, camera có thể trở về QVGA; chọn lại VGA trên `http://10.82.212.69/`.

Mở hai PowerShell tại thư mục gốc dự án:

```powershell
# Cửa sổ 1: phát video nguồn sạch trên màn hình, lặp lại và chậm 0.5 lần
.\.venv-alpr\Scripts\python.exe -u -B python/play_plate_video.py --speed 0.5

# Cửa sổ 2: AI chỉ đọc ảnh từ ESP32-CAM thật
.\.venv-alpr\Scripts\python.exe -u -B python/plate_scanner.py --source http://10.82.212.69/capture --snapshot --plate-max-gap 1.5
```

- Hướng camera vào **cửa sổ video nguồn**, không quay cửa sổ camera nhận dạng (tránh hình lặp vô hạn). Chỉnh vị trí/góc để phần biển rõ, gần và ít phản sáng; đóng các tab khác đang đọc camera.
- Trong video: Space tạm dừng/phát, F toàn màn hình, R về đầu, Q/Escape thoát. Có thể giữ video dừng ở lúc xe gần để căn nét rồi phát tiếp. Video không có âm thanh.
- Trong cửa sổ nhận dạng: khung xanh có chữ đồng thuận, khung cam/PENDING chưa đủ bằng chứng; `raw:` là OCR hiện tại. S lưu ảnh camera gốc/annotated/crop/JSON, Q thoát.
- Thử tăng VGA lên SVGA trên trang camera nếu ký tự còn nhỏ và đường truyền ổn. Đưa camera quá sát có thể mất nét; cần nhìn ảnh camera để căn, không chỉ nhìn video gốc bằng mắt.
- `--plate-max-gap 1.5` chỉ tăng thời gian giữ track biển trong luồng camera chậm; không đổi timeout đèn, không phải bù trễ camera/MQTT. Không áp dụng cho chế độ `--video`.

Đã kiểm tra: API camera trả ảnh 640×480, trình phát Tk mở/đóng được, 9 kiểm thử ALPR còn đạt. Ảnh camera trước khi căn góc chỉ có vùng sáng, không có biển. Việc kết nối camera không đồng nghĩa đã xác nhận OCR đọc được video qua màn hình; cần hướng ống kính và kiểm tra chữ/ảnh lưu thực tế.

Trong lần thử thật, `/capture` có lúc timeout sau một số ảnh. Đã thêm thử lại khi đọc lỗi tạm thời; 3 lần đọc thất bại liên tiếp mới dừng (mỗi lần HTTP tối đa 5 giây). Cửa sổ báo đang thử lại và không chạy OCR lặp trên ảnh cũ. Đóng tab stream khác, kiểm tra nguồn/Wi-Fi nếu còn lỗi. Hai kiểm thử phục hồi sau lỗi tạm thời và dừng/giải phóng khi lỗi kéo dài đều đạt. Đây chưa phải kiểm thử ổn định camera kéo dài.

## Chạy ngay trên máy này

Đã tạo `.venv-alpr` và tải model. PowerShell tại `D:\Ki1_4\IOT\BTL`:

```powershell
# ESP32-CAM: thay IP ví dụ bằng IP từ Serial Monitor
# Dùng /capture vì đây là endpoint đã được xác nhận hoạt động
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --source http://192.168.1.10/capture --snapshot

# MJPEG nếu /stream hoạt động được
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --source http://192.168.1.10:81/stream

# Webcam laptop / USB (thử 1 nếu camera ngoài không phải số 0)
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --source 0

# Ảnh: xử lý một lần, lưu kết quả, không mở cửa sổ
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --image "data/snapshots/anh_bien_so.jpg"
```

Click cửa sổ hình: **S** lưu thêm thủ công, **Q/Escape** thoát. Đóng cửa sổ cũng thoát. Camera đã bật tự lưu mặc định như ghi ở đầu tài liệu.

Kết quả camera mới trong `data/plates/<thời_gian>/`; kết quả ảnh/video và các lần thử cũ trong `data/plate_tests/`. Các bộ ảnh gồm `frame.jpg` gốc, `annotated.jpg`, `plate_0.jpg` (và các biển khác khi lưu thủ công nếu có), `result.json` chứa thời gian, nguồn hình, model, tọa độ, confidence detector và OCR thô. Không coi confidence là độ chính xác đã kiểm chứng. Tự lưu camera theo track, không lưu từng frame.

Luồng đọc riêng chỉ giữ frame mới nhất để hạn chế tích lũy độ trễ khi chạy AI. Thời gian AI hiển thị không phải độ trễ tổng camera/Wi-Fi.

## Chuẩn bị ESP32-CAM

1. Dùng firmware `testCamera` hiện tại; lấy IP trong Serial Monitor 115200.
2. Mở `http://<IP>` và tăng Frame Size từ QVGA lên **VGA 640×480**, có thể thử SVGA nếu nguồn và Wi-Fi ổn. Chưa đổi mặc định firmware.
3. Đủ sáng, tránh phản quang, giữ biển gần và ít nghiêng. Ảnh phải rõ từng ký tự; phóng to ảnh mờ không tạo thêm chi tiết.
4. Đóng các tab xem stream trước khi chạy Python. Laptop và camera cùng mạng.
5. Nếu không có khung, thử `--confidence 0.25`; ngưỡng thấp có thể tăng nhận nhầm.
6. Test biển ô tô một dòng và xe máy hai dòng riêng; nhấn S để giữ cả trường hợp đúng/sai phục vụ đánh giá và fine-tune.

Mất nguồn/mạng: chương trình báo lỗi và thoát; kiểm tra rồi chạy lại. Webcam có thể đang bị ứng dụng khác chiếm hoặc chưa được Windows cấp quyền camera cho desktop apps.

## Cài trên máy mới

Python 3.13 đã được kiểm tra cho môi trường ALPR này; môi trường phần xe/Streamlit được quản lý riêng.

```powershell
python -m venv .venv-alpr
.\.venv-alpr\Scripts\python.exe -m pip install -r requirements-alpr.txt
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --download-models
```

Model khoảng 11 MB, cache trong `%USERPROFILE%\.cache\open-image-models` và `%USERPROFILE%\.cache\fast-plate-ocr`. Lần sau dùng cache, suy luận không cần dịch vụ cloud. Tài khoản Windows khác cần tải lại hoặc chuyển cache.

Dùng môi trường riêng vì FastALPR kéo OpenCV headless; chương trình mới dùng Tkinter để hiển thị. `camera_viewer.py` cũ dùng `.venv` với OpenCV GUI. Không cài `requirements.txt` vào `.venv-alpr` vì hai gói OpenCV cùng cung cấp `cv2`.

## Model, nguồn và giới hạn

- [FastALPR](https://github.com/ankandrew/fast-alpr) 0.4.0.
- Detector ONNX `yolo-v9-t-384-license-plate-end2end`, từ [Open Image Models](https://github.com/ankandrew/open-image-models) 0.6.0.
- OCR ONNX `cct-xs-v2-global-model`, từ [FastPlateOCR](https://github.com/ankandrew/fast-plate-ocr) 1.1.0.
- Chọn model nhỏ có sẵn để test CPU ngay; chưa train vì repo chưa có bộ ảnh gán nhãn. EasyOCR/PaddleOCR có thể thử tiếp nếu model chưa đáp ứng biển Việt Nam; fine-tune khi có ảnh camera thật và nhãn đúng.
- Đã thử nhanh 4 ảnh Việt Nam, gồm biển hai dòng; chưa có benchmark trên tập kiểm thử độc lập hoặc camera thật. Giữ kết quả thô để thấy lỗi OCR. Nhãn quốc gia cũng có thể sai.
- Mã nguồn ba thư viện mang MIT. [Trao đổi tác giả detector](https://github.com/ankandrew/open-image-models/issues/14) chưa làm rõ dứt điểm quyền weights YOLO và mọi ảnh huấn luyện; không suy ra weights/dataset đều là MIT. Giữ model cache local phục vụ thử nghiệm, không đưa weights/dữ liệu mẫu lên Git; rà lại khi phân phối sản phẩm.

## Bằng chứng kiểm thử 03/11/2026

- Tải/khởi tạo cả hai model thành công trên CPU.
- Ảnh mẫu upstream `assets/test_image.png`: tìm 1 biển, đọc `5AU5341`, khoảng 73 ms cho lần đo đầu; đã xem ảnh annotated và đối chiếu ký tự.
- Đây là biển nước ngoài và smoke test một ảnh, chưa phải benchmark FPS hoặc xác nhận độ chính xác biển Việt Nam.
- Môi trường riêng `.venv-alpr`: chạy lại ảnh mẫu đọc cùng kết quả, khoảng 132 ms ở lần đo này; `pip check` đạt.
- HTTP JPEG server local → luồng đọc snapshot → detector/OCR thật → cửa sổ Tk → phím S lưu đủ ảnh gốc/annotated/crop/JSON → Q thoát: đạt. Đây là kiểm thử đường truyền giả lập, không phải camera thật.
- Ảnh đen không sinh biển số; HTTP không kết nối được báo lỗi và thoát.
- Chưa test ESP32-CAM thật trong phiên này vì chưa có IP/URL camera.

Ảnh mẫu được tải local, có thể chạy lại:

```powershell
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --image data/test_samples/fast_alpr_sample.png
```

## Bước 2 — ảnh mẫu Việt Nam (đã chạy 03/11/2026)

Đã tải 4 ảnh từ thư mục [test_image của trungdinh22/License-Plate-Recognition](https://github.com/trungdinh22/License-Plate-Recognition/tree/main/test_image) vào `data/test_samples/vietnam/`. Chỉ lưu local để thử; chưa thấy giấy phép riêng cho các ảnh nên không đưa vào Git hoặc dùng làm tập train/phân phối. URL nguồn và đường dẫn kết quả nằm trong `data/test_samples/vietnam/sources_and_results.json`.

| Ảnh | Chuỗi OCR ở các vùng tìm thấy | Thời gian lần đo này |
| --- | --- | --- |
| `1.jpg` | `59U116124`, `59G163188`, `50LD00454` | 69 ms |
| `3.jpg` | `30A33918` | 185 ms |
| `4.jpg` | `30F21717`, `30G70516` | 62 ms |
| `bien_so.jpg` | `30E99999`, `51F99999`, `30A99999`, `51A99999` | 73 ms |

Đã mở cả 4 ảnh annotated và đối chiếu ký tự nhìn rõ ở 10 vùng được phát hiện: khớp, gồm biển xe máy hai dòng. Cảnh đông xe `1.jpg` còn nhiều biển nhỏ không được phát hiện. Không coi 10 vùng này là toàn bộ biển trong 4 ảnh, không suy ra độ chính xác 100% trên dữ liệu thực tế; các ảnh cũng có thể trùng dữ liệu huấn luyện upstream.

Tự chạy ảnh ô tô một biển trước:

```powershell
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --image data/test_samples/vietnam/3.jpg
```

Kỳ vọng có 1 vùng và OCR `30A33918`. Mở `annotated.jpg` trong thư mục được in sau `Saved:` để kiểm tra. Thử tiếp `1.jpg` để xem nhiều biển, gồm biển xe máy hai dòng.

## Bước 3 — video giao thông Việt Nam có sẵn

Đã tải `test_videos/test.MOV` từ [ALPR_System của longphungtuan94](https://github.com/longphungtuan94/ALPR_System), commit `0a6d781137870ac362262bb1fa9b0fdf4d99e49d`, về `data/test_samples/vietnam/traffic_sample.MOV`. Video khoảng 59 MB, 1920×1080, 835 frame, khoảng 29.97 FPS (27.9 giây). URL nguồn lưu ở `data/test_samples/vietnam/video_source.json`. Repo mang Apache-2.0; chưa thấy giấy phép riêng của video. Chỉ giữ bản tải local để thử, không đưa vào Git hoặc dùng train/phân phối mặc định.

```powershell
# Chạy toàn bộ file, không cần camera hoặc cửa sổ xem trực tiếp
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --video data/test_samples/vietnam/traffic_sample.MOV

# Thử nhanh 100 frame đầu
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --video data/test_samples/vietnam/traffic_sample.MOV --max-frames 100
```

Mỗi 100 frame chương trình in tiến độ. Kết thúc sẽ in `Saved video and logs:`. Thư mục kết quả gồm:

- `annotated.mp4`: video có khung/chữ. Giữ FPS của bản gốc, không có âm thanh; không tự tăng tốc khi AI chạy chậm. Thời gian xử lý thực ghi riêng trong summary.
- `frames.jsonl`: mỗi frame một dòng gồm chỉ số frame từ 0, thời gian tương đối trong video, tọa độ biển, OCR và confidence. Giữ cả frame không tìm thấy biển. Thời gian video không được coi là giờ quay thực hoặc dùng để ghép đèn MQTT hiện tại.
- `summary.json`: số frame xử lý, số frame có biển, thời gian xử lý và tần suất các chuỗi OCR thô. Tần suất này không phải số xe khác nhau; chưa có tracking/biểu quyết OCR theo xe.
- Một thư mục ảnh gốc/annotated/crop/JSON cho frame đầu tiên tìm thấy biển.

Đọc tuần tự tất cả frame được giải mã, không dùng cơ chế bỏ frame của camera trực tiếp. `--max-frames` giới hạn đoạn test; Ctrl+C giữ phần đã ghi và đánh dấu `interrupted` trong summary. Không có cơ chế tự sửa ký tự hoặc loại bỏ OCR sai để che lỗi.

Kiểm thử chức năng video (không tải model, dùng video nhỏ tạo tạm):

```powershell
.\.venv-alpr\Scripts\python.exe -B -m unittest discover -s tests -p test_plate_video.py -v
```

Hai bài kiểm thử đạt: file trống/không tồn tại bị từ chối; video không có kết quả OCR vẫn xuất đủ frame, log và giữ FPS; giới hạn số frame hoạt động đúng.

Kết quả chạy toàn bộ video mẫu ngày 03/11/2026:

- Xử lý 835/835 frame, khoảng 27.86 giây video. Có phát hiện biển ở 477 frame; đây không phải tỷ lệ đọc đúng vì chưa gán nhãn tất cả frame.
- Thời gian xử lý khoảng 133 giây, tương đương 6.27 frame/giây trên CPU trong lần chạy này; chưa đạt xử lý thời gian thực 30 FPS.
- Frame đầu đọc `29A33185`, đã mở ảnh kiểm tra khớp `29A-331.85`. Các chuỗi thường gặp khác có `30A61329`, `30A61235`, `29A90101`, `30V4495`; giữ cả các biến thể sai/thiếu ký tự trong JSONL, chưa xác nhận tất cả chuỗi bằng nhãn chuẩn.
- Đầu ra local: `data/plate_tests/video_20261103_093938_489875/annotated.mp4`, `frames.jsonl`, `summary.json`.
- Bước sau: chọn OCR ổn định theo track xe, đánh giá lỗi, rồi mới ghép sự kiện/SQLite và thử camera thật.

## Bước 4 — ổn định chữ biển số qua nhiều frame

Đã thêm `python/plate_consensus.py` và bật mặc định trong chế độ video/camera của `plate_scanner.py`. Luồng nhận diện xe ByteTrack/vượt vạch hiện có chưa thay đổi; ID ở đây chỉ là track vùng biển trong công cụ ALPR riêng.

Chạy lại bằng lệnh video như bước 3. Để xem bản chỉ OCR thô, thêm `--raw-ocr`:

```powershell
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --video data/test_samples/vietnam/traffic_sample.MOV
.\.venv-alpr\Scripts\python.exe python/plate_scanner.py --video data/test_samples/vietnam/traffic_sample.MOV --raw-ocr
```

- Ghép bbox biển qua các frame theo IoU tốt nhất hai chiều, tối thiểu 0.15; ghép mơ hồ khi chồng lấn thì tách ID, không chia sẻ phiếu. Track hết hạn sau 0.5 giây không được phát hiện. Video dùng thời gian trong file, camera dùng monotonic; không coi là timestamp phơi sáng.
- Cửa sổ 15 quan sát gần nhất gồm cả lần không đọc được. Chỉ bỏ phiếu cho chuỗi dạng thường gặp `2 chữ số + 1–2 chữ cái + 4–6 chữ số`, confidence ký tự thấp nhất >=0.8. Chuẩn hóa viết hoa/bỏ dấu phân cách; không tự đổi O thành 0 hoặc B thành 8. Bộ lọc này chưa bao quát mọi loại biển Việt Nam.
- Chỉ hiện kết quả khi cùng chuỗi có ít nhất 5 phiếu và chiếm >=60% cửa sổ hiện tại. Thiếu bằng chứng hoặc phiếu cũ đã trôi khỏi cửa sổ thì hiện **PENDING**, không giữ chữ cũ vô thời hạn.
- Khung xanh: có đồng thuận; khung cam: PENDING. `#4 29A90101 (14/15)` nghĩa track số 4 có 14/15 quan sát ủng hộ chuỗi đó. Dòng `raw:` luôn cho thấy OCR frame hiện tại, có thể khác chuỗi ổn định.
- `frames.jsonl` vẫn giữ nguyên `results` thô, bổ sung `plate_tracks` với ID, raw/stable, trạng thái và số phiếu. Nhấn S ở camera cũng lưu cả hai trong `result.json`.
- Video có thêm `tracks.json`: thời gian, số quan sát và lịch sử đồng thuận của mỗi track. `last_consensus` là kết quả từng được chấp nhận trong lịch sử, không khẳng định chuỗi đó còn đang được chấp nhận tại frame cuối. Track có thể bị chia nhỏ hoặc ghép nhầm; số track không phải số xe.

Kết quả chạy lại 835 frame ngày 03/11/2026:

- Xuất đủ 835 frame MP4 và 835 dòng JSONL, kiểm tra giải mã lại đạt. Có 12 track vùng biển, 5 track từng đạt đồng thuận.
- 214 chuỗi OCR thô khác nhau; phần đồng thuận chỉ xuất hiện 5 chuỗi: `29A33185`, `30A61235`, `29A90101`, `30A61329`, `30V4495`. Đã mở ảnh cắt rõ của cả 5 và đối chiếu khớp ký tự. Các biển khác hoặc quan sát mờ có thể vẫn PENDING, không tuyên bố đã đọc hết xe trong video.
- 249 lần đổi OCR thô trong cùng track; không có lần đổi từ một chuỗi đồng thuận sang chuỗi đồng thuận khác ở 5 track đã xác nhận trong video này. Có 22 quan sát đang hiện chuỗi ổn định khác OCR thô. So sánh này bỏ qua PENDING, không phải đo độ chính xác trên tập nhãn độc lập.
- Lần chạy này khoảng 76.5 giây (10.91 FPS xử lý). Chưa đạt 30 FPS và không so sánh tốc độ giữa các lần chạy như benchmark có kiểm soát.
- Video mới: `data/plate_tests/video_20261103_094521_833380/annotated.mp4`; log cùng thư mục. `comparison.json` lưu số liệu so sánh; `data/plate_tests/consensus_visual_check.jpg` là ảnh đối chiếu 5 biển.
- 9 kiểm thử ALPR đạt, gồm lỗi OCR xen kẽ, hai biển đổi thứ tự detection, mất track, confidence thấp, phiếu cũ hết hạn, bbox ghép mơ hồ, timestamp sai và đọc/ghi video. HTTP snapshot local + model thật + cửa sổ Tk + S lưu metadata stable/raw + Q thoát cũng đạt; chưa thay thế kiểm thử camera thật.

```powershell
.\.venv-alpr\Scripts\python.exe -B -m unittest discover -s tests -p "test_plate*.py" -v
```

Giới hạn: nhiều lần đọc cùng sai vẫn có thể đạt đồng thuận; giao nhau/che khuất hoặc xe mới vào cùng vị trí có thể đổi/nhầm ID. Camera xử lý quá chậm (khoảng cách giữa quan sát >0.5 giây) có thể không giữ được track. Bước sau là ghép kết quả với ID xe ByteTrack/sự kiện rồi SQLite/Streamlit và đánh giá trên camera thật.

## Bước 5 — biển số trong sự kiện, SQLite và Streamlit

Đã tích hợp `--plate-ocr` vào `vehicle_detector.py`. Biển phải có ít nhất 90% diện tích nằm trong đúng một bbox xe ByteTrack. Nếu nhiều xe chồng lên cùng biển hoặc một xe chứa nhiều biển thì giữ trạng thái ghép mơ hồ, không lấy biển tùy ý. Phiếu OCR được lưu riêng theo ID xe, hết hạn sau `--plate-max-gap` (mặc định 0.5 giây); cửa sổ/điều kiện đồng thuận như bước 4.

Kết quả được lấy **ngay lúc crossing**, không lấy kết quả biết sau này để điền ngược. Nếu frame crossing không thấy biển hoặc chưa có đồng thuận thì `plate_text` vẫn NULL. Lưu nguyên OCR thô, bbox và tỷ lệ phiếu trong payload. Chưa có tác vụ cập nhật biển muộn sau crossing.

Máy hiện tại đã cài môi trường `.venv` cho luồng đầy đủ. Mở giao diện:

```powershell
.\.venv\Scripts\python.exe -m streamlit run python/dashboard.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

1. Mở `http://127.0.0.1:8501`.
2. Trong **Chọn dữ liệu**, chọn **Video biển số**.
3. Nhập `29A33185` vào ô tìm kiếm: có 1 sự kiện với biển ổn định.
4. Xem bảng và 4 ảnh: gốc, có khung, xe, biển số. CSV trang hiện tại cũng có biển/trạng thái.

Database mẫu: `data/demos/plate_pipeline/traffic.db`, tách khỏi `data/traffic.db` thật. Đã chạy 150 frame đầu của video giao thông có sẵn qua **YOLOv8n → ByteTrack → detector biển/OCR → crossing → SQLite**:

| ID xe | Biển lúc crossing | Trạng thái OCR | Đèn / kết quả |
| --- | --- | --- | --- |
| 1 | `29A33185` | Có đồng thuận (frame 24) | UNKNOWN / chưa xác minh |
| 5 | Chưa có | Không thấy biển | UNKNOWN / chưa xác minh |
| 2 | Chưa có | Chưa ổn định | UNKNOWN / chưa xác minh |

Các ID này thuộc phiên test đã chạy, không phải cam kết ID luôn như vậy khi đổi model/video. Tốc độ lần thử khoảng 4.12 FPS CPU khi chạy cả YOLO/ByteTrack/OCR; chưa phải hệ thống thời gian thực. Không có dữ liệu đèn của thời điểm quay, do đó không tạo nghi vượt đèn đỏ từ video này. `--save-all-evidence` chỉ để lưu cả ảnh sự kiện UNKNOWN khi thử, không đổi kết quả phân loại.

Tự chạy lại (sẽ thêm một phiên sự kiện mới vào database mẫu):

```powershell
.\.venv\Scripts\python.exe -u -B python/vehicle_detector.py --source data/test_samples/vietnam/traffic_sample.MOV --track --plate-ocr --no-display --line 0.05 0.65 0.95 0.65 --save-all-evidence --max-frames 150 --database data/demos/plate_pipeline/traffic.db --evidence-dir data/demos/plate_pipeline/evidence --output data/demos/plate_pipeline/logs --save-last
```

Cài luồng kết hợp trên máy mới:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-traffic-ocr.txt
```

Thư viện upstream YOLO và FastALPR lần lượt yêu cầu các gói OpenCV GUI/headless dùng chung tên `cv2`. Luồng kết hợp đã kiểm tra với **`--no-display` và xem ảnh trên Streamlit**; không phụ thuộc cửa sổ HighGUI. Nếu muốn xem camera quét biển trực tiếp bằng Tk, tiếp tục dùng môi trường riêng `.venv-alpr` theo bước đầu. Không cài lại gói OpenCV trong lúc một tiến trình video đang chạy. Model YOLOv8n tải lần đầu vào `models/`, giấy phép/nguồn như [YOLO.md](YOLO.md).

SQLite tự thêm các cột `plate_text`, `plate_status`, `plate_vote_share`, `plate_image` khi mở bằng EventStore; giữ dữ liệu cũ. Dashboard chỉ đọc, xử lý được database chưa có các cột này mà không tự nâng cấp hoặc ghi file. Ảnh `plate.jpg` nằm cùng thư mục bằng chứng sự kiện, dùng quy trình ghi tạm/rollback hiện có. Khi không yêu cầu lưu ảnh, biển/trạng thái vẫn có thể lưu mà đường dẫn ảnh là NULL.

Kiểm thử 03/11: **66 bài đạt**, gồm 5 bài ghép biển/ID xe, 12 bài storage, 7 bài dashboard và các bài tracking/đèn/MQTT/OCR còn lại. Đã kiểm tra dữ liệu video thật qua Streamlit AppTest: tìm biển không phân biệt hoa thường ra đúng 1 sự kiện; cả 4 ảnh bằng chứng mở được; máy chủ local trả HTTP 200/health OK. Chưa xác nhận bố cục bằng trình duyệt của người dùng hoặc camera + ESP32 đèn thật chạy chung. Đồng thuận OCR có thể sai; `plate_vote_share` là tỷ lệ phiếu, không phải xác suất nhận dạng đúng.
