import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="My Reef Manager", page_icon="🐠", layout="wide")

# --- 🎨 디자인 수정 (글씨 잘 보이게!) ---
st.markdown("""
<style>
    /* 전체 폰트 적용 (깔끔한 고딕) */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }

    /* 배경: 아주 연한 민트색 (글씨가 잘 보이도록) */
    .stApp {
        background-color: #F0F4F8;
    }

    /* 제목 및 헤더: 진한 남색/청록색으로 가독성 확보 */
    h1, h2, h3 {
        color: #1A237E !important;
        font-weight: 700 !important;
    }
    
    /* 일반 텍스트: 검은색 */
    p, div, label {
        color: #000000 !important;
    }

    /* 카드 박스 디자인 (흰색 배경 + 그림자) */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        border: 1px solid #CFD8DC;
    }

    /* 버튼 디자인 */
    .stButton > button {
        background-color: #00897B !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
    }
    .stButton > button:hover {
        background-color: #00695C !important;
    }
    
    /* 사이드바 배경 */
    [data-testid="stSidebar"] {
        background-color: #E0F7FA;
        border-right: 1px solid #B2EBF2;
    }
</style>
""", unsafe_allow_html=True)

SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# 👇👇👇 [선생님의 키를 여기에 붙여넣으세요] 👇👇👇
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
            st.error("🚨 **코드 위쪽 'ROBOT_KEY'에 키 값을 넣어주세요!**")
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

def delete_rows(indices):
    sheet_log, _ = get_sheet_tabs()
    for idx in sorted(indices, reverse=True): sheet_log.delete_rows(idx)

# --- 4. 설정 관리 ---
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

# --- 5. 그래프 ---
def draw_radar(cats, vals, t_vals, title, color):
    norm_vals = [v/t if t>0 else 0 for v,t in zip(vals, t_vals)]
    cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line_color="gray", line_dash='dot', name='목표'))
    fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', line_color=color, name='현재'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=False)), margin=dict(t=30,b=30), height=300, title=dict(text=title, font=dict(size=15)))
    return fig

# --- 6. 메인 화면 ---
st.title("🐠 My Reef Manager")

if "config" not in st.session_state: st.session_state.config = load_config()
cfg = st.session_state.config

# [사이드바] 목표치 설정 (복구됨!)
with st.sidebar:
    st.header("⚙️ 목표 설정")
    volume = st.number_input("물량 (L)", value=float(cfg["volume"]), step=0.1)
    base_dose = st.number_input("기본 도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    st.divider()
    st.caption("목표 수치")
    t_kh = st.number_input("목표 KH", value=float(cfg["t_kh"]), step=0.01)
    t_ca = st.number_input("목표 Ca", value=int(cfg["t_ca"]), step=10)
    t_mg = st.number_input("목표 Mg", value=int(cfg["t_mg"]), step=10)
    t_no3 = st.number_input("목표 NO3", value=float(cfg["t_no3"]), step=0.1)
    t_po4 = st.number_input("목표 PO4", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
    
    # 나머지 덜 중요한 건 변수로만 저장 (공간 절약)
    t_no2=0.01; t_ph=8.3
    
    if st.button("💾 설정 저장"):
        new_conf = cfg.copy()
        new_conf.update({"volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, "t_mg":t_mg, "t_no3":t_no3, "t_po4":t_po4})
        save_config(new_conf)
        st.session_state.config = new_conf
        st.toast("설정 저장 완료!"); st.rerun()

st.success("✅ 연결 완료")

# [입력창] (복구됨!)
with st.expander("📝 기록 입력하기 (클릭해서 열기)", expanded=True):
    with st.form("entry"):
        c1,c2,c3,c4 = st.columns(4)
        d_date=c1.date_input("날짜",date.today())
        d_kh=c1.number_input("KH",value=float(cfg["t_kh"]),step=0.01)
        d_ca=c2.number_input("Ca",value=int(cfg["t_ca"]),step=10); d_mg=c2.number_input("Mg",value=int(cfg["t_mg"]),step=10)
        d_no3=c3.number_input("NO3",value=float(cfg["t_no3"]),step=0.1); d_po4=c3.number_input("PO4",value=float(cfg["t_po4"]),format="%.3f",step=0.01)
        d_temp=c4.number_input("온도",value=25.0,step=0.1); d_sal=c4.number_input("염도",value=35.0,step=0.1)
        d_memo=st.text_area("메모")
        if st.form_submit_button("저장 💾", type="primary"):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":0,"NO3":d_no3,"PO4":d_po4,"pH":8.3,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
            save_data(entry)
            st.toast("저장됨!"); st.rerun()

st.divider()
df = load_data()

if not df.empty:
    last = df.iloc[-1]
    
    # [화면 배치] 왼쪽: 그래프 / 오른쪽: 스케줄 (반반 배치)
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("📊 수질 그래프")
        # 그래프 2개 나란히
        g1, g2 = st.columns(2)
        g1.plotly_chart(draw_radar(["KH","Ca","Mg"],[last["KH"],last["Ca"],last["Mg"]],[cfg["t_kh"],cfg["t_ca"],cfg["t_mg"]],"3요소","#009688"), use_container_width=True)
        g2.plotly_chart(draw_radar(["NO3","PO4","염도"],[last["NO3"],last["PO4"]*100,last["Salinity"]],[cfg["t_no3"],cfg["t_po4"]*100,35.0],"환경","#FF7043"), use_container_width=True)
        
        # AI 한줄평
        kh_diff = last["KH"] - float(cfg["t_kh"])
        if abs(kh_diff) <= 0.15: st.success(f"✨ KH 완벽 ({last['KH']})")
        elif kh_diff < 0: st.error(f"📉 KH 부족! 추천: {base_dose + 0.3*(volume/100):.1f}ml")
        else: st.warning(f"📈 KH 과다! 추천: {max(0, base_dose - 0.3*(volume/100)):.1f}ml")

    with col_right:
        # [스케줄] 깔끔한 직사각형 메모장
        st.subheader("📅 주간 스케줄")
        with st.container():
            cur_sch = cfg.get("schedule", "")
            new_sch = st.text_area("관리 계획 (수정 후 저장 버튼)", value=cur_sch, height=250)
            if st.button("💾 스케줄 저장", use_container_width=True):
                new_c = cfg.copy(); new_c["schedule"] = new_sch
                save_config(new_c); st.session_state.config = new_c
                st.toast("스케줄 저장됨!")

    st.divider()
    
    # [기록 관리] 엑셀형 목록 + 체크 삭제 (복구됨!)
    st.subheader("📋 전체 기록 관리")
    df_show = df.sort_values("날짜", ascending=False).copy()
    df_show.insert(0, "삭제", False)
    df_show['Memo'] = df_show['Memo'].apply(lambda x: str(x) if x else "")
    
    edited = st.data_editor(
        df_show,
        column_config={
            "삭제": st.column_config.CheckboxColumn("선택", width="small"),
            "_row_idx": None,
            "Memo": st.column_config.TextColumn("메모", width="large")
        },
        disabled=HEADERS, hide_index=True, use_container_width=True
    )
    
    if st.button("🗑️ 선택한 기록 삭제하기", type="primary"):
        to_del = edited[edited["삭제"]==True]["_row_idx"].tolist()
        if to_del:
            delete_rows(to_del)
            st.toast("삭제 완료!"); st.rerun()
        else:
            st.warning("삭제할 항목을 선택해주세요.")
else:
    st.info("👋 기록이 없습니다.")
