import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 페이지 기본 설정 ---
st.set_page_config(page_title="My Lovely Reef", page_icon="🐠", layout="wide")

# --- 🎨 CSS 디자인 주입 (여기가 마법의 주문입니다!) ---
st.markdown("""
<style>
    /* 1. 귀여운 폰트 가져오기 (구글 웹폰트) */
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;600;700&display=swap');

    /* 2. 전체 배경 및 폰트 적용 */
    .stApp {
        background: linear-gradient(to bottom right, #E0F7FA, #F0F4C3); /* 은은한 바다색 그라데이션 */
        font-family: 'Quicksand', sans-serif !important;
    }

    /* 3. 제목 및 헤더 스타일 */
    h1, h2, h3 {
        color: #00796B !important; /* 진한 청록색 */
        font-weight: 700 !important;
    }

    /* 4. 컨테이너(카드) 스타일 - 둥글고 그림자 있게 */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 20px; /* 둥근 모서리 */
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); /* 부드러운 그림자 */
        border: 1px solid #B2EBF2; /* 연한 하늘색 테두리 */
    }

    /* 5. 버튼 스타일 - 둥글고 산호색으로 */
    .stButton > button {
        border-radius: 25px !important;
        background-color: #FF8A65 !important; /* 산호색 */
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 10px 25px !important;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #FF7043 !important; /* 마우스 올리면 진하게 */
        box-shadow: 0 5px 15px rgba(255, 138, 101, 0.4);
        transform: translateY(-2px);
    }

    /* 6. 입력창 스타일 - 부드럽게 */
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stDateInput > div > div > input, .stTextArea > div > div > textarea {
        border-radius: 15px !important;
        border: 1px solid #E0E0E0 !important;
        background-color: #FAFAFA !important;
    }
    
    /* 7. 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #B2EBF240 !important; /* 반투명한 하늘색 */
        border-right: 1px solid #B2EBF2;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
         color: #006064 !important;
    }

    /* 8. 확장팩(Expander) 스타일 */
    .streamlit-expanderHeader {
        background-color: #FFFFFF !important;
        border-radius: 15px !important;
        border: 1px solid #B2EBF2 !important;
    }
    
    /* 9. 데이터 프레임(표) 스타일 */
    [data-testid="stDataFrame"] {
        border-radius: 15px;
        overflow: hidden;
        border: 1px solid #B2EBF2;
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

def get_sheet_tabs():
    client = get_client()
    sh = None
    try: sh = client.open(SHEET_NAME)
    except: pass
    if sh is None:
        if 'sheet_url' in st.session_state:
            try: sh = client.open_by_url(st.session_state['sheet_url'])
            except: pass
    if sh is None:
        st.warning(f"⚠️ '{SHEET_NAME}' 파일을 못 찾았습니다.")
        sheet_url = st.text_input("👇 구글 시트 URL을 입력해주세요", key="url_input")
        if sheet_url:
            try: sh = client.open_by_url(sheet_url); st.session_state['sheet_url'] = sheet_url; st.success("✅ 연결 성공!"); st.rerun()
            except: st.error("🚨 연결 실패"); st.stop()
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

def delete_rows_by_indices(row_indices):
    sheet_log, _ = get_sheet_tabs()
    for idx in sorted(row_indices, reverse=True): sheet_log.delete_rows(idx)

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

# --- 5. 그래프 (디자인 수정) ---
def draw_radar(cats, vals, t_vals, title, color_fill, color_line):
    norm_vals = []; txt_vals = []
    for v, t in zip(vals, t_vals):
        txt_vals.append(f"{v}"); norm_vals.append(v/t if t>0.01 and v<=t else (1+(v-t)*50 if t<=0.01 else v/t))
    cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]; txt_vals=[*txt_vals,""]
    fig = go.Figure()
    # 목표치 (점선)
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line_color="#B0BEC5", line_dash='dot', name='목표', line_width=1.5))
    # 내 수조 (채우기)
    fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', fillcolor=color_fill, line_color=color_line, mode='lines+markers+text', text=txt_vals, textfont=dict(color=color_line, family="Quicksand"), marker=dict(size=8), line_width=2.5, name="현재"))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=False, range=[0,1.5]),
            angularaxis=dict(tickfont=dict(color="#00796B", size=12, family="Quicksand"), gridcolor="#E0F2F1"),
            bgcolor="rgba(255,255,255,0.6)" # 그래프 배경 반투명
        ),
        paper_bgcolor="rgba(0,0,0,0)", # 전체 배경 투명
        font=dict(family="Quicksand"),
        height=320,
        margin=dict(t=40,b=30,l=30,r=30),
        title=dict(text=title, font=dict(color="#00796B", size=16), y=0.95)
    )
    return fig

# --- 6. 메인 화면 ---
st.title("🐠 My Lovely Reef Manager")
st.caption("오늘도 즐거운 물생활 되세요! 💙")

if "config" not in st.session_state: st.session_state.config = load_config()
cfg = st.session_state.config

# 사이드바 디자인
with st.sidebar:
    st.header("⚙️ 수조 환경 설정")
    with st.container(): # 카드형 컨테이너 적용
        volume = st.number_input("💧 총 물량 (L)", value=float(cfg["volume"]), step=0.1)
        base_dose = st.number_input("💉 기본 도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    
    st.divider()
    st.subheader("🎯 나의 목표 수치")
    with st.container():
        t_kh = st.number_input("KH (경도)", value=float(cfg["t_kh"]), step=0.01)
        c_ca, c_mg = st.columns(2)
        t_ca = c_ca.number_input("Ca (칼슘)", value=int(cfg["t_ca"]), step=10)
        t_mg = c_mg.number_input("Mg (마그네슘)", value=int(cfg["t_mg"]), step=10)
        
        st.caption("영양염 및 기타")
        c_no3, c_po4 = st.columns(2)
        t_no3 = c_no3.number_input("NO3", value=float(cfg["t_no3"]), step=0.1)
        t_po4 = c_po4.number_input("PO4", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
        # (나머지 생략)
        t_no2=float(cfg["t_no2"]); t_ph=float(cfg["t_ph"])

    if st.button("💾 설정 저장하기", use_container_width=True):
        new_conf = cfg.copy()
        new_conf.update({"volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, "t_mg":t_mg, "t_no3":t_no3, "t_po4":t_po4})
        save_config(new_conf)
        st.session_state.config = new_conf
        st.toast("설정이 예쁘게 저장되었어요! 🎉"); st.rerun()

# 메인 입력창
with st.expander("📝 오늘의 기록 남기기 (Click!)", expanded=False):
    with st.form("entry"):
        st.write("측정값을 입력해주세요.")
        c1,c2,c3,c4 = st.columns(4)
        d_date=c1.date_input("📅 날짜",date.today())
        d_kh=c1.number_input("KH",value=t_kh,step=0.01)
        d_ca=c2.number_input("Ca",value=t_ca,step=10); d_mg=c2.number_input("Mg",value=t_mg,step=10)
        d_no3=c3.number_input("NO3",value=t_no3,step=0.1); d_po4=c3.number_input("PO4",value=t_po4,format="%.3f",step=0.01)
        d_temp=c4.number_input("온도",value=25.0,step=0.1); d_sal=c4.number_input("염도",value=35.0,step=0.1)
        # (나머지 기본값)
        d_no2=0.0; d_ph=8.3
        d_memo=st.text_area("💬 메모 (오늘의 특이사항)")
        
        if st.form_submit_button("기록 저장 💾", use_container_width=True):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":d_no2,"NO3":d_no3,"PO4":d_po4,"pH":d_ph,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
            save_data(entry)
            st.toast("기록이 안전하게 저장되었습니다! 💖"); st.rerun()

st.divider()
df = load_data()

if not df.empty:
    last = df.iloc[-1]
    
    # 그래프 및 분석 구역 (카드형 적용)
    with st.container():
        g1, g2 = st.columns([1.4, 0.8])
        with g1:
            st.subheader("📊 수질 밸런스 확인")
            col_g1, col_g2 = st.columns(2)
            # 그래프 색상 변경 (산호색/바다색)
            col_g1.plotly_chart(draw_radar(["KH","Ca","Mg"],[last["KH"],last["Ca"],last["Mg"]],[t_kh,t_ca,t_mg],"주요 3요소","rgba(255, 138, 101, 0.4)", "#FF7043"), use_container_width=True)
            col_g2.plotly_chart(draw_radar(["NO3","PO4","염도"],[last["NO3"],last["PO4"]*100,last["Salinity"]],[t_no3,t_po4*100,35.0],"영양염/환경","rgba(38, 198, 218, 0.4)", "#00ACC1"), use_container_width=True)
        
        with g2:
            st.subheader("🤖 AI 산호 요정의 조언")
            kh_diff = last["KH"] - t_kh
            vol_factor = volume / 100.0
            
            with st.container(): # 조언 박스
                if abs(kh_diff) <= 0.15:
                    st.success(f"✨ 와우! KH가 목표치({t_kh})와 거의 같아요. 완벽합니다! 👍")
                elif kh_diff < 0:
                    add = 0.3 * vol_factor
                    st.error(f"💧 KH가 조금 낮아요. 도징량을 약 {base_dose+add:.1f}ml로 늘려보는 건 어떨까요?")
                else:
                    sub = 0.3 * vol_factor
                    st.warning(f"🔥 KH가 조금 높네요. 도징량을 약 {max(0, base_dose-sub):.1f}ml로 줄여주세요.")

    st.divider()
    
    # 스케줄 관리 (카드형 적용)
    with st.container():
        st.subheader("🗓️ 주간 관리 스케줄")
        current_sch = cfg.get("schedule", "")
        new_sch = st.text_area("잊지 말아야 할 일들을 적어두세요!", value=current_sch, height=120, placeholder="예: 수요일 환수, 토요일 산호 밥 주기")
        if st.button("💾 스케줄 저장"):
            updated_conf = cfg.copy()
            updated_conf["schedule"] = new_sch
            save_config(updated_conf)
            st.session_state.config = updated_conf
            st.toast("스케줄이 저장되었어요!")

    st.divider()
    
    # 기록 관리 (엑셀형 + 삭제)
    st.subheader("📋 전체 기록부")
    with st.container():
        df_display = df.sort_values("날짜", ascending=False).copy()
        df_display.insert(0, "삭제", False)
        df_display['Memo'] = df_display['Memo'].apply(lambda x: str(x) if x else "")

        edited_df = st.data_editor(
            df_display,
            column_config={
                "삭제": st.column_config.CheckboxColumn("선택", width="small"),
                "_row_idx": None,
                "Memo": st.column_config.TextColumn("메모", width="large"),
                "날짜": st.column_config.DateColumn("날짜", format="YYYY-MM-DD")
            },
            disabled=HEADERS, hide_index=True, use_container_width=True
        )
        
        col_del_btn, _ = st.columns([1,3])
        if col_del_btn.button("🗑️ 선택 삭제", type="primary", use_container_width=True):
            rows_to_delete = edited_df[edited_df["삭제"] == True]
            if not rows_to_delete.empty:
                indices = rows_to_delete["_row_idx"].tolist()
                delete_rows_by_indices(indices)
                st.toast(f"{len(indices)}개의 기록을 삭제했습니다! ✨"); st.rerun()
            else:
                st.warning("삭제할 기록을 먼저 선택해주세요.")
else:
    st.info("👋 아직 기록이 없어요. 첫 기록을 남겨보세요!")
