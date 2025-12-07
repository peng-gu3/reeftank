import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 페이지 설정 (넓은 화면 사용) ---
st.set_page_config(page_title="Reef Manager Pro", page_icon="🐠", layout="wide")

SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# --- 1. 인증 (코드에 키 없음! 오직 Secrets만 사용) ---
def get_creds():
    # Streamlit Secrets 확인
    if "gcp_service_account" not in st.secrets:
        st.error("🚨 **치명적 오류: Secrets 설정이 없습니다!**")
        st.info("Streamlit 홈페이지 > 앱 설정(Settings) > Secrets 메뉴에 키를 붙여넣어 주세요.")
        st.stop()

    # Secrets에서 정보 가져오기
    secrets_data = st.secrets["gcp_service_account"]
    
    # 딕셔너리로 변환 (info 방식 or 개별 방식 모두 호환)
    if "info" in secrets_data:
        try:
            return json.loads(secrets_data["info"], strict=False)
        except:
            st.error("🚨 Secrets JSON 형식이 깨졌습니다.")
            st.stop()
    return dict(secrets_data)

creds_dict = get_creds()

# --- 2. 구글 시트 연결 ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=60) # 60초마다 데이터 갱신 (속도 향상)
def load_data_cached():
    client = get_client()
    try:
        sh = client.open(SHEET_NAME)
    except:
        return None, None

    sheet_log = sh.sheet1
    # 헤더 확인 및 생성
    try:
        if not sheet_log.row_values(1): sheet_log.insert_row(HEADERS, index=1)
    except: pass

    # 설정 시트
    try: sheet_config = sh.worksheet("Config")
    except: sheet_config = sh.add_worksheet(title="Config", rows=20, cols=5)
    
    # 데이터 가져오기
    rows = sheet_log.get_all_values()
    if len(rows) < 2: 
        df = pd.DataFrame(columns=HEADERS)
    else:
        df = pd.DataFrame(rows[1:], columns=HEADERS)
        
    # 숫자 변환
    cols_to_num = ["KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량"]
    for c in cols_to_num:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    
    # 행 번호(삭제용)
    df['_row_idx'] = range(2, len(df) + 2)
    
    return df, sheet_config

# 데이터 로드 (캐시 사용 안함 - 즉시 반영 위해 래퍼 함수 사용)
def load_data_fresh():
    st.cache_data.clear()
    return load_data_cached()

# 저장 함수
def save_entry(entry):
    client = get_client()
    sh = client.open(SHEET_NAME)
    sheet_log = sh.sheet1
    row = [str(entry["날짜"]), entry["KH"], entry["Ca"], entry["Mg"], entry["NO2"], entry["NO3"], entry["PO4"], entry["pH"], entry["Temp"], entry["Salinity"], entry["도징량"], entry["Memo"]]
    sheet_log.append_row(row)
    st.cache_data.clear() # 캐시 초기화

# 삭제 함수
def delete_rows(indices):
    client = get_client()
    sh = client.open(SHEET_NAME)
    sheet_log = sh.sheet1
    for idx in sorted(indices, reverse=True):
        sheet_log.delete_rows(idx)
    st.cache_data.clear()

# 설정 관리
def manage_config(sheet_config, mode="load", new_conf=None):
    default = {"volume":150.0,"base_dose":3.00,"t_kh":8.30,"t_ca":420,"t_mg":1420,"t_no2":0.010,"t_no3":5.00,"t_po4":0.040,"t_ph":8.30, "schedule":""}
    
    if mode == "load":
        records = sheet_config.get_all_records()
        if not records: return default
        saved = records[0]
        for k, v in default.items():
            if k not in saved: saved[k] = v
        return saved
    elif mode == "save":
        sheet_config.clear()
        sheet_config.append_row(list(new_conf.keys()))
        sheet_config.append_row(list(new_conf.values()))
        st.cache_data.clear()

# --- 3. UI 및 로직 ---

# 데이터 불러오기 시도
df, sheet_config = load_data_cached()

if df is None:
    st.error(f"🚨 구글 시트 '{SHEET_NAME}'를 찾을 수 없습니다. (공유 확인 필요)")
    st.stop()

# 설정 로드
if "config" not in st.session_state:
    st.session_state.config = manage_config(sheet_config, "load")
cfg = st.session_state.config

# --- [사이드바] 설정 ---
with st.sidebar:
    st.title("⚙️ 목표 설정")
    volume = st.number_input("물량 (L)", value=float(cfg["volume"]), step=0.1)
    base_dose = st.number_input("기본 도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    st.divider()
    st.caption("목표 수치")
    t_kh = st.number_input("KH", value=float(cfg["t_kh"]), step=0.01)
    t_ca = st.number_input("Ca", value=int(cfg["t_ca"]), step=10)
    t_mg = st.number_input("Mg", value=int(cfg["t_mg"]), step=10)
    # (나머지 생략 가능)
    
    if st.button("💾 설정 저장", use_container_width=True):
        new_conf = cfg.copy()
        new_conf.update({"volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, "t_mg":t_mg})
        manage_config(sheet_config, "save", new_conf)
        st.session_state.config = new_conf
        st.toast("설정 저장됨!")

# --- [메인 화면] 탭 구성 ---
st.title("🐠 My Reef Manager")

# 탭으로 화면 분할 (깔끔하게!)
tab1, tab2, tab3 = st.tabs(["📊 대시보드 & 입력", "📅 스케줄 관리", "📋 기록 데이터 (삭제)"])

# === 탭 1: 대시보드 & 입력 ===
with tab1:
    # 1. 최신 상태 요약 (Metrics)
    if not df.empty:
        last = df.iloc[-1]
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("KH (경도)", f"{last['KH']}", f"{last['KH']-float(cfg['t_kh']):.2f}")
        col_m2.metric("Ca (칼슘)", f"{last['Ca']}", f"{last['Ca']-int(cfg['t_ca'])}")
        col_m3.metric("Mg (마그네슘)", f"{last['Mg']}", f"{last['Mg']-int(cfg['t_mg'])}")
        col_m4.metric("Temp (온도)", f"{last['Temp']}°C")
    
    st.divider()

    # 2. 입력 및 그래프 (좌우 배치)
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("📝 오늘의 측정값 입력")
        with st.form("main_entry"):
            c1, c2 = st.columns(2)
            d_date = c1.date_input("날짜", date.today())
            d_kh = c2.number_input("KH", value=float(cfg["t_kh"]), step=0.01)
            
            c3, c4 = st.columns(2)
            d_ca = c3.number_input("Ca", value=int(cfg["t_ca"]), step=10)
            d_mg = c4.number_input("Mg", value=int(cfg["t_mg"]), step=10)
            
            c5, c6 = st.columns(2)
            d_no3 = c5.number_input("NO3", value=float(cfg["t_no3"]), step=0.1)
            d_po4 = c6.number_input("PO4", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
            
            # (나머지 항목들은 기본값 처리하거나 필요시 추가)
            d_ph = 8.3; d_temp = 25.0; d_sal = 35.0; d_no2 = 0.0
            
            d_memo = st.text_area("메모", height=80)
            
            if st.form_submit_button("기록 저장 💾", type="primary"):
                entry = {"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":d_no2,"NO3":d_no3,"PO4":d_po4,"pH":d_ph,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
                save_entry(entry)
                st.toast("저장되었습니다!"); st.rerun()

    with col_right:
        st.subheader("🤖 AI 분석 & 그래프")
        if not df.empty:
            # 원형 그래프
            def draw_radar(cats, vals, t_vals, title):
                norm_vals = [v/t if t>0 else 0 for v,t in zip(vals, t_vals)]
                cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line_color="gray", line_dash='dot', name='목표'))
                fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', line_color="#00FFAA", name='내 수조'))
                fig.update_layout(polar=dict(radialaxis=dict(visible=False)), margin=dict(t=20,b=20), height=300)
                return fig
            
            st.plotly_chart(draw_radar(["KH","Ca","Mg"], [last['KH'],last['Ca'],last['Mg']], [cfg['t_kh'],cfg['t_ca'],cfg['t_mg']], "3요소"), use_container_width=True)
            
            # AI 조언
            kh_diff = last["KH"] - float(cfg["t_kh"])
            vol_factor = volume / 100.0
            if abs(kh_diff) <= 0.15: st.success(f"✅ 수질 상태가 아주 좋습니다.")
            elif kh_diff < 0: st.error(f"📉 KH 부족! 도징량을 {base_dose + 0.3*vol_factor:.1f}ml로 늘리세요.")
            else: st.warning(f"📈 KH 과다! 도징량을 {max(0, base_dose - 0.3*vol_factor):.1f}ml로 줄이세요.")

# === 탭 2: 스케줄 관리 ===
with tab2:
    st.subheader("📅 관리 스케줄 (자동 저장)")
    current_sch = cfg.get("schedule", "")
    new_sch = st.text_area("주간 계획을 자유롭게 작성하세요", value=current_sch, height=300)
    
    if st.button("💾 스케줄 업데이트", type="primary"):
        new_conf = cfg.copy()
        new_conf["schedule"] = new_sch
        manage_config(sheet_config, "save", new_conf)
        st.session_state.config = new_conf
        st.toast("스케줄이 저장되었습니다!")

# === 탭 3: 기록 데이터 (엑셀형 + 삭제) ===
with tab3:
    st.subheader("📋 전체 기록 관리")
    if not df.empty:
        df_show = df.sort_values("날짜", ascending=False).copy()
        df_show.insert(0, "삭제", False) # 체크박스 컬럼 추가
        
        # 엑셀 스타일 편집기
        edited = st.data_editor(
            df_show,
            column_config={
                "삭제": st.column_config.CheckboxColumn("선택", width="small"),
                "_row_idx": None,
                "Memo": st.column_config.TextColumn("메모", width="large")
            },
            disabled=HEADERS, 
            hide_index=True, 
            use_container_width=True
        )
        
        col_btn, _ = st.columns([1, 4])
        if col_btn.button("🗑️ 선택한 기록 삭제하기", type="primary"):
            to_del = edited[edited["삭제"]==True]["_row_idx"].tolist()
            if to_del:
                delete_rows(to_del)
                st.toast("삭제 완료!"); st.rerun()
            else:
                st.warning("삭제할 항목을 선택해주세요.")
    else:
        st.info("아직 기록이 없습니다.")
