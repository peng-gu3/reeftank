import streamlit as st
import pandas as pd
import os
import json
from datetime import date
import plotly.graph_objects as go

# --- 1. 기본 설정 및 파일 처리 ---
st.set_page_config(page_title="My Triton Lab Pro", page_icon="🐠", layout="wide")
DATA_FILE = "my_reef_log.csv"
CONFIG_FILE = "reef_config.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["날짜", "KH", "Ca", "Mg", "NO2", "NO3", "PO4", "pH", "Temp", "Salinity", "도징량", "Memo"])
        df.to_csv(DATA_FILE, index=False)
        return df
    df = pd.read_csv(DATA_FILE)
    required_cols = {"pH": 8.1, "Memo": "", "NO2": 0.0}
    for col, default_val in required_cols.items():
        if col not in df.columns:
            df[col] = default_val
    return df

def save_dataframe(df):
    df.to_csv(DATA_FILE, index=False)

# 설정값 불러오기 (물량, 도징량도 소수점 지원하도록 float 처리)
def load_settings():
    default_settings = {
        "volume": 150.0,       # 소수점 지원을 위해 .0 추가
        "base_dose": 3.00,     # 소수점 둘째자리 지원
        "t_kh": 8.30, "t_ca": 420, "t_mg": 1420,
        "t_no2": 0.010, "t_no3": 5.00, "t_po4": 0.040, "t_ph": 8.30
    }
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_settings, f)
        return default_settings
    
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_settings(settings):
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f)

def draw_radar_chart(categories, values, target_values, title, color_fill):
    normalized_values = []
    real_value_text = []

    for v, t in zip(values, target_values):
        if isinstance(v, float): real_value_text.append(f"{v:.2f}")
        else: real_value_text.append(f"{v}")

        if t <= 0.01: 
            if v <= t: normalized_values.append(v / t if t > 0 else 0)
            else: normalized_values.append(1 + (v - t) * 50)
        else: 
            normalized_values.append(v / t)
    
    categories = [*categories, categories[0]]
    normalized_values = [*normalized_values, normalized_values[0]]
    real_value_text = [*real_value_text, ""]

    TEXT_COLOR = "#00BFFF" 
    GRID_COLOR = "#444444"
    TARGET_LINE_COLOR = "white" 

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[1] * len(categories), theta=categories, fill=None, name='목표(Target)', line_color=TARGET_LINE_COLOR, line_dash='dot', hoverinfo='skip'))
    fig.add_trace(go.Scatterpolar(
        r=normalized_values, theta=categories, fill='toself', name='내 수조', line_color=color_fill, opacity=0.7,
        mode='lines+markers+text', text=real_value_text, textposition="top center", 
        textfont=dict(color=color_fill, size=13, weight="bold")
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 1.5]),
            angularaxis=dict(tickfont=dict(color=TEXT_COLOR, size=14, weight="bold"), linecolor=GRID_COLOR, gridcolor=GRID_COLOR),
            bgcolor="rgba(0,0,0,0)"
        ),
        title=dict(text=title, font=dict(color=TEXT_COLOR, size=20)),
        font=dict(color=TEXT_COLOR),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=380, margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(font=dict(color="white"), orientation="h", y=-0.1)
    )
    return fig

# --- 2. 사이드바: 설정 관리 ---
config = load_settings()

with st.sidebar:
    st.header("⚙️ 수조 & 목표 설정")
    st.info("수치를 수정하고 맨 아래 **[저장]** 버튼을 누르세요.")
    
    # [수정] 물량과 도징량도 소수점 입력 가능하게 변경 (step, format 적용)
    volume = st.number_input("총 물량 (L)", value=float(config["volume"]), step=0.1, format="%.1f")
    current_base_dose = st.number_input("현재 기본 도징량 (ml)", value=float(config["base_dose"]), step=0.01, format="%.2f")
    
    st.divider()
    st.subheader("🎯 목표치 (Target)")
    t_kh = st.number_input("목표 KH", value=config["t_kh"], step=0.01, format="%.2f")
    t_ca = st.number_input("목표 Ca", value=config["t_ca"], step=10)
    t_mg = st.number_input("목표 Mg", value=config["t_mg"], step=10)
    t_no2 = st.number_input("목표 NO2 (최대)", value=config["t_no2"], step=0.001, format="%.3f")
    t_no3 = st.number_input("목표 NO3", value=config["t_no3"], step=0.10, format="%.2f")
    t_po4 = st.number_input("목표 PO4", value=config["t_po4"], step=0.001, format="%.3f")
    t_ph = st.number_input("목표 pH", value=config["t_ph"], step=0.01, format="%.2f")

    # 버튼 하나로 모든 설정(물량, 도징량, 목표치) 저장
    if st.button("💾 설정값 영구 저장하기"):
        new_settings = {
            "volume": volume, "base_dose": current_base_dose,
            "t_kh": t_kh, "t_ca": t_ca, "t_mg": t_mg,
            "t_no2": t_no2, "t_no3": t_no3, "t_po4": t_po4, "t_ph": t_ph
        }
        save_settings(new_settings)
        st.success("모든 설정이 저장되었습니다! (새로고침 중...)")
        st.rerun()

# --- 3. 메인 화면 ---
st.title("🌊 My Triton Reef Manager")

with st.expander("📝 **오늘의 수질 & 스케줄 입력하기**", expanded=True):
    with st.form("entry_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            in_date = st.date_input("날짜", date.today())
            in_kh = st.number_input("KH (경도)", value=t_kh, step=0.01, format="%.2f")
        with c2:
            in_ca = st.number_input("Ca (칼슘)", value=t_ca, step=10)
            in_mg = st.number_input("Mg (마그네슘)", value=t_mg, step=10)
        with c3:
            in_no2 = st.number_input("NO2 (아질산)", value=0.000, step=0.001, format="%.3f")
            in_no3 = st.number_input("NO3 (질산염)", value=t_no3, step=0.01, format="%.2f")
            in_po4 = st.number_input("PO4 (인산염)", value=t_po4, step=0.001, format="%.3f")
        with c4:
            in_ph = st.number_input("pH (산성도)", value=t_ph, step=0.01, format="%.2f")
            in_sal = st.number_input("염도 (ppt)", value=35.0, step=0.1, format="%.1f")
            in_temp = st.number_input("온도 (°C)", value=25.0, step=0.1, format="%.1f")
        
        in_memo = st.text_area("📅 스케줄 / 메모", placeholder="예: 리프 로이즈 급여, 환수, 스키머 청소")
        submit_btn = st.form_submit_button("입력 완료 및 분석 시작 🚀")

if submit_btn:
    new_data = {"날짜": in_date, "KH": in_kh, "Ca": in_ca, "Mg": in_mg, "NO2": in_no2, "NO3": in_no3, "PO4": in_po4, "pH": in_ph, "Temp": in_temp, "Salinity": in_sal, "도징량": current_base_dose, "Memo": in_memo}
    df = load_data()
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    save_dataframe(df)
    st.toast("저장 완료!", icon="✅")

st.divider()
df = load_data()
if not df.empty:
    last_row = df.iloc[-1]
    
    col_graph, col_ai = st.columns([1.1, 0.9])
    
    with col_graph:
        st.subheader("📊 수질 밸런스")
        g1, g2 = st.columns(2)
        with g1:
            fig1 = draw_radar_chart(["KH", "Ca", "Mg"], [last_row["KH"], last_row["Ca"], last_row["Mg"]], [t_kh, t_ca, t_mg], "주요 3요소", "#00FFAA")
            st.plotly_chart(fig1, use_container_width=True)
        with g2:
            fig2 = draw_radar_chart(["NO2", "NO3", "PO4", "pH"], [last_row["NO2"], last_row["NO3"], last_row["PO4"] * 100, last_row["pH"]], [t_no2, t_no3, t_po4 * 100, t_ph], "영양염 & pH", "#FF5500")
            st.plotly_chart(fig2, use_container_width=True)
            if last_row["NO2"] > t_no2: st.error(f"🚨 **NO2(아질산) 위험! ({last_row['NO2']})**")

    with col_ai:
        st.subheader("🤖 AI Reef Advisor")
        
        st.markdown("##### 1. 트리톤 도징 처방")
        kh_diff = last_row["KH"] - t_kh
        rec_dose = current_base_dose
        
        # 150L 기준, 보정 로직 (물량에 따라 자동 조절됨)
        # 공식: (차이) * (물량/100) * 보정계수
        volume_factor = volume / 100.0
        
        if abs(kh_diff) <= 0.15:
            st.success(f"✅ **완벽합니다!** (KH {last_row['KH']:.2f})\n\n현재 도징량 **{current_base_dose:.2f}ml**를 유지하세요.")
        elif kh_diff < 0:
            # 단순 0.3ml가 아니라 물량에 비례해서 계산 (더 정확하게)
            # 예: 150L에서 0.5dKH 떨어지면 -> 약 1~2ml 증량 필요 (트리톤 농도 감안)
            # 여기서는 안전하게 0.3 * (물량/100) 정도로 제안
            add_amount = 0.3 * volume_factor
            rec_dose = current_base_dose + add_amount
            st.error(f"📉 **KH 부족 ({last_row['KH']:.2f})**\n\n트리톤 4종 도징량을 **{rec_dose:.2f}ml**로 증량하세요.")
        else:
            sub_amount = 0.3 * volume_factor
            rec_dose = max(0, current_base_dose - sub_amount)
            st.warning(f"📈 **KH 과다 ({last_row['KH']:.2f})**\n\n트리톤 4종 도징량을 **{rec_dose:.2f}ml**로 감량하세요.")

        st.markdown("---")
        st.markdown("##### 2. 종합 상태 분석")
        
        issues_found = False
        if last_row["Mg"] < 1280:
            st.warning("⚠️ **마그네슘(Mg) 부족** - KH 소모가 빨라질 수 있습니다.")
            issues_found = True
        if last_row["NO3"] > 15:
            st.warning(f"⚠️ **질산염(NO3) 높음 ({last_row['NO3']:.1f})** - 환수 또는 사료 감량 필요.")
            issues_found = True
        elif last_row["NO3"] < 1:
            st.info("💡 **질산염 낮음** - 산호 발색을 위해 사료를 약간 늘려보세요.")
            issues_found = True
        if last_row["PO4"] >= 0.1:
            st.error(f"🚨 **인산염(PO4) 위험 ({last_row['PO4']:.3f})** - GFO/란타늄 고려.")
            issues_found = True
        if last_row["pH"] < 7.9:
            st.warning("⚠️ **pH 낮음** - 환기/스키머 외부 공기 연결 추천.")
            issues_found = True
            
        if not issues_found:
            st.info("🎉 **모든 수치가 안정적입니다!**")

st.divider()
st.subheader("📋 전체 기록 관리")
if not df.empty:
    edited_df = st.data_editor(df.sort_values("날짜", ascending=False), num_rows="dynamic", use_container_width=True)
    if not edited_df.equals(df.sort_values("날짜", ascending=False)) and st.button("변경 사항 저장"):
        save_dataframe(edited_df)
        st.success("업데이트 완료! 새로고침하세요.")
        st.rerun()