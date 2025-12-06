import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 1. 기본 설정 ---
st.set_page_config(page_title="My Triton Lab Pro", page_icon="🐠", layout="wide")
SHEET_NAME = "MyReefLog" # 구글 시트 이름

# --- 2. 구글 시트 연결 함수 (핵심!) ---
def connect_to_gsheet():
    """Secrets에서 열쇠를 꺼내 구글 시트와 연결합니다."""
    try:
        # Streamlit Secrets에서 정보 가져오기 (TOML 형식으로 저장된 것 자동 변환)
        # Secrets에 [gcp_service_account] 라고 저장했으므로 그대로 불러옵니다.
        # 만약 JSON 내용을 통째로 붙여넣었다면 st.secrets["gcp_service_account"] 자체가 딕셔너리가 됩니다.
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        return sheet
    except Exception as e:
        return None

# --- 3. 데이터 불러오기/저장하기 (구글 시트 버전) ---
def load_data():
    sheet = connect_to_gsheet()
    if sheet:
        # 구글 시트에서 데이터 가져오기
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["날짜", "KH", "Ca", "Mg", "NO2", "NO3", "PO4", "pH", "Temp", "Salinity", "도징량", "Memo"])
        df = pd.read_json(json.dumps(data)) # 데이터 형변환 안전장치
        
        # 필수 컬럼 확인
        required_cols = {"pH": 8.1, "Memo": "", "NO2": 0.0}
        for col, default_val in required_cols.items():
            if col not in df.columns:
                df[col] = default_val
        return df
    else:
        # 구글 시트 연결 실패 시 (로컬 테스트용) - 빈 데이터 반환
        return pd.DataFrame(columns=["날짜", "KH", "Ca", "Mg", "NO2", "NO3", "PO4", "pH", "Temp", "Salinity", "도징량", "Memo"])

def save_data(new_entry):
    sheet = connect_to_gsheet()
    if sheet:
        # 구글 시트에 행 추가
        # 순서 보장을 위해 리스트로 변환
        row = [
            str(new_entry["날짜"]), 
            new_entry["KH"], new_entry["Ca"], new_entry["Mg"], 
            new_entry["NO2"], new_entry["NO3"], new_entry["PO4"], 
            new_entry["pH"], new_entry["Temp"], new_entry["Salinity"], 
            new_entry["도징량"], new_entry["Memo"]
        ]
        # 헤더가 없으면 먼저 씀
        if len(sheet.get_all_values()) == 0:
            header = ["날짜", "KH", "Ca", "Mg", "NO2", "NO3", "PO4", "pH", "Temp", "Salinity", "도징량", "Memo"]
            sheet.append_row(header)
            
        sheet.append_row(row)
        return True
    return False

# --- 4. 설정값 관리 (세션 스테이트 사용 - 시트 저장 X, 간편하게) ---
# (구글 시트에 설정까지 저장하면 복잡해지므로, 설정은 앱 켜져있는 동안만 유지되게 하거나
#  필요하면 시트에 'Config' 탭을 따로 파야 함. 여기선 기본값 사용)
if "config" not in st.session_state:
    st.session_state.config = {
        "volume": 150.0, "base_dose": 3.00,
        "t_kh": 8.30, "t_ca": 420, "t_mg": 1420,
        "t_no2": 0.010, "t_no3": 5.00, "t_po4": 0.040, "t_ph": 8.30
    }

# 그래프 함수 (디자인 유지)
def draw_radar_chart(categories, values, target_values, title, color_fill):
    normalized_values = []
    real_value_text = []
    for v, t in zip(values, target_values):
        if isinstance(v, float): real_value_text.append(f"{v:.2f}")
        else: real_value_text.append(f"{v}")
        if t <= 0.01: 
            if v <= t: normalized_values.append(v / t if t > 0 else 0)
            else: normalized_values.append(1 + (v - t) * 50)
        else: normalized_values.append(v / t)
    categories = [*categories, categories[0]]
    normalized_values = [*normalized_values, normalized_values[0]]
    real_value_text = [*real_value_text, ""]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[1]*len(categories), theta=categories, fill=None, name='목표', line_color="white", line_dash='dot', hoverinfo='skip'))
    fig.add_trace(go.Scatterpolar(r=normalized_values, theta=categories, fill='toself', name='내 수조', line_color=color_fill, opacity=0.7, mode='lines+markers+text', text=real_value_text, textposition="top center", textfont=dict(color=color_fill, size=13, weight="bold")))
    fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 1.5]), angularaxis=dict(tickfont=dict(color="#00BFFF", size=14, weight="bold"), linecolor="#444", gridcolor="#444"), bgcolor="rgba(0,0,0,0)"), title=dict(text=title, font=dict(color="#00BFFF", size=20)), font=dict(color="#00BFFF"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=380, margin=dict(l=40, r=40, t=60, b=40), legend=dict(font=dict(color="white"), orientation="h", y=-0.1))
    return fig

# --- 5. 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 수조 & 목표 설정")
    cfg = st.session_state.config
    volume = st.number_input("총 물량 (L)", value=cfg["volume"], step=0.1, format="%.1f")
    base_dose = st.number_input("기본 도징량 (ml)", value=cfg["base_dose"], step=0.01, format="%.2f")
    st.divider()
    st.subheader("🎯 목표치")
    t_kh = st.number_input("목표 KH", value=cfg["t_kh"], step=0.01, format="%.2f")
    t_ca = st.number_input("목표 Ca", value=cfg["t_ca"], step=10)
    t_mg = st.number_input("목표 Mg", value=cfg["t_mg"], step=10)
    t_no2 = st.number_input("목표 NO2", value=cfg["t_no2"], step=0.001, format="%.3f")
    t_no3 = st.number_input("목표 NO3", value=cfg["t_no3"], step=0.10, format="%.2f")
    t_po4 = st.number_input("목표 PO4", value=cfg["t_po4"], step=0.001, format="%.3f")
    t_ph = st.number_input("목표 pH", value=cfg["t_ph"], step=0.01, format="%.2f")
    
    # 설정값 업데이트
    st.session_state.config.update({
        "volume": volume, "base_dose": base_dose,
        "t_kh": t_kh, "t_ca": t_ca, "t_mg": t_mg,
        "t_no2": t_no2, "t_no3": t_no3, "t_po4": t_po4, "t_ph": t_ph
    })

# --- 6. 메인 화면 ---
st.title("🌊 My Triton Reef Manager (Cloud)")

# 연결 상태 확인
sheet_status = connect_to_gsheet()
if sheet_status is None:
    st.error("⚠️ 구글 시트 연결 실패! (Secrets 설정을 확인하세요)")
    st.info("설정이 완료될 때까지 기록이 저장되지 않습니다.")
else:
    st.success(f"✅ 구글 시트 '{SHEET_NAME}'와 연결됨")

with st.expander("📝 **기록 입력**", expanded=True):
    with st.form("entry"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            d_date = st.date_input("날짜", date.today())
            d_kh = st.number_input("KH", value=t_kh, step=0.01, format="%.2f")
        with c2:
            d_ca = st.number_input("Ca", value=t_ca, step=10)
            d_mg = st.number_input("Mg", value=t_mg, step=10)
        with c3:
            d_no2 = st.number_input("NO2", value=0.000, step=0.001, format="%.3f")
            d_no3 = st.number_input("NO3", value=t_no3, step=0.01, format="%.2f")
            d_po4 = st.number_input("PO4", value=t_po4, step=0.001, format="%.3f")
        with c4:
            d_ph = st.number_input("pH", value=t_ph, step=0.01, format="%.2f")
            d_sal = st.number_input("염도", value=35.0, step=0.1, format="%.1f")
            d_temp = st.number_input("온도", value=25.0, step=0.1, format="%.1f")
        d_memo = st.text_area("메모")
        
        if st.form_submit_button("저장 💾"):
            entry = {"날짜": d_date, "KH": d_kh, "Ca": d_ca, "Mg": d_mg, "NO2": d_no2, "NO3": d_no3, "PO4": d_po4, "pH": d_ph, "Temp": d_temp, "Salinity": d_sal, "도징량": base_dose, "Memo": d_memo}
            if save_data(entry):
                st.toast("구글 시트에 저장 완료!", icon="✅")
            else:
                st.error("저장 실패")

st.divider()
df = load_data()
if not df.empty:
    last = df.iloc[-1]
    g1, g2 = st.columns([1.2, 0.8])
    with g1:
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(draw_radar_chart(["KH", "Ca", "Mg"], [last["KH"], last["Ca"], last["Mg"]], [t_kh, t_ca, t_mg], "3요소", "#00FFAA"), use_container_width=True)
        with c2: st.plotly_chart(draw_radar_chart(["NO2", "NO3", "PO4", "pH"], [last["NO2"], last["NO3"], last["PO4"]*100, last["pH"]], [t_no2, t_no3, t_po4*100, t_ph], "영양염", "#FF5500"), use_container_width=True)
    with g2:
        st.subheader("🤖 AI 분석")
        kh_diff = last["KH"] - t_kh
        rec_dose = base_dose
        if abs(kh_diff) <= 0.15: st.info(f"✅ KH 완벽 ({last['KH']}). 유지하세요.")
        elif kh_diff < 0: 
            add = 0.3 * (volume/100)
            st.error(f"📉 KH 부족. {base_dose+add:.2f}ml로 증량!")
        else: 
            sub = 0.3 * (volume/100)
            st.warning(f"📈 KH 과다. {max(0, base_dose-sub):.2f}ml로 감량!")
            
st.subheader("📋 기록 (구글 시트 연동)")
if not df.empty:
    st.dataframe(df.sort_values("날짜", ascending=False), use_container_width=True)
