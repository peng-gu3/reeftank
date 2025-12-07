from datetime import date
from typing import Dict, List, Tuple

import gspread
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="My Triton Lab Pro", page_icon="🐠", layout="wide")

SHEET_NAME = "MyReefLog"
HEADERS = [
    "날짜",
    "KH",
    "Ca",
    "Mg",
    "NO2",
    "NO3",
    "PO4",
    "pH",
    "Temp",
    "Salinity",
    "도징량",
    "Memo",
]


# --- 1. 인증 ---
def get_creds() -> Dict[str, str]:
    if "gcp_service_account" in st.secrets:
        return dict(st.secrets["gcp_service_account"])

    st.error(
        "🚨 인증 정보를 찾을 수 없습니다! 배포 화면의 [Settings] > [Secrets] 설정을 확인해주세요."
    )
    st.stop()


@st.cache_resource(show_spinner=False)
def get_client(creds_dict: Dict[str, str]) -> gspread.Client:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)


# --- 2. 구글 시트 연결 ---
def resolve_sheet(client: gspread.Client) -> gspread.Spreadsheet:
    sheet = None
    error_message = None

    try:
        sheet = client.open(SHEET_NAME)
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)

    url_placeholder = "https://docs.google.com/spreadsheets/d/..."
    sheet_url = st.sidebar.text_input(
        "📎 직접 연결 (선택)",
        value=st.session_state.get("sheet_url", ""),
        placeholder=url_placeholder,
        help="기본 이름으로 열 수 없을 때 URL을 붙여넣어주세요.",
    )

    if not sheet and sheet_url:
        try:
            sheet = client.open_by_url(sheet_url)
            st.session_state["sheet_url"] = sheet_url
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"URL로 연결 실패: {exc}")

    if not sheet:
        if error_message:
            st.sidebar.warning(
                f"'{SHEET_NAME}' 파일을 찾을 수 없습니다. 오류: {error_message}"
            )
        st.stop()

    return sheet


def ensure_worksheets(spreadsheet: gspread.Spreadsheet) -> Tuple[gspread.Worksheet, gspread.Worksheet]:
    try:
        sheet_log = spreadsheet.worksheet("Logs")
    except gspread.WorksheetNotFound:
        sheet_log = spreadsheet.add_worksheet(title="Logs", rows=2000, cols=20)

    try:
        current_headers = sheet_log.row_values(1)
        if not current_headers or current_headers[0] != "날짜":
            sheet_log.insert_row(HEADERS, index=1)
    except Exception:  # noqa: BLE001
        pass

    try:
        sheet_config = spreadsheet.worksheet("Config")
    except gspread.WorksheetNotFound:
        sheet_config = spreadsheet.add_worksheet(title="Config", rows=20, cols=10)

    return sheet_log, sheet_config


# --- 3. 데이터 관리 ---
def load_data(sheet_log: gspread.Worksheet) -> pd.DataFrame:
    rows = sheet_log.get_all_values()
    if len(rows) < 2:
        return pd.DataFrame(columns=HEADERS)

    df = pd.DataFrame(rows[1:], columns=HEADERS)
    df["_row_idx"] = range(2, len(df) + 2)

    numeric_cols = ["KH", "Ca", "Mg", "NO2", "NO3", "PO4", "pH", "Temp", "Salinity", "도징량"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df.sort_values("날짜", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def save_data(entry: Dict[str, str], sheet_log: gspread.Worksheet) -> None:
    row = [
        str(entry["날짜"]),
        entry["KH"],
        entry["Ca"],
        entry["Mg"],
        entry["NO2"],
        entry["NO3"],
        entry["PO4"],
        entry["pH"],
        entry["Temp"],
        entry["Salinity"],
        entry["도징량"],
        entry["Memo"],
    ]
    sheet_log.append_row(row)


def delete_rows_by_indices(row_indices: List[int], sheet_log: gspread.Worksheet) -> None:
    for idx in sorted(row_indices, reverse=True):
        sheet_log.delete_rows(idx)


# --- 4. 설정 관리 ---
def load_config(sheet_config: gspread.Worksheet) -> Dict[str, float]:
    default = {
        "volume": 150.0,
        "base_dose": 3.00,
        "t_kh": 8.30,
        "t_ca": 420.0,
        "t_mg": 1420.0,
        "t_no2": 0.010,
        "t_no3": 5.00,
        "t_po4": 0.040,
        "t_ph": 8.30,
    }

    records = sheet_config.get_all_records()
    if not records:
        return default

    saved = {**records[0]}
    for k, v in default.items():
        saved.setdefault(k, v)
    return saved


def save_config(new_conf: Dict[str, float], sheet_config: gspread.Worksheet) -> None:
    sheet_config.clear()
    sheet_config.append_row(list(new_conf.keys()))
    sheet_config.append_row(list(new_conf.values()))


# --- 5. 시각화 ---
def draw_radar(categories: List[str], values: List[float], targets: List[float], color: str) -> go.Figure:
    normalized = []
    labels = []
    for value, target in zip(values, targets):
        safe_target = target if target else 0.01
        ratio = value / safe_target if safe_target else 0
        normalized.append(min(max(ratio, 0), 2))
        labels.append(f"{value}")

    categories = [*categories, categories[0]]
    normalized = [*normalized, normalized[0]]
    labels = [*labels, ""]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=[1] * len(categories),
            theta=categories,
            line_color="white",
            line_dash="dot",
            name="목표",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=normalized,
            theta=categories,
            fill="toself",
            line_color=color,
            mode="lines+markers+text",
            text=labels,
            textfont=dict(color=color),
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=False, range=[0, 1.6]),
            angularaxis=dict(tickfont=dict(color="#00BFFF", size=12)),
            bgcolor="rgba(0,0,0,0)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#00BFFF"),
        height=350,
        margin=dict(t=40, b=40),
        showlegend=False,
    )
    return fig


def plot_trend(df: pd.DataFrame, columns: List[str], targets: Dict[str, float], title: str) -> go.Figure:
    fig = go.Figure()
    for col in columns:
        fig.add_trace(
            go.Scatter(
                x=df["날짜"],
                y=df[col],
                mode="lines+markers",
                name=col,
            )
        )
        if col in targets:
            fig.add_hline(y=targets[col], line_dash="dot", line_color="#999", annotation_text=f"{col} 목표")

    fig.update_layout(
        title=title,
        height=320,
        margin=dict(t=60, b=20),
        legend=dict(orientation="h"),
    )
    fig.update_xaxes(title="날짜")
    return fig


# --- 6. 유틸리티 ---
def compute_health(last_row: pd.Series, targets: Dict[str, float], volume: float, base_dose: float) -> List[str]:
    recommendations = []
    kh_diff = last_row["KH"] - targets["t_kh"]
    ca_diff = last_row["Ca"] - targets["t_ca"]
    mg_diff = last_row["Mg"] - targets["t_mg"]

    vol_factor = max(volume / 100.0, 0.1)
    if abs(kh_diff) <= 0.15:
        recommendations.append("KH는 안정적입니다.")
    elif kh_diff < 0:
        add = 0.3 * vol_factor
        recommendations.append(f"KH 부족: 도징 {base_dose + add:.2f} ml 제안")
    else:
        sub = 0.3 * vol_factor
        recommendations.append(f"KH 과다: 도징 {max(0, base_dose - sub):.2f} ml 제안")

    if ca_diff < -10:
        recommendations.append("칼슘이 낮습니다. 미세 조정 후 24시간 뒤 재측정하세요.")
    elif ca_diff > 20:
        recommendations.append("칼슘이 높습니다. 부분 환수 또는 도징량 축소를 고려하세요.")

    if mg_diff < -20:
        recommendations.append("마그네슘이 부족합니다. Mg 보충제를 소량 추가하세요.")
    elif mg_diff > 50:
        recommendations.append("마그네슘이 높습니다. 도징량을 잠시 중단하고 경과를 확인하세요.")

    if not recommendations:
        recommendations.append("측정값이 목표에 근접합니다. 유지 관리만 진행하세요.")
    return recommendations


def format_date(dt_value: pd.Timestamp) -> str:
    if pd.isna(dt_value):
        return ""
    return dt_value.strftime("%Y-%m-%d")


# --- 7. 메인 앱 ---
st.title("🌊 My Triton Manager (Cloud)")
creds_dict = get_creds()
client = get_client(creds_dict)
spreadsheet = resolve_sheet(client)
sheet_log, sheet_config = ensure_worksheets(spreadsheet)

st.success("✅ 구글 시트 연결됨")

if "config" not in st.session_state:
    st.session_state.config = load_config(sheet_config)

cfg = st.session_state.config

with st.sidebar:
    st.header("⚙️ 수조 & 목표 설정")
    volume = st.number_input("물량 (L)", value=float(cfg["volume"]), step=0.1)
    base_dose = st.number_input("도징량 (ml)", value=float(cfg["base_dose"]), step=0.01)
    st.divider()
    st.subheader("🎯 목표치")
    t_kh = st.number_input("목표 KH", value=float(cfg["t_kh"]), step=0.01)
    t_ca = st.number_input("목표 Ca", value=float(cfg["t_ca"]), step=10)
    t_mg = st.number_input("목표 Mg", value=float(cfg["t_mg"]), step=10)
    t_no2 = st.number_input("목표 NO2", value=float(cfg["t_no2"]), format="%.3f", step=0.001)
    t_no3 = st.number_input("목표 NO3", value=float(cfg["t_no3"]), step=0.1)
    t_po4 = st.number_input("목표 PO4", value=float(cfg["t_po4"]), format="%.3f", step=0.001)
    t_ph = st.number_input("목표 pH", value=float(cfg["t_ph"]), step=0.1)

    if st.button("💾 설정값 영구 저장", use_container_width=True):
        new_conf = {
            "volume": volume,
            "base_dose": base_dose,
            "t_kh": t_kh,
            "t_ca": t_ca,
            "t_mg": t_mg,
            "t_no2": t_no2,
            "t_no3": t_no3,
            "t_po4": t_po4,
            "t_ph": t_ph,
        }
        save_config(new_conf, sheet_config)
        st.session_state.config = new_conf
        st.toast("설정 저장 완료! 새로고침합니다.")
        st.rerun()

# --- 데이터 불러오기 ---
df = load_data(sheet_log)

with st.expander("📝 새 기록 입력하기", expanded=False):
    with st.form("entry"):
        c1, c2, c3, c4 = st.columns(4)
        d_date = c1.date_input("날짜", date.today())
        d_kh = c1.number_input("KH", value=t_kh, step=0.01)
        d_ca = c2.number_input("Ca", value=t_ca, step=10)
        d_mg = c2.number_input("Mg", value=t_mg, step=10)
        d_no2 = c3.number_input("NO2", value=0.0, format="%.3f", step=0.001)
        d_no3 = c3.number_input("NO3", value=t_no3, step=0.1)
        d_po4 = c3.number_input("PO4", value=t_po4, format="%.3f", step=0.001)
        d_ph = c4.number_input("pH", value=t_ph, step=0.1)
        d_sal = c4.number_input("염도", value=35.0, step=0.1)
        d_temp = c4.number_input("온도", value=25.0, step=0.1)
        d_memo = st.text_area("메모")

        if st.form_submit_button("저장 💾"):
            entry = {
                "날짜": d_date,
                "KH": d_kh,
                "Ca": d_ca,
                "Mg": d_mg,
                "NO2": d_no2,
                "NO3": d_no3,
                "PO4": d_po4,
                "pH": d_ph,
                "Temp": d_temp,
                "Salinity": d_sal,
                "도징량": base_dose,
                "Memo": d_memo,
            }
            save_data(entry, sheet_log)
            st.toast("저장되었습니다! 잠시 후 최신 데이터가 표시됩니다.")
            st.rerun()

st.divider()

if df.empty:
    st.info("👋 기록이 없습니다. 데이터를 입력해주세요!")
    st.stop()

# --- 최신 정보 및 요약 ---
latest = df.iloc[-1]
previous = df.iloc[-2] if len(df) > 1 else None

summary_cols = st.columns(4)
summary_cols[0].metric(
    "최근 측정일",
    format_date(latest["날짜"]),
    delta=(
        f"{(latest['날짜'] - previous['날짜']).days}일" if previous is not None else None
    ),
)
summary_cols[1].metric(
    "KH",
    f"{latest['KH']:.2f}",
    delta=(f"{latest['KH'] - previous['KH']:.2f}" if previous is not None else None),
)
summary_cols[2].metric(
    "Ca",
    f"{latest['Ca']:.0f}",
    delta=(f"{latest['Ca'] - previous['Ca']:.0f}" if previous is not None else None),
)
summary_cols[3].metric(
    "Mg",
    f"{latest['Mg']:.0f}",
    delta=(f"{latest['Mg'] - previous['Mg']:.0f}" if previous is not None else None),
)

health_cols = st.columns([1.2, 0.8])
with health_cols[0]:
    st.subheader("현재 상태 요약")
    st.plotly_chart(
        draw_radar(
            ["KH", "Ca", "Mg"],
            [latest["KH"], latest["Ca"], latest["Mg"]],
            [t_kh, t_ca, t_mg],
            "#00FFAA",
        ),
        use_container_width=True,
    )
    st.plotly_chart(
        draw_radar(
            ["NO2", "NO3", "PO4", "pH"],
            [latest["NO2"], latest["NO3"], latest["PO4"] * 100, latest["pH"]],
            [t_no2, t_no3, t_po4 * 100, t_ph],
            "#FF5500",
        ),
        use_container_width=True,
    )

with health_cols[1]:
    st.subheader("🤖 AI 분석")
    recs = compute_health(
        latest,
        {
            "t_kh": t_kh,
            "t_ca": t_ca,
            "t_mg": t_mg,
        },
        volume=volume,
        base_dose=base_dose,
    )
    for rec in recs:
        st.write("• " + rec)

    nutrient_delta = latest["NO3"] - t_no3
    po4_delta = latest["PO4"] - t_po4
    st.caption(
        f"NO3 편차: {nutrient_delta:+.2f}, PO4 편차: {po4_delta:+.3f}. 과다 시 환수 또는 스키밍을 검토하세요."
    )

# --- 추세 차트 ---
st.subheader("📈 추세")
trend1 = plot_trend(
    df,
    ["KH", "Ca", "Mg"],
    {"KH": t_kh, "Ca": t_ca, "Mg": t_mg},
    "3대 요소 추세",
)
trend2 = plot_trend(
    df,
    ["NO2", "NO3", "PO4", "pH"],
    {"NO2": t_no2, "NO3": t_no3, "PO4": t_po4, "pH": t_ph},
    "영양염 추세",
)

c_trend1, c_trend2 = st.columns(2)
c_trend1.plotly_chart(trend1, use_container_width=True)
c_trend2.plotly_chart(trend2, use_container_width=True)

# --- 필터링 및 테이블 ---
st.subheader("📋 기록 관리")

min_date = df["날짜"].min()
max_date = df["날짜"].max()
start_date, end_date = st.date_input(
    "조회 기간",
    (min_date.date(), max_date.date()),
    min_value=min_date.date() if pd.notna(min_date) else date.today(),
    max_value=max_date.date() if pd.notna(max_date) else date.today(),
)

mask = (df["날짜"].dt.date >= start_date) & (df["날짜"].dt.date <= end_date)
filtered_df = df.loc[mask].copy()
filtered_df["날짜"] = filtered_df["날짜"].dt.strftime("%Y-%m-%d")
filtered_df.insert(0, "삭제", False)
filtered_df["Memo"] = filtered_df["Memo"].fillna("")

edited_df = st.data_editor(
    filtered_df,
    column_config={
        "삭제": st.column_config.CheckboxColumn("삭제 선택", default=False),
        "_row_idx": None,
        "Memo": st.column_config.TextColumn("메모", width="large"),
    },
    disabled=[c for c in HEADERS],
    hide_index=True,
    use_container_width=True,
)

c_actions = st.columns([0.3, 0.7])
with c_actions[0]:
    if st.button("🗑️ 선택 삭제", type="primary", use_container_width=True):
        rows_to_delete = edited_df[edited_df["삭제"]]
        if not rows_to_delete.empty:
            delete_rows_by_indices(rows_to_delete["_row_idx"].tolist(), sheet_log)
            st.toast(f"{len(rows_to_delete)}개의 기록을 삭제했습니다!")
            st.rerun()
        else:
            st.warning("먼저 표에서 지울 항목을 체크해주세요.")

with c_actions[1]:
    csv_bytes = filtered_df[[c for c in filtered_df.columns if c != "삭제"]].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ CSV 다운로드 (필터 적용)",
        csv_bytes,
        file_name="reef_log_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption("데이터는 Google Sheet에 바로 저장되며, 언제든 새로고침 후 최신 상태를 확인할 수 있습니다.")
