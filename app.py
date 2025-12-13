import streamlit as st
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(layout="wide", page_title="주식 매매일지 Pro")

# HTML/JS/CSS 코드
html_code = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 매매일지</title>
    <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css" />
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --primary: #2563eb; 
            --red: #ef4444; --red-bg: #fef2f2; --red-text: #b91c1c;
            --blue: #3b82f6; --blue-bg: #eff6ff; --blue-text: #1d4ed8;
            --green: #22c55e; --green-bg: #f0fdf4; --green-text: #15803d; /* 초록색 변수 추가 */
            --gray: #64748b; --gray-bg: #f8fafc; --gray-text: #334155;
            --bg: #ffffff; --surface: #ffffff;
            --text-main: #1e293b; --text-sub: #64748b;
            --border: #e2e8f0;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        body { font-family: 'Pretendard', sans-serif; background: var(--bg); color: var(--text-main); margin: 0; padding: 20px; line-height: 1.5; overflow-x: hidden; }
        
        .main-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .main-title { font-size: 24px; font-weight: 800; margin: 0; }
        
        .btn-backup { padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: white; cursor: pointer; font-weight: 600; color: var(--text-sub); font-size: 13px; transition: 0.2s; }
        .btn-backup:hover { background: #f1f5f9; color: var(--text-main); }

        .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: var(--surface); padding: 20px; border-radius: 16px; box-shadow: var(--shadow); border: 1px solid var(--border); display: flex; flex-direction: column; justify-content: center; }
        .stat-card h3 { margin: 0 0 8px 0; font-size: 13px; color: var(--text-sub); font-weight: 600; }
        .stat-card p { margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
        .text-up { color: var(--red-text); } .text-down { color: var(--blue-text); } .text-neutral { color: var(--text-main); }
        
        .chart-container { background: var(--surface); border-radius: 16px; padding: 20px; box-shadow: var(--shadow); border: 1px solid var(--border); margin-bottom: 20px; height: 250px; position: relative; }

        .calendar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; background: var(--surface); padding: 10px 20px; border-radius: 16px; box-shadow: var(--shadow); }
        .calendar-header h2 { margin: 0; font-size: 18px; font-weight: 700; }
        .btn-nav { background: var(--bg); border: none; padding: 6px 12px; border-radius: 8px; cursor: pointer; font-weight: 600; color: var(--text-sub); font-size: 13px; }
        .btn-nav:hover { background: #e2e8f0; color: var(--text-main); }

        .calendar-wrapper { background: var(--surface); border-radius: 16px; box-shadow: var(--shadow); padding: 20px; border: 1px solid var(--border); }
        .calendar { display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; }
        .day-header { text-align: left; font-weight: 600; color: var(--text-sub); padding-bottom: 10px; font-size: 12px; padding-left: 5px; }
        .day { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; min-height: 100px; padding: 8px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; transition: 0.2s; position: relative; }
        .day:hover { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(37,99,235,0.1); z-index: 10; }
        .day.today { background: #f8fafc; border-color: var(--primary); }
        
        .day-num { font-size: 13px; font-weight: 600; color: var(--text-sub); margin-bottom: 2px; }
        .day.today .day-num { background: var(--primary); color: white; border-radius: 50%; width: 22px; height: 22px; display: flex; justify-content: center; align-items: center; }
        .day-emoji { position: absolute; top: 8px; right: 8px; font-size: 16px; }

        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.4); backdrop-filter: blur(4px); z-index: 1000; justify-content: center; align-items: center; }
        .modal { background: white; border-radius: 20px; width: 450px; max-width: 95%; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; }
        .modal-header { padding: 15px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; background: white; }
        .modal-title { font-size: 16px; font-weight: 700; margin: 0; }
        .btn-close { border: none; background: none; cursor: pointer; font-size: 20px; color: var(--text-sub); }
        
        .modal-body { padding: 20px; overflow-y: auto; background: #fafafa; }
        .form-group { margin-bottom: 12px; }
        .form-label { display: block; margin-bottom: 4px; font-size: 12px; font-weight: 600; color: var(--text-sub); }
        .form-input, .form-select { width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; box-sizing: border-box; background: white; }
        .form-input:disabled, .form-select:disabled { background: #f1f5f9; color: #94a3b8; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        
        .btn-save { width: 100%; padding: 10px; background: #1e293b; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 14px; margin-top: 10px; }
        .btn-cancel { width: 100%; padding: 10px; background: #e2e8f0; color: var(--text-sub); border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 14px; margin-top: 10px; }

        /* 달력 뱃지 스타일 */
        .badge { font-size: 10px; padding: 4px 6px; border-radius: 4px; font-weight: 500; display:flex; flex-direction:column; gap:1px; margin-bottom: 2px; }
        
        /* 매수 = 빨강 */
        .badge.buy { background: var(--red-bg); color: var(--red-text); border: 1px solid rgba(248,113,113,0.2); }
        
        /* 매도 = 파랑 */
        .badge.sell { background: var(--blue-bg); color: var(--blue-text); border: 1px solid rgba(59,130,246,0.2); }
        
        /* 기타(예수금) = 연한 초록 */
        .badge.other { background: var(--green-bg); color: var(--green-text); border: 1px solid #bbf7d0; }
        
        .badge-amt { font-size: 9px; font-weight: 400; opacity: 0.9; }

        .log-section { margin-top: 15px; border-top: 1px dashed var(--border); padding-top: 15px; }
        .log-item { background: white; border: 1px solid var(--border); border-radius: 6px; padding: 8px; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
        .log-name { font-weight: 700; font-size: 12px; color: var(--text-main); }
        .log-detail { font-size: 10px; color: var(--text-sub); }
        
        .btn-group { display: flex; gap: 5px; }
        .btn-edit { color: #475569; background: #f1f5f9; border: 1px solid #e2e8f0; cursor: pointer; font-size: 11px; padding: 3px 6px; border-radius: 4px; font-weight: 600; }
        .btn-edit:hover { background: #e2e8f0; }
        .btn-delete { color: #cbd5e1; background: none; border: none; cursor: pointer; font-size: 16px; }
        .btn-delete:hover { color: var(--red); }
    </style>
</head>
<body>

<div class="container">
    <div class="main-header">
        <h1 class="main-title">📈 하루 20만 목표!!! (Streamlit)</h1>
        <div style="display:flex; gap:10px;">
            <button class="btn-backup" onclick="exportData()">💾 백업 저장</button>
            <button class="btn-backup" onclick="document.getElementById('fileInput').click()">📂 데이터 복구</button>
            <input type="file" id="fileInput" style="display:none" onchange="importData(this)" accept=".json">
        </div>
    </div>

    <div class="summary-grid">
        <div class="stat-card"><h3>💰 총 누적 손익</h3><p id="totalProfit" class="text-neutral">0원</p></div>
        <div class="stat-card"><h3>📉 이번 달 수익</h3><p id="monthProfit" class="text-neutral">0원</p></div>
        <div class="stat-card"><h3>⚖️ 평균 손익 (1회)</h3><p id="avgProfit" class="text-neutral">0원</p></div>
        <div class="stat-card"><h3>🏆 베스트</h3><p id="bestStock" class="text-neutral">-</p></div>
    </div>

    <div class="chart-container">
        <canvas id="assetChart"></canvas>
    </div>

    <div class="calendar-header">
        <button class="btn-nav" onclick="changeMonth(-1)">◀ 이전</button>
        <h2 id="currentMonthLabel"></h2>
        <button class="btn-nav" onclick="changeMonth(1)">다음 ▶</button>
    </div>
    <div class="calendar-wrapper"><div class="calendar" id="calendarGrid"></div></div>
</div>

<div class="modal-overlay" id="modalOverlay">
    <div class="modal">
        <div class="modal-header">
            <h2 class="modal-title" id="modalTitle">거래 입력</h2>
            <button class="btn-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <div class="form-group"><label class="form-label">날짜</label><input type="date" id="inputDate" class="form-input"></div>
            <div class="form-row">
                <div class="form-group">
                    <label class="form-label">구분</label>
                    <select id="inputType" class="form-select" onchange="handleTypeChange()">
                        <option value="buy">매수 (Buy)</option>
                        <option value="sell">매도 (Sell)</option>
                        <option value="other">기타 (예수금)</option>
                    </select>
                </div>
                <div class="form-group"><label class="form-label">종목명</label><input type="text" id="inputName" class="form-input" placeholder="종목명"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label class="form-label" id="priceLabel">매수 단가</label><input type="number" id="inputPrice" class="form-input" placeholder="원"></div>
                <div class="form-group"><label class="form-label">수량</label><input type="number" id="inputQty" class="form-input" value="1" placeholder="주"></div>
            </div>
            <div style="text-align: right; font-size: 11px; color: var(--text-sub); margin-bottom: 5px;">합계: <strong id="calcTotal">0</strong> 원</div>
            
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 10px;">
                <button class="btn-cancel" onclick="closeModal()">취소</button>
                <button class="btn-save" onclick="save()">저장</button>
            </div>

            <div class="log-section">
                <div style="font-size:12px; font-weight:700; color:#aaa; margin-bottom:10px;">🗓 기록 & 보유</div>
                <div id="dayLogList"></div>
            </div>
        </div>
    </div>
</div>

<script>
    let currentDate = new Date();
    let transactions = JSON.parse(localStorage.getItem('stockData_st')) || [];
    let myChart = null;
    let linkedBuyData = null; let currentMode = 'new';
    let editingId = null; 

    function init() { renderAll(); }
    function renderAll() { renderCalendar(); updateSummary(); renderChart(); }
    function formatMoney(n) { return Number(n).toLocaleString(); }
    function formatMoneyFull(n) { return Number(n).toLocaleString() + '원'; }
    
    // 데이터 백업/복구
    function exportData() {
        const dataStr = JSON.stringify(transactions);
        const link = document.createElement('a');
        link.href = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
        link.download = 'stock_backup.json';
        link.click();
    }
    function importData(input) {
        const file = input.files[0];
        if(!file) return;
        const reader = new FileReader();
        reader.onload = function(e) {
            if(confirm("기존 데이터를 덮어쓰시겠습니까?")) {
                transactions = JSON.parse(e.target.result);
                localStorage.setItem('stockData_st', JSON.stringify(transactions));
                location.reload();
            }
        };
        reader.readAsText(file);
    }

    // 차트
    function renderChart() {
        const ctx = document.getElementById('assetChart').getContext('2d');
        let sortedLogs = [...transactions].sort((a,b) => new Date(a.date) - new Date(b.date));
        let dateMap = new Map();
        let currentTotal = 0;
        sortedLogs.forEach(log => {
            let val = 0;
            if(log.type === 'sell') val = (log.profit || 0);
            else if (log.type === 'other') val = (log.price || 0);
            currentTotal += val;
            dateMap.set(log.date, currentTotal);
        });
        const labels = Array.from(dateMap.keys());
        const data = Array.from(dateMap.values());

        if(myChart) myChart.destroy();
        myChart = new Chart(ctx, {
            type: 'line',
            data: { labels: labels, datasets: [{ label: '자산', data: data, borderColor: '#2563eb', backgroundColor: 'rgba(37, 99, 235, 0.05)', borderWidth: 2, tension: 0.3, fill: true, pointRadius: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { beginAtZero: false } } }
        });
    }

    // 달력
    function renderCalendar() {
        const grid = document.getElementById('calendarGrid');
        const y = currentDate.getFullYear();
        const m = currentDate.getMonth();
        document.getElementById('currentMonthLabel').innerText = `${y}년 ${m+1}월`;
        
        grid.innerHTML = `<div class="day-header" style="color:#ef4444">일</div><div class="day-header">월</div><div class="day-header">화</div><div class="day-header">수</div><div class="day-header">목</div><div class="day-header">금</div><div class="day-header" style="color:#3b82f6">토</div>`;
        const first = new Date(y, m, 1).getDay();
        const last = new Date(y, m+1, 0).getDate();

        for(let i=0; i<first; i++) grid.innerHTML += `<div class="day" style="opacity:0; pointer-events:none;"></div>`;

        for(let i=1; i<=last; i++) {
            const dStr = `${y}-${String(m+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;
            const logs = transactions.filter(t => t.date === dStr);
            let emoji = '';
            let prof = 0, hasSell = false, hasBuy = false;
            logs.forEach(l => { if(l.type === 'sell') { hasSell=true; prof+=(l.profit||0); } if(l.type === 'buy') hasBuy=true; });
            if(hasSell) emoji = (prof > 0 ? '😄' : '😭');
            if(hasBuy && !hasSell) emoji = '🔥';

            let html = `<div class="day" onclick="openModal('${dStr}')">
                <div class="day-num">${i}</div>${emoji ? `<div class="day-emoji">${emoji}</div>` : ''}`;
            
            logs.forEach(l => {
                if(l.type === 'buy') {
                    let totalBuy = l.price * l.qty;
                    html += `<div class="badge buy ${l.remainingQty===0?'sold-out':''}"><span>${l.name}</span><span class="badge-amt">매수 ${formatMoney(totalBuy)}</span></div>`;
                } else if(l.type === 'sell') {
                    html += `<div class="badge sell"><span>${l.name}</span><span class="badge-amt">매도 ${formatMoney(l.profit)}</span></div>`;
                } else {
                    html += `<div class="badge other"><span>${l.name}</span><span class="badge-amt">${formatMoney(l.price)}</span></div>`;
                }
            });
            grid.innerHTML += html + `</div>`;
        }
    }
    function changeMonth(d) { currentDate.setMonth(currentDate.getMonth()+d); renderCalendar(); }

    // 모달 & 입력
    function openModal(dStr) {
        currentMode = 'new'; linkedBuyData = null; editingId = null;
        document.getElementById('modalOverlay').style.display = 'flex';
        document.getElementById('modalTitle').innerText = "거래 입력"; 
        document.getElementById('inputDate').value = dStr;
        document.getElementById('inputType').disabled = false;
        document.getElementById('inputType').value = 'buy';
        document.getElementById('inputName').readOnly = false;
        document.getElementById('inputName').value = '';
        document.getElementById('inputPrice').value = '';
        document.getElementById('inputQty').value = '1';
        handleTypeChange(); renderLog(dStr);
        document.getElementById('inputPrice').oninput = calc;
        document.getElementById('inputQty').oninput = calc;
    }
    function closeModal() { document.getElementById('modalOverlay').style.display = 'none'; }
    
    function handleTypeChange() {
        const t = document.getElementById('inputType').value;
        const pl = document.getElementById('priceLabel');
        const qi = document.getElementById('inputQty');
        if(t === 'buy') { pl.innerText = "매수 단가"; qi.disabled = false; }
        else if(t === 'sell') { pl.innerText = "매도 단가"; qi.disabled = false; }
        else { pl.innerText = "금액 (+/-)"; qi.value = 1; qi.disabled = true; }
        calc();
    }
    function calc() {
        const p = Number(document.getElementById('inputPrice').value);
        const q = Number(document.getElementById('inputQty').value);
        document.getElementById('calcTotal').innerText = formatMoneyFull(p * q);
    }
    
    // 저장 (신규 or 수정)
    function save() {
        const d = document.getElementById('inputDate').value;
        const t = document.getElementById('inputType').value;
        const n = document.getElementById('inputName').value;
        const p = Number(document.getElementById('inputPrice').value);
        const q = Number(document.getElementById('inputQty').value);

        if(!n || (!p && p!==0) || !q) { alert("입력 확인"); return; }

        if (editingId) {
            let target = transactions.find(x => x.id === editingId);
            if (target) {
                if (target.type === 'buy') {
                    const diffQty = q - target.qty;
                    target.remainingQty += diffQty;
                    if(target.price !== p) {
                        transactions.filter(x => x.linkedBuyId === target.id).forEach(s => {
                            s.profit = (s.price - p) * s.qty;
                        });
                    }
                }
                target.date = d;
                target.name = n;
                target.price = p;
                target.qty = q;

                if (target.type === 'sell' && target.linkedBuyId) {
                    let buyRec = transactions.find(x => x.id === target.linkedBuyId);
                    if (buyRec) target.profit = (p - buyRec.price) * q;
                }
            }
            editingId = null;
        } else {
            if(t === 'sell' && currentMode === 'sell_link' && linkedBuyData) {
                if(q > linkedBuyData.remainingQty) { alert("보유 초과"); return; }
                transactions.push({id:Date.now(), date:d, type:'sell', name:n, price:p, qty:q, linkedBuyId:linkedBuyData.id, profit:(p-linkedBuyData.price)*q});
                linkedBuyData.remainingQty -= q;
            } else if(t === 'buy') {
                transactions.push({id:Date.now(), date:d, type:'buy', name:n, price:p, qty:q, remainingQty:q});
            } else {
                transactions.push({id:Date.now(), date:d, type:'other', name:n, price:p, qty:1});
            }
        }
        
        localStorage.setItem('stockData_st', JSON.stringify(transactions));
        
        if(t === 'sell' && !editingId) closeModal(); 
        else { 
            document.getElementById('inputName').value=''; 
            document.getElementById('inputPrice').value=''; 
            if (t==='buy') document.getElementById('inputQty').value='1';
            document.getElementById('modalTitle').innerText = "거래 입력";
            editingId = null; 
            renderLog(d); 
        }
        renderAll();
    }

    function editLog(id) {
        let t = transactions.find(x => x.id === id);
        if (!t) return;
        
        editingId = id;
        document.getElementById('modalTitle').innerText = "거래 수정";
        document.getElementById('inputDate').value = t.date;
        document.getElementById('inputType').value = t.type;
        document.getElementById('inputType').disabled = true;
        
        document.getElementById('inputName').value = t.name;
        document.getElementById('inputPrice').value = t.price;
        document.getElementById('inputQty').value = t.qty;
        
        if (t.type === 'sell') { document.getElementById('inputName').readOnly = true; } 
        else { document.getElementById('inputName').readOnly = false; }
        
        handleTypeChange();
    }

    function renderLog(dStr) {
        const list = document.getElementById('dayLogList');
        const logs = transactions.filter(x => x.date === dStr);
        let html = '';
        logs.forEach(g => {
            let info = '';
            if(g.type === 'buy') info = `[매수] ${g.qty}주 @ ${formatMoneyFull(g.price)}`;
            else if(g.type === 'sell') info = `[매도] 수익:${formatMoneyFull(g.profit)}`;
            else info = `[기타] ${formatMoneyFull(g.price)}`;
            
            html += `<div class="log-item">
                <div style="display:flex;flex-direction:column;">
                    <span class="log-name">${g.name}</span>
                    <span class="log-detail">${info}</span>
                </div>
                <div class="btn-group">
                    <button class="btn-edit" onclick="editLog(${g.id})">수정</button>
                    <button class="btn-delete" onclick="del(${g.id})">&times;</button>
                </div>
            </div>`;
        });
        
        const hlds = transactions.filter(x => x.type === 'buy' && x.remainingQty > 0);
        if(hlds.length > 0) {
            html += '<div style="font-size:12px; font-weight:700; color:#ea580c; margin:15px 0 5px 0;">📦 매도 가능 (클릭)</div>';
            hlds.forEach(g => {
                let totalBuyVal = g.price * g.remainingQty;
                html += `<div class="log-item" style="border-left:3px solid #2563eb; cursor:pointer;" onclick="initiateSell(${g.id})">
                    <div style="display:flex;flex-direction:column;">
                        <span class="log-name">${g.name}</span>
                        <span class="log-detail">${g.date} | 잔여:${g.remainingQty}주 | 매수금:${formatMoneyFull(totalBuyVal)}</span>
                    </div>
                </div>`;
            });
        }
        list.innerHTML = html;
    }

    function initiateSell(bid) {
        let b = transactions.find(x => x.id === bid); if(!b) return;
        currentMode = 'sell_link'; linkedBuyData = b; editingId = null;
        document.getElementById('modalTitle').innerText = "매도 입력";
        document.getElementById('inputType').value = 'sell'; document.getElementById('inputType').disabled = true;
        document.getElementById('inputName').value = b.name; document.getElementById('inputName').readOnly = true;
        document.getElementById('inputPrice').value = ''; document.getElementById('inputQty').value = b.remainingQty;
        handleTypeChange();
    }

    function del(id) {
        if(!confirm("삭제하시겠습니까?")) return;
        transactions = transactions.filter(x => x.id !== id);
        localStorage.setItem('stockData_st', JSON.stringify(transactions));
        renderLog(document.getElementById('inputDate').value); renderAll();
    }

    function updateSummary() {
        let tp=0, mp=0, sc=0, sps=0, maxP=-Infinity, maxN="-", cm=`${currentDate.getFullYear()}-${String(currentDate.getMonth()+1).padStart(2,'0')}`;
        transactions.forEach(t => {
            if(t.type === 'sell') {
                let p = t.profit||0; tp+=p; sps+=p; sc++;
                if(t.date.startsWith(cm)) { mp+=p; if(p>maxP){maxP=p; maxN=t.name;} }
            } else if(t.type === 'other') { tp+=t.price; if(t.date.startsWith(cm)) mp+=t.price; }
        });
        document.getElementById('totalProfit').innerText = formatMoneyFull(tp);
        document.getElementById('monthProfit').innerText = formatMoneyFull(mp);
        document.getElementById('avgProfit').innerText = formatMoneyFull(sc>0?Math.round(sps/sc):0);
        document.getElementById('bestStock').innerText = maxN;
    }

    init();
</script>
</body>
</html>
"""

components.html(html_code, height=1200, scrolling=True)
