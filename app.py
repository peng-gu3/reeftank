import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime
import plotly.express as px

# --- 페이지 설정 ---
st.set_page_config(page_title="주식 매매일지", layout="wide", page_icon="📈")

# --- 데이터 관리 함수 ---
# Streamlit Cloud는 껐다 켜면 파일이 초기화되므로, 
# '파일 업로드/다운로드' 방식으로 데이터를 관리해야 안전합니다.

if 'transactions' not in st.session_state:
    st.session_state.transactions = []

def load_data(uploaded_file):
    try:
        data = json.load(uploaded_file)
        st.session_state.transactions = data
        st.success("데이터 복구 완료!")
    except:
        st.error("잘못된 파일입니다.")

# --- 사이드바: 입력 및 관리 ---
with st.sidebar:
    st.header("📝 거래 입력")
    
    with st.form("input_form", clear_on_submit=True):
        date = st.date_input("날짜", datetime.now())
        type_option = st.selectbox("구분", ["매수 (Buy)", "매도 (Sell)", "기타 (예수금)"])
        
        # 매도 시 보유 종목 선택 기능
        holdings = [t for t in st.session_state.transactions if t['type'] == 'buy' and t.get('remaining_qty', 0) > 0]
        holding_map = {f"{t['name']} (잔여: {t.get('remaining_qty')}주)": t['id'] for t in holdings}
        
        selected_holding_id = None
        name = ""
        
        if type_option == "매도 (Sell)":
            if holdings:
                sel = st.selectbox("보유 종목 선택", list(holding_map.keys()))
                selected_holding_id = holding_map[sel]
            else:
                st.warning("매도할 종목이 없습니다.")
        elif type_option == "매수 (Buy)":
            name = st.text_input("종목명")
        else:
            name = st.text_input("내용 (예: 월급)")
            
        price = st.number_input("단가/금액", value=0, step=100)
        qty = st.number_input("수량", min_value=1, value=1)
        
        submitted = st.form_submit_button("기록 저장")
        
        if submitted:
            new_id = int(time.time() * 1000)
            date_str = date.strftime("%Y-%m-%d")
            
            if type_option == "매수 (Buy)" and name:
                st.session_state.transactions.append({
                    "id": new_id, "date": date_str, "type": "buy",
                    "name": name, "price": price, "qty": qty, "remaining_qty": qty
                })
                st.success("매수 저장됨")
                
            elif type_option == "매도 (Sell)" and selected_holding_id:
                target = next((t for t in st.session_state.transactions if t['id'] == selected_holding_id), None)
                if target and qty <= target['remaining_qty']:
                    target['remaining_qty'] -= qty
                    profit = (price - target['price']) * qty
                    st.session_state.transactions.append({
                        "id": new_id, "date": date_str, "type": "sell",
                        "name": target['name'], "price": price, "qty": qty,
                        "linked_buy_id": target['id'], "profit": profit
                    })
                    st.success("매도 저장됨")
                else:
                    st.error("수량 오류")
                    
            elif type_option == "기타 (예수금)":
                st.session_state.transactions.append({
                    "id": new_id, "date": date_str, "type": "other",
                    "name": name, "price": price, "qty": 1
                })
                st.success("저장됨")

    st.markdown("---")
    st.subheader("💾 데이터 관리")
    
    # 데이터 다운로드 (백업)
    json_str = json.dumps(st.session_state.transactions, ensure_ascii=False, indent=4)
    st.download_button("💾 백업 파일 다운로드", json_str, file_name="stock_backup.json", mime="application/json")
    
    # 데이터 업로드 (복구)
    uploaded_file = st.file_uploader("📂 백업 파일 불러오기", type="json")
    if uploaded_file is not None:
        load_data(uploaded_file)

# --- 메인 대시보드 ---
st.title("💰 주식 매매일지 Dashboard")

# 데이터 처리 및 통계 계산
df = pd.DataFrame(st.session_state.transactions)
total_profit = 0
month_profit = 0
avg_profit = 0
sell_count = 0
current_month = datetime.now().strftime("%Y-%m")
asset_history = []
temp_asset = 0

if not df.empty:
    # 날짜 정렬
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    for index, row in df.iterrows():
        val = 0
        if row['type'] == 'sell':
            p = row.get('profit', 0)
            total_profit += p
            sell_count += 1
            if row['date'].strftime("%Y-%m") == current_month:
                month_profit += p
            val = p
        elif row['type'] == 'other':
            val = row['price']
            total_profit += val
            if row['date'].strftime("%Y-%m") == current_month:
                month_profit += val
        
        if val != 0:
            temp_asset += val
            asset_history.append({"date": row['date'], "asset": temp_asset})
    
    if sell_count > 0:
        # 순수 매매 손익 합계 계산 (기타 제외)
        pure_profit = sum([t.get('profit', 0) for t in st.session_state.transactions if t['type']=='sell'])
        avg_profit = int(pure_profit / sell_count)

# 1. 요약 카드
col1, col2, col3, col4 = st.columns(4)
col1.metric("총 누적 자산", f"{total_profit:,}원")
col2.metric("이번 달 수익", f"{month_profit:,}원")
col3.metric("1회 평균 손익", f"{avg_profit:,}원")
col4.metric("총 매도 횟수", f"{sell_count}회")

# 2. 자산 추이 그래프
st.subheader("📈 자산 추이")
if asset_history:
    chart_df = pd.DataFrame(asset_history)
    # 날짜별 마지막 자산 기준
    chart_df = chart_df.groupby('date').last().reset_index()
    fig = px.line(chart_df, x='date', y='asset', markers=True)
    fig.update_traces(line_color='#2563eb', line_width=3)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("거래 내역이 쌓이면 그래프가 표시됩니다.")

# 3. 내역 탭
tab1, tab2 = st.tabs(["📅 전체 내역", "📦 보유 종목"])

with tab1:
    if not df.empty:
        # 보기 좋게 가공
        display_df = df.copy()
        display_df['date'] = display_df['date'].dt.strftime("%Y-%m-%d")
        
        def make_desc(row):
            if row['type'] == 'buy': return f"🔴 매수 | {row['name']}"
            elif row['type'] == 'sell': return f"🔵 매도 | {row['name']} (수익: {row.get('profit',0):,}원)"
            else: return f"⚪ 기타 | {row['name']}"
            
        display_df['내용'] = display_df.apply(make_desc, axis=1)
        st.dataframe(display_df[['date', '내용', 'price', 'qty']].sort_values('date', ascending=False), use_container_width=True)
    else:
        st.write("기록이 없습니다.")

with tab2:
    holdings = [t for t in st.session_state.transactions if t['type'] == 'buy' and t.get('remaining_qty', 0) > 0]
    if holdings:
        h_df = pd.DataFrame(holdings)
        h_df['평가액'] = h_df['price'] * h_df['remaining_qty']
        st.dataframe(h_df[['date', 'name', 'price', 'remaining_qty', '평가액']], use_container_width=True)
    else:
        st.write("보유 중인 종목이 없습니다.")
