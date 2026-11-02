"""Local Streamlit event browser; reads SQLite without writing it."""

import csv
from datetime import datetime
import io
import json
from pathlib import Path
import sqlite3
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import streamlit as st
from PIL import Image
from dashboard_data import load_events

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENTS = {
    "suspected_red_light": "Nghi vượt đèn đỏ",
    "no_red_light_evidence": "Không có bằng chứng đèn đỏ",
    "unverified": "Chưa xác minh",
    "not_applicable_direction": "Không xét chiều này",
}
PRESETS = {
    "Dữ liệu chạy thật": ROOT / "data/traffic.db",
    "Demo lưu trữ": ROOT / "data/demos/storage/traffic.db",
    "Video mẫu": ROOT / "data/demos/storage_pipeline/traffic.db",
    "Đường dẫn khác": None,
}


def main():
    st.set_page_config(page_title="Giám sát giao thông", page_icon="🚦", layout="wide")
    st.title("Giám sát giao thông")
    st.caption("Tra cứu sự kiện qua vạch và ảnh bằng chứng trên laptop.")
    with st.sidebar:
        st.header("Nguồn dữ liệu")
        preset = st.selectbox("Chọn dữ liệu", list(PRESETS), key="dataset")
        if PRESETS[preset] is None:
            database = Path(st.text_input("Đường dẫn SQLite", str(ROOT / "data/traffic.db"), key="database"))
        else:
            database = PRESETS[preset]
        st.button("Làm mới dữ liệu")
        st.header("Bộ lọc")
        assessment = st.selectbox("Kết quả", [None, *ASSESSMENTS],
                                  format_func=lambda value: "Tất cả" if value is None else ASSESSMENTS[value], key="assessment")
        vehicle_class = st.selectbox("Loại xe", [None, "car", "motorcycle", "bus", "truck", "bicycle"],
                                     format_func=lambda value: value or "Tất cả", key="vehicle_class")
        light = st.selectbox("Trạng thái đèn", [None, "RED", "GREEN", "YELLOW", "UNKNOWN"],
                             format_func=lambda value: value or "Tất cả", key="light_state")
        by_date = st.checkbox("Lọc ngày ghi nhận", key="by_date")
        today = datetime.now(ZoneInfo("Asia/Bangkok")).date()
        date_from = st.date_input("Từ ngày", today, key="date_from") if by_date else None
        date_to = st.date_input("Đến ngày", today, key="date_to") if by_date else None
        search = st.text_input("Tìm ID sự kiện, ID xe hoặc nguồn", key="search")
        page_size = st.selectbox("Số dòng mỗi trang", [25, 50, 100], key="page_size")
        page = int(st.number_input("Trang", min_value=1, step=1, value=1, key="page"))
    if preset in {"Demo lưu trữ", "Video mẫu"}:
        st.warning("Đang xem dữ liệu thử, không phải sự kiện vi phạm thực tế.")
    st.caption("Kết quả nghi vượt đèn đỏ cần kiểm tra lại. Nhận dạng biển số/OCR chưa triển khai.")
    if date_from and date_to and date_from > date_to:
        st.error("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")
        return
    if not database.is_file():
        st.info("Chưa có database ở nguồn đã chọn. Chọn ‘Demo lưu trữ’ hoặc chạy chương trình tracking trước.")
        st.code(r".\.venv\Scripts\python.exe python/storage_demo.py", language="powershell")
        return
    try:
        rows, total, summary = load_events(database, assessment, vehicle_class, light,
                                           date_from, date_to, search, page_size, (page - 1) * page_size)
    except (sqlite3.Error, OSError, ValueError) as exc:
        st.error(f"Không đọc được dữ liệu: {exc}")
        return
    for column, label, value in zip(st.columns(4),
            ["Sự kiện theo bộ lọc", "Nghi vượt đèn đỏ", "Chưa xác minh", "Không có bằng chứng đỏ"],
            [total, summary.get("suspected_red_light", 0), summary.get("unverified", 0), summary.get("no_red_light_evidence", 0)]):
        column.metric(label, value)
    if not rows:
        st.info("Không có sự kiện ở trang này. Thử bỏ bộ lọc hoặc quay về trang 1.")
        return
    st.subheader("Danh sách sự kiện")
    display_rows = [{"ID sự kiện": row["event_id"], "Thời gian": row["observed_at"],
                     "ID xe": row["track_id"], "Loại xe": row["vehicle_class"], "Độ tin cậy": row["confidence"],
                     "Đèn": row["light_state"], "Kết quả": ASSESSMENTS.get(row["assessment"], row["assessment"])} for row in rows]
    st.dataframe(display_rows, hide_index=True, width="stretch")
    st.caption(f"Trang {page} / {max(1, (total + page_size - 1) // page_size)} · {len(rows)} dòng hiển thị / {total} sự kiện phù hợp. Thống kê tính trên toàn bộ kết quả lọc.")
    export = io.StringIO(newline="")
    writer = csv.DictWriter(export, fieldnames=list(display_rows[0]))
    writer.writeheader()
    writer.writerows(display_rows)
    st.download_button("Tải CSV trang hiện tại", export.getvalue().encode("utf-8-sig"), "traffic_events.csv", "text/csv")
    if summary:
        with st.expander("Phân bố kết quả"):
            st.bar_chart({"Số sự kiện": {ASSESSMENTS.get(key, key): value for key, value in summary.items()}})
    st.subheader("Chi tiết và ảnh bằng chứng")
    ids = [row["event_id"] for row in rows]
    selected = st.selectbox("Chọn sự kiện để xem ảnh", ids, key="event_id")
    row = next(row for row in rows if row["event_id"] == selected)
    st.write(f"**Kết quả:** {ASSESSMENTS.get(row['assessment'], row['assessment'])}")
    st.caption(f"Hướng: {row['direction']} · Lý do: {row['assessment_reason']} · Nguồn: {row['source']}")
    try:
        payload = json.loads(row["payload_json"])
        if payload.get("simulation"):
            st.warning("Sự kiện này là giả lập.")
    except (ValueError, TypeError):
        payload = {"error": "Payload JSON không đọc được", "event_id": row["event_id"]}
    for column, key, label in zip(st.columns(3),
            ["raw_image", "annotated_image", "vehicle_image"], ["Ảnh gốc", "Ảnh có khung", "Ảnh cắt xe"]):
        with column:
            st.markdown(f"**{label}**")
            image_path = row.get(key)
            if not image_path:
                st.info("Sự kiện này không lưu ảnh.")
            elif not Path(image_path).is_file():
                st.warning("Không tìm thấy file ảnh. Kiểm tra thư mục bằng chứng.")
            else:
                try:
                    with Image.open(image_path) as image:
                        image.verify()
                    st.image(image_path, width="stretch")
                except (OSError, ValueError) as exc:
                    st.warning(f"Không mở được ảnh: {exc}")
    with st.expander("Thông tin sự kiện đầy đủ"):
        st.json(payload)


if __name__ == "__main__":
    main()
