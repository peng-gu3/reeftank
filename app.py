import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="My Triton Lab", page_icon="🧪", layout="wide")

# --- 🎨 CSS: HTML 파일의 'Deep Navy & Neon' 테마 완벽 이식 ---
st.markdown("""
<style>
    /* 1. 폰트 및 전체 배경 (강제 적용) */
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif !important;
        color: #eef6ff !important; /* 기본 글씨: 밝은 흰색 */
    }
    
    /* 메인 배경색 (어두운 네이비) */
    .stApp {
        background-color: #0c1236 !important;
        background-image: radial-gradient(circle at 18% 22%, #1c3f8d 0%, #0c1236 45%) !important;
        background-attachment: fixed !important;
    }

    /* 2. 카드 박스 스타일 (반투명 네이비) */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #10244a !important;
        border: 1px solid #2a416a !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
    }

    /* 3. 제목 (형광 시안색) */
    h1, h2, h3 {
        color: #4be8ff !important;
        text-shadow: 0 0 10px rgba(75, 232, 255, 0.3) !important;
    }
    
    /* 4. 입력창 스타일 (진한 네이비 배경 + 흰색 글씨) */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
        background-color: #080c24 !important;
        color: #ffffff !important; /* 입력 글씨 흰색 */
        border: 1px solid #2a416a !important;
        border-radius: 8px !important;
    }
    /* 입력창 라벨 색상 */
    .stNumberInput label, .stDateInput label, .stTextArea label, .stTextInput label {
        color: #a9bdd6 !important;
    }

    /* 5. 버튼 스타일 (그라데이션 네온) */
    .stButton > button {
        background: linear-gradient(135deg, #4be8ff, #1c3f8d) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
    }
    
    /* 삭제 버튼 (빨간색 계열) */
    div[data-testid="column"] button[kind="secondary"] {
        background: linear-gradient(135deg, #ff5252, #b71c1c) !important;
        border: 1px solid #ff5252 !important;
    }

    /* 6. 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #080c24 !important;
        border-right: 1px solid #2a416a !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #4be8ff !important;
    }
    [data-testid="stSidebar"] label {
        color: #eef6ff !important;
    }

    /* 7. 기록 리스트 아이템 스타일 (커스텀) */
    .log-item {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# --- 1. 인증 (Secrets 사용) ---
def get_creds():
    if "gcp_service_account" not in st.secrets:
        st.error("🚨 **Secrets 설정이 없습니다!**")
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

def get_sheet_tabs():
    client = get_client()
    try: sh = client.open(SHEET_NAME)
    except:
        if 'sheet_url' in st.session_state:
            try: sh = client.open_by_url(st.session_state['sheet_url'])
            except: pass
        if 'sh' not in locals() or sh is None:
            st.warning(f"⚠️ '{SHEET_NAME}' 시트를 못 찾았습니다.")
            url = st.text_input("👇 구글 시트 URL 입력:", key="url_input")
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

def delete_row(row_idx):
    sheet_log, _ = get_sheet_tabs()
    sheet_log.delete_rows(row_idx)

# --- 4. 설정 관리 ---
def load_config():
    _, sheet_config = get_sheet_tabs()
    records = sheet_config.get_all_records()
    default = {"volume":150.0,"base_dose":3.00,"t_kh":8.30,"t_ca":420,"t_mg":1420,"t_no2":0.010,"t_no3":5.00,"t_po4":0.040,"t_ph":8.30,"t_temp":26.0,"t_sal":35.0, "schedule":""}
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

# --- 5. 그래프 ---
def draw_radar(cats, vals, t_vals, title, color_fill, color_line):
    norm_vals = [v/t if t>0 else 0 for v,t in zip(vals, t_vals)]
    cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]
    
    fig = go.Figure()
    # 목표치 (점선, 밝은 회색)
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line=dict(color="#a9bdd6", dash='dot'), name='Target'))
    # 현재치 (실선, 형광색)
    fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', fillcolor=color_fill, line=dict(color=color_line, width=2), name='Current'))
    
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

# --- 6. 메인 화면 ---
st.title("🧪 My Triton Lab")

if "config" not in st.session_state: st.session_state.config = load_config()
cfg = st.session_state.config

# [사이드바]
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
    # 추가된 목표치
    t_no2 = st.number_input("NO2 (ppm)", value=float(cfg.get("t_no2", 0.01)), format="%.3f", step=0.001)
    t_ph = st.number_input("pH", value=float(cfg.get("t_ph", 8.3)), step=0.1)
    t_temp = st.number_input("Temp", value=float(cfg.get("t_temp", 26.0)), step=0.1)
    t_sal = st.number_input("Salinity", value=float(cfg.get("t_sal", 35.0)), step=0.1)
    
    if st.button("💾 SAVE CONFIG"):
        new_conf = cfg.copy()
        new_conf.update({
            "volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, 
            "t_mg":t_mg, "t_no3":t_no3, "t_po4":t_po4, "t_no2":t_no2,
            "t_ph":t_ph, "t_temp":t_temp, "t_sal":t_sal
        })
        save_config(new_conf)
        st.session_state.config = new_conf
        st.toast("Settings Saved!")

st.success("✅ Connected")

# [입력창] 카드형 디자인
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
        d_no2 = c7.number_input("NO2", value=0.00, format="%.3f", step=0.001)
        d_ph = c8.number_input("pH", value=float(cfg.get("t_ph", 8.3)), step=0.1)
        
        c9,c10,c11 = st.columns([1,1,2])
        d_temp = c9.number_input("Temp", value=float(cfg.get("t_temp", 26.0)), step=0.1)
        d_sal = c10.number_input("Salinity", value=float(cfg.get("t_sal", 35.0)), step=0.1)
        d_memo = c11.text_input("Memo")
        
        if st.form_submit_button("SAVE LOG 💾"):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":d_no2,"NO3":d_no3,"PO4":d_po4,"pH":d_ph,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
            save_data(entry)
            st.toast("Saved!"); st.rerun()

st.markdown("---")
df = load_data()

if not df.empty:
    last = df.iloc[-1]
    
    # [그래프]
    g1, g2 = st.columns([1.3, 0.7])
    with g1:
        st.markdown("### 📊 Analysis")
        gc1, gc2 = st.columns(2)
        # 왼쪽 그래프: 3요소 + pH
        gc1.plotly_chart(draw_radar(["KH","Ca","Mg","pH"],[last["KH"],last["Ca"],last["Mg"],last["pH"]],[cfg["t_kh"],cfg["t_ca"],cfg["t_mg"],cfg["t_ph"]],"Major & pH","rgba(75, 232, 255, 0.3)","#4be8ff"), use_container_width=True)
        # 오른쪽 그래프: 영양염 + 온도
        gc2.plotly_chart(draw_radar(["NO3","PO4","Sal","Temp"],[last["NO3"],last["PO4"]*100,last["Salinity"],last["Temp"]],[cfg["t_no3"],cfg["t_po4"]*100,cfg["t_sal"],cfg["t_temp"]],"Env & Nutrients","rgba(164, 255, 156, 0.3)","#a4ff9c"), use_container_width=True)
    
    with g2:
        st.markdown("### 🤖 Advisor")
        with st.container():
            kh_diff = last["KH"] - float(cfg["t_kh"])
            vol_factor = volume / 100.0
            if abs(kh_diff) <= 0.15: st.success(f"✨ **Perfect!** KH 유지하세요.")
            elif kh_diff < 0: 
                rec = base_dose + 0.3 * vol_factor
                st.error(f"📉 **KH Low!** ({last['KH']})\n추천 도징: **{rec:.1f}ml**")
            else: 
                rec = max(0, base_dose - 0.3 * vol_factor)
                st.warning(f"📈 **KH High!** ({last['KH']})\n추천 도징: **{rec:.1f}ml**")
            
            st.markdown("---")
            st.markdown("#### 📅 Schedule")
            cur_sch = cfg.get("schedule", "")
            new_sch = st.text_area("Schedule", value=cur_sch, height=100, label_visibility="collapsed")
            if st.button("SAVE SCHEDULE"):
                new_c = cfg.copy(); new_c["schedule"] = new_sch
                save_config(new_c); st.session_state.config = new_c; st.toast("Saved!")

    st.markdown("---")
    
    # [기록 리스트] 엑셀형 X -> 깔끔한 리스트형 O
    st.markdown("### 📋 History Log")
    
    # 최신순 정렬
    df_show = df.sort_values("날짜", ascending=False)
    
    for index, row in df_show.iterrows():
        # 각 행을 박스(컨테이너)로 예쁘게 표시
        with st.container():
            c_date, c_main, c_env, c_del = st.columns([1.5, 3, 3, 1])
            
            with c_date:
                st.markdown(f"**📅 {row['날짜']}**")
            
            with c_main:
                st.caption("Major")
                st.write(f"🧪 KH:{row['KH']} Ca:{row['Ca']} Mg:{row['Mg']}")
            
            with c_env:
                st.caption("Memo/Env")
                memo_txt = f"📝 {row['Memo']}" if row['Memo'] and str(row['Memo']).strip() else ""
                st.write(f"{memo_txt} (NO3:{row['NO3']} PO4:{row['PO4']})")
                
            with c_del:
                st.write("") # 줄바꿈
                # 빨간색 삭제 버튼
                if st.button("🗑️ Del", key=f"del_{row['_row_idx']}", type="secondary"):
                    delete_row(row['_row_idx'])
                    st.toast("Deleted!"); st.rerun()

else:
    st.info("👋 No logs yet.")
