import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="My Triton Lab", page_icon="🧪", layout="wide")

# --- 🎨 CSS: 보내주신 HTML 디자인 이식 (Deep Dark & Neon) ---
st.markdown("""
<style>
    /* 1. 폰트 및 전체 배경 (Deep Navy) */
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
        color: #eef6ff;
    }
    
    /* 메인 배경색 */
    .stApp {
        background-color: #0c1236;
        background-image: radial-gradient(circle at 18% 22%, #1c3f8d 0%, #0c1236 45%);
        background-attachment: fixed;
    }

    /* 2. 카드 박스 스타일 (Glassmorphism + Navy) */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #10244a;
        border: 1px solid #2a416a;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    /* 3. 제목 및 텍스트 색상 */
    h1, h2, h3 {
        color: #4be8ff !important; /* 네온 시안 */
        text-shadow: 0 0 10px rgba(75, 232, 255, 0.3);
    }
    p, label, span {
        color: #eef6ff !important;
    }

    /* 4. 입력창 스타일 (어둡게) */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
        background-color: #080c24 !important;
        color: #4be8ff !important;
        border: 1px solid #2a416a !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #4be8ff !important;
        box-shadow: 0 0 5px rgba(75, 232, 255, 0.5);
    }

    /* 5. 버튼 스타일 (그라데이션 네온) */
    .stButton > button {
        background: linear-gradient(135deg, #4be8ff, #1c3f8d) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        transition: transform 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(75, 232, 255, 0.4);
    }

    /* 6. 데이터프레임 (표) 스타일 */
    [data-testid="stDataFrame"] {
        background-color: #10244a;
        border: 1px solid #2a416a;
    }
    
    /* 7. 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #080c24;
        border-right: 1px solid #2a416a;
    }
    
    /* 8. 메트릭(수치) 스타일 */
    [data-testid="stMetricValue"] {
        color: #a4ff9c !important; /* 연두색 포인트 */
        font-family: 'Pretendard';
    }
    [data-testid="stMetricLabel"] {
        color: #a9bdd6 !important;
    }
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# --- 1. 인증 (Secrets만 사용) ---
def get_creds():
    if "gcp_service_account" not in st.secrets:
        st.error("🚨 **비밀 금고(Secrets)가 비어있습니다!**")
        st.stop()
    
    secrets_data = st.secrets["gcp_service_account"]
    if "info" in secrets_data:
        try: return json.loads(secrets_data["info"], strict=False)
        except: st.error("🚨 Secrets JSON 형식 오류"); st.stop()
    return dict(secrets_data)

creds_dict = get_creds()

# --- 2. 구글 시트 연결 ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_data_cached():
    client = get_client()
    try: sh = client.open(SHEET_NAME)
    except: return None, None

    sheet_log = sh.sheet1
    try:
        if not sheet_log.row_values(1): sheet_log.insert_row(HEADERS, index=1)
    except: pass

    try: sheet_config = sh.worksheet("Config")
    except: sheet_config = sh.add_worksheet(title="Config", rows=20, cols=5)
    
    rows = sheet_log.get_all_values()
    if len(rows) < 2: df = pd.DataFrame(columns=HEADERS)
    else: df = pd.DataFrame(rows[1:], columns=HEADERS)
    
    cols = ["KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량"]
    for c in cols:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df['_row_idx'] = range(2, len(df) + 2)
    return df, sheet_config

def save_entry(entry):
    client = get_client(); sh = client.open(SHEET_NAME); sheet_log = sh.sheet1
    row = [str(entry["날짜"]), entry["KH"], entry["Ca"], entry["Mg"], entry["NO2"], entry["NO3"], entry["PO4"], entry["pH"], entry["Temp"], entry["Salinity"], entry["도징량"], entry["Memo"]]
    sheet_log.append_row(row)
    st.cache_data.clear()

def delete_rows(indices):
    client = get_client(); sh = client.open(SHEET_NAME); sheet_log = sh.sheet1
    for idx in sorted(indices, reverse=True): sheet_log.delete_rows(idx)
    st.cache_data.clear()

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

# --- 3. 메인 화면 ---
df, sheet_config = load_data_cached()

if df is None:
    st.error(f"🚨 구글 시트 '{SHEET_NAME}'를 찾을 수 없습니다.")
    st.stop()

if "config" not in st.session_state:
    st.session_state.config = manage_config(sheet_config, "load")
cfg = st.session_state.config

# --- 사이드바 (설정) ---
with st.sidebar:
    st.markdown("## ⚙️ SYSTEM SETUP")
    volume = st.number_input("물량 (L)", value=float(cfg["volume"]), step=0.1)
    base_dose = st.number_input("기본 도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    st.markdown("---")
    st.markdown("### 🎯 TARGETS")
    t_kh = st.number_input("KH (Target)", value=float(cfg["t_kh"]), step=0.01)
    t_ca = st.number_input("Ca (Target)", value=int(cfg["t_ca"]), step=10)
    t_mg = st.number_input("Mg (Target)", value=int(cfg["t_mg"]), step=10)
    t_no3 = st.number_input("NO3 (Target)", value=float(cfg["t_no3"]), step=0.1)
    t_po4 = st.number_input("PO4 (Target)", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
    
    if st.button("💾 SAVE CONFIG", use_container_width=True):
        new_conf = cfg.copy()
        new_conf.update({"volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, "t_mg":t_mg, "t_no3":t_no3, "t_po4":t_po4})
        manage_config(sheet_config, "save", new_conf)
        st.session_state.config = new_conf
        st.toast("설정이 저장되었습니다!")

# --- 메인 헤더 ---
st.title("🧪 My Triton Lab")
st.caption(f"Last Update: {date.today()}")

# --- 상단 대시보드 (주요 수치 카드) ---
if not df.empty:
    last = df.iloc[-1]
    
    # 카드형 레이아웃을 위한 컨테이너
    with st.container():
        col1, col2, col3, col4, col5 = st.columns(5)
        # 각 컬럼에 메트릭 표시 (CSS로 색상 자동 적용됨)
        col1.metric("KH", f"{last['KH']}", f"{last['KH']-float(cfg['t_kh']):.2f}")
        col2.metric("Ca", f"{last['Ca']}", f"{last['Ca']-int(cfg['t_ca'])}")
        col3.metric("Mg", f"{last['Mg']}", f"{last['Mg']-int(cfg['t_mg'])}")
        col4.metric("NO3", f"{last['NO3']}")
        col5.metric("PO4", f"{last['PO4']}")

    st.markdown("---")

    # --- 그래프 & AI 분석 ---
    c_left, c_right = st.columns([1.2, 0.8])
    
    with c_left:
        st.markdown("### 📊 Parameter Radar")
        
        # 다크모드 전용 레이더 차트 함수
        def draw_dark_radar(cats, vals, t_vals):
            norm_vals = [v/t if t>0 else 0 for v,t in zip(vals, t_vals)]
            cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]
            
            fig = go.Figure()
            # 목표선 (시안색 점선)
            fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line=dict(color="#4be8ff", dash='dot'), name='Target'))
            # 현재값 (채우기, 연두색)
            fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', fillcolor='rgba(164, 255, 156, 0.3)', line=dict(color="#a4ff9c"), name='Current'))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=False, range=[0, 1.5]),
                    angularaxis=dict(tickfont=dict(color="#eef6ff", size=13), gridcolor="#2a416a"),
                    bgcolor="rgba(0,0,0,0)"
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#eef6ff"),
                margin=dict(t=20, b=20, l=40, r=40),
                height=350,
                showlegend=False
            )
            return fig

        st.plotly_chart(draw_dark_radar(["KH","Ca","Mg","NO3","PO4","Salinity"], 
                                        [last['KH'],last['Ca'],last['Mg'],last['NO3'],last['PO4']*100,last['Salinity']], 
                                        [cfg['t_kh'],cfg['t_ca'],cfg['t_mg'],cfg['t_no3'],cfg['t_po4']*100,35.0]), use_container_width=True)

    with c_right:
        st.markdown("### 🤖 AI Analysis")
        with st.container():
            kh_diff = last["KH"] - float(cfg["t_kh"])
            vol_factor = volume / 100.0
            
            if abs(kh_diff) <= 0.15:
                st.info(f"✨ **Perfect!** KH 수치가 목표와 일치합니다.\n현재 도징량 **{base_dose}ml**를 유지하세요.")
            elif kh_diff < 0:
                rec = base_dose + 0.3 * vol_factor
                st.error(f"📉 **KH Low!** ({last['KH']})\n도징량을 **{rec:.1f}ml**로 증량하세요.")
            else:
                rec = max(0, base_dose - 0.3 * vol_factor)
                st.warning(f"📈 **KH High!** ({last['KH']})\n도징량을 **{rec:.1f}ml**로 감량하세요.")
            
            st.markdown("---")
            # 스케줄 (작게 배치)
            st.markdown("#### 📅 Schedule")
            cur_sch = cfg.get("schedule", "")
            new_sch = st.text_area("Memo", value=cur_sch, height=100, label_visibility="collapsed")
            if st.button("Save Schedule", use_container_width=True):
                new_c = cfg.copy(); new_c["schedule"] = new_sch
                manage_config(sheet_config, "save", new_c)
                st.session_state.config = new_c
                st.toast("Saved!")

# --- 입력창 (Expander) ---
st.markdown("---")
with st.expander("➕ NEW LOG (기록 추가)", expanded=False):
    with st.form("entry"):
        c1,c2,c3,c4 = st.columns(4)
        d_date=c1.date_input("Date",date.today())
        d_kh=c1.number_input("KH",value=float(cfg["t_kh"]),step=0.01)
        d_ca=c2.number_input("Ca",value=int(cfg["t_ca"]),step=10); d_mg=c2.number_input("Mg",value=int(cfg["t_mg"]),step=10)
        d_no3=c3.number_input("NO3",value=float(cfg["t_no3"]),step=0.1); d_po4=c3.number_input("PO4",value=float(cfg["t_po4"]),format="%.3f",step=0.01)
        d_temp=c4.number_input("Temp",value=25.0,step=0.1); d_sal=c4.number_input("Salinity",value=35.0,step=0.1)
        d_memo=st.text_area("Memo")
        
        if st.form_submit_button("SAVE LOG 💾", type="primary", use_container_width=True):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":0,"NO3":d_no3,"PO4":d_po4,"pH":8.3,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
            save_entry(entry)
            st.toast("저장되었습니다!"); st.rerun()

# --- 기록 목록 (엑셀형) ---
if not df.empty:
    st.markdown("### 📋 History Log")
    
    df_show = df.sort_values("날짜", ascending=False).copy()
    df_show.insert(0, "DEL", False)
    df_show['Memo'] = df_show['Memo'].apply(lambda x: str(x) if x else "")

    edited_df = st.data_editor(
        df_show,
        column_config={
            "DEL": st.column_config.CheckboxColumn("삭제", width="small", default=False),
            "_row_idx": None,
            "Memo": st.column_config.TextColumn("메모", width="large")
        },
        disabled=HEADERS, hide_index=True, use_container_width=True
    )
    
    if st.button("🗑️ DELETE SELECTED", type="secondary"):
        to_del = edited_df[edited_df["DEL"]==True]["_row_idx"].tolist()
        if to_del:
            delete_rows(to_del)
            st.toast("Deleted!"); st.rerun()
        else:
            st.warning("선택된 항목이 없습니다.")
