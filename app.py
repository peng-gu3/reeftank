import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="My Triton Lab Pro", page_icon="🐠", layout="wide")
SHEET_NAME = "MyReefLog"

# --- 1. 자격 증명(열쇠) 확보하기 (가장 먼저 실행) ---
def get_creds():
    # 1순위: Secrets 확인
    if "gcp_service_account" in st.secrets:
        try:
            secrets_data = st.secrets["gcp_service_account"]
            if "info" in secrets_data:
                creds = json.loads(secrets_data["info"])
            else:
                creds = dict(secrets_data)
            
            # 이메일 확인 (유효성 검사)
            if "client_email" in creds:
                return creds
        except:
            pass

    # 2순위: 이미 업로드된 파일이 있는지 확인 (Session State)
    if "uploaded_creds" in st.session_state:
        return st.session_state.uploaded_creds

    return None

# --- 2. 열쇠가 없으면 업로드 버튼 띄우기 (여기서 결판냄) ---
creds_dict = get_creds()

if creds_dict is None:
    st.warning("⚠️ Secrets 설정이 안 되어 있습니다. **로봇 열쇠 파일(JSON)**을 업로드해주세요.")
    
    # 파일 업로더 (고유 key 부여로 에러 방지)
    uploaded_file = st.file_uploader("여기에 'reef-tank-...' JSON 파일을 끌어다 놓으세요", type="json", key="auth_uploader")
    
    if uploaded_file is not None:
        try:
            loaded_creds = json.load(uploaded_file)
            if "client_email" in loaded_creds:
                st.session_state.uploaded_creds = loaded_creds # 저장
                st.success("✅ 인증 성공! (새로고침 중...)")
                st.rerun() # 앱 재시작
            else:
                st.error("🚨 올바른 키 파일이 아닙니다. (client_email 없음)")
                st.stop()
        except Exception as e:
            st.error(f"🚨 파일 읽기 오류: {e}")
            st.stop()
    else:
        st.info("👆 위 박스에 파일을 넣어야 앱이 실행됩니다.")
        st.stop() # 파일 없으면 여기서 코드 실행 중단! (에러 원천 봉쇄)

# --- 3. 구글 시트 연결 함수 (이제 안전함) ---
def connect_to_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # 위에서 확보한 creds_dict를 사용
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
    except Exception as e:
        st.error(f"⚠️ 구글 시트 연결 실패: {e}")
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
    t_kh=st.number_input("KH",value=cfg["t_kh"],step=0.01); t_ca=st.number_input("Ca",value=cfg["t_ca"]); t_mg=st.number_input("Mg",value=cfg["t_mg"])
    t_no2=st.number_input("NO2",value=cfg["t_no2"],format="%.3f"); t_no3=st.number_input("NO3",value=cfg["t_no3"]); t_po4=st.number_input("PO4",value=cfg["t_po4"],format="%.3f"); t_ph=st.number_input("pH",value=cfg["t_ph"])
    st.session_state.config.update({"volume":volume,"base_dose":base_dose,"t_kh":t_kh,"t_ca":t_ca,"t_mg":t_mg,"t_no2":t_no2,"t_no3":t_no3,"t_po4":t_po4,"t_ph":t_ph})

st.title("🌊 My Triton Manager (Cloud)")

# 시트 연결 시도
sheet = connect_to_gsheet()
if sheet:
    st.success(f"✅ 구글 시트 연결 성공!")

with st.expander("📝 기록 입력", expanded=True):
    with st.form("entry"):
        c1,c2,c3,c4 = st.columns(4)
        d_date=c1.date_input("날짜",date.today()); d_kh=c1.number_input("KH",value=t_kh,step=0.01)
        d_ca=c2.number_input("Ca",value=t_ca); d_mg=c2.number_input("Mg",value=t_mg)
        d_no2=c3.number_input("NO2",value=0.0,format="%.3f"); d_no3=c3.number_input("NO3",value=t_no3); d_po4=c3.number_input("PO4",value=t_po4,format="%.3f")
        d_ph=c4.number_input("pH",value=t_ph); d_sal=c4.number_input("염도",value=35.0); d_temp=c4.number_input("온도",value=25.0)
        d_memo=st.text_area("메모")
        if st.form_submit_button("저장 💾"):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":d_no2,"NO3":d_no3,"PO4":d_po4,"pH":d_ph,"Temp":d_temp,"Salinity":d_sal,"도징량":base_dose,"Memo":d_memo}
            if save_data(entry): st.toast("저장됨!"); st.rerun()

st.divider()
df=load_data()
if not df.empty:
    last=df.iloc[-1]
    g1,g2=st.columns([1.2,0.8])
    g1.plotly_chart(draw_radar(["KH","Ca","Mg"],[last["KH"],last["Ca"],last["Mg"]],[t_kh,t_ca,t_mg],"3요소","#00FFAA"),use_container_width=True)
    g1.plotly_chart(draw_radar(["NO2","NO3","PO4","pH"],[last["NO2"],last["NO3"],last["PO4"]*100,last["pH"]],[t_no2,t_no3,t_po4*100,t_ph],"영양염","#FF5500"),use_container_width=True)
    g2.subheader("🤖 AI 분석")
    diff=last["KH"]-t_kh
    if abs(diff)<=0.15: g2.info(f"✅ KH 완벽 ({last['KH']})")
    elif diff<0: g2.error(f"📉 KH 부족. 추천: {base_dose+0.3*(volume/100):.2f}ml")
    else: g2.warning(f"📈 KH 과다. 추천: {max(0, base_dose-0.3*(volume/100)):.2f}ml")
    
    st.subheader("📋 기록")
    st.dataframe(df.sort_values("날짜",ascending=False),use_container_width=True)
