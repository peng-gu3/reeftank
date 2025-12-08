import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="My Triton Lab", page_icon="🧪", layout="wide")

# --- 🎨 디자인 (Deep Navy & Neon) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif !important;
        color: #eef6ff !important;
    }
    
    /* 배경 (Deep Navy) */
    .stApp {
        background-color: #0c1236 !important;
        background-image: radial-gradient(circle at 18% 22%, #1c3f8d 0%, #0c1236 45%) !important;
        background-attachment: fixed !important;
    }

    /* 카드 박스 */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: rgba(16, 36, 74, 0.7) !important;
        border: 1px solid rgba(75, 232, 255, 0.1) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        backdrop-filter: blur(10px);
    }

    /* 텍스트 색상 */
    h1, h2, h3 { color: #4be8ff !important; text-shadow: 0 0 10px rgba(75, 232, 255, 0.3) !important; }
    p, label, span, div { color: #eef6ff; }

    /* 입력창 */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
        background-color: rgba(0, 0, 0, 0.3) !important;
        color: #4be8ff !important;
        border: 1px solid rgba(75, 232, 255, 0.2) !important;
        border-radius: 8px !important;
    }
    
    /* 버튼 */
    .stButton > button {
        background: linear-gradient(135deg, #4be8ff, #1c3f8d) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
    }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background-color: #080c24 !important;
        border-right: 1px solid #2a416a !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #4be8ff !important;
    }
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# --- 1. 인증 (오직 Secrets만 사용 - 코드에 키 없음!) ---
def get_creds():
    # Streamlit Secrets에서 설정 확인
    if "gcp_service_account" not in st.secrets:
        st.error("🚨 **Secrets 설정이 없습니다!**")
        st.info("내 컴퓨터: `.streamlit/secrets.toml` 파일 확인\n서버 배포: [Settings] > [Secrets] 확인")
        st.stop()

    secrets_data = st.secrets["gcp_service_account"]

    # 1) 'info' 키에 JSON 전체를 넣은 경우
    if "info" in secrets_data:
        try:
            return json.loads(secrets_data["info"], strict=False)
        except json.JSONDecodeError:
            st.error("🚨 Secrets의 JSON 형식이 잘못되었습니다.")
            st.stop()
    
    # 2) 개별 키값으로 넣은 경우
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
            url = st.text_input("👇 구글 시트 URL 입력 (최초 1회):", key="url_input")
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

def delete_rows(indices):
    sheet_log, _ = get_sheet_tabs()
    for idx in sorted(indices, reverse=True): sheet_log.delete_rows(idx)

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
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line=dict(color="#a9bdd6", dash='dot'), name='Target'))
    fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', fillcolor=color_fill, line=dict(color=color_line, width=2), name='Current'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=False), angularaxis=dict(tickfont=dict(color="#eef6ff"), gridcolor="rgba(255,255,255,0.1)"), bgcolor="rgba(0,0,0,0)"), paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=30,b=30,l=40,r=40), height=300, title=dict(text=title, font=dict(color="#4be8ff", size=16)))
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
    
    t_no2 = st.number_input("NO2 (ppm)", value=float(cfg.get("t_no2", 0.01)), format="%.3f", step=0.001)
    t_ph = st.number_input("pH", value=float(cfg.get("t_ph", 8.3)), step=0.1)
    t_temp = st.number_input("Temp", value=float(cfg.get("t_temp", 26.0)), step=0.1)
    t_sal = st.number_input("Salinity", value=float(cfg.get("t_sal", 35.0)), step=0.1)
    
    if st.button("💾 SAVE CONFIG"):
        new_conf = cfg.copy()
        new_conf.update({"volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, "t_mg":t_mg, "t_no3":t_no3, "t_po4":t_po4, "t_no2":t_no2, "t_ph":t_ph, "t_temp":t_temp, "t_sal":t_sal})
        save_config(new_conf)
        st.session_state.config = new_conf
        st.toast("설정 저장 완료!"); st.rerun()

st.success("✅ Connected")

# [입력창]
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
            st.toast("저장되었습니다!"); st.rerun()

st.markdown("---")
df = load_data()

if not df.empty:
    last = df.iloc[-1]
    
    # [그래프 & AI & 스케줄]
    g1, g2 = st.columns([1.3, 0.7])
    with g1:
        st.markdown("### 📊 Analysis")
        gc1, gc2 = st.columns(2)
        gc1.plotly_chart(draw_radar(["KH","Ca","Mg","pH"],[last["KH"],last["Ca"],last["Mg"],last["pH"]],[cfg["t_kh"],cfg["t_ca"],cfg["t_mg"],cfg["t_ph"]],"Major & pH","rgba(75, 232, 255, 0.3)","#4be8ff"), use_container_width=True)
        gc2.plotly_chart(draw_radar(["NO3","PO4","Sal","Temp"],[last["NO3"],last["PO4"]*100,last["Salinity"],last["Temp"]],[cfg["t_no3"],cfg["t_po4"]*100,cfg["t_sal"],cfg["t_temp"]],"Env & Nutrients","rgba(164, 255, 156, 0.3)","#a4ff9c"), use_container_width=True)
    
    with g2:
        st.markdown("### 🤖 Advisor")
        with st.container():
            kh_diff = last["KH"] - float(cfg["t_kh"])
            vol_factor = volume / 100.0
            if abs(kh_diff) <= 0.15: st.success(f"✨ **Perfect!** KH 유지하세요.")
            elif kh_diff < 0: 
                rec = base_dose + 0.3 * vol_factor
                st.error(f"📉 **KH Low!** Rec: {rec:.1f}ml")
            else: 
                rec = max(0, base_dose - 0.3 * vol_factor)
                st.warning(f"📈 **KH High!** Rec: {rec:.1f}ml")
            
            st.markdown("---")
            st.markdown("#### 📅 Schedule")
            cur_sch = cfg.get("schedule", "")
            new_sch = st.text_area("Schedule", value=cur_sch, height=120, label_visibility="collapsed")
            if st.button("SAVE SCHEDULE"):
                new_c = cfg.copy(); new_c["schedule"] = new_sch
                save_config(new_c); st.session_state.config = new_c; st.toast("스케줄 저장됨!")

    st.markdown("---")
    
    # [기록 관리] 엑셀형 + 체크박스 삭제
    st.markdown("### 📋 History Log")
    df_show = df.sort_values("날짜", ascending=False).copy()
    df_show.insert(0, "삭제", False)
    df_show['Memo'] = df_show['Memo'].apply(lambda x: str(x) if x else "")

    edited_df = st.data_editor(
        df_show,
        column_config={
            "삭제": st.column_config.CheckboxColumn("선택", width="small", default=False),
            "_row_idx": None,
            "Memo": st.column_config.TextColumn("메모", width="large")
        },
        disabled=HEADERS, hide_index=True, use_container_width=True
    )
    
    if st.button("🗑️ 선택한 기록 삭제하기"):
        to_del = edited_df[edited_df["삭제"] == True]["_row_idx"].tolist()
        if to_del:
            delete_rows(to_del)
            st.toast("삭제 완료!"); st.rerun()
        else:
            st.warning("선택된 항목이 없습니다.")
else:
    st.info("👋 기록이 없습니다.")
