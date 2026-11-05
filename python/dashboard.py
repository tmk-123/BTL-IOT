"""Read-only local workspace for suspected traffic violations and evidence."""

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
    'suspected_red_light': 'Nghi vượt đèn đỏ',
    'no_red_light_evidence': 'Không có bằng chứng đèn đỏ',
    'unverified': 'Chưa xác minh',
    'not_applicable_direction': 'Không xét chiều này',
}
OCR_STATUSES = {'consensus': 'Có đồng thuận', 'pending': 'Chưa ổn định',
                'ambiguous': 'Ghép biển mơ hồ', 'no_plate': 'Không thấy biển',
                'not_enabled': 'Chưa bật OCR'}
VEHICLES = {'car': 'Ô tô', 'motorcycle': 'Xe máy', 'bus': 'Xe buýt', 'truck': 'Xe tải', 'bicycle': 'Xe đạp'}
LIGHTS = {'RED': 'Đỏ', 'YELLOW': 'Vàng', 'GREEN': 'Xanh', 'UNKNOWN': 'Chưa có dữ liệu'}
PRESETS = {
    'Dữ liệu chạy thật': ROOT / 'data/traffic.db',
    'Demo lưu trữ': ROOT / 'data/demos/storage/traffic.db',
    'Video mẫu': ROOT / 'data/demos/storage_pipeline/traffic.db',
    'Video biển số': ROOT / 'data/demos/plate_pipeline/traffic.db',
    'Demo giao diện': ROOT / 'data/demos/dashboard/traffic.db',
    'Camera + đèn giả lập': ROOT / 'data/demos/live_simulation/traffic.db',
    'Đường dẫn khác': None,
}


def display_time(value):
    try:
        moment = datetime.fromisoformat(value)
        if moment.tzinfo is not None:
            moment = moment.astimezone(ZoneInfo('Asia/Bangkok'))
        return moment.strftime('%d/%m/%Y %H:%M:%S')
    except (TypeError, ValueError):
        return str(value)


def show_image(row, key, label):
    st.markdown(f'**{label}**')
    image_path = row.get(key)
    if not image_path:
        st.info('Chưa có ảnh ở mục này.')
    elif not Path(image_path).is_file():
        st.warning('Không tìm thấy file ảnh. Kiểm tra thư mục bằng chứng.')
    else:
        try:
            with Image.open(image_path) as image:
                image.verify()
            st.image(image_path, width='stretch')
        except (OSError, ValueError) as error:
            st.warning(f'Không mở được ảnh: {error}')


def main():
    st.set_page_config(page_title='Xe nghi vi phạm | Giám sát giao thông', page_icon='🚦', layout='wide')
    st.markdown('''<style>
        .block-container {max-width: 1480px; padding-top: 2rem; padding-bottom: 3rem;}
        h1 {letter-spacing: -0.035em;}
        [data-testid="stMetricValue"] {font-size: 2rem;}
    </style>''', unsafe_allow_html=True)
    st.caption('GIÁM SÁT GIAO THÔNG  /  HỒ SƠ SỰ KIỆN')
    st.title('Xe nghi vi phạm')
    st.write('Tra cứu biển số, đối chiếu thời điểm qua vạch và xem ảnh bằng chứng.')
    default = ('Dữ liệu chạy thật' if PRESETS['Dữ liệu chạy thật'].is_file()
               else 'Demo giao diện' if PRESETS['Demo giao diện'].is_file()
               else 'Video biển số' if PRESETS['Video biển số'].is_file() else 'Dữ liệu chạy thật')
    with st.sidebar:
        st.header('Dữ liệu giám sát')
        preset = st.selectbox('Chọn dữ liệu', list(PRESETS), index=list(PRESETS).index(default), key='dataset')
        database = PRESETS[preset]
        if database is None:
            database = Path(st.text_input('Đường dẫn SQLite', str(ROOT / 'data/traffic.db'), key='database'))
        st.button('Làm mới dữ liệu', width='stretch')
        view = st.radio('Hiển thị', ['Nghi vi phạm', 'Tất cả sự kiện'], key='view')
        st.divider()
        st.subheader('Bộ lọc')
        assessment = ('suspected_red_light' if view == 'Nghi vi phạm' else
                      st.selectbox('Kết quả', [None, *ASSESSMENTS],
                                   format_func=lambda value: ASSESSMENTS.get(value, 'Tất cả'), key='assessment'))
        vehicle_class = st.selectbox('Loại xe', [None, *VEHICLES],
                                     format_func=lambda value: VEHICLES.get(value, 'Tất cả'), key='vehicle_class')
        light = st.selectbox('Trạng thái đèn', [None, *LIGHTS],
                             format_func=lambda value: LIGHTS.get(value, 'Tất cả'), key='light_state')
        by_date = st.checkbox('Lọc theo ngày', key='by_date')
        today = datetime.now(ZoneInfo('Asia/Bangkok')).date()
        date_from = st.date_input('Từ ngày', today, key='date_from') if by_date else None
        date_to = st.date_input('Đến ngày', today, key='date_to') if by_date else None
        page_size = st.selectbox('Số dòng mỗi trang', [25, 50, 100], key='page_size')
    if preset in {'Demo lưu trữ', 'Video mẫu', 'Video biển số', 'Demo giao diện', 'Camera + đèn giả lập'}:
        st.warning('DỮ LIỆU DEMO — dùng để thử giao diện, không phải hồ sơ vi phạm thực tế.')
    search = st.text_input('Tìm biển số hoặc mã sự kiện', placeholder='Ví dụ: 29A33185', key='search')
    signature = (str(database), assessment, vehicle_class, light, str(date_from), str(date_to), search, page_size)
    if st.session_state.get('_filters') != signature:
        st.session_state['page'] = 1
        st.session_state['_filters'] = signature
    with st.sidebar:
        page = int(st.number_input('Trang', min_value=1, step=1, key='page'))
        st.caption('Ảnh quét biển đơn lẻ không tự trở thành sự kiện vi phạm.')
    if date_from and date_to and date_from > date_to:
        st.error('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')
        return
    if not database.is_file():
        st.info('Chưa có dữ liệu ở nguồn đã chọn. Bạn có thể chọn Demo giao diện để xem mẫu.')
        st.code(r'.\.venv\Scripts\python.exe python/dashboard_demo.py', language='powershell')
        return
    try:
        rows, total, summary = load_events(database, assessment, vehicle_class, light,
                                           date_from, date_to, search.strip(), page_size, (page-1)*page_size)
    except (sqlite3.Error, OSError, ValueError) as error:
        st.error(f'Không đọc được dữ liệu: {error}')
        return
    for column, label, value in zip(st.columns(4),
            ['Sự kiện theo bộ lọc', 'Nghi vượt đèn đỏ', 'Chưa xác minh', 'Không có bằng chứng đỏ'],
            [total, summary.get('suspected_red_light', 0), summary.get('unverified', 0), summary.get('no_red_light_evidence', 0)]):
        with column.container(border=True):
            st.metric(label, value)
    st.subheader('Danh sách nghi vi phạm' if view == 'Nghi vi phạm' else 'Tất cả sự kiện')
    if not rows:
        st.info('Không có sự kiện phù hợp. Thử bỏ bộ lọc, tìm biển khác hoặc chọn Tất cả sự kiện.')
        return
    display_rows = [{'Thời gian': display_time(row['observed_at']), 'Biển số': row.get('plate_text') or 'Chưa đọc được',
                     'Loại xe': VEHICLES.get(row['vehicle_class'], row['vehicle_class']),
                     'Trạng thái đèn': LIGHTS.get(row['light_state'], row['light_state']),
                     'Kết quả': ASSESSMENTS.get(row['assessment'], row['assessment']),
                     'Đọc biển': OCR_STATUSES.get(row.get('plate_status'), 'Chưa bật OCR')} for row in rows]
    st.dataframe(display_rows, hide_index=True, width='stretch')
    st.caption(f'Trang {page} / {max(1, (total+page_size-1)//page_size)} · {len(rows)} dòng / {total} sự kiện phù hợp.')
    export = io.StringIO(newline='')
    writer = csv.DictWriter(export, fieldnames=list(display_rows[0]))
    writer.writeheader()
    writer.writerows(display_rows)
    st.download_button('Tải CSV trang hiện tại', export.getvalue().encode('utf-8-sig'), 'traffic_events.csv', 'text/csv')
    st.divider()
    st.subheader('Chi tiết sự kiện')
    by_id = {row['event_id']: row for row in rows}
    selected = st.selectbox('Chọn sự kiện để xem ảnh', list(by_id), key='event_id',
                            format_func=lambda identity: f"{by_id[identity].get('plate_text') or 'Chưa đọc được biển'} · {display_time(by_id[identity]['observed_at'])} · Xe #{by_id[identity]['track_id']}")
    row = by_id[selected]
    try:
        payload = json.loads(row['payload_json'])
        if payload.get('simulation'):
            st.warning('Sự kiện giả lập: dùng để minh họa giao diện; không dùng làm bằng chứng vi phạm.')
    except (ValueError, TypeError):
        payload = {'error': 'Payload JSON không đọc được', 'event_id': row['event_id']}
    if row['assessment'] == 'suspected_red_light':
        st.warning('Nghi vượt đèn đỏ — cần đối chiếu ảnh và thời điểm trước khi xác nhận.')
    else:
        st.info(ASSESSMENTS.get(row['assessment'], row['assessment']))
    evidence, details = st.columns([2, 1], gap='large')
    with evidence:
        show_image(row, 'annotated_image', 'Xe tại vạch và trạng thái ghi nhận')
    with details:
        st.subheader(row.get('plate_text') or 'Chưa đọc được biển')
        st.write(f"**Thời gian:** {display_time(row['observed_at'])}")
        st.write(f"**Loại xe:** {VEHICLES.get(row['vehicle_class'], row['vehicle_class'])}")
        st.write(f"**Đèn:** {LIGHTS.get(row['light_state'], row['light_state'])}")
        st.write(f"**Đọc biển:** {OCR_STATUSES.get(row.get('plate_status'), 'Chưa bật OCR')}")
        show_image(row, 'plate_image', 'Ảnh biển số')
        if row.get('plate_vote_share') is not None:
            st.caption(f"Tỷ lệ đồng thuận OCR: {row['plate_vote_share']:.0%}. Đây không phải xác suất biển số đúng.")
    with st.expander('Ảnh gốc và ảnh cắt xe'):
        original, vehicle = st.columns(2)
        with original: show_image(row, 'raw_image', 'Ảnh toàn cảnh gốc')
        with vehicle: show_image(row, 'vehicle_image', 'Ảnh cắt xe')
    with st.expander('Thông tin kỹ thuật của sự kiện'):
        st.write(f"Mã sự kiện: {row['event_id']}")
        st.write(f"Nguồn: {row['source']}")
        st.write(f"Lý do phân loại: {row['assessment_reason']}")
        st.json(payload)


if __name__ == '__main__':
    main()
