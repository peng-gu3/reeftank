import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px

# --- 설정 및 데이터 관리 ---
FILE_PATH = 'stock_data.json'
st.set_page_config(page_title="주식 매매일지 Pro", layout="wide", page_icon="📈")

def load_data():
    if not os.path.exists(FILE_PATH):
        return []
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return []

def save_data(data):
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 데이터 불러오기
transactions = load_data()

# --- 사이드바: 거래 입력 ---
st.sidebar.header("📝 거래 입력")

# 입력 폼
with st.sidebar.form("transaction_form", clear_on_submit=True):
    date = st.date_input("날짜", datetime.now())
    type_option = st.selectbox("구분", ["매수 (Buy)", "매도 (Sell)", "기타 (예수금/입출금)"])
    
    # 매도일 경우 보유 종목 불러오기
    holdings = [t for t in transactions if t['type'] == 'buy' and t.get('remaining_qty', 0) > 0]
    holding_options = {f"{t['name']} (잔여: {t.get('remaining_qty')}주, 단가: {t['price']:,}원) - {t['date']}": t['id'] for t in holdings}
    
    selected_holding_id = None
    name = ""
    
    if type_option == "매도 (Sell)":
        if not holdings:
            st.error("매도 가능한 보유 종목이 없습니다.")
            sell_ready = False
        else:
            selected_option = st.selectbox("매도할 보유 종목 선택", list(holding_options.keys()))
            selected_holding_id = holding_options[selected_option]
            sell_ready = True
    elif type_option == "매수 (Buy)":
        name = st.text_input("종목명")
    else:
        name = st.text_input("내용 (예: 월급)")

    price = st.number_input("단가 / 금액", min_value=-1000000000, value=0, step=100)
    qty = st.number_input("수량", min_value=1, value=1)
    
    submitted = st.form_submit_button("기록 저장")

    if submitted:
        new_id = int(datetime.now().timestamp() * 1000)
        date_str = date.strftime("%Y-%m-%d")
        
        if type_option == "매수 (Buy)":
            if name and price > 0:
                new_record = {
                    "id": new_id, "date": date_str, "type": "buy",
                    "name": name, "price": price, "qty": qty, "remaining_qty": qty
                }
                transactions.append(new_record)
                save_data(transactions)
                st.success("매수 기록 저장 완료!")
                st.rerun()

        elif type_option == "매도 (Sell)" and sell_ready:
            # 매도 로직 (HTML 버전과 동일하게 연결된 매수 기록 차감)
            target_buy = next((t for t in transactions if t['id'] == selected_holding_id), None)
            if target_buy:
                if qty > target_buy['remaining_qty']:
                    st.error(f"보유 수량 초과! (잔여: {target_buy['remaining_qty']}주)")
                else:
                    profit = (price - target_buy['price']) * qty
                    target_buy['remaining_qty'] -= qty # 잔여 수량 차감
                    
                    new_record = {
                        "id": new_id, "date": date_str, "type": "sell",
                        "name": target_buy['name'], "price": price, "qty": qty,
                        "linked_buy_id": target_buy['id'], "profit": profit
                    }
                    transactions.append(new_record)
                    save_data(transactions)
                    st.success("매도 기록 저장 완료!")
                    st.rerun()

        elif type_option == "기타 (예수금/입출금)":
            if name and price != 0:
                new_record = {
                    "id": new_id, "date": date_str, "type": "other",
                    "name": name, "price": price, "qty": 1
                }
                transactions.append(new_record)
                save_data(transactions)
                st.success("기록 저장 완료!")
                st.rerun()

# --- 메인 대시보드 ---
st.title("💰 주식 매매일지 Dashboard")

# 1. 통계 계산
total_profit = 0
month_profit = 0
sell_count = 0
sell_profit_sum = 0
current_month = datetime.now().strftime("%Y-%m")
asset_flow = [] # 차트용 데이터

# 날짜순 정렬
sorted_transactions = sorted(transactions, key=lambda x: x['date'])

temp_asset = 0
for t in sorted_transactions:
    val = 0
    if t['type'] == 'sell':
        p = t.get('profit', 0)
        total_profit += p
        sell_profit_sum += p
        sell_count += 1
        if t['date'].startswith(current_month):
            month_profit += p
        val = p
    elif t['type'] == 'other':
        total_profit += t['price']
        if t['date'].startswith(current_month):
            month_profit += t['price']
        val = t['price']
    
    if val != 0:
        temp_asset += val
        asset_flow.append({"date": t['date'], "asset": temp_asset})

# 평균 손익 계산
avg_profit = int(sell_profit_sum / sell_count) if sell_count > 0 else 0

# 2. 상단 요약 카드 (Metrics)
col1, col2, col3, col4 = st.columns(4)
col1.metric("총 누적 자산(손익)", f"{total_profit:,}원", delta_color="normal")
col2.metric("이번 달 수익", f"{month_profit:,}원", delta=f"{month_profit:,}원")
col3.metric("1회 평균 손익 (매매)", f"{avg_profit:,}원")
col4.metric("총 매도 횟수", f"{sell_count}회")

# 3. 자산 추이 차트
st.subheader("📈 자산 추이 그래프")
if asset_flow:
    df_chart = pd.DataFrame(asset_flow)
    # 같은 날짜가 여러개면 마지막 값만 사용 (누적 개념이므로)
    df_chart = df_chart.groupby('date').last().reset_index()
    
    fig = px.line(df_chart, x='date', y='asset', markers=True, 
                  labels={'date': '날짜', 'asset': '누적 자산(원)'})
    fig.update_layout(xaxis_title=None, yaxis_title=None)
    fig.update_traces(line_color='#2563eb', line_width=3)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("데이터가 쌓이면 그래프가 표시됩니다.")

# 4. 탭 구성 (보유 종목 / 거래 내역)
tab1, tab2, tab3 = st.tabs(["📦 보유 종목", "📅 전체 거래 내역", "💾 데이터 관리"])

with tab1:
    holdings_list = []
    for t in transactions:
        if t['type'] == 'buy' and t.get('remaining_qty', 0) > 0:
            days = (datetime.now() - datetime.strptime(t['date'], "%Y-%m-%d")).days
            holdings_list.append({
                "종목명": t['name'],
                "매수일": t['date'],
                "보유기간": f"{days}일째",
                "매수단가": f"{t['price']:,}원",
                "잔여수량": f"{t['remaining_qty']}주",
                "총평가액": f"{t['price'] * t['remaining_qty']:,}원"
            })
    
    if holdings_list:
        st.dataframe(pd.DataFrame(holdings_list), use_container_width=True)
    else:
        st.info("현재 보유 중인 종목이 없습니다.")

with tab2:
    # 데이터프레임 변환을 위해 보기 좋게 가공
    display_list = []
    for t in sorted_transactions:
        row = {
            "날짜": t['date'],
            "구분": "매수" if t['type'] == 'buy' else ("매도" if t['type'] == 'sell' else "기타"),
            "종목/내용": t['name'],
            "금액/단가": f"{t['price']:,}원",
            "수량": t['qty']
        }
        
        if t['type'] == 'sell':
            profit = t.get('profit', 0)
            emoji = "😄" if profit > 0 else "😭"
            row['수익금'] = f"{emoji} {profit:,}원"
        elif t['type'] == 'buy':
            row['수익금'] = "🔥 (보유/매수)"
        else:
            row['수익금'] = "-"
            
        display_list.append(row)

    if display_list:
        # 최신순 정렬
        st.dataframe(pd.DataFrame(display_list)[::-1], use_container_width=True)
    else:
        st.info("거래 내역이 없습니다.")

with tab3:
    st.write("### 데이터 백업 및 삭제")
    
    # JSON 다운로드
    json_string = json.dumps(transactions, ensure_ascii=False, indent=4)
    st.download_button(
        label="💾 데이터 백업 다운로드 (.json)",
        data=json_string,
        file_name="stock_data_backup.json",
        mime="application/json"
    )
    
    st.write("---")
    if st.button("⚠️ 모든 데이터 초기화 (주의)"):
        if os.path.exists(FILE_PATH):
            os.remove(FILE_PATH)
            st.success("데이터가 초기화되었습니다. 새로고침하세요.")
            st.rerun()
