import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="My Reef Manager", page_icon="🐠", layout="wide")

# --- 🎨 디자인 (Deep Navy & Neon) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #F0F4F8; }
    
    /* 제목 및 텍스트 */
    h1, h2, h3 { color: #1A237E !important; font-weight: 700 !important; }
    
    /* 카드 박스 (게시글 스타일) */
    .log-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #E0E0E0;
        margin-bottom: 15px;
    }
    
    /* 중요 수치 강조 */
    .metric-value {
        font-size: 1.1em;
        font-weight: bold;
        color: #004D40;
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        background-color: #00897B !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
    }
    
    /* 삭제 버튼 (빨간색) */
    div[data-testid="column"] button[kind="secondary"] {
        background-color: #FF5252 !important;
        color: white !important;
        border: none !important;
    }

    [data-testid="stSidebar"] { background-color: #E0F7FA; border-right: 1px solid #B2EBF2; }
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# 👇👇👇 [여기에 JSON 키를 붙여넣으세요] 👇👇👇
ROBOT_KEY = """
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "...",
  "token_uri": "...",
  "auth_provider_x509_cert_url": "...",
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}
"""
# 👆👆👆 [여기까지만 수정하세요] 👆👆👆

# --- 1. 인증 ---
def get_creds():
    try:
        if "project_id" not in ROBOT_KEY or "..." in ROBOT_KEY:
            st.error("🚨 **코드 위쪽 'ROBOT_KEY' 부분에 JSON 내용을 붙여넣어 주세요!**")
            st.stop()
        
        creds = json.loads(ROBOT_KEY, strict=False)
        if "private_key" in creds:
            creds["private_key"] = creds["private_key"].replace("\\n", "\n").strip()
        return creds
    except json.JSONDecodeError:
        st.error("🚨 키 형식이 잘못되었습니다.")
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
    default = {"volume":150.0,"base_dose":3.00,"t_kh":8.30,"t_ca":420,"t_mg":1420,"t_no2":0.010,"t_no3":5.00,"t_po4":0.040,"t_ph":8.30, "t_temp":26.0, "t_sal":35.0, "schedule":""}
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
def draw_radar(cats, vals, t_vals, title, color):
    norm_vals = [v/t if t>0 else 0 for v,t in zip(vals, t_vals)]
    cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line_color="gray", line_dash='dot', name='목표'))
    fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', line_color=color, name='현재'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=False)), margin=dict(t=30,b=30), height=300, title=dict(text=title))
    return fig

# --- 6. 메인 화면 ---
st.title("🐠 My Reef Manager")

if "config" not in st.session_state: st.session_state.config = load_config()
cfg = st.session_state.config

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    volume = st.number_input("물량 (L)", value=float(cfg["volume"]), step=0.1)
    base_dose = st.number_input("도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    st.divider()
    st.subheader("🎯 목표치")
    t_kh = st.number_input("KH", value=float(cfg["t_kh"]), step=0.01)
    t_ca = st.number_input("Ca", value=int(cfg["t_ca"]), step=10)
    t_mg = st.number_input("Mg", value=int(cfg["t_mg"]), step=10)
    t_no3 = st.number_input("NO3", value=float(cfg["t_no3"]), step=0.1)
    t_po4 = st.number_input("PO4", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
    
    t_no2 = st.number_input("NO2", value=float(cfg.get("t_no2", 0.01)), format="%.3f", step=0.001)
    t_ph = st.number_input("pH", value=float(cfg.get("t_ph", 8.3)), step=0.1)
    t_temp = st.number_input("Temp", value=float(cfg.get("t_temp", 26.0)), step=0.1)
    t_sal = st.number_input("Salinity", value=float(cfg.get("t_sal", 35.0)), step=0.1)
    
    if st.button("💾 설정 저장"):
        new_conf = cfg.copy()
        new_conf.update({"volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, "t_mg":t_mg, "t_no3":t_no3, "t_po4":t_po4, "t_no2":t_no2, "t_ph":t_ph, "t_temp":t_temp, "t_sal":t_sal})
        save_config(new_conf)
        st.session_state.config = new_conf
        st.toast("설정 저장됨!"); st.rerun()

st.success("✅ 연결 완료")

# 입력창
with st.expander("📝 새 기록 입력하기", expanded=True):
    with st.form("entry"):
        c1,c2,c3,c4 = st.columns(4)
        d_date = c1.date_input("날짜", date.today())
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
        d_memo = c11.text_input("메모")
        
        if st.form_submit_button("💾 기록 저장", type="primary"):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":d_no2,"NO3":d_no3,"PO4":d_po4,"pH":d_ph,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
            save_data(entry)
            st.toast("저장됨!"); st.rerun()

st.divider()
df = load_data()

if not df.empty:
    last = df.iloc[-1]
    
    g1, g2 = st.columns([1.3, 0.7])
    with g1:
        st.subheader("📊 그래프")
        gc1, gc2 = st.columns(2)
        gc1.plotly_chart(draw_radar(["KH","Ca","Mg","pH"],[last["KH"],last["Ca"],last["Mg"],last["pH"]],[cfg["t_kh"],cfg["t_ca"],cfg["t_mg"],cfg["t_ph"]],"주요 3요소","#009688"), use_container_width=True)
        gc2.plotly_chart(draw_radar(["NO3","PO4","Sal","Temp"],[last["NO3"],last["PO4"]*100,last["Salinity"],last["Temp"]],[cfg["t_no3"],cfg["t_po4"]*100,cfg["t_sal"],cfg["t_temp"]],"환경","#FF7043"), use_container_width=True)
    
    with g2:
        st.subheader("🤖 AI 분석")
        kh_diff = last["KH"] - float(cfg["t_kh"])
        vol_factor = volume / 100.0
        if abs(kh_diff) <= 0.15: st.success(f"✅ KH 완벽 ({last['KH']})")
        elif kh_diff < 0: st.error(f"📉 KH 부족! 추천: {base_dose+0.3*vol_factor:.2f}ml")
        else: st.warning(f"📈 KH 과다! 추천: {max(0, base_dose-0.3*vol_factor):.2f}ml")
        
        st.divider()
        st.subheader("📅 스케줄")
        current_sch = cfg.get("schedule", "")
        new_sch = st.text_area("주간 계획", value=current_sch, height=150)
        if st.button("💾 스케줄 저장"):
            updated_conf = cfg.copy(); updated_conf["schedule"] = new_sch
            save_config(updated_conf); st.session_state.config = updated_conf
            st.toast("저장됨!")

    st.divider()
    
    # -------------------------------------------------------------
    # [수정된 부분] 엑셀형 X -> 게시판(카드)형 O
    # -------------------------------------------------------------
    st.subheader("📋 전체 기록 관리")
    
    df_show = df.sort_values("날짜", ascending=False)
    
    for index, row in df_show.iterrows():
        # 각 기록을 하나의 카드(컨테이너)로 표시
        with st.container():
            # 날짜 헤더
            st.markdown(f"#### 📅 {row['날짜']}")
            
            c_data, c_btn = st.columns([5, 1])
            
            with c_data:
                # 주요 수치 표시 (진하게)
                st.markdown(f"""
                <div style='background-color: #F8F9FA; padding: 10px; border-radius: 8px;'>
                    <span class='metric-value'>🧪 KH: {row['KH']}</span> &nbsp;|&nbsp; 
                    Ca: {row['Ca']} &nbsp;|&nbsp; Mg: {row['Mg']} &nbsp;|&nbsp; 
                    NO3: {row['NO3']} &nbsp;|&nbsp; PO4: {row['PO4']} &nbsp;|&nbsp; 
                    💧 도징: {row['도징량']}ml
                </div>
                """, unsafe_allow_html=True)
                
                # 메모가 있으면 표시
                if row['Memo'] and str(row['Memo']).strip():
                    st.info(f"📝 {row['Memo']}")
            
            with c_btn:
                # 삭제 버튼
                st.write("") # 줄바꿈
                if st.button("🗑️ 삭제", key=f"del_{row['_row_idx']}", type="secondary", use_container_width=True):
                    delete_row(row['_row_idx'])
                    st.toast("삭제되었습니다!")
                    st.rerun()
            
            st.divider() # 구분선

else:
    st.info("👋 기록이 없습니다.")
