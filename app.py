import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="My Triton Lab Pro", page_icon="🐠", layout="wide")
SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# --- 1. 인증 (금고에서 꺼내오기) ---
def get_creds():
    # Streamlit Secrets(금고) 확인
    if "gcp_service_account" in st.secrets:
        try:
            # 금고에 있는 'info'를 꺼냅니다.
            return json.loads(st.secrets["gcp_service_account"]["info"], strict=False)
        except Exception as e:
            st.error(f"🚨 금고 설정 오류: {e}")
            st.info("Secrets에 JSON 내용을 정확히 붙여넣었는지 확인해주세요.")
            st.stop()
    else:
        st.error("🚨 비밀 금고(Secrets)가 비어있습니다!")
        st.info("Streamlit 대시보드 > Settings > Secrets 에 키를 넣어주세요.")
        st.stop()

creds_dict = get_creds()

# --- 2. 구글 시트 연결 ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def get_sheet_tabs():
    client = get_client()
    try: sh = client.open(SHEET_NAME)
    except:
        # 이름으로 못 찾으면 주소 입력창 띄우기
        st.warning(f"⚠️ '{SHEET_NAME}' 시트를 못 찾았습니다.")
        sheet_url = st.text_input("👇 구글 시트 주소(URL)를 붙여넣으세요:", key="sheet_url")
        if sheet_url:
            try:
                sh = client.open_by_url(sheet_url)
                st.success("✅ 연결 성공!")
            except:
                st.error("🚨 연결 실패. 로봇을 초대했는지 확인하세요.")
                st.stop()
        else:
            st.stop()

    sheet_log = sh.sheet1
    try:
        if not sheet_log.row_values(1):
            sheet_log.insert_row(HEADERS, index=1)
    except: pass

    try: sheet_config = sh.worksheet("Config")
    except: sheet_config = sh.add_worksheet(title="Config", rows=20, cols=5)
    return sheet_log, sheet_config

# --- 3. 데이터 관리 ---
def load_data():
    sheet_log, _ = get_sheet_tabs()
    rows = sheet_log.get_all_values()
    if len(rows) < 2: return pd.DataFrame(columns=HEADERS)
    df = pd.DataFrame(rows[1:], columns=HEADERS)
    df['_row_idx'] = range(2, len(df) + 2)
    cols = ["KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량"]
    for c in cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

def save_data(entry):
    sheet_log, _ = get_sheet_tabs()
    row = [str(entry["날짜"]), entry["KH"], entry["Ca"], entry["Mg"], entry["NO2"], entry["NO3"], entry["PO4"], entry["pH"], entry["Temp"], entry["Salinity"], entry["도징량"], entry["Memo"]]
    sheet_log.append_row(row)
    return True

def delete_rows_by_indices(rows):
    sheet_log, _ = get_sheet_tabs()
    for i in sorted(rows, reverse=True): sheet_log.delete_rows(i)

# --- 4. 설정 ---
def load_config():
    _, sheet_config = get_sheet_tabs()
    records = sheet_config.get_all_records()
    default = {"volume":150.0,"base_dose":3.00,"t_kh":8.30,"t_ca":420,"t_mg":1420,"t_no2":0.010,"t_no3":5.00,"t_po4":0.040,"t_ph":8.30}
    if not records: return default
    saved = records[0]
    for k,v in default.items(): 
        if k not in saved: saved[k]=v
    return saved

def save_config(conf):
    _, sheet_config = get_sheet_tabs()
    sheet_config.clear()
    sheet_config.append_row(list(conf.keys()))
    sheet_config.append_row(list(conf.values()))

# --- 5. 화면 ---
st.title("🌊 My Triton Manager")

if "config" not in st.session_state: st.session_state.config = load_config()
cfg = st.session_state.config

with st.sidebar:
    st.header("⚙️ 설정")
    volume = st.number_input("물량", value=float(cfg["volume"]), step=0.1)
    base_dose = st.number_input("도징량", value=float(cfg["base_dose"]), step=0.01)
    st.divider()
    t_kh = st.number_input("목표 KH", value=float(cfg["t_kh"]), step=0.01)
    # (나머지 목표치 입력 생략 - 필요시 추가 가능)
    if st.button("💾 설정 저장"):
        new_conf = cfg.copy()
        new_conf.update({"volume":volume, "base_dose":base_dose, "t_kh":t_kh})
        save_config(new_conf)
        st.session_state.config = new_conf
        st.toast("저장 완료!"); st.rerun()

st.success("✅ 구글 시트 연결됨")

with st.expander("📝 기록 입력", expanded=False):
    with st.form("entry"):
        c1,c2 = st.columns(2)
        d_date = c1.date_input("날짜", date.today())
        d_kh = c2.number_input("KH", value=t_kh, step=0.01)
        # (필요한 입력 필드들)
        d_memo = st.text_area("메모")
        if st.form_submit_button("저장"):
            # 데이터 저장 로직
            entry = {"날짜":d_date, "KH":d_kh, "Ca":0, "Mg":0, "NO2":0, "NO3":0, "PO4":0, "pH":0, "Temp":0, "Salinity":0, "도징량":base_dose, "Memo":d_memo}
            save_data(entry)
            st.toast("저장됨!"); st.rerun()

st.divider()
df = load_data()
if not df.empty:
    # 표 및 삭제 기능
    st.subheader("📋 기록 관리")
    df_show = df.sort_values("날짜", ascending=False).copy()
    df_show.insert(0, "삭제", False)
    
    edited = st.data_editor(
        df_show, 
        column_config={"삭제":st.column_config.CheckboxColumn("선택"), "_row_idx":None},
        disabled=HEADERS, hide_index=True, use_container_width=True
    )
    
    if st.button("🗑️ 선택 삭제"):
        to_del = edited[edited["삭제"]==True]["_row_idx"].tolist()
        if to_del:
            delete_rows_by_indices(to_del)
            st.toast("삭제 완료!"); st.rerun()
