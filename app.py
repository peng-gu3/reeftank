import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import os
import json

# 페이지 기본 설정
st.set_page_config(page_title="내 손안의 바다 - 리프 매니저 Pro", page_icon="🐠", layout="wide")

# 파일 경로 설정
DATA_FILE = "reef_log.csv"
CONFIG_FILE = "config.json"

# --- 1. 데이터 및 설정 관리 함수 ---

# 기본 설정값 (사용자가 요청한 범위의 중간값 또는 일반적 수치로 초기화)
DEFAULT_CONFIG = {
    "volume": 150.0,
    "target_kh": 8.3,
    "target_ca": 420,
    "target_mg": 1420,
    "target_no2": 0.01,
    "target_no3": 5.0,
    "target_po4": 0.04,
    "target_ph": 8.2,
    "target_temp": 25.0,
    "target_salinity": 35.0,
    "dosing_product_info": "기본 KH 보충제 (예: 10ml당 100L에서 1dKH 상승)"
}

def load_config():
    """설정 파일(JSON) 로드, 없으면 기본값 생성"""
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config_data):
    """설정 파일 저장"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)

def load_data():
    """CSV 데이터 로드"""
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["날짜", "KH", "Ca", "Mg", "NO2", "NO3", "PO4", "pH", "온도", "염도", "도징량", "메모"])
    df = pd.read_csv(DATA_FILE)
    df['날짜'] = pd.to_datetime(df['날짜']).dt.date
    return df

def save_data(df):
    """CSV 데이터 저장"""
    df.to_csv(DATA_FILE, index=False)

# 설정 로드
config = load_config()

# --- 2. 사이드바: 목표 설정 및 수조 정보 ---
with st.sidebar:
    st.header("⚙️ 수조 설정 및 목표치 관리")
    st.info("목표치를 수정하고 '설정 저장' 버튼을 눌러야 적용됩니다.")

    with st.form("config_form"):
        st.subheader("수조 기본 정보")
        vol = st.number_input("총 물량 (L)", value=float(config["volume"]), step=1.0)
        prod_info = st.text_area("사용 중인 도징 제품 정보 (메모용)", value=config["dosing_product_info"])

        st.subheader("🎯 목표 수치 (Target)")
        col1, col2 = st.columns(2)
        with col1:
            t_kh = st.number_input("목표 KH (dKH)", value=float(config["target_kh"]), step=0.01, format="%.2f", help="추천: 8.0 ~ 8.5")
            t_ca = st.number_input("목표 Ca (ppm)", value=int(config["target_ca"]), step=10, help="추천: 400 ~ 440")
            t_mg = st.number_input("목표 Mg (ppm)", value=int(config["target_mg"]), step=10, help="추천: 1400 ~ 1440")
            t_ph = st.number_input("목표 pH", value=float(config["target_ph"]), step=0.1, format="%.2f", help="추천: 8.1 ~ 8.3")
        with col2:
            t_no2 = st.number_input("목표 NO2 (ppm)", value=float(config["target_no2"]), step=0.01, format="%.2f", help="추천: 0 ~ 0.01")
            t_no3 = st.number_input("목표 NO3 (ppm)", value=float(config["target_no3"]), step=0.1, format="%.1f", help="추천: 5 ~ 10")
            t_po4 = st.number_input("목표 PO4 (ppm)", value=float(config["target_po4"]), step=0.01, format="%.2f", help="추천: 0.03 ~ 0.05")
            t_temp = st.number_input("목표 온도 (°C)", value=float(config["target_temp"]), step=0.5, format="%.1f", help="추천: 25")
            t_sal = st.number_input("목표 염도 (ppt)", value=float(config["target_salinity"]), step=0.1, format="%.1f", help="추천: 35")

        if st.form_submit_button("💾 설정 저장 (고정하기)"):
            new_config = {
                "volume": vol, "target_kh": t_kh, "target_ca": t_ca, "target_mg": t_mg,
                "target_no2": t_no2, "target_no3": t_no3, "target_po4": t_po4, "target_ph": t_ph,
                "target_temp": t_temp, "target_salinity": t_sal, "dosing_product_info": prod_info
            }
            save_config(new_config)
            st.success("목표치가 업데이트 및 고정되었습니다!")
            st.rerun() # 설정 변경 후 앱 리로드

# --- 3. 메인 페이지: 데이터 입력 ---
st.title("🐠 리프 매니저 Pro - 기록 & 분석")

st.subheader("📝 오늘의 수질 기록 입력")
with st.form("entry_form", clear_on_submit=True):
    col_in1, col_in2, col_in3, col_in4 = st.columns(4)
    with col_in1:
        date_in = st.date_input("날짜", date.today())
        kh_in = st.number_input("KH (dKH)", step=0.01, format="%.2f")
        ph_in = st.number_input("pH", step=0.01, format="%.2f")
    with col_in2:
        ca_in = st.number_input("Ca (ppm)", step=10)
        mg_in = st.number_input("Mg (ppm)", step=10)
        dose_in = st.number_input("오늘 도징량 (ml)", step=0.1, format="%.1f")
    with col_in3:
        no3_in = st.number_input("NO3 (ppm)", step=0.1, format="%.1f")
        po4_in = st.number_input("PO4 (ppm)", step=0.01, format="%.2f")
        no2_in = st.number_input("NO2 (ppm)", step=0.001, format="%.3f")
    with col_in4:
        temp_in = st.number_input("온도 (°C)", step=0.1, format="%.1f")
        sal_in = st.number_input("염도 (ppt)", step=0.1, format="%.1f")

    memo_in = st.text_area("메모 (특이사항, 산호 상태 등)")

    submitted = st.form_submit_button("기록 저장 💾")
    if submitted:
        new_data = pd.DataFrame({
            "날짜": [date_in], "KH": [kh_in], "Ca": [ca_in], "Mg": [mg_in],
            "NO2": [no2_in], "NO3": [no3_in], "PO4": [po4_in], "pH": [ph_in],
            "온도": [temp_in], "염도": [sal_in], "도징량": [dose_in], "메모": [memo_in]
        })
        df = load_data()
        df = pd.concat([df, new_data], ignore_index=True)
        save_data(df)
        st.success("저장 완료!")
        st.rerun()

st.divider()

# --- 4. 대시보드: 그래프 및 AI 분석 ---
df = load_data()

if not df.empty:
    st.subheader("📊 수질 현황 대시보드")
    latest = df.iloc[-1] # 가장 최근 데이터

    # --- 원형 그래프 (레이더 차트) 그리기 함수 ---
    def plot_radar(categories, current_vals, target_vals, title, range_max_list):
        fig = go.Figure()
        # 목표치 (파란색 점선)
        fig.add_trace(go.Scatterpolar(
            r=target_vals, theta=categories, fill='toself', name='목표치',
            line=dict(color='blue', dash='dot')
        ))
        # 현재치 (붉은색 실선)
        fig.add_trace(go.Scatterpolar(
            r=current_vals, theta=categories, fill='toself', name='현재 측정값',
            line=dict(color='red')
        ))
        
        # 각 축의 최대값 설정 (그래프 왜곡 방지)
        radial_axis_settings = []
        for i, cat in enumerate(categories):
             # 목표치나 현재치가 설정된 최대범위보다 크면 범위를 늘려줌
            max_val = max(range_max_list[i], target_vals[i] * 1.2, current_vals[i] * 1.2) if range_max_list[i] > 0 else 1
            radial_axis_settings.append(dict(range=[0, max_val]))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            title=title, height=400, showlegend=True
        )
        return fig

    col_graph1, col_graph2 = st.columns(2)

    # 1. 주요 3요소 그래프 (KH, Ca, Mg)
    with col_graph1:
        cats1 = ['KH', 'Ca', 'Mg']
        # 값이 0이거나 입력 안된 경우 처리
        curr1 = [latest['KH'] if latest['KH'] > 0 else 0, latest['Ca'], latest['Mg']]
        targ1 = [config['target_kh'], config['target_ca'], config['target_mg']]
        # 각 축의 적절한 최대 범위 설정 (시각적으로 보기 좋게)
        ranges1 = [12, 500, 1600] 
        st.plotly_chart(plot_radar(cats1, curr1, targ1, "주요 3요소 밸런스 (KH, Ca, Mg)", ranges1), use_container_width=True)

    # 2. 영양염 및 환경 그래프 (NO3, PO4, pH, Temp, Salinity)
    with col_graph2:
        cats2 = ['NO3', 'PO4', 'pH', '온도', '염도']
        curr2 = [latest['NO3'], latest['PO4'], latest['pH'], latest['온도'], latest['염도']]
        targ2 = [config['target_no3'], config['target_po4'], config['target_ph'], config['target_temp'], config['target_salinity']]
        # 각 축의 적절한 최대 범위 설정
        ranges2 = [20, 0.2, 9.0, 30, 40]
        st.plotly_chart(plot_radar(cats2, curr2, targ2, "영양염 및 환경 밸런스", ranges2), use_container_width=True)


    # --- AI 분석 및 도징 추천 ---
    st.subheader("🤖 AI 수질 분석 및 도징 제안")
    analysis_col1, analysis_col2 = st.columns([2, 1])

    with analysis_col1:
        st.markdown(f"**최근 측정일: {latest['날짜']}** (물량 설정: {config['volume']}L)")
        
        # KH 분석
        kh_diff = latest['KH'] - config['target_kh']
        if latest['KH'] <= 0.1:
             st.warning("⚠️ KH 정보가 없습니다. 측정이 필요합니다.")
        elif abs(kh_diff) < 0.3:
            st.success(f"✅ **KH ({latest['KH']:.2f})**: 목표치({config['target_kh']:.2f})에 근접합니다. 현재 상태를 유지하세요.")
        elif kh_diff < 0:
            # 도징량 계산 로직 (예시: 100L당 1dKH 올리는데 10ml 필요한 제품 기준 -> 계수 10)
            # 실제 제품에 따라 이 계수(calculation_factor)를 조정해야 합니다.
            calculation_factor = 10 
            needed_dose = abs(kh_diff) * (config['volume'] / 100) * calculation_factor
            st.error(f"🔻 **KH 부족 ({latest['KH']:.2f})**: 목표보다 {abs(kh_diff):.2f} 낮습니다.")
            st.info(f"💡 **도징 제안**: 약 **{needed_dose:.1f}ml**의 KH 보충제 투입이 필요할 수 있습니다.\n\n(※ 주의: 100L당 1dKH 상승에 10ml가 필요한 일반적인 제품 기준 추정치입니다. 사용하시는 제품의 농도에 맞춰 실제 투입량을 결정하세요. 한 번에 너무 많이 올리지 마세요.)")
        else:
             st.warning(f"🔺 **KH 높음 ({latest['KH']:.2f})**: 목표보다 {kh_diff:.2f} 높습니다. 도징을 중단하고 자연 소모를 기다리세요.")

        # 간단한 영양염 코멘트
        if latest['PO4'] > config['target_po4'] * 2:
             st.warning(f"⚠️ **인산염(PO4) 높음 ({latest['PO4']:.2f})**: 목표치의 2배 이상입니다. 먹이량을 줄이거나 흡착제 사용을 고려하세요.")
        if latest['NO3'] > config['target_no3'] * 2:
             st.warning(f"⚠️ **질산염(NO3) 높음 ({latest['NO3']:.1f})**: 환수나 박테리아 도징 스케줄을 점검하세요.")

    with analysis_col2:
        st.markdown("**ℹ️ 참고 정보**")
        st.write(f"설정된 도징 제품 정보:\nIs{config['dosing_product_info']}")
        st.caption("제안된 도징량은 단순 계산 값이며, 실제 수조 상황에 따라 다를 수 있습니다. 조금씩 넣으며 변화를 관찰하세요.")

else:
    st.info("데이터가 없습니다. 첫 번째 기록을 입력해주세요.")

st.divider()

# --- 5. 기록 관리 및 스케줄 ---
col_hist, col_sched = st.columns([2, 1])

with col_hist:
    st.subheader("📋 기록 목록 (최신순)")
    if not df.empty:
        # 최신순 정렬
        df_reversed = df.sort_values(by="날짜", ascending=False).reset_index(drop=True)

        for index, row in df_reversed.iterrows():
            # 메모 유무 표시
            memo_preview = "📝메모 있음" if row['메모'] and str(row['메모']).strip() != "" else ""
            
            # 확장 가능한 형태로 기록 표시
            with st.expander(f"[{row['날짜']}] KH: {row['KH']:.2f} | Ca: {row['Ca']:.0f} | Mg: {row['Mg']:.0f} {memo_preview}"):
                col_detail1, col_detail2, col_btn = st.columns([3, 3, 1])
                with col_detail1:
                    st.write(f"**주요 수치:** KH {row['KH']:.2f}, Ca {row['Ca']:.0f}, Mg {row['Mg']:.0f}, pH {row['pH']:.2f}")
                    st.write(f"**환경:** 온도 {row['온도']:.1f}°C, 염도 {row['염도']:.1f}ppt")
                with col_detail2:
                    st.write(f"**영양염:** NO3 {row['NO3']:.1f}, PO4 {row['PO4']:.2f}, NO2 {row['NO2']:.3f}")
                    st.write(f"**도징:** {row['도징량']:.1f}ml")
                
                # 전체 메모 내용 표시
                if row['메모'] and str(row['메모']).strip() != "":
                    st.info(f"**메모 내용:**\n{row['메모']}")
                
                # 삭제 버튼 (고유한 키 생성을 위해 인덱스와 날짜 조합)
                with col_btn:
                    st.write("") # 줄바꿈용
                    if st.button("🗑️ 삭제", key=f"del_{index}_{row['날짜']}"):
                        # 원본 데이터프레임에서 해당 날짜의 데이터 삭제 (중복 날짜가 있을 경우 가장 최근 것 하나만 삭제됨)
                        # 더 정확한 삭제를 위해서는 고유 ID가 필요하지만, 여기서는 날짜 기준으로 처리
                        original_idx = df[df['날짜'] == row['날짜']].index[-1]
                        df = df.drop(original_idx)
                        save_data(df)
                        st.rerun()
    else:
        st.write("저장된 기록이 없습니다.")

with col_sched:
    st.subheader("📅 산호 먹이 및 관리 스케줄")
    # 간단한 텍스트 영역으로 구현 (더 복잡한 기능은 DB 필요)
    schedule_note = st.text_area("주간/월간 계획을 메모하세요 (자동 저장 안됨, 필요시 별도 기록 권장)", height=300, 
                                 placeholder="- 월요일: 산호 먹이 (피딩)\n- 수요일: 유리벽 청소\n- 토요일: 환수 10%")
    st.caption("이 영역은 임시 메모장입니다. 중요한 스케줄은 별도 관리하세요.")
