import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

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
    
    .stApp {
        background-color: #0c1236 !important;
        background-image: radial-gradient(circle at 18% 22%, #1c3f8d 0%, #0c1236 45%) !important;
        background-attachment: fixed !important;
    }

    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #10244a !important;
        border: 1px solid #2a416a !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5) !important;
    }

    h1, h2, h3 { color: #4be8ff !important; text-shadow: 0 0 10px rgba(75, 232, 255, 0.3) !important; }
    
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
        background-color: #080c24 !important;
        color: #ffffff !important;
        border: 1px solid #2a416a !important;
        border-radius: 8px !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #4be8ff, #1c3f8d) !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
        border-radius: 8px !important;
    }
    
    div[data-testid="column"] button[kind="secondary"] {
        background: linear-gradient(135deg, #ff5252, #b71c1c) !important;
        border: 1px solid #ff5252 !important;
        color: white !important;
    }

    [data-testid="stSidebar"] {
        background-color: #080c24 !important;
        border-right: 1px solid #2a416a !important;
    }
    
    [data-testid="stDataFrame"] {
        background-color: transparent !important;
    }
</style>
""", unsafe_allow_html=True)

HEADERS = ["날짜","KH","Ca","Mg","NO2","NO3","PO4","pH","Temp","Salinity","도징량","Memo"]

# --- 1. 데이터 관리 (세션 스테이트 사용) ---
# 앱이 켜져있는 동안만 데이터를 기억합니다.
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=HEADERS)

if 'config' not in st.session_state:
    st.session_state.config = {
        "volume":150.0,"base_dose":3.00,"t_kh":8.30,"t_ca":420,"t_mg":1420,
        "t_no2":0.010,"t_no3":5.00,"t_po4":0.040,"t_ph":8.30,"t_temp":26.0,"t_sal":35.0,
        "schedule":""
    }

def save_data(entry):
    new_row = pd.DataFrame([entry])
    st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)

def delete_row(index):
    st.session_state.df = st.session_state.df.drop(index).reset_index(drop=True)

# --- 2. 그래프 함수 ---
def draw_radar(cats, vals, t_vals, title, color_fill, color_line):
    norm_vals = [v/t if t>0 else 0 for v,t in zip(vals, t_vals)]
    cats=[*cats,cats[0]]; norm_vals=[*norm_vals,norm_vals[0]]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[1]*len(cats), theta=cats, line=dict(color="#a9bdd6", dash='dot'), name='Target'))
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

# --- 3. 메인 화면 ---
st.title("🧪 My Triton Lab (Local)")
cfg = st.session_state.config

# [사이드바]
with st.sidebar:
    st.header("⚙️ SYSTEM SETUP")
    cfg["volume"] = st.number_input("💧 총 물량 (L)", value=float(cfg["volume"]), step=0.1)
    cfg["base_dose"] = st.number_input("💉 기본 도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    
    st.markdown("---")
    st.header("🎯 TARGETS")
    cfg["t_kh"] = st.number_input("KH (dKH)", value=float(cfg["t_kh"]), step=0.01)
    cfg["t_ca"] = st.number_input("Ca (ppm)", value=int(cfg["t_ca"]), step=10)
    cfg["t_mg"] = st.number_input("Mg (ppm)", value=int(cfg["t_mg"]), step=10)
    cfg["t_no3"] = st.number_input("NO3 (ppm)", value=float(cfg["t_no3"]), step=0.1)
    cfg["t_po4"] = st.number_input("PO4 (ppm)", value=float(cfg["t_po4"]), format="%.3f", step=0.01)
    # 숨김 변수 (필요시 꺼내 쓰세요)
    cfg["t_no2"]=0.01; cfg["t_ph"]=8.3; cfg["t_temp"]=26.0; cfg["t_sal"]=35.0
    
    st.info("💡 이 버전은 인터넷 연결 없이 작동합니다. 새로고침하면 기록이 초기화됩니다.")

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
        d_ph = c8.number_input("pH", value=float(cfg["t_ph"]), step=0.1)
        
        c9,c10,c11 = st.columns([1,1,2])
        d_temp = c9.number_input("Temp", value=float(cfg["t_temp"]), step=0.1)
        d_sal = c10.number_input("Salinity", value=float(cfg["t_sal"]), step=0.1)
        d_memo = c11.text_input("Memo")
        
        if st.form_submit_button("SAVE LOG 💾"):
            entry={"날짜":d_date,"KH":d_kh,"Ca":d_ca,"Mg":d_mg,"NO2":d_no2,"NO3":d_no3,"PO4":d_po4,"pH":d_ph,"Temp":d_temp,"Salinity":d_sal,"도징량":cfg["base_dose"],"Memo":d_memo}
            save_data(entry)
            st.toast("Saved!"); st.rerun()

st.markdown("---")
df = st.session_state.df

if not df.empty:
    last = df.iloc[-1]
    
    # [그래프]
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
            vol_factor = cfg["volume"] / 100.0
            
            if abs(kh_diff) <= 0.15: 
                st.success(f"✨ **Perfect!** KH 유지하세요.")
            elif kh_diff < 0: 
                rec = cfg["base_dose"] + 0.3 * vol_factor
                st.error(f"📉 **KH Low!**\n추천 도징: **{rec:.1f}ml**")
            else: 
                rec = max(0, cfg["base_dose"] - 0.3 * vol_factor)
                st.warning(f"📈 **KH High!**\n추천 도징: **{rec:.1f}ml**")
            
            st.markdown("---")
            st.markdown("#### 📅 Schedule")
            # 스케줄은 세션에 저장
            new_sch = st.text_area("Schedule", value=cfg["schedule"], height=100, label_visibility="collapsed")
            if new_sch != cfg["schedule"]:
                cfg["schedule"] = new_sch # 자동 저장 효과

    st.markdown("---")
    
    # [기록 리스트]
    st.markdown("### 📋 History Log")
    
    # 최신순 정렬해서 보여주기
    df_show = df.sort_values(by=df.index.name or '날짜', ascending=False, ignore_index=True)
    
    for index, row in df_show.iterrows():
        # 원본 데이터프레임의 인덱스를 추적하기 위해 역순 계산 필요하지만
        # 간단하게 여기선 보이는 순서대로 처리
        
        with st.container():
            c_date, c_main, c_env, c_del = st.columns([1.5, 4, 3, 1])
            
            with c_date:
                st.markdown(f"**📅 {row['날짜']}**")
            
            with c_main:
                st.caption("Data")
                st.write(f"🧪 KH:{row['KH']} Ca:{row['Ca']} Mg:{row['Mg']} 💧:{row['도징량']}ml")
            
            with c_env:
                st.caption("Memo/Env")
                memo_txt = f"📝 {row['Memo']}" if row['Memo'] and str(row['Memo']).strip() else ""
                st.write(f"{memo_txt} (NO3:{row['NO3']} PO4:{row['PO4']})")
                
            with c_del:
                st.write("") 
                # 삭제는 실제 데이터프레임(df)의 마지막부터 매칭 (가장 최신이 맨 뒤에 추가되므로)
                # 역순 출력이므로 index 0 은 실제 df의 마지막 요소
                real_idx = len(df) - 1 - index
                if st.button("🗑️ Del", key=f"del_{index}", type="secondary", use_container_width=True):
                    delete_row(real_idx)
                    st.rerun()

else:
    st.info("👋 기록을 입력하면 분석이 시작됩니다.")
