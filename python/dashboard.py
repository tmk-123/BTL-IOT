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
from light_state import SUSPECTED_ASSESSMENTS

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENTS = {
    'suspected_red_light': 'Nghi vượt đèn đỏ',
    'suspected_yellow_light': 'Nghi vượt đèn vàng',
    'no_red_light_evidence': 'Không có bằng chứng đèn đỏ',
    'unverified': 'Chưa xác minh',
    'not_applicable_direction': 'Không xét chiều này',
}
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


@st.dialog('Chi tiết vi phạm', width='large')
def show_event_details(row):
    """Open the evidence belonging to the clicked event, including duplicate plates."""
    try:
        payload = json.loads(row.get('payload_json') or '{}')
    except (ValueError, TypeError):
        payload = {}
    if isinstance(payload, dict) and payload.get('simulation'):
        st.warning('Sự kiện giả lập: dùng để minh họa giao diện; không dùng làm bằng chứng vi phạm.')
    if row['assessment'] in SUSPECTED_ASSESSMENTS:
        st.warning(f"{ASSESSMENTS[row['assessment']]} — cần đối chiếu ảnh và thời điểm trước khi xác nhận.")
    else:
        st.info(ASSESSMENTS.get(row['assessment'], row['assessment']))
    evidence, details = st.columns([2, 1], gap='large')
    with evidence:
        show_image(row, 'annotated_image', 'Ảnh ghi nhận tại vạch')
    with details:
        st.subheader(row.get('plate_text') or 'Chưa đọc được biển')
        st.write(f"**Thời gian:** {display_time(row['observed_at'])}")
        st.write(f"**Đèn lúc qua vạch:** {LIGHTS.get(row['light_state'], row['light_state'])}")
        show_image(row, 'plate_image', 'Ảnh biển số')
    with st.expander('Xem ảnh gốc và ảnh xe'):
        original, vehicle = st.columns(2)
        with original:
            show_image(row, 'raw_image', 'Ảnh toàn cảnh gốc')
        with vehicle:
            show_image(row, 'vehicle_image', 'Ảnh cắt xe')


def main():
    st.set_page_config(page_title='Xe nghi vi phạm | Giám sát giao thông', page_icon='🚦', layout='wide')
    st.markdown('''<style>
        .block-container {max-width: 1480px; padding-top: 2rem; padding-bottom: 3rem;}
        h1 {letter-spacing: -0.035em;}
        [data-testid="stMetricValue"] {font-size: 2rem;}
        .st-key-event_list button {justify-content: flex-start; text-align: left; min-height: 3.4rem;}
        .st-key-event_list button p {text-align: left;}
    </style>''', unsafe_allow_html=True)
    st.caption('GIÁM SÁT GIAO THÔNG  /  HỒ SƠ SỰ KIỆN')
    st.title('Xe nghi vi phạm')
    st.write('Tra cứu biển số, đối chiếu thời điểm qua vạch và xem ảnh bằng chứng.')
    default = ('Dữ liệu chạy thật' if PRESETS['Dữ liệu chạy thật'].is_file()
               else 'Demo giao diện' if PRESETS['Demo giao diện'].is_file()
               else 'Video biển số' if PRESETS['Video biển số'].is_file() else 'Dữ liệu chạy thật')
    with st.sidebar:
        st.button('Làm mới dữ liệu', width='stretch')
        with st.expander('Nhật ký kiểm tra'):
            journal = st.checkbox('Xem tất cả sự kiện', key='show_journal')
            st.caption('Xem thêm lượt qua lúc xanh, chưa xác minh và các bản ghi cũ.')
            journal_assessment = (st.selectbox('Loại ghi nhận', [None, *ASSESSMENTS],
                                  format_func=lambda value: ASSESSMENTS.get(value, 'Tất cả'),
                                  key='journal_assessment') if journal else None)
        with st.expander('Cài đặt'):
            preset = st.selectbox('Chọn dữ liệu', list(PRESETS), index=list(PRESETS).index(default), key='dataset')
            database = PRESETS[preset]
            if database is None:
                database = Path(st.text_input('Đường dẫn SQLite', str(ROOT / 'data/traffic.db'), key='database'))
            by_date = st.checkbox('Lọc theo ngày', key='by_date')
            today = datetime.now(ZoneInfo('Asia/Bangkok')).date()
            date_from = st.date_input('Từ ngày', today, key='date_from') if by_date else None
            date_to = st.date_input('Đến ngày', today, key='date_to') if by_date else None
    assessment = journal_assessment if journal else SUSPECTED_ASSESSMENTS
    if preset in {'Demo lưu trữ', 'Video mẫu', 'Video biển số', 'Demo giao diện', 'Camera + đèn giả lập'}:
        st.warning('DỮ LIỆU DEMO — dùng để thử giao diện, không phải hồ sơ vi phạm thực tế.')
    summary_slot = st.container()
    search_column, light_column = st.columns([3, 1])
    with search_column:
        search = st.text_input('Tìm biển số', placeholder='Ví dụ: 29A22222', key='search')
    with light_column:
        light = st.selectbox('Màu đèn', [None, 'RED', 'YELLOW'],
                             format_func=lambda value: LIGHTS.get(value, 'Tất cả'), key='violation_color')
    page_size = st.session_state.get('page_size', 25)
    signature = (str(database), journal, assessment, light, str(date_from), str(date_to), search, page_size)
    if st.session_state.get('_filters') != signature:
        st.session_state['page'] = 1
        st.session_state['_filters'] = signature
    page = int(st.session_state.get('page', 1))
    if date_from and date_to and date_from > date_to:
        st.error('Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.')
        return
    if not database.is_file():
        st.info('Chưa có dữ liệu ở nguồn đã chọn. Chạy camera rồi bấm Làm mới dữ liệu.')
        return
    try:
        filters = dict(assessment=assessment, light_state=light, date_from=date_from, date_to=date_to,
                       search=search.strip(), limit=page_size, plate_only=True)
        rows, total, summary = load_events(database, **filters, offset=(page-1)*page_size)
        last_page = max(1, (total+page_size-1)//page_size)
        if page > last_page:
            page = last_page
            st.session_state['page'] = page
            rows, total, summary = load_events(database, **filters, offset=(page-1)*page_size)
    except (sqlite3.Error, OSError, ValueError) as error:
        st.error(f'Không đọc được dữ liệu: {error}')
        return
    suspected_total = sum(summary.get(kind, 0) for kind in SUSPECTED_ASSESSMENTS)
    with summary_slot:
        with st.container(border=True):
            st.metric('Tổng lượt nghi vượt đèn', suspected_total, help='Số lượt đỏ và vàng theo bộ lọc hiện tại.')
    st.subheader('Nhật ký kiểm tra' if journal else 'Danh sách nghi vượt đèn')
    if not rows:
        st.info('Không có lượt ghi nhận phù hợp. Thử chọn Tất cả màu đèn, bỏ tìm kiếm hoặc mở Nhật ký kiểm tra.')
        return
    display_rows = [{'Thời gian': display_time(row['observed_at']), 'Biển số': row.get('plate_text') or 'Chưa đọc được',
                     'Trạng thái đèn': LIGHTS.get(row['light_state'], row['light_state']),
                     'Kết quả': ASSESSMENTS.get(row['assessment'], row['assessment'])} for row in rows]
    st.caption('Bấm vào một dòng để xem chi tiết và ảnh bằng chứng.')
    with st.container(key='event_list'):
        for row, display in zip(rows, display_rows):
            label = f"**{display['Biển số']}** · {display['Thời gian']} · {display['Kết quả']}"
            if st.button(label, key=f"details:{row['event_id']}", width='stretch',
                         icon=':material/description:', help='Mở chi tiết và ảnh của lần ghi nhận này'):
                show_event_details(row)
    st.caption(f'{len(rows)} / {total} lượt ghi nhận' + (f' · Trang {page}/{last_page}' if last_page > 1 else ''))
    if total > 25:
        page_column, size_column = st.columns(2)
        with page_column:
            if last_page > 1:
                st.number_input('Trang', min_value=1, max_value=last_page, step=1, key='page')
        with size_column:
            st.selectbox('Số dòng mỗi trang', [25, 50, 100], key='page_size')
    export = io.StringIO(newline='')
    writer = csv.DictWriter(export, fieldnames=list(display_rows[0]))
    writer.writeheader()
    writer.writerows(display_rows)
    with st.expander('Xuất dữ liệu'):
        st.download_button('Tải CSV trang hiện tại', export.getvalue().encode('utf-8-sig'), 'traffic_events.csv', 'text/csv')


if __name__ == '__main__':
    main()
