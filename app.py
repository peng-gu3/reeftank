import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="My Triton Lab Pro", page_icon="🐠", layout="wide")
SHEET_NAME = "MyReefLog"

# --- 1. 만능 연결 함수 (Secrets 실패 시 파일 업로드 창 띄움) ---
def connect_to_gsheet():
    creds_dict = None
    
    # [1단계] Secrets 먼저 확인
    if "gcp_service_account" in st.secrets:
        try:
            secrets_data = st.secrets["gcp_service_account"]
            if "info" in secrets_data:
                creds_dict = json.loads(secrets_data["info"])
            else:
                creds_dict = dict(secrets_data)
            
            # 중요: 이메일이 없으면 실패 처리
            if "client_email" not in creds_dict:
                creds_dict = None 
        except:
            creds_dict = None

    # [2단계] Secrets가 안 되면 -> 파일 업로더 표시
    if creds_dict is None:
        st.warning("⚠️ Secrets 설정에 문제가 있습니다. 임시로 **로봇 열쇠 파일(JSON)**을 직접 올려주세요.")
        uploaded_file = st.file_uploader("여기에 'reef-tank-...' JSON 파일을 끌어다 놓으세요", type="json")
        
        if uploaded_file is not None:
            try:
                creds_dict = json.load(uploaded_file)
                st.success("✅ 파일 확인 완료! (이 상태로 기록 가능합니다)")
                
                # [보너스] 다음 번을 위해 올바른 Secrets 내용 만들어주기
                st.divider()
                st.info("👇 나중에 이 내용을 복사해서 Secrets에 붙여넣으면 파일 업로드 없이 접속됩니다.")
                toml_str = '[gcp_service_account]\ninfo = """\n' + json.dumps(creds_dict) + '\n"""'
                st.code(toml_str, language="toml")
                st.divider()
            except:
                st.error("🚨 잘못된 파일입니다.")
                return None
        else:
            return None

    # [3단계] 연결 시도
    if creds_dict:
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            return sheet
        except Exception as e:
            st.error(f"연결 실패: {e}")
            return None
    return None

# --- 데이터 관리 ---
def load_data():
    sheet = connect_to_gsheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            if not data: return pd.DataFrame(columns=["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"])
            df = pd.read_json(json.dumps(data))
            required = {"pH":8.1, "Memo":"", "NO2":0.0}
            for c,v in required.items(): 
                if c not in df.columns: df[c]=v
            return df
        except: pass
    return pd.DataFrame(columns=["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"])

def save_data(new_entry):
    sheet = connect_to_gsheet()
    if sheet:
        row = [str(new_entry["날짜"]), new_entry["KH"], new_entry["Ca"], new_entry["Mg"], new_entry["NO2"], new_entry["NO3"], new_entry["PO4"], new_entry["pH"], new_entry["Temp"], new_entry["Salinity"], new_entry["도징량"], new_entry["Memo"]]
        if len(sheet.get_all_values()) == 0: sheet.append_row(["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"])
        sheet.append_row(row)
        return True
    return False

# --- 설정 관리 ---
if "config" not in st.session_state:
    st.session_state.config = {"volume":150.0,"base_dose":3.00,"t_kh":8.30,"t_ca":420,"t_mg":1420,"t_no2":0.010,"t_no3":5.00,"t_po4":0.040,"t_ph":8.30}

# --- 그래프 ---
def draw_radar(cats, vals, t_vals, title, color):
    norm_vals = []
    txt_vals = []
    for v, t in zip(vals, t_vals):
        txt_vals.append(f"{v:.2f}" if isinstance(v, float) else f"{v}")
        if t <= 0.01: norm_vals.append(v/t if t>0 and v<=t else (1+(v-t)*50))
        else: norm_vals.append(v/t)
    cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]; txt_vals=[*txt_vals,""]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line_color="white", line_dash='dot', name='목표'))
    fig.add_trace(go.Scatterpolar(r=norm_vals, theta=cats, fill='toself', line_color=color, mode='lines+markers+text', text=txt_vals, textfont=dict(color=color, weight="bold")))
    fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0,1.5]), angularaxis=dict(color="#00BFFF", weight="bold"), bgcolor="rgba(0,0,0,0)"), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#00BFFF"), height=350, margin=dict(t=40,b=40))
    return fig

# --- 화면 구성 ---
with st.sidebar:
    st.header("⚙️ 설정"); cfg=st.session_state.config
    volume=st.number_input("물량",value=cfg["volume"],step=0.1); base_dose=st.number_input("도징량",value=cfg["base_dose"],step=0.01)
    st.divider(); st.subheader("🎯 목표")
    t_kh=st.number_input("KH",value=cfg["t_kh"],step=0.01); t_ca=st.number_input("Ca",value=cfg["t_ca"]); t_mg=st.number_input("Mg",value
