import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="My Triton Lab", page_icon="🧪", layout="wide")

# --- 2. 🎨 CSS 디자인 주입 (보내주신 HTML 스타일 적용) ---
st.markdown("""
<style>
    /* 폰트 로드 */
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');

    /* 전체 배경 (Deep Navy Gradients) */
    .stApp {
        background-color: #0c1236;
        background-image: 
            radial-gradient(circle at 18% 22%, #1c3f8d 0%, #0c1236 45%),
            radial-gradient(circle at 80% 12%, rgba(148, 255, 208, 0.2) 0%, transparent 40%),
            linear-gradient(180deg, #0a102b 0%, #0c1236 55%);
        background-attachment: fixed;
        font-family: 'Pretendard', sans-serif;
        color: #eef6ff;
    }

    /* 제목 및 텍스트 스타일 */
    h1, h2, h3 { color: #eef6ff !important; font-weight: 700 !important; }
    p, label, span, div { color: #eef6ff; }
    
    /* 강조 색상 (네온 시안) */
    .highlight { color: #4be8ff !important; font-weight: bold; }

    /* 컨테이너(카드) 스타일 - Glassmorphism */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background: linear-gradient(135deg, rgba(26, 66, 118, 0.88), rgba(16, 36, 74, 0.9));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.3);
    }

    /* 입력창 스타일 (다크 모드 최적화) */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: #eef6ff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: #4be8ff !important;
        box-shadow: 0 0 0 2px rgba(75, 232, 255, 0.2) !important;
    }
    
    /* 라벨 색상 강제 지정 */
    .stNumberInput label, .stDateInput label, .stTextArea label, .stTextInput label {
        color: #a9bdd6 !important;
        font-size: 14px !important;
    }

    /* 버튼 스타일 (그라데이션) */
    .stButton > button {
        background: linear-gradient(135deg, #4be8ff, #9fffa3) !important;
        color: #03131f !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.5rem 1rem !important;
        transition: transform 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(75, 232, 255, 0.4);
    }
    
    /* 데이터프레임(표) 스타일 */
    [data-testid="stDataFrame"] {
        background-color: rgba(16, 36, 74, 0.5);
        border-radius: 10px;
    }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #0a102b;
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #4be8ff !important;
    }
    
    /* Expander 헤더 스타일 */
    .streamlit-expanderHeader {
        background-color: rgba(255,255,255,0.05) !important;
        color: #eef6ff !important;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# --- 3. 인증 (Secrets 사용) ---
def get_creds():
    if "gcp_service_account" not in st.secrets:
        st.error("🚨 Secrets 설정이 없습니다. Streamlit 배포 설정에서 Secrets를 확인해주세요.")
        st.stop()
    
    secrets_data = st.secrets["gcp_service_account"]
    if "info" in secrets_data:
        try: return json.loads(secrets_data["info"], strict=False)
        except: st.error("🚨 Secrets JSON 형식 오류"); st.stop()
    return dict(secrets_data)

creds_dict = get_creds()

# --- 4. 구글 시트 연결 ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def get_sheet_tabs():
    client = get_client()
    try: sh = client.open(SHEET_NAME)
    except:
        if 'sheet_url' in st.session_state:
            try: sh = client.open_by_url(st.session_state['sheet_url'])
            except: pass
        if 'sh' not in locals() or sh is None:
            st.warning(f"⚠️ '{SHEET_NAME}' 시트를 못 찾았습니다.")
            url = st.text_input("👇 구글 시트 URL을 입력하세요:", key="url_input")
            if url:
                try: sh = client.open_by_url(url); st.session_state['sheet_url']=url; st.success("연결됨!"); st.rerun()
                except: st.error("연결 실패"); st.stop()
            else: st.stop()

    sheet_log = sh.sheet1
    try:
        if not sheet_log.row_values(1): sheet_log.insert_row(HEADERS, index=1)
    except: pass

    try: sheet_config = sh.worksheet("Config")
    except: sheet_config = sh.add_worksheet(title="Config", rows=20, cols=5)
    return sheet_log, sheet_config

# --- 5. 데이터 관리 함수 ---
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

def delete_rows(indices):
    sheet_log, _ = get_sheet_tabs()
    for idx in sorted(indices, reverse=True): sheet_log.delete_rows(idx)

# --- 6. 설정 관리 ---
def load_config():
    _, sheet_config = get_sheet_tabs()
    records = sheet_config.get_all_records()
    default = {"volume":150.0,"base_dose":3.00,"t_kh":8.30,"t_ca":420,"t_mg":1420,"t_no2":0.010,"t_no3":5.00,"t_po4":0.040,"t_ph":8.30, "schedule":""}
    if not records: return default
    saved = records[0]
    for k, v in default.items(): 
        if k not in saved: saved[k] = v
    return saved

def save_config(new_conf):
    _, sheet_config = get_sheet_tabs()
    sheet_config.clear()
    sheet_config.append_row(list(new_conf.keys()))
    sheet_config.append_row(list(new_conf.values()))

# --- 7. 그래프 함수 (다크 테마 적용) ---
def draw_radar(cats, vals, t_vals, title, color_fill, color_line):
    norm_vals = [v/t if t>0 else 0 for v,t in zip(vals, t_vals)]
    cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]
    
    fig = go.Figure()
    # 목표치 (점선, 밝은 회색)
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line=dict(color="#a9bdd6", dash='dot'), name='목표'))
    # 현재치 (실선, 형광색)
    fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', fillcolor=color_fill, line=dict(color=color_line, width=2), name='현재'))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 1.5]),
            angularaxis=dict(tickfont=dict(color="#eef6ff", size=12), gridcolor="rgba(255,255,255,0.1)"),
            bgcolor="rgba(0,0,0,0)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30, b=30, l=40, r=40),
        title=dict(text=title, font=dict(color="#4be8ff", size=16), y=0.95),
        showlegend=False
    )
    return fig

# --- 8. 메인 UI ---
st.title("🐠 My Triton Lab")

if "config" not in st.session_state: st.session_state.config = load_config()
cfg = st.session_state.config

# [사이드바] 목표 설정
with st.sidebar:
    st.header("⚙️ SYSTEM SETUP")
    volume = st.number_input("💧 총 물량 (L)", value=float(cfg["volume"]), step=0.1)
    base_dose = st.number_input("💉 기본 도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    
    st.markdown("---")
    st.header("🎯 TARGETS")
    t_kh = st.number_input("KH (dKH)", value=float(cfg["t_kh"]), step=0.01)
    t_ca = st.number_input("Ca (ppm)", value=int(cfg["t_ca"]), step=10)
    t_mg = st.number_input("Mg (ppm)", value=int(cfg["t_mg"]), step=10)
    t_no3 = st.number_input("NO3 (ppm)", value=float(cfg["t_no3"]), step=0.1)
    t_po4 = st.number_input("PO4 (ppm)", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
    
    # (나머지 숨김 변수)
    t_no2=0.01; t_ph=8.3; t_temp=26.0; t_sal=35.0
    
    if st.button("💾 SAVE CONFIG"):
        new_conf = cfg.copy()
        new_conf.update({"volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, "t_mg":t_mg, "t_no3":t_no3, "t_po4":t_po4})
        save_config(new_conf)
        st.session_state.config = new_conf
        st.toast("설정이 저장되었습니다!")

st.success("✅ Connected to Lab Server")

# [입력창] (카드형 디자인 적용)
st.markdown("### 📝 New Log Entry")
with st.container():
    with st.form("entry"):
        c1,c2,c3,c4 = st.columns(4)
        d_date = c1.date_input("Date", date.today())
        d_kh = c2.number_input("KH", value=float(cfg["t_kh"]), step=0.01)
        d_ca = c3.number_input("Ca", value=int(cfg["t_ca"]), step=10)
        d_mg = c4.number_input("Mg", value=int(cfg["t_mg"]), step=10)
        
        c5,c6,c7,c8 = st.columns(4)
        d_no3 = c5.number_input("NO3", value=float(cfg["t_no3"]), step=0.1)
        d_po4 = c6.number_input("PO4", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
        d_temp = c7.number_input("Temp", value=25.0, step=0.1)
        d_sal = c8.number_input("Salinity", value=35.0, step=0.1)
        
        d_memo = st.text_area("Memo")
        
        # 나머지 기본값
        d_no2=0.0; d_ph=8.3
        
        if st.form_submit_button("SAVE LOG 💾"):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":d_no2,"NO3":d_no3,"PO4":d_po4,"pH":d_ph,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
            save_data(entry)
            st.toast("기록 저장 완료!"); st.rerun()

st.markdown("---")
df = load_data()

if not df.empty:
    last = df.iloc[-1]
    
    # [그래프 & AI & 스케줄]
    # 카드형 디자인을 위해 컨테이너 사용
    with st.container():
        g1, g2 = st.columns([1.3, 0.7])
        
        with g1:
            st.markdown("### 📊 Parameter Radar")
            gc1, gc2 = st.columns(2)
            # 색상: HTML 파일의 accent 색상(#4be8ff, #a4ff9c) 활용
            gc1.plotly_chart(draw_radar(["KH","Ca","Mg"],[last["KH"],last["Ca"],last["Mg"]],[cfg["t_kh"],cfg["t_ca"],cfg["t_mg"]],"Major Elements","rgba(75, 232, 255, 0.3)","#4be8ff"), use_container_width=True)
            gc2.plotly_chart(draw_radar(["NO3","PO4","Salinity"],[last["NO3"],last["PO4"]*100,last["Salinity"]],[cfg["t_no3"],cfg["t_po4"]*100,35.0],"Nutrients & Env","rgba(164, 255, 156, 0.3)","#a4ff9c"), use_container_width=True)
        
        with g2:
            st.markdown("### 🤖 AI Analysis")
            kh_diff = last["KH"] - float(cfg["t_kh"])
            vol_factor = volume / 100.0
            
            # AI 박스 디자인
            if abs(kh_diff) <= 0.15: 
                st.success(f"✨ **Perfect!** KH가 목표와 일치합니다.\n현재 도징량 **{base_dose}ml** 유지하세요.")
            elif kh_diff < 0: 
                rec = base_dose + 0.3 * vol_factor
                st.error(f"📉 **KH Low!** ({last['KH']})\n도징량을 **{rec:.1f}ml**로 증량하세요.")
            else: 
                rec = max(0, base_dose - 0.3 * vol_factor)
                st.warning(f"📈 **KH High!** ({last['KH']})\n도징량을 **{rec:.1f}ml**로 감량하세요.")
            
            st.markdown("---")
            st.markdown("#### 📅 Schedule")
            cur_sch = cfg.get("schedule", "")
            new_sch = st.text_area("주간 계획 (수정 가능)", value=cur_sch, height=150, label_visibility="collapsed")
            if st.button("💾 SAVE SCHEDULE"):
                updated_conf = cfg.copy(); updated_conf["schedule"] = new_sch
                save_config(updated_conf); st.session_state.config = updated_conf
                st.toast("스케줄 저장됨!")

    st.markdown("---")
    
    # [기록 관리]
    st.markdown("### 📋 History Log")
    with st.container():
        df_display = df.sort_values("날짜", ascending=False).copy()
        df_display.insert(0, "DEL", False)
        df_display['Memo'] = df_display['Memo'].apply(lambda x: str(x) if x else "")

        edited_df = st.data_editor(
            df_display,
            column_config={
                "DEL": st.column_config.CheckboxColumn("삭제", width="small", default=False),
                "_row_idx": None,
                "Memo": st.column_config.TextColumn("메모", width="large")
            },
            disabled=HEADERS, hide_index=True, use_container_width=True
        )
        
        if st.button("🗑️ DELETE SELECTED", type="secondary"):
            to_del = edited_df[edited_df["DEL"] == True]["_row_idx"].tolist()
            if to_del:
                delete_rows(to_del)
                st.toast("Deleted!"); st.rerun()
            else:
                st.warning("선택된 항목이 없습니다.")
else:
    st.info("👋 No data yet. Please add your first log.")
