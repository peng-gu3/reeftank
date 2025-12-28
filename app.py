import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
import datetime

# 페이지 설정
st.set_page_config(page_title="내 주식 비서", page_icon="📈")

st.title("🚀 2026 대박 매매일지 (Web)")

# 1. 데이터 관리 (세션 상태 사용)
if 'df' not in st.session_state:
    # 초기 데이터 구조
    st.session_state.df = pd.DataFrame(columns=['날짜', '종목명', '매수단가', '수량', '비고'])

# 2. 사이드바: 매수 입력
with st.sidebar:
    st.header("📝 매수 기록 입력")
    input_date = st.date_input("날짜")
    input_name = st.text_input("종목명 (예: 삼성전자)")
    input_price = st.number_input("매수 단가", value=0, step=100)
    input_qty = st.number_input("수량", value=1, step=1)
    input_memo = st.text_area("비고")
    
    if st.button("추가하기"):
        if input_name and input_price > 0:
            new_data = pd.DataFrame({
                '날짜': [input_date],
                '종목명': [input_name],
                '매수단가': [input_price],
                '수량': [input_qty],
                '비고': [input_memo]
            })
            st.session_state.df = pd.concat([st.session_state.df, new_data], ignore_index=True)
            st.success(f"{input_name} 추가 완료!")
        else:
            st.error("종목명과 가격을 확인해주세요.")

    st.markdown("---")
    # CSV 저장/불러오기 기능 (서버 재부팅 대비)
    st.subheader("💾 데이터 백업/복구")
    
    # 내보내기
    csv = st.session_state.df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("엑셀(CSV)로 저장", data=csv, file_name="my_stock_log.csv", mime="text/csv")
    
    # 불러오기
    uploaded_file = st.file_uploader("파일 불러오기")
    if uploaded_file is not None:
        st.session_state.df = pd.read_csv(uploaded_file)
        st.success("데이터 복구 완료!")

# 3. 메인 화면: 보유 종목 현황 (편집 가능)
st.subheader("📦 현재 보유 목록 (직접 수정 가능)")
edited_df = st.data_editor(st.session_state.df, num_rows="dynamic")
st.session_state.df = edited_df # 수정된 내용 반영

# 4. 실시간 잔고 평가 버튼
if st.button("📈 실시간 수익률 조회 (Click)", type="primary"):
    if not edited_df.empty:
        with st.spinner('현재가를 불러오는 중입니다...'):
            total_invest = 0
            total_eval = 0
            
            # KRX 전체 종목 코드 로딩 (캐싱)
            @st.cache_data
            def get_stock_list():
                krx = fdr.StockListing('KRX')
                return dict(zip(krx['Name'], krx['Code']))
            
            stock_map = get_stock_list()
            
            # 계산 로직
            result_list = []
            
            # 날짜 설정 (최근 데이터 확보용)
            week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')

            for index, row in edited_df.iterrows():
                name = row['종목명']
                qty = float(row['수량'])
                buy_price = float(row['매수단가'])
                
                cur_price = buy_price # 실패 시 평단가 유지
                code = stock_map.get(name)
                
                if code:
                    try:
                        # 최근 데이터 가져와서 마지막 값(현재가) 사용
                        df_price = fdr.DataReader(code, week_ago)
                        if not df_price.empty:
                            cur_price = int(df_price.iloc[-1]['Close'])
                    except:
                        pass
                
                invest = buy_price * qty
                eval_amt = cur_price * qty
                profit = eval_amt - invest
                rate = ((cur_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0
                
                total_invest += invest
                total_eval += eval_amt
                
                result_list.append({
                    '종목명': name,
                    '현재가': f"{cur_price:,}원",
                    '수익률': f"{rate:.2f}%",
                    '평가손익': profit
                })
            
            # 결과 출력
            total_profit = total_eval - total_invest
            total_rate = (total_profit / total_invest * 100) if total_invest > 0 else 0
            
            # 메트릭 표시
            col1, col2, col3 = st.columns(3)
            col1.metric("총 매수금액", f"{int(total_invest):,}원")
            col2.metric("총 평가금액", f"{int(total_eval):,}원")
            col3.metric("총 평가손익", f"{int(total_profit):,}원", f"{total_rate:.2f}%")
            
            # 상세 표
            st.table(pd.DataFrame(result_list))
            
    else:
        st.warning("데이터가 없습니다. 왼쪽에서 매수 기록을 추가하거나 엑셀을 업로드하세요.")
