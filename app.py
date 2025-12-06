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

# --- 1. 인증 및 연결 (가장 튼튼한 버전) ---
def get_creds():
    # 1순위: Secrets 확인 (형식이 조금 틀려도 최대한 읽어보려 노력함)
    if "gcp_service_account" in st.secrets:
        try:
            secrets_data = st.secrets["gcp_service_account"]
            # info = """...""" 형태로 저장된 경우
            if "info" in secrets_data:
                return json.loads(secrets_data["info"])
            # 그냥 내용이 바로 저장된 경우
            else:
                return dict(secrets_data)
        except:
            pass # Secrets가 이상하면 무시하고 다음 단계(파일 업로드)로 넘어감

    # 2순위: 이미 업로드한 파일이 있는지 확인 (새로고침 해도 유지되게)
    if "uploaded_creds" in st.session_state:
        return st.session_state.uploaded_creds
        
    return None

creds_dict = get_creds()

# 인증 파일 없으면 업로더 표시
if creds_dict is None:
    st.warning("⚠️ **로봇 열쇠 파일(JSON)**을 업로드해주세요.")
    # key를 고정해서 에러 방지
    uploaded_file = st.file_uploader("JSON 파일 드래그 & 드롭", type="json", key="auth_file")
    
    if uploaded_file:
        try:
            creds = json.load(uploaded_file)
            if "client_email" in creds:
                # [핵심] 업로드한 열쇠를 앱이 기억하게 저장
                st.session_state.uploaded_creds = creds
                st.success("✅ 인증 성공! (잠시만 기다리세요...)")
                st.rerun()
            else: 
                st.error("🚨 올바른 키 파일이 아닙니다.")
        except: 
            st.error("🚨 파일 읽기 오류")
    st.stop() # 인증 전에는 아래 코드 실행 막기

# --- 2. 구글 시트 연결 ---
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def get_sheet_tabs():
    client = get_client()
    try: sh = client.open(SHEET_NAME)
    except: st.error(f"🚨 구글 시트 '{SHEET_NAME}'를 찾을 수 없습니다."); st.stop()

    sheet_log = sh.sheet1
    if sheet_log.title != "Logs": 
        try: sheet_log.update_title("Logs")
        except: pass
    
    # 헤더 복구
    try:
        current_headers = sheet_log.row_values(1)
        if not current_headers or current_headers[0] != "날짜":
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
    # 삭제를 위해 행 번호 저장
    df['sheet_row_num'] = range(2, len(df) + 2)
    
    cols_to_num = ["KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량"]
    for c in cols_to_num:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df

def save_data(entry):
    sheet_log, _ = get_sheet_tabs()
    row = [str(entry["날짜"]), entry["KH"], entry["Ca"], entry["Mg"], entry["NO2"], entry["NO3"], entry["PO4"], entry["pH"], entry["Temp"], entry["Salinity"], entry["도징량"], entry["Memo"]]
    sheet_log.append_row(row)
    return True

def delete_data(sheet_row_num):
    sheet_log, _ = get_sheet_tabs()
    sheet_log.delete_rows(sheet_row_num)

# --- 4. 설정 관리 ---
def load_config():
    _, sheet_config = get_sheet_tabs()
    records = sheet_config.get_all_records()
    default = {"volume":150.0,"base_dose":3.00,"t_kh":8.30,"t_ca":420,"t_mg":1420,"t_no2":0.010,"t_no3":5.00,"t_po4":0.040,"t_ph":8.30}
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
    norm_vals = []; txt_vals = []
    for v, t in zip(vals, t_vals):
        txt_vals.append(f"{v}"); norm_vals.append(v/t if t>0.01 and v<=t else (1+(v-t)*50 if t<=0.01 else v/t))
    cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]; txt_vals=[*txt_vals,""]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line_color="white", line_dash='dot', name='목표'))
    fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', line_color=color, mode='lines+markers+text', text=txt_vals, textfont=dict(color=color)))
    fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0,1.5]), angularaxis=dict(tickfont=dict(color="#00BFFF", size=12)), bgcolor="rgba(0,0,0,0)"), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#00BFFF"), height=350, margin=dict(t=40,b=40))
    return fig

# --- 6. 메인 화면 ---
st.title("🌊 My Triton Manager (Cloud)")

if "config" not in st.session_state: st.session_state.config = load_config()
cfg = st.session_state.config

# 사이드바
with st.sidebar:
    st.header("⚙️ 수조 & 목표 설정")
    volume = st.number_input("물량 (L)", value=float(cfg["volume"]), step=0.1)
    base_dose = st.number_input("도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    st.divider(); st.subheader("🎯 목표치")
    t_kh = st.number_input("목표 KH", value=float(cfg["t_kh"]), step=0.01)
    t_ca = st.number_input("목표 Ca", value=int(cfg["t_ca"]), step=10)
    t_mg = st.number_input("목표 Mg", value=int(cfg["t_mg"]), step=10)
    t_no2 = st.number_input("목표 NO2", value=float(cfg["t_no2"]), format="%.3f", step=0.001)
    t_no3 = st.number_input("목표 NO3", value=float(cfg["t_no3"]), step=0.1)
    t_po4 = st.number_input("목표 PO4", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
    t_ph = st.number_input("목표 pH", value=float(cfg["t_ph"]), step=0.1)
    
    if st.button("💾 설정값 영구 저장"):
        new_conf = {"volume":volume, "base_dose":base_dose, "t_kh":t_kh, "t_ca":t_ca, "t_mg":t_mg, "t_no2":t_no2, "t_no3":t_no3, "t_po4":t_po4, "t_ph":t_ph}
        save_config(new_conf)
        st.session_state.config = new_conf
        st.toast("설정 저장 완료!"); st.rerun()

st.success("✅ 구글 시트 연결됨")

# 기록 입력창
with st.expander("📝 새 기록 입력하기", expanded=False):
    with st.form("entry"):
        c1,c2,c3,c4 = st.columns(4)
        d_date=c1.date_input("날짜",date.today())
        d_kh=c1.number_input("KH",value=t_kh,step=0.01)
        d_ca=c2.number_input("Ca",value=t_ca,step=10)
        d_mg=c2.number_input("Mg",value=t_mg,step=10)
        d_no2=c3.number_input("NO2",value=0.0,format="%.3f",step=0.001)
        d_no3=c3.number_input("NO3",value=t_no3,step=0.1)
        d_po4=c3.number_input("PO4",value=t_po4,format="%.3f",step=0.01)
        d_ph=c4.number_input("pH",value=t_ph,step=0.1)
        d_sal=c4.number_input("염도",value=35.0,step=0.1)
        d_temp=c4.number_input("온도",value=25.0,step=0.1)
        d_memo=st.text_area("메모 (길게 써도 됩니다)")
        if st.form_submit_button("저장 💾"):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":d_no2,"NO3":d_no3,"PO4":d_po4,"pH":d_ph,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
            if save_data(entry): st.toast("저장되었습니다!"); st.rerun()

st.divider()
df = load_data()

if not df.empty:
    last = df.iloc[-1]
    g1,g2 = st.columns([1.2, 0.8])
    with g1:
        c1,c2 = st.columns(2)
        c1.plotly_chart(draw_radar(["KH","Ca","Mg"],[last["KH"],last["Ca"],last["Mg"]],[t_kh,t_ca,t_mg],"3요소","#00FFAA"), use_container_width=True)
        c2.plotly_chart(draw_radar(["NO2","NO3","PO4","pH"],[last["NO2"],last["NO3"],last["PO4"]*100,last["pH"]],[t_no2,t_no3,t_po4*100,t_ph],"영양염","#FF5500"), use_container_width=True)
    with g2:
        st.subheader("🤖 AI 분석 (최신 기록)")
        kh_diff = last["KH"] - t_kh
        vol_factor = volume / 100.0
        if abs(kh_diff) <= 0.15: st.info(f"✅ KH 완벽 ({last['KH']})")
        elif kh_diff < 0: 
            add = 0.3 * vol_factor
            st.error(f"📉 KH 부족. 추천: {base_dose+add:.2f}ml")
        else: 
            sub = 0.3 * vol_factor
            st.warning(f"📈 KH 과다. 추천: {max(0, base_dose-sub):.2f}ml")

    st.divider()
    
    # [수정 완료] 다시 깔끔한 '전체 표(List)'로 복귀!
    st.subheader("📋 전체 기록 (최신순)")
    
    # 1. 보기 편하게 메모가 있으면 아이콘으로 표시
    df_display = df.sort_values("날짜", ascending=False).copy()
    
    # 2. 메인 표 보여주기 (여기서 다 봅니다)
    st.dataframe(
        df_display[['날짜','KH','Ca','Mg','NO2','NO3','PO4','pH','Temp','Salinity','도징량','Memo']], 
        use_container_width=True,
        hide_index=True
    )
    
    # 3. 삭제 기능 (선택 상자로 깔끔하게)
    st.markdown("### 🗑️ 기록 삭제")
    col_del1, col_del2 = st.columns([3, 1])
    with col_del1:
        # 삭제할 기록을 선택하세요
        del_target = st.selectbox(
            "삭제할 기록 선택:", 
            options=df_display.index, 
            format_func=lambda i: f"[{df_display.loc[i,'날짜']}] KH: {df_display.loc[i,'KH']} (기록 #{i+1})",
            label_visibility="collapsed"
        )
    with col_del2:
        if st.button("삭제하기", type="primary"):
            if del_target is not None:
                # 선택된 행의 진짜 시트 행 번호를 가져와서 삭제
                real_row_num = df_display.loc[del_target, 'sheet_row_num']
                delete_data(real_row_num)
                st.toast("삭제 완료! 새로고침 중...")
                st.rerun()

else:
    st.info("👋 기록이 없습니다. 데이터를 입력해주세요!")
