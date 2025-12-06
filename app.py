import streamlit as st
import json
import re

st.set_page_config(page_title="앱 생성기 V2", layout="wide")
st.title("🤖 최종 앱 코드 생성기 (강력 청소 버전)")
st.info("아래 칸에 로봇 열쇠(JSON) 내용을 붙여넣고 버튼을 누르세요.")

# 1. 키 입력 받기
key_input = st.text_area("여기에 키 붙여넣기", height=300)

# 2. 진짜 앱 코드 템플릿
FINAL_APP_CODE = r'''import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="My Triton Lab Pro", page_icon="🐠", layout="wide")
SHEET_NAME = "MyReefLog"
HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# ▼▼▼ 선생님의 키가 여기에 자동으로 들어갑니다 ▼▼▼
ROBOT_KEY = """
__KEY_HERE__
"""
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

# --- 1. 인증 ---
def get_creds():
    try:
        # strict=False로 설정하여 줄바꿈 문자 등을 관대하게 처리
        return json.loads(ROBOT_KEY, strict=False)
    except Exception as e:
        st.error(f"🚨 키 설정 오류: {e}")
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
    except: st.error(f"🚨 구글 시트 '{SHEET_NAME}'를 찾을 수 없습니다. (시트 이름을 확인하세요!)"); st.stop()

    sheet_log = sh.sheet1
    if sheet_log.title != "Logs": 
        try: sheet_log.update_title("Logs")
        except: pass
    
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
    # 행 번호 저장
    df['_row_idx'] = range(2, len(df) + 2)
    cols_to_num = ["KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량"]
    for c in cols_to_num:
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

with st.expander("📝 새 기록 입력하기", expanded=False):
    with st.form("entry"):
        c1,c2,c3,c4 = st.columns(4)
        d_date=c1.date_input("날짜",date.today()); d_kh=c1.number_input("KH",value=t_kh,step=0.01)
        d_ca=c2.number_input("Ca",value=t_ca,step=10); d_mg=c2.number_input("Mg",value=t_mg,step=10)
        d_no2=c3.number_input("NO2",value=0.0,format="%.3f",step=0.001); d_no3=c3.number_input("NO3",value=t_no3,step=0.1); d_po4=c3.number_input("PO4",value=t_po4,format="%.3f",step=0.01)
        d_ph=c4.number_input("pH",value=t_ph,step=0.1); d_sal=c4.number_input("염도",value=35.0,step=0.1); d_temp=c4.number_input("온도",value=25.0,step=0.1)
        d_memo=st.text_area("메모")
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
        st.subheader("🤖 AI 분석")
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
    st.subheader("📋 전체 기록 관리 (체크 후 삭제)")
    df_display = df.sort_values("날짜", ascending=False).copy()
    df_display.insert(0, "삭제", False)
    
    # 메모 보여주기
    df_display['Memo'] = df_display['Memo'].apply(lambda x: f"📝 {x}" if x and str(x).strip() else "")

    edited_df = st.data_editor(
        df_display,
        column_config={"삭제": st.column_config.CheckboxColumn("삭제 선택", default=False), "_row_idx": None},
        disabled=HEADERS, hide_index=True, use_container_width=True
    )
    if st.button("🗑️ 선택한 기록 삭제하기", type="primary"):
        rows_to_delete = edited_df[edited_df["삭제"] == True]
        if not rows_to_delete.empty:
            indices = rows_to_delete["_row_idx"].tolist()
            delete_rows_by_indices(indices)
            st.toast(f"{len(indices)}개의 기록을 삭제했습니다!"); st.rerun()
        else:
            st.warning("먼저 표에서 지울 항목을 체크해주세요.")
else:
    st.info("👋 기록이 없습니다. 데이터를 입력해주세요!")
'''

if st.button("🚀 내 전용 앱 코드 만들기 (클릭)"):
    if not key_input.strip():
        st.error("⚠️ 키 내용을 먼저 붙여넣어 주세요!")
    else:
        try:
            # [강력 청소 기능]
            # 1. 눈에 안 보이는 제어 문자 제거
            cleaned_key = "".join(ch for ch in key_input if ch.isprintable() or ch in ['\n', '\r', '\t'])
            # 2. JSON 파싱 시도 (strict=False로 조금 더 관대하게)
            json_obj = json.loads(cleaned_key, strict=False)
            
            # 3. 다시 깨끗한 문자열로 변환
            clean_json_str = json.dumps(json_obj, indent=2)
            
            # 4. 코드 생성
            final_code = FINAL_APP_CODE.replace("__KEY_HERE__", clean_json_str)
            
            st.success("🎉 성공! 아래 코드를 복사해서 app.py에 덮어씌우세요.")
            st.code(final_code, language="python")
        except Exception as e:
            st.error(f"🚨 아직도 형식이 안 맞습니다. 에러 내용: {e}")
            st.info("메모장에서 { 괄호부터 } 괄호까지 정확하게 복사했는지 다시 확인해주세요.")
