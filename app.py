import html
import re
import calendar as py_calendar
from datetime import date, datetime, timedelta, timezone

import gspread
import pandas as pd
import streamlit as st

# ======================= 視覺主題：馬卡龍療癒積木風（Soft Pastel Bento） =======================
ACCENT = "#FF7A59"
INCOME_COLOR = "#18865B"
EXPENSE_COLOR = "#D94E34"
WARN_COLOR = "#D99316"
PALETTE = [
    "#FF8A65", "#4DB6AC", "#FFD54F", "#F06292",
    "#64B5F6", "#81C784", "#BA68C8", "#A1887F",
]
CAT_COLORS = {
    "伙食": "#FF8A65", "飲料": "#64B5F6", "交通": "#4DB6AC", "日用": "#81C784",
    "購物": "#F06292", "娛樂": "#FFD54F", "居家": "#BA68C8", "醫療": "#4DD0E1",
    "學習": "#7986CB", "社交": "#FF8A80", "保險": "#A1887F",
    "其他支出": "#B0BEC5", "每月固定費用": "#90A4AE",
}
CAT_BADGES = {
    "伙食": ("🍱", "#FFE5D9"), "飲料": ("🧋", "#E2F0FF"), "交通": ("🚇", "#D9F4E8"),
    "日用": ("🧴", "#E8F5E9"), "購物": ("🛍️", "#FCE4EC"), "娛樂": ("🎬", "#FFF2C6"),
    "居家": ("🏠", "#F3E5F5"), "醫療": ("💊", "#E0F7FA"), "學習": ("📚", "#E8EAF6"),
    "社交": ("🎁", "#FFEBEE"), "保險": ("🛡️", "#EFEBE9"), "每月固定費用": ("📌", "#ECEFF1"),
    "其他支出": ("🧾", "#F5EFEA"), "總預算": ("🎯", "#FFE5D9"),
    "薪資": ("💼", "#D9F4E8"), "獎金": ("🎉", "#FFF2C6"), "投資": ("📈", "#E2F0FF"),
    "副業": ("✨", "#F3E5F5"), "回饋": ("💎", "#D9F4E8"), "其他收入": ("🪙", "#FFF2C6"),
}


def cat_badge_html(name, fallback_icon="🏷️", fallback_bg="#F5EFEA"):
    icon, bg = CAT_BADGES.get(str(name).strip(), (fallback_icon, fallback_bg))
    return f"<span class='cat-badge' style='background:{bg};'>{icon}</span>"


CSS = """
<style>
:root {
  --bg:#FFF9F5;
  --ink:#2D2A32;
  --ink-muted:#7E747B;
  --primary:#FF7A59;
  --primary-hover:#F26745;
  --primary-soft:rgba(255,122,89,.18);
  --income:#18865B;
  --income-soft:#D9F4E8;
  --expense:#D94E34;
  --expense-soft:#FFE5D9;
  --warning:#C78008;
  --warning-soft:#FFF2C6;
  --sky-soft:#E2F0FF;
  --sky-ink:#1D528F;
  --line:#EFE4DC;
  --card:#FFFFFF;
  --card-hover:#FFFDFB;
  --track:#F3EAE3;
  --r-sm:14px; --r-md:20px; --r-lg:26px;
  --shadow-card:0 6px 22px rgba(176,140,122,.12);
  --shadow-lift:0 10px 26px rgba(176,140,122,.18);
  --ease:cubic-bezier(.2,.7,.2,1);
}

/* 全域奶油白畫布與深可可文字 */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background-color:var(--bg) !important;
  color:var(--ink) !important;
}
.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp span {
  font-family:"PingFang TC","Hiragino Maru Gothic ProN","Microsoft JhengHei","Noto Sans TC",system-ui,-apple-system,sans-serif;
  -webkit-font-smoothing:antialiased;
}
footer { display:none; }
div.block-container, div[data-testid="stMainBlockContainer"] {
  max-width:1080px; padding:4rem 1rem 4rem;
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color:var(--ink) !important; }
.stApp h3 { font-size:1.15rem; font-weight:700; letter-spacing:.01em; margin-top:.6rem; }
.stApp h4 { font-size:.92rem; font-weight:700; color:var(--ink-muted) !important; letter-spacing:.03em; }
.stApp hr { border-color:var(--line) !important; margin:1.4rem 0; }
.stApp [data-testid="stCaptionContainer"], .stApp [data-testid="stCaptionContainer"] p {
  color:var(--ink-muted) !important; opacity:1;
}

/* ---------- 標題 ---------- */
.app-header { display:flex; align-items:center; gap:12px; }
.app-logo {
  width:46px; height:46px; border-radius:999px; background:var(--expense-soft);
  display:flex; align-items:center; justify-content:center; font-size:1.45rem;
  box-shadow:0 4px 12px rgba(255,122,89,.16); flex-shrink:0;
}
.app-header h1 { font-size:1.45rem; font-weight:800; line-height:1.25; margin:0; padding:0; color:var(--ink) !important; }
.app-header p { margin:.18rem 0 0; color:var(--ink-muted) !important; font-size:.84rem; }
.st-key-topbar div[data-testid="stHorizontalBlock"],
.st-key-month_nav div[data-testid="stHorizontalBlock"],
.st-key-csv_export_row div[data-testid="stHorizontalBlock"] {
  flex-direction:row !important; flex-wrap:nowrap !important; align-items:center; gap:8px;
}
.st-key-topbar div[data-testid="stColumn"],
.st-key-month_nav div[data-testid="stColumn"],
.st-key-csv_export_row div[data-testid="stColumn"] { min-width:0 !important; }

/* ---------- 按鈕 ---------- */
.stButton button, .stDownloadButton button {
  min-height:44px; font-weight:600; border-radius:999px;
  background:var(--card) !important; color:var(--ink) !important;
  border:1.5px solid var(--line) !important;
  box-shadow:0 3px 10px rgba(176,140,122,.08);
  transition:transform .16s var(--ease), box-shadow .16s var(--ease), background .16s var(--ease), border-color .16s var(--ease);
}
.stButton button p, .stDownloadButton button p { color:var(--ink) !important; }
.stButton button:hover, .stDownloadButton button:hover {
  border-color:var(--primary) !important; transform:translateY(-1px); box-shadow:var(--shadow-lift);
}
.stButton button:active, .stDownloadButton button:active { transform:translateY(0) scale(.98); box-shadow:none; }
.stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {
  background:linear-gradient(135deg,#FF8666 0%,#FF6B4A 100%) !important;
  border:none !important; color:#fff !important; font-weight:700;
  box-shadow:0 6px 16px rgba(255,107,74,.32) !important;
}
.stButton button[kind="primary"] p, .stButton button[data-testid="stBaseButton-primary"] p,
.stButton button[kind="primary"] span, .stButton button[data-testid="stBaseButton-primary"] span {
  color:#fff !important;
}
.stButton button[kind="primary"]:hover, .stButton button[data-testid="stBaseButton-primary"]:hover {
  filter:brightness(1.05); box-shadow:0 8px 22px rgba(255,107,74,.42) !important;
}
.stButton button:focus-visible, .stDownloadButton button:focus-visible {
  outline:2px solid var(--primary); outline-offset:2px;
}
.st-key-btn_delete button,
.st-key-btn_delete_exp button,
.st-key-btn_delete_inc button {
  color:var(--expense) !important; border-color:#F5B7A8 !important; background:#FFF6F3 !important;
}
.st-key-btn_delete button p,
.st-key-btn_delete_exp button p,
.st-key-btn_delete_inc button p { color:var(--expense) !important; }
.st-key-btn_delete button:hover,
.st-key-btn_delete_exp button:hover,
.st-key-btn_delete_inc button:hover { background:var(--expense-soft) !important; }

/* ---------- 表單與卡片容器 ---------- */
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
  border-radius:var(--r-sm) !important;
  background:#FFFBF8 !important; color:var(--ink) !important;
}
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
  border-radius:var(--r-sm) !important;
  background:#FFFBF8 !important; border-color:var(--line) !important;
}
div[data-baseweb="select"] span, div[data-baseweb="select"] div { color:var(--ink) !important; }
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
  border-color:var(--primary) !important;
  box-shadow:0 0 0 3px var(--primary-soft) !important;
}
.stApp label p { font-size:.85rem; font-weight:600; color:var(--ink-muted) !important; }
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius:var(--r-lg) !important;
  background:var(--card) !important;
  border:1.5px solid var(--line) !important;
  box-shadow:var(--shadow-card) !important;
}

/* ---------- 分頁籤 ---------- */
.stTabs [data-baseweb="tab-list"] { gap:6px; border-bottom:1.5px solid var(--line); }
.stTabs [data-baseweb="tab"] {
  height:42px; padding:0 14px; border-radius:14px 14px 0 0;
  font-weight:600; color:var(--ink-muted) !important;
}
.stTabs [aria-selected="true"] { color:var(--primary) !important; font-weight:700; }
.stTabs [data-baseweb="tab-highlight"] { background:var(--primary) !important; height:3.5px; border-radius:999px; }

/* ---------- 主導覽（馬卡龍膠囊列） ---------- */
.st-key-view_mode { margin:10px 0 20px; }
.st-key-view_mode button {
  min-height:44px; font-weight:600; border-radius:999px !important;
  background:var(--card) !important; color:var(--ink-muted) !important;
  border:1.5px solid var(--line) !important;
}
.st-key-view_mode button[aria-pressed="true"],
.st-key-view_mode button[kind="segmented_controlActive"] {
  background:var(--primary) !important; color:#fff !important;
  border-color:var(--primary) !important;
  box-shadow:0 4px 14px rgba(255,122,89,.32) !important;
}
.st-key-view_mode button[aria-pressed="true"] p,
.st-key-view_mode button[kind="segmented_controlActive"] p { color:#fff !important; }

/* ---------- 內建 metric 卡 ---------- */
div[data-testid="stMetric"] {
  background:var(--card); border:1.5px solid var(--line); border-radius:var(--r-md);
  padding:14px 16px; box-shadow:var(--shadow-card); font-variant-numeric:tabular-nums;
}
div[data-testid="stMetricLabel"] p { font-size:.8rem; color:var(--ink-muted) !important; }
div[data-testid="stMetricValue"] { font-weight:700; color:var(--ink) !important; font-variant-numeric:tabular-nums; }

/* ---------- 提示框、進度條、表格 ---------- */
div[data-testid="stAlert"] { border-radius:var(--r-md); border:1.5px solid var(--line); }
div[data-testid="stProgress"] > div > div { border-radius:999px; background:var(--primary) !important; }
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
  border:1.5px solid var(--line); border-radius:var(--r-md); overflow:hidden;
  box-shadow:var(--shadow-card);
}
div[data-testid="stExpander"] {
  border-radius:var(--r-md); border:1.5px solid var(--line);
  background:var(--card); box-shadow:0 3px 12px rgba(176,140,122,.07);
}

/* ---------- Bento 拼圖總覽卡 ---------- */
.bento-hero {
  display:grid; grid-template-columns:1.35fr 1fr; gap:12px;
  margin:14px 0 12px; font-variant-numeric:tabular-nums;
}
.bento-main {
  background:var(--income-soft); color:#164E3B;
  border-radius:var(--r-lg); padding:20px 22px;
  display:flex; flex-direction:column; justify-content:space-between; gap:12px;
  box-shadow:0 6px 20px rgba(24,134,91,.10);
}
.bento-main.is-neg {
  background:#FFDCD4; color:#7A2315;
  box-shadow:0 6px 20px rgba(217,78,52,.12);
}
.bento-main-top { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
.bento-label { font-size:.82rem; font-weight:600; opacity:.78; }
.bento-net { font-size:2.35rem; font-weight:800; line-height:1.12; margin:4px 0 2px; letter-spacing:-.02em; }
.bento-side { display:flex; flex-direction:column; gap:12px; }
.bento-inc {
  background:var(--warning-soft); color:#6B4A06;
  border-radius:22px; padding:14px 18px; flex:1;
  display:flex; flex-direction:column; justify-content:center;
}
.bento-exp {
  background:var(--expense-soft); color:#7A2E1B;
  border-radius:22px; padding:14px 18px; flex:1;
  display:flex; flex-direction:column; justify-content:center;
}
.bento-sub-v { font-size:1.35rem; font-weight:800; line-height:1.2; margin:2px 0 4px; }
.bento-delta { font-size:.78rem; font-weight:600; display:flex; align-items:center; gap:6px; flex-wrap:wrap; }
.bento-delta .mut { opacity:.72; }
.pos { color:var(--income); } .neg { color:var(--expense); }
.pill { display:inline-block; padding:2px 9px; border-radius:999px; font-weight:700; font-size:.76rem; }
.pill.pos { background:rgba(24,134,91,.14); color:#146C49; }
.pill.neg { background:rgba(217,78,52,.15); color:#B53A24; }
.pill.zero { background:rgba(45,42,50,.08); color:inherit; opacity:.75; }

/* ---------- 圓形分類徽章 ---------- */
.cat-badge {
  width:34px; height:34px; border-radius:999px;
  display:inline-flex; align-items:center; justify-content:center;
  font-size:1rem; flex-shrink:0;
}

/* ---------- 預算與分期進度卡 ---------- */
.bud {
  background:var(--card); border:1.5px solid var(--line); border-radius:var(--r-md);
  padding:15px 18px; margin-bottom:12px; font-variant-numeric:tabular-nums;
  box-shadow:var(--shadow-card);
  transition:transform .16s var(--ease), box-shadow .16s var(--ease);
}
.bud:hover { transform:translateY(-1px); box-shadow:var(--shadow-lift); }
.bud-top { display:flex; justify-content:space-between; align-items:center; gap:10px; font-size:.95rem; }
.bud-title { display:flex; align-items:center; gap:10px; min-width:0; }
.bud-sub { color:var(--ink-muted); font-size:.82rem; margin:6px 0 10px; }
.bud-bar { height:10px; border-radius:999px; background:var(--track); overflow:hidden; }
.bud-bar > i { display:block; height:100%; border-radius:999px; animation:grow .7s var(--ease) both; transform-origin:left; }
.bud-ok > i   { background:linear-gradient(90deg,#2AB57D,#18865B); }
.bud-warn > i { background:linear-gradient(90deg,#FFBE42,#E59A14); }
.bud-over > i { background:linear-gradient(90deg,#FF7A59,#D94E34); }
.bud-inst > i { background:linear-gradient(90deg,#6BB1F8,#3B82F6); }
.t-ok { background:var(--income-soft); color:#146C49; padding:2px 10px; border-radius:999px; font-weight:700; font-size:.8rem; }
.t-warn { background:var(--warning-soft); color:#8A5A00; padding:2px 10px; border-radius:999px; font-weight:700; font-size:.8rem; }
.t-over { background:var(--expense-soft); color:#B53A24; padding:2px 10px; border-radius:999px; font-weight:700; font-size:.8rem; }
.t-inst { background:var(--sky-soft); color:var(--sky-ink); padding:2px 10px; border-radius:999px; font-weight:700; font-size:.8rem; white-space:nowrap; }
@keyframes grow { from { transform:scaleX(0); } to { transform:scaleX(1); } }

/* ---------- 月曆 ---------- */
.cal-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px; }
.cal-card {
  background:var(--card); border:1.5px solid var(--line); border-radius:16px;
  padding:8px 10px; height:132px; overflow:hidden; margin-bottom:8px;
  box-shadow:0 3px 10px rgba(176,140,122,.07);
  transition:transform .15s var(--ease), box-shadow .15s var(--ease);
}
.cal-grid .cal-card { margin-bottom:0; }
.cal-card:hover { transform:translateY(-1px); box-shadow:var(--shadow-card); }
.cal-card.empty { opacity:.35; background:transparent; border-style:dashed; box-shadow:none; }
.cal-card.today {
  border-color:var(--primary); background:#FFF6F2;
  box-shadow:0 0 0 2px var(--primary-soft), var(--shadow-card);
}
.cal-day-header {
  font-size:.8rem; font-weight:700; border-bottom:1px solid var(--line);
  padding-bottom:4px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;
}
.cal-card.today .cal-day-header > span:first-child {
  background:var(--primary); color:#fff; border-radius:999px; padding:0 8px; min-width:22px; text-align:center;
}
.cal-day-total { font-size:.75rem; font-weight:700; font-variant-numeric:tabular-nums; }
.cal-amt { font-size:.8rem; font-weight:700; font-variant-numeric:tabular-nums; }
.cal-item { margin-bottom:6px; }
.cal-note { font-size:.75rem; color:var(--ink-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:block; }
.cal-wd { text-align:center; font-weight:700; color:var(--ink-muted); font-size:.85rem; padding:4px 0; }

/* ---------- 今日已記帳小清單 ---------- */
.recent-box {
  background:var(--card); border:1.5px solid var(--line); border-radius:var(--r-lg);
  padding:16px 18px; margin-top:14px; font-variant-numeric:tabular-nums;
  box-shadow:var(--shadow-card);
}
.recent-head { font-size:.82rem; font-weight:700; color:var(--ink-muted); margin-bottom:8px; letter-spacing:.03em; }
.recent-row {
  display:flex; justify-content:space-between; align-items:center; gap:10px;
  padding:8px 0; border-top:1px solid var(--line); font-size:.9rem;
}
.recent-l { display:flex; align-items:center; gap:10px; min-width:0; }
.recent-txt { display:flex; flex-direction:column; min-width:0; line-height:1.3; }
.recent-txt b { color:var(--ink); font-size:.9rem; }
.recent-note { color:var(--ink-muted); font-size:.78rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.recent-r { font-weight:800; white-space:nowrap; font-size:.95rem; }
.recent-more { font-size:.78rem; color:var(--ink-muted); margin-top:8px; padding-top:8px; border-top:1.5px dashed var(--line); }

/* ---------- 登入頁 ---------- */
div[data-testid="stHeading"] h1 { text-align:center; font-weight:800; margin-top:8vh; color:var(--ink) !important; }

@media (max-width:640px) {
  div.block-container, div[data-testid="stMainBlockContainer"] { padding:3.1rem .85rem 3rem; }
  .stTabs [data-baseweb="tab"] { padding:0 10px; font-size:.9rem; }
  .bento-hero { grid-template-columns:1fr; gap:10px; }
  .bento-side { flex-direction:row; gap:10px; }
  .bento-main { padding:16px 18px; border-radius:22px; }
  .bento-net { font-size:1.95rem; }
  .bento-inc, .bento-exp { padding:12px 14px; border-radius:18px; }
  .bento-sub-v { font-size:1.1rem; }
  .cal-grid { gap:4px; }
  .cal-card { height:96px; padding:6px; border-radius:12px; }
  .cal-amt, .cal-day-total, .cal-note { font-size:.65rem; }
}

@media (min-width:900px) {
  html { font-size:18px; }
  div.block-container, div[data-testid="stMainBlockContainer"] { max-width:1180px; padding:4rem 1.5rem 4rem; }
  .cal-card { height:150px; }
  .bento-label, .bento-delta, .bud-sub, .cal-day-total, .cal-note { font-size:.88rem; }
  .app-header h1 { font-size:1.7rem; }
  .bento-net { font-size:2.65rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition:none !important; animation:none !important; }
}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def theme_show(fig, stretch):
    y_title = ""
    try:
        y_title = fig.layout.yaxis.title.text or ""
    except Exception:
        y_title = ""

    has_y_label = y_title in ("金額", "總金額")
    fig.update_layout(
        margin=dict(l=72 if has_y_label else 10, r=14, t=50, b=10),
        title=dict(font=dict(size=15, color="#2D2A32"), x=0, xanchor="left"),
        legend=dict(title_text="", orientation="h", y=-0.25, x=0, font=dict(color="#5C535A")),
        paper_bgcolor="rgba(255,255,255,0.88)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="PingFang TC, Microsoft JhengHei, Noto Sans TC, sans-serif", size=12, color="#2D2A32"),
        hoverlabel=dict(font_size=12, bgcolor="#FFFFFF", bordercolor="#EFE4DC", font_color="#2D2A32"),
    )
    fig.update_xaxes(title_text="", showgrid=False, linecolor="#E6D8CE", tickfont=dict(color="#6D636A"))
    fig.update_yaxes(title_text="", gridcolor="#F2E7DF", zeroline=False, tickfont=dict(color="#6D636A"))

    if has_y_label:
        fig.add_annotation(
            text="<br>".join(list(y_title)),
            xref="paper", yref="paper",
            x=0, y=0.5,
            xanchor="right", yanchor="middle",
            xshift=-48,
            textangle=0,
            showarrow=False,
            font=dict(size=12, color="#7E747B"),
        )

    st.plotly_chart(fig, theme=None, **stretch)


def money(n):
    return f"-${abs(n):,.0f}" if n < 0 else f"${n:,.0f}"


def _delta(v, invert=False):
    if round(v) == 0:
        return "<span class='pill zero'>±0</span>"
    good = (v <= 0) if invert else (v >= 0)
    sign = "+" if v > 0 else "-"
    return f"<span class='pill {'pos' if good else 'neg'}'>{sign}{abs(v):,.0f}</span>"


def _saving_ring_svg(rate, is_neg=False):
    pct = max(0.0, min(float(rate), 1.0))
    circ = 2 * 3.14159 * 20
    dash = pct * circ
    track_col = "rgba(122,35,21,0.16)" if is_neg else "rgba(22,78,59,0.16)"
    stroke_col = "#D94E34" if is_neg else "#18865B"
    text_col = "#7A2315" if is_neg else "#164E3B"
    label = f"{max(rate, 0):.0%}"
    return (
        f"<svg width='56' height='56' viewBox='0 0 52 52' style='flex-shrink:0;' aria-label='儲蓄率 {label}'>"
        f"<circle cx='26' cy='26' r='20' fill='none' stroke='{track_col}' stroke-width='5.5'/>"
        f"<circle cx='26' cy='26' r='20' fill='none' stroke='{stroke_col}' stroke-width='5.5' "
        f"stroke-linecap='round' stroke-dasharray='{dash:.1f} {circ:.1f}' transform='rotate(-90 26 26)'/>"
        f"<text x='26' y='30' text-anchor='middle' font-size='11' font-weight='800' fill='{text_col}'>{label}</text>"
        f"</svg>"
    )


def summary_card(period_label, income, expense, net, d_inc=None, d_exp=None, d_net=None, rate=None, sub_label="本月存下", compare_label="較上月"):
    is_neg = net < 0
    ring_html = _saving_ring_svg(rate, is_neg=is_neg) if rate is not None else ""
    delta_top = f"<div class='bento-delta'><span class='mut'>{compare_label}</span> {_delta(d_net)}</div>" if d_net is not None else ""
    delta_inc_html = f"<div class='bento-delta'>{_delta(d_inc)}</div>" if d_inc is not None else ""
    delta_exp_html = f"<div class='bento-delta'>{_delta(d_exp, invert=True)}</div>" if d_exp is not None else ""
    st.markdown(
        f"<div class='bento-hero'>"
        f"  <div class='bento-main{' is-neg' if is_neg else ''}'>"
        f"    <div class='bento-main-top'>"
        f"      <div>"
        f"        <div class='bento-label'>{html.escape(str(period_label))} {html.escape(str(sub_label))}</div>"
        f"        <div class='bento-net'>{money(net)}</div>"
        f"      </div>"
        f"      {ring_html}"
        f"    </div>"
        f"    {delta_top}"
        f"  </div>"
        f"  <div class='bento-side'>"
        f"    <div class='bento-inc'>"
        f"      <div class='bento-label'>總收入</div>"
        f"      <div class='bento-sub-v'>{money(income)}</div>"
        f"      {delta_inc_html}"
        f"    </div>"
        f"    <div class='bento-exp'>"
        f"      <div class='bento-label'>總支出</div>"
        f"      <div class='bento-sub-v'>{money(expense)}</div>"
        f"      {delta_exp_html}"
        f"    </div>"
        f"  </div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def budget_card(name, spent, limit):
    ratio = spent / limit if limit > 0 else 0
    status = "over" if ratio >= 1 else ("warn" if ratio >= 0.8 else "ok")
    left = limit - spent
    left_txt = f"剩餘 ${left:,.0f}" if left >= 0 else f"超支 ${-left:,.0f}"
    st.markdown(
        f"<div class='bud'>"
        f"<div class='bud-top'><span class='bud-title'>{cat_badge_html(name)}<b>{html.escape(str(name))}</b></span>"
        f"<span class='t-{status}'>{ratio:.0%}</span></div>"
        f"<div class='bud-sub'>${spent:,.0f} / ${limit:,.0f} · {left_txt}</div>"
        f"<div class='bud-bar bud-{status}'><i style='width:{min(ratio, 1) * 100:.1f}%'></i></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def installment_card(title, paid_cnt, total_cnt, per_amt, remain_amt, end_ym):
    ratio = paid_cnt / total_cnt if total_cnt > 0 else 0
    rem_cnt = max(0, total_cnt - paid_cnt)
    st.markdown(
        f"<div class='bud'>"
        f"<div class='bud-top'><span class='bud-title'>{cat_badge_html('分期', '💳', '#E2F0FF')}<b>{html.escape(str(title))}</b></span>"
        f"<span class='t-inst'>已繳 {paid_cnt}/{total_cnt} 期（剩 {rem_cnt} 期）</span></div>"
        f"<div class='bud-sub'>每期 ${per_amt:,.0f} · 未清償餘額 ${remain_amt:,.0f} · 預計 {end_ym} 繳清</div>"
        f"<div class='bud-bar bud-inst'><i style='width:{min(ratio, 1) * 100:.1f}%'></i></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ======================= 基本設定 =======================
st.set_page_config(page_title="我是有錢人", page_icon="💰", layout="wide")


def get_secret(name, default=""):
    for k in (name, name.lower(), name.upper()):
        if k in st.secrets:
            return st.secrets[k]
    return default


SPREADSHEET_URL = str(get_secret("SPREADSHEET_URL", "")).strip()
TW_TZ = timezone(timedelta(hours=8))


def today():
    return datetime.now(TW_TZ).date()


TODAY = today()


def load_px():
    import plotly.express as px_
    px_.defaults.color_discrete_sequence = PALETTE
    return px_


PAY_OPTIONS = ["現金", "信用卡", "行動支付"]
DEFAULT_EXPENSE_CATS = [
    "伙食", "飲料", "交通", "日用", "購物", "娛樂", "居家",
    "醫療", "學習", "社交", "保險", "其他支出", "每月固定費用",
]
DEFAULT_INCOME_CATS = ["薪資", "獎金", "投資", "副業", "回饋", "其他收入"]
EXPENSE_CATS = list(DEFAULT_EXPENSE_CATS)
INCOME_CATS = list(DEFAULT_INCOME_CATS)
FIELDS = ["日期", "類型", "分類", "金額", "付款方式", "備註"]
SETTINGS_HEADER = ["項目名稱", "預設金額", "付款方式", "扣款日"]
BUDGET_HEADER = ["分類", "每月上限"]
CAT_HEADER = ["類型", "分類"]
RULE_HEADER = ["關鍵字", "分類"]
CONFIG_HEADER = ["項目", "值"]
DEFAULT_AUTO_RULES = [
    ["7-11,統一超商,全家,萊爾富,麥當勞,肯德基,摩斯,便當,早餐,火鍋,拉麵,餐廳,Uber Eats,foodpanda", "伙食"],
    ["星巴克,路易莎,cama,50嵐,迷客夏,清心,麻古,咖啡,手搖,飲料", "飲料"],
    ["中油,台塑石油,加油,高鐵,台鐵,捷運,Uber,悠遊卡,停車,eTag,Gogoro", "交通"],
    ["全聯,家樂福,好市多,大潤發,美廉社,寶雅,屈臣氏,康是美", "日用"],
    ["蝦皮,momo,PChome,酷澎,UNIQLO,NET,IKEA,百貨,新光三越,SOGO", "購物"],
    ["電影,威秀,秀泰,國賓,Netflix,Spotify,Steam,KTV,錢櫃", "娛樂"],
    ["藥局,診所,醫院,牙醫,眼科,掛號", "醫療"],
    ["誠品,博客來,課程,書籍", "學習"],
]
CFG_SALARY = "預設月薪"
CFG_GOAL = "儲蓄目標"
CFG_CAT_VER = "預設分類版本"
CURRENT_CAT_VER = "v2"
WEEKDAY_NAMES = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
TOTAL_KEY = "總預算"
CACHE_TTL = 60
CACHE_TTL_CFG = 600

MODE_ADD = "記帳"
MODE_LIST = "明細"
MODE_CHART = "圖表"
MODE_BUDGET = "預算"
MODE_CAL = "月曆"


def sort_expense_cats(cats):
    seen = set()
    clean_cats = []
    for c in cats:
        s = str(c).strip()
        if s and s not in seen:
            seen.add(s)
            clean_cats.append(s)
    two_char = [c for c in clean_cats if len(c) == 2 and c not in ("其他支出", "每月固定費用")]
    others_mid = [c for c in clean_cats if len(c) != 2 and c not in ("其他支出", "每月固定費用")]
    tail = []
    if "其他支出" in clean_cats:
        tail.append("其他支出")
    if "每月固定費用" in clean_cats:
        tail.append("每月固定費用")
    return two_char + others_mid + tail


def _ver_tuple():
    parts = []
    for p in st.__version__.split(".")[:2]:
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


STRETCH = {"width": "stretch"} if _ver_tuple() >= (1, 50) else {"use_container_width": True}
inject_css()


def show(fig):
    theme_show(fig, STRETCH)


HEADER_HTML = (
    "<div class='app-header'>"
    "<div class='app-logo'>💰</div>"
    "<div><h1>我是有錢人</h1>"
    "<p>一天一塊錢，七天就有七塊錢</p></div>"
    "</div>"
)


# ======================= Google 帳號登入 =======================
def parse_allowed(v):
    if isinstance(v, str):
        items = v.replace("\n", ",").split(",")
    else:
        try:
            items = list(v)
        except TypeError:
            items = []
    return {str(x).strip().lower() for x in items if str(x).strip()}


def require_login():
    if not hasattr(st, "login"):
        st.error("目前的 Streamlit 版本太舊，Google 登入需要 1.42 以上。請把 requirements.txt 改成 streamlit>=1.42 並加上 Authlib>=1.3.2。")
        st.stop()

    if "auth" not in st.secrets:
        st.error("尚未設定 Google 登入。請到 Streamlit Secrets 加入 [auth] 區塊。")
        st.stop()

    redir = str(st.secrets["auth"].get("redirect_uri", "")).strip()
    if not redir.endswith("/oauth2callback"):
        st.error(f"Secrets 中的 redirect_uri 格式錯誤（目前為：{redir}），結尾必須是 /oauth2callback 且不可有斜線。")
        st.stop()

    allowed = parse_allowed(get_secret("ALLOWED_EMAILS", ""))
    if not allowed:
        st.error("尚未設定 ALLOWED_EMAILS。請到 Streamlit Secrets 加入：ALLOWED_EMAILS = [\"你的信箱@gmail.com\"]")
        st.stop()

    if not st.user.is_logged_in:
        st.title("我是有錢人")
        _, mid, _ = st.columns([1, 1, 1])
        with mid:
            st.caption("請使用 Google 帳號登入")
            st.button("使用 Google 帳號登入", type="primary", on_click=st.login, **STRETCH)
        st.stop()

    email = str(st.user.get("email", "") or "").strip().lower()
    verified = st.user.get("email_verified", True)
    if email not in allowed or verified is False:
        st.title("我是有錢人")
        st.error(f"此帳號（{email or '未知'}）沒有使用權限。")
        _, mid, _ = st.columns([1, 1, 1])
        mid.button("改用其他帳號登入", on_click=st.logout, **STRETCH)
        st.stop()


require_login()

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"), icon=":material/check_circle:")
if "editor_ver" not in st.session_state:
    st.session_state.editor_ver = 0


# ======================= 工具函數 =======================
BANK_KEYWORDS = [
    ("富邦", "富邦信用卡"),
    ("國泰", "國泰信用卡"),
    ("聯邦", "聯邦信用卡"),
    ("第一", "第一銀行信用卡"),
    ("安泰", "安泰信用卡"),
    ("連線", "LINE Bank信用卡"),
    ("LINE Bank", "LINE Bank信用卡"),
    ("台新", "台新信用卡"),
    ("玉山", "玉山信用卡"),
    ("中信", "中信信用卡"),
    ("永豐", "永豐信用卡"),
    ("星展", "星展信用卡"),
]
TASKER_VAR_RE = re.compile(r"\s*%[a-zA-Z_][a-zA-Z0-9_]*")
AUTO_CARD_RE = re.compile(r"^\[自動\]\s*(?:(.+?)\s*)?信用卡消費\s*([0-9,.]+)\s*元通知.*$")
INSTALLMENT_RE = re.compile(r"^(.+?)\s*\((\d+)/(\d+)期\)$")


def clean_note_text(s, amt_str=""):
    txt = TASKER_VAR_RE.sub("", str(s or "")).strip()
    m = AUTO_CARD_RE.match(txt)
    if m:
        prefix = (m.group(1) or "").strip()
        amount_val = m.group(2) or str(amt_str).strip()
        search_pool = f"{prefix} {txt}".lower()
        card_label = next(
            (label for kw, label in BANK_KEYWORDS if kw.lower() in search_pool),
            f"{prefix}信用卡" if prefix else "信用卡",
        )
        return f"{card_label}刷 {amount_val} 元"
    return re.sub(r"\s{2,}", " ", txt).strip()


def add_months(base_date, offset):
    total_m = base_date.year * 12 + (base_date.month - 1) + offset
    y, m = divmod(total_m, 12)
    m += 1
    last_day = py_calendar.monthrange(y, m)[1]
    return date(y, m, min(base_date.day, last_day))


def shift_ym(ym, offset):
    y, m = map(int, ym.split("-"))
    total_m = y * 12 + (m - 1) + offset
    ny, nm = divmod(total_m, 12)
    return f"{ny}-{nm + 1:02d}"


def split_installments(total_amt, months):
    total_int = int(round(total_amt))
    base = total_int // months
    rem = total_int % months
    return [base + (1 if i < rem else 0) for i in range(months)]


def analyze_installments(df_all, ref_ym):
    if df_all.empty:
        return [], {}
    exp = df_all[df_all["類型"] == "支出"]
    groups = {}
    future_by_month = {}

    for _, r in exp.iterrows():
        m = INSTALLMENT_RE.match(str(r["備註"]).strip())
        if not m:
            continue
        ym = str(r["年月"])
        if not re.fullmatch(r"\d{4}-\d{2}", ym):
            continue
        base_name = m.group(1).strip()
        cur_idx = int(m.group(2))
        tot_cnt = int(m.group(3))
        amt = float(r["金額_num"])
        start_ym = shift_ym(ym, -(cur_idx - 1))

        if ym > ref_ym:
            future_by_month[ym] = future_by_month.get(ym, 0.0) + amt

        key = (base_name, tot_cnt, r["分類"], start_ym)
        g = groups.setdefault(key, {
            "title": base_name,
            "total_cnt": tot_cnt,
            "paid_cnt": 0,
            "remain_amt": 0.0,
            "per_amt": amt,
            "end_ym": ym,
        })
        if ym <= ref_ym:
            g["paid_cnt"] += 1
        else:
            g["remain_amt"] += amt
        if ym > g["end_ym"]:
            g["end_ym"] = ym

    active_list = [g for g in groups.values() if g["remain_amt"] > 0 or g["paid_cnt"] < g["total_cnt"]]
    active_list.sort(key=lambda x: x["end_ym"])
    return active_list, dict(sorted(future_by_month.items()))


def pad_row(row, n=6):
    return list(row[:n]) + [""] * max(0, n - len(row))


def to_number(v):
    s = str(v).strip().replace(",", "").replace("$", "").replace("NT", "").strip()
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return str(v).strip()


def flash_and_rerun(msg):
    """在 @st.fragment 內外都能強制整頁刷新，確保頂部總覽卡、預算警示與 toast 同步更新。"""
    st.session_state["flash"] = msg
    try:
        st.rerun(scope="app")
    except TypeError:
        st.rerun()


def safe_load(fn, arg, default, label):
    try:
        return fn(arg)
    except Exception as e:
        st.warning(f"讀取「{label}」失敗：{e}（可按「重新整理」重試）")
        return default


def prev_month_str(ym):
    y, m = map(int, ym.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def md_escape(s):
    return re.sub(r"([\\`*_{}\[\]()#+\-!|~$<>])", r"\\\1", str(s))


def sums(d):
    if d.empty:
        return 0.0, 0.0
    return (
        d.loc[d["類型"] == "收入", "金額_num"].sum(),
        d.loc[d["類型"] == "支出", "金額_num"].sum(),
    )


# ======================= 連線 Google 試算表 =======================
@st.cache_resource
def get_google_sheet():
    if not SPREADSHEET_URL:
        raise ValueError("尚未設定 SPREADSHEET_URL，請到 Streamlit Secrets 加入：SPREADSHEET_URL = \"你的試算表網址\"")
    info = dict(st.secrets["gcp_service_account"])
    info["private_key"] = info["private_key"].replace("\\n", "\n")
    info.setdefault("universe_domain", "googleapis.com")
    gc = gspread.service_account_from_dict(info)
    return gc.open_by_url(SPREADSHEET_URL)


try:
    sh = get_google_sheet()
except Exception as e:
    sh = None
    st.error(f"連線 Google 試算表失敗：{e}")


@st.cache_resource
def get_sheet_map(_sh):
    return {w.title: w for w in _sh.worksheets()}


@st.cache_resource
def get_main_ws(_sh):
    return next(iter(get_sheet_map(_sh).values()))


worksheet = get_main_ws(sh) if sh else None


def get_ws(title, rows, cols, init_rows):
    if not sh:
        return None
    try:
        m = get_sheet_map(sh)
        if title in m:
            return m[title]
        ws = sh.add_worksheet(title=title, rows=rows, cols=cols)
        ws.append_rows(init_rows)
        get_sheet_map.clear()
        return ws
    except Exception as e:
        st.warning(f"無法取得「{title}」分頁：{e}")
        return None


settings_ws = get_ws(
    "固定支出設定", 100, 4,
    [SETTINGS_HEADER, ["孝親費", "5000", "現金", "5"], ["電信費", "599", "信用卡", "10"]],
)
budget_ws = get_ws("預算設定", 50, 2, [BUDGET_HEADER, [TOTAL_KEY, 30000], ["伙食", 8000]])
cat_ws = get_ws(
    "分類設定", 100, 2,
    [CAT_HEADER] + [["支出", c] for c in EXPENSE_CATS] + [["收入", c] for c in INCOME_CATS],
)
config_ws = get_ws("系統設定", 20, 2, [CONFIG_HEADER, [CFG_SALARY, 45000], [CFG_GOAL, 0]])
rule_ws = get_ws("自動分類規則", 100, 2, [RULE_HEADER] + DEFAULT_AUTO_RULES)

CFG_SHEETS = (
    ("固定支出設定", 4),
    ("預算設定", 2),
    ("分類設定", 2),
    ("系統設定", 2),
    ("自動分類規則", 2),
)


@st.cache_data(ttl=CACHE_TTL_CFG)
def fetch_config_bundle(_sh):
    ranges = [f"'{t}'!A:Z" for t, _ in CFG_SHEETS]
    try:
        value_ranges = [vr.get("values", []) for vr in _sh.values_batch_get(ranges).get("valueRanges", [])]
    except AttributeError:
        value_ranges = [_sh.worksheet(t).get_all_values() for t, _ in CFG_SHEETS]
    out = {}
    for (title, n), values in zip(CFG_SHEETS, value_ranges):
        rows = [pad_row(r, n) for r in values[1:]]
        out[title] = [r for r in rows if str(r[0]).strip()]
    return out


_cfg_loaded = {}


def load_rows(ws, label):
    if not ws:
        return []
    if "data" not in _cfg_loaded:
        _cfg_loaded["data"] = safe_load(fetch_config_bundle, sh, {}, "設定分頁")
    return _cfg_loaded["data"].get(label, [])


def parse_day(v):
    try:
        d = int(float(str(v).strip()))
        return d if 1 <= d <= 31 else None
    except ValueError:
        return None


def build_templates(rows):
    templates = {}
    for r in rows:
        name = r[0].strip()
        if not name:
            continue
        try:
            amt = float(str(r[1]).strip().replace(",", "")) if str(r[1]).strip() else 0
        except ValueError:
            amt = 0
        pay = r[2].strip() if r[2].strip() else "現金"
        templates[name] = {"amount": amt, "pay": pay, "day": parse_day(r[3])}
    return templates


settings_rows = load_rows(settings_ws, "固定支出設定")
fixed_templates = build_templates(settings_rows)


# ======================= 預算設定 =======================
def build_budgets(rows):
    budgets = {}
    for name, val in rows:
        try:
            amt = float(str(val).strip().replace(",", ""))
        except ValueError:
            continue
        if amt > 0:
            budgets[str(name).strip()] = amt
    return budgets


budget_rows = load_rows(budget_ws, "預算設定")
budgets = build_budgets(budget_rows)


# ======================= 系統設定 =======================
config_rows = load_rows(config_ws, "系統設定")
config = {str(r[0]).strip(): r[1] for r in config_rows}


def cfg_num(key, default):
    v = to_number(config.get(key, default))
    return default if isinstance(v, str) else v


def cfg_str(key, default=""):
    return str(config.get(key, default) or "").strip()


def save_config(key, value):
    data = config_ws.get_all_values()
    for i, r in enumerate(data[1:], start=2):
        if r and str(r[0]).strip() == key:
            config_ws.update(range_name=f"B{i}", values=[[value]])
            break
    else:
        config_ws.append_row([key, value])
    fetch_config_bundle.clear()


# ======================= 分類設定 =======================
_cat_rows = load_rows(cat_ws, "分類設定")
_exp = [c.strip() for t, c in _cat_rows if t.strip() == "支出" and c.strip()]
_inc = [c.strip() for t, c in _cat_rows if t.strip() == "收入" and c.strip()]
if _exp:
    EXPENSE_CATS = _exp
if _inc:
    INCOME_CATS = _inc

_missing_cats = []
_need_v2_seed = cfg_str(CFG_CAT_VER, "") != CURRENT_CAT_VER

if _need_v2_seed:
    for c in DEFAULT_EXPENSE_CATS:
        if c not in EXPENSE_CATS:
            EXPENSE_CATS.append(c)
            _missing_cats.append(["支出", c])
    for c in DEFAULT_INCOME_CATS:
        if c not in INCOME_CATS:
            INCOME_CATS.append(c)
            _missing_cats.append(["收入", c])
else:
    for c in ("其他支出", "每月固定費用"):
        if c not in EXPENSE_CATS:
            EXPENSE_CATS.append(c)
            _missing_cats.append(["支出", c])
    if "薪資" not in INCOME_CATS:
        INCOME_CATS.append("薪資")
        _missing_cats.append(["收入", "薪資"])

EXPENSE_CATS = sort_expense_cats(EXPENSE_CATS)
ALL_CATS = list(dict.fromkeys(EXPENSE_CATS + INCOME_CATS))

if cat_ws and _cat_rows:
    if _missing_cats:
        try:
            cat_ws.append_rows(_missing_cats)
            fetch_config_bundle.clear()
        except Exception:
            pass
    if _need_v2_seed and config_ws:
        try:
            save_config(CFG_CAT_VER, CURRENT_CAT_VER)
            config[CFG_CAT_VER] = CURRENT_CAT_VER
        except Exception:
            pass


# ======================= 自動分類規則與信用卡帳單週期 =======================
def _split_keywords(raw):
    return [k.strip() for k in re.split(r"[,，、;/|]+", str(raw or "")) if k.strip()]


def build_auto_rules(rows):
    rules = []
    for r in rows:
        kws = _split_keywords(r[0])
        cat = str(r[1]).strip() if len(r) > 1 else ""
        if kws and cat:
            rules.append((kws, cat))
    return rules


def match_auto_category(note, rules, allowed_cats):
    low = str(note or "").strip().lower()
    if not low:
        return None
    for kws, cat in rules:
        if cat in allowed_cats and any(kw.lower() in low for kw in kws):
            return cat
    return None


rule_rows = load_rows(rule_ws, "自動分類規則")
auto_rules = build_auto_rules(rule_rows)


def render_budget_banner(df_month, total_spent, budgets, month_label):
    limit = budgets.get(TOTAL_KEY)
    if limit:
        ratio = total_spent / limit
        if ratio >= 1:
            st.error(f"已超出總預算 ${total_spent - limit:,.0f}！（${total_spent:,.0f} / ${limit:,.0f}）")
        elif ratio >= 0.8:
            st.warning(f"總預算已使用 {ratio:.0%}，本月只剩 ${limit - total_spent:,.0f}。")

    over = []
    exp = df_month[df_month["類型"] == "支出"]
    for cat, lim in budgets.items():
        if cat == TOTAL_KEY or lim <= 0:
            continue
        spent = exp.loc[exp["分類"] == cat, "金額_num"].sum()
        if spent >= lim:
            over.append(f"{cat}（${spent:,.0f} / ${lim:,.0f}）")
    if over:
        st.error("以下分類已超出預算：" + "、".join(over))


# ======================= 讀取記帳主表 =======================
DF_COLS = ["_row"] + FIELDS + ["_raw_note", "年月", "日期_std", "金額_num"]


@st.cache_data(ttl=CACHE_TTL)
def fetch_data(_sh):
    if not _sh:
        return pd.DataFrame(columns=DF_COLS)
    ws = get_main_ws(_sh)
    raw_data = ws.get_all_values()
    if len(raw_data) < 2:
        return pd.DataFrame(columns=DF_COLS)

    rows = []
    for r_idx, row in enumerate(raw_data[1:]):
        p = pad_row(row)
        if not any(str(c).strip() for c in p):
            continue
        rec = {"_row": r_idx + 2}
        for name, val in zip(FIELDS, p):
            rec[name] = str(val).strip()
        rec["_raw_note"] = rec["備註"]
        rec["備註"] = clean_note_text(rec["備註"], rec["金額"])
        rows.append(rec)

    df_t = pd.DataFrame(rows)
    if df_t.empty:
        return pd.DataFrame(columns=DF_COLS)

    clean = df_t["日期"].str.replace("/", "-", regex=False)
    parsed = pd.to_datetime(clean, errors="coerce")
    df_t["年月"] = parsed.dt.strftime("%Y-%m")
    df_t["日期_std"] = parsed.dt.strftime("%Y-%m-%d")
    bad = df_t["年月"].isna()
    if bad.any():
        df_t.loc[bad, "年月"] = clean[bad].str.slice(0, 7)
        df_t.loc[bad, "日期_std"] = clean[bad]
    df_t["金額_num"] = pd.to_numeric(
        df_t["金額"].str.replace(",", "", regex=False), errors="coerce"
    ).fillna(0)
    return df_t


def bump_editor():
    st.session_state.editor_ver += 1


def clear_data_cache():
    fetch_data.clear()
    bump_editor()


def rows_still_match(ws, df_rows):
    if df_rows.empty:
        return True
    ranges = [f"A{int(n)}:F{int(n)}" for n in df_rows["_row"]]
    got = ws.batch_get(ranges)
    for (_, r), vals in zip(df_rows.iterrows(), got):
        cloud = pad_row(vals[0] if vals else [])
        for i, col in enumerate(FIELDS):
            expected = str(r["_raw_note"]).strip() if col == "備註" else str(r[col]).strip()
            if str(cloud[i]).strip() != expected:
                return False
    return True


def delete_rows(ws, row_nos):
    nos = sorted({int(x) for x in row_nos}, reverse=True)
    requests = [{
        "deleteDimension": {
            "range": {
                "sheetId": ws.id,
                "dimension": "ROWS",
                "startIndex": n - 1,
                "endIndex": n,
            }
        }
    } for n in nos]
    sh.batch_update({"requests": requests})
    return len(nos)


def already_recorded(df_all, ym, cat, note=None):
    if df_all.empty:
        return False
    m = (df_all["年月"] == ym) & (df_all["分類"] == cat)
    if note is not None:
        m &= df_all["備註"] == clean_note_text(note)
    return bool(m.any())


def pending_fixed(df_all, templates, ref_date):
    ym = ref_date.strftime("%Y-%m")
    last = py_calendar.monthrange(ref_date.year, ref_date.month)[1]
    sub = df_all[(df_all["年月"] == ym) & (df_all["分類"] == "每月固定費用")]
    done = set(sub["備註"].str.strip()) if not sub.empty else set()
    out = []
    for name, t in templates.items():
        d = t.get("day")
        if not d or t["amount"] <= 0:
            continue
        due = min(d, last)
        if due <= ref_date.day and name not in done:
            out.append((name, t, date(ref_date.year, ref_date.month, due)))
    return out


def validate_row(r):
    errs = []

    d = str(r["日期"]).strip().replace("/", "-")
    date_ok = ""
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", d):
        parsed = pd.to_datetime(d, errors="coerce")
        if not pd.isna(parsed):
            date_ok = parsed.strftime("%Y-%m-%d")
    if not date_ok:
        errs.append("日期格式需為 YYYY-MM-DD（例如 2026-10-14）")

    typ = str(r["類型"]).strip()
    cat = str(r["分類"]).strip()
    if typ not in ("支出", "收入"):
        errs.append("類型必須是「支出」或「收入」")
    else:
        allowed = EXPENSE_CATS if typ == "支出" else INCOME_CATS
        if cat not in allowed:
            errs.append(f"「{typ}」的分類必須是：{'、'.join(allowed)}")

    amt = to_number(r["金額"])
    if isinstance(amt, str) or amt <= 0:
        errs.append("金額必須是大於 0 的純數字（不可含文字，例如「元」）")

    pay = str(r["付款方式"]).strip()
    if pay and pay not in PAY_OPTIONS:
        errs.append(f"付款方式必須是：{'、'.join(PAY_OPTIONS)}")

    return errs, [date_ok, typ, cat, amt, pay, clean_note_text(r["備註"], amt)]


# ======================= 主程式 =======================
if sh and worksheet:
    df = safe_load(fetch_data, sh, pd.DataFrame(columns=DF_COLS), "記帳資料")
    ver = st.session_state.editor_ver

    with st.container(key="topbar"):
        h1, h2, h3 = st.columns([8, 1.2, 1.2])
        h1.markdown(HEADER_HTML, unsafe_allow_html=True)
        if h2.button("", icon=":material/refresh:", help="重新整理", key="btn_refresh", **STRETCH):
            fetch_data.clear()
            fetch_config_bundle.clear()
            bump_editor()
            st.rerun()
        h3.button("", icon=":material/logout:", help="登出", key="btn_logout", on_click=st.logout, **STRETCH)

    if not df.empty:
        bad_rows = df[~df["年月"].fillna("").str.fullmatch(r"\d{4}-\d{2}")]
        if not bad_rows.empty:
            st.warning(
                f"有 {len(bad_rows)} 筆日期格式異常"
                f"（試算表第 {', '.join(map(str, bad_rows['_row']))} 列），不會出現在月份篩選中。"
            )

    current_month_str = TODAY.strftime("%Y-%m")
    db_months = [m for m in df["年月"].dropna().unique().tolist() if re.fullmatch(r"\d{4}-\d{2}", str(m))]
    all_months = sorted(set(db_months + [current_month_str]), reverse=True)

    if st.session_state.get("month_sel") not in all_months:
        st.session_state.month_sel = current_month_str

    def shift_month(step):
        i = all_months.index(st.session_state.month_sel) - step
        if 0 <= i < len(all_months):
            st.session_state.month_sel = all_months[i]

    def go_current_month():
        st.session_state.month_sel = current_month_str

    cur_m_idx = all_months.index(st.session_state.month_sel)
    is_not_current = st.session_state.month_sel != current_month_str

    with st.container(key="month_nav"):
        if is_not_current:
            nav1, nav2, nav3, nav4 = st.columns([1, 2.4, 1, 1.2])
        else:
            nav1, nav2, nav3 = st.columns([1, 3, 1])
            nav4 = None
        nav1.button(
            "", icon=":material/chevron_left:", help="上個月", key="btn_prev",
            on_click=shift_month, args=(-1,),
            disabled=(cur_m_idx >= len(all_months) - 1),
            **STRETCH,
        )
        nav2.selectbox("月份", all_months, key="month_sel", label_visibility="collapsed")
        nav3.button(
            "", icon=":material/chevron_right:", help="下個月", key="btn_next",
            on_click=shift_month, args=(1,),
            disabled=(cur_m_idx <= 0),
            **STRETCH,
        )
        if nav4 is not None:
            nav4.button("回本月", key="btn_back_today", on_click=go_current_month, **STRETCH)
    selected_month = st.session_state.month_sel

    df_selected = (
        df[df["年月"] == selected_month]
        .sort_values(["日期_std", "_row"], ascending=False)
        .reset_index(drop=True)
    )

    total_income, total_expense = sums(df_selected)
    prev_income, prev_expense = sums(df[df["年月"] == prev_month_str(selected_month)])
    net_balance = total_income - total_expense
    prev_net = prev_income - prev_expense

    summary_card(
        selected_month, total_income, total_expense, net_balance,
        total_income - prev_income, total_expense - prev_expense, net_balance - prev_net,
        rate=(net_balance / total_income if total_income > 0 else None),
    )

    render_budget_banner(df_selected, total_expense, budgets, selected_month)
    n_pend = len(pending_fixed(df, fixed_templates, TODAY))
    if n_pend:
        st.info(f"有 {n_pend} 筆固定支出已到扣款日、尚未記錄，請到「{MODE_ADD}」→「固定」補登。")

    MODES = [MODE_ADD, MODE_LIST, MODE_CHART, MODE_BUDGET, MODE_CAL]
    if st.session_state.get("view_mode") not in MODES:
        st.session_state.view_mode = st.session_state.get("_last_mode", MODE_ADD)
    view_mode = st.segmented_control(
        "選擇檢視模式",
        MODES,
        label_visibility="collapsed",
        key="view_mode",
        **STRETCH,
    )
    view_mode = view_mode or MODE_ADD
    st.session_state["_last_mode"] = view_mode

    # ---------- 記帳與設定 ----------
    if view_mode == MODE_ADD:
        tab_general, tab_salary, tab_fixed, tab_settings = st.tabs(
            ["記一筆", "薪資", "固定", "預算與設定"]
        )

        @st.fragment
        def add_entry_form():
            for wkey, lkey in (("gen_type", "_last_type"), ("gen_cat", "_last_cat"), ("gen_pay", "_last_pay")):
                if wkey not in st.session_state and lkey in st.session_state:
                    st.session_state[wkey] = st.session_state[lkey]
            with st.container(border=True):
                tx_type = st.radio("類型", ["支出", "收入"], horizontal=True, key="gen_type")
                cat_options = EXPENSE_CATS if tx_type == "支出" else INCOME_CATS
                if st.session_state.get("gen_cat") not in cat_options:
                    st.session_state.pop("gen_cat", None)

                c_cat, c_pay = st.columns(2)
                category = c_cat.selectbox("分類", cat_options, key="gen_cat")
                pay_method = c_pay.selectbox("付款方式", PAY_OPTIONS, key="gen_pay")
                st.session_state.update(_last_type=tx_type, _last_cat=category, _last_pay=pay_method)

                installments = 1
                if tx_type == "支出" and pay_method == "信用卡":
                    c_amt, c_date, c_inst = st.columns([2, 1.6, 1.4])
                    amount = c_amt.number_input("金額", value=None, step=1, min_value=0, placeholder="請輸入金額...", key=f"amt_{ver}")
                    installments = c_inst.number_input(
                        "分期（1=不分期）",
                        min_value=1, max_value=36, value=1, step=1,
                        key=f"inst_{ver}",
                    )
                    tx_date = c_date.date_input("首期日" if installments > 1 else "日期", value=TODAY)
                else:
                    c_amt, c_date = st.columns([1.4, 1])
                    amount = c_amt.number_input("金額", value=None, step=1, min_value=0, placeholder="請輸入金額...", key=f"amt_{ver}")
                    tx_date = c_date.date_input("日期", value=TODAY)

                note = st.text_input("備註 (例如：鮮天下、加油)", key=f"note_{ver}")

                clean_n = clean_note_text(note, amount or "")

                if installments > 1 and amount is not None and amount > 0:
                    parts = split_installments(amount, installments)
                    end_date = add_months(tx_date, installments - 1)
                    st.info(
                        f"分 **{installments} 期** 拆帳：首期 **${parts[0]:,}**"
                        + (f"，其餘每期 **${parts[1]:,}**" if len(set(parts)) > 1 else f"，每期 **${parts[0]:,}**")
                        + f"（{tx_date.strftime('%Y-%m')} ～ {end_date.strftime('%Y-%m')}）"
                    )

                gen_dup = False
                if installments == 1 and amount is not None and amount > 0 and not df.empty:
                    gen_dup = bool((
                        (df["日期_std"] == str(tx_date)) & (df["類型"] == tx_type) & (df["分類"] == category)
                        & (df["金額_num"] == float(amount)) & (df["備註"] == clean_n)
                    ).any())
                allow_gen_dup = True
                if gen_dup:
                    st.warning(f"{tx_date} 已有一筆完全相同的紀錄（分類、金額、備註都一樣）。")
                    allow_gen_dup = st.checkbox("我確定要再記一筆", key=f"allow_gen_dup_{ver}")

                btn_text = f"送出分期記帳（共 {installments} 期）" if installments > 1 else "送出記帳"
                if st.button(btn_text, type="primary", icon=":material/add:", **STRETCH):
                    if amount is not None and amount > 0 and not allow_gen_dup:
                        st.warning("已有相同紀錄，請先勾選「我確定要再記一筆」。")
                    elif amount is not None and amount > 0:
                        try:
                            if installments > 1:
                                parts = split_installments(amount, installments)
                                base_label = clean_n or f"{category}分期"
                                new_rows = [
                                    [
                                        str(add_months(tx_date, i)),
                                        tx_type,
                                        category,
                                        part_amt,
                                        pay_method,
                                        f"{base_label} ({i + 1}/{installments}期)",
                                    ]
                                    for i, part_amt in enumerate(parts)
                                ]
                                worksheet.append_rows(new_rows, value_input_option="RAW")
                                clear_data_cache()
                                flash_and_rerun(f"已建立 {installments} 期分期帳目（總額 ${int(amount):,}）！")
                            else:
                                worksheet.append_row(
                                    [str(tx_date), tx_type, category, amount, pay_method, clean_n],
                                    value_input_option="RAW",
                                )
                                clear_data_cache()
                                flash_and_rerun("一般記帳新增成功！")
                        except Exception as e:
                            st.error(f"寫入失敗: {e}")
                    else:
                        st.warning("請輸入有效的金額！")

        with tab_general:
            add_entry_form()
            if not df.empty:
                today_iso = TODAY.strftime("%Y-%m-%d")
                df_today = df[df["日期_std"] == today_iso].sort_values("_row", ascending=False)
                if not df_today.empty:
                    t_inc, t_exp = sums(df_today)
                    items_html = "".join(
                        f"<div class='recent-row'>"
                        f"<span class='recent-l'>{cat_badge_html(r['分類'])}"
                        f"<span class='recent-txt'><b>{html.escape(str(r['分類']))}</b>"
                        f"<span class='recent-note'>{html.escape(str(r['備註']))}</span></span></span>"
                        f"<span class='recent-r {'pos' if r['類型'] == '收入' else 'neg'}'>"
                        f"{'+' if r['類型'] == '收入' else '-'}${r['金額_num']:,.0f}</span>"
                        f"</div>"
                        for _, r in df_today.head(5).iterrows()
                    )
                    more_txt = f"<div class='recent-more'>今天共 {len(df_today)} 筆 · 支出 ${t_exp:,.0f}" + (f" · 收入 ${t_inc:,.0f}" if t_inc > 0 else "") + "</div>"
                    st.markdown(
                        f"<div class='recent-box'><div class='recent-head'>今日已記帳</div>{items_html}{more_txt}</div>",
                        unsafe_allow_html=True,
                    )

        with tab_salary:
            with st.container(border=True):
                default_salary = st.number_input(
                    "預設月薪金額", value=int(cfg_num(CFG_SALARY, 45000)), step=1000, key=f"salary_amt_{ver}"
                )
                if config_ws and st.button("記住為預設月薪"):
                    try:
                        save_config(CFG_SALARY, default_salary)
                        bump_editor()
                        flash_and_rerun("已更新預設月薪！")
                    except Exception as e:
                        st.error(f"儲存失敗: {e}")
                salary_date = st.date_input("入帳日期", value=TODAY, key="sal_date")

                salary_dup = already_recorded(df, salary_date.strftime("%Y-%m"), "薪資")
                allow_salary_dup = True
                if salary_dup:
                    st.warning(f"{salary_date.strftime('%Y-%m')} 已經有薪資紀錄了。")
                    allow_salary_dup = st.checkbox("我確定要再入帳一次", key=f"allow_sal_dup_{ver}")

                if st.button("入帳本月薪資", type="primary", **STRETCH):
                    if not allow_salary_dup:
                        st.warning("本月已有薪資紀錄，請先勾選「我確定要再入帳一次」。")
                    else:
                        try:
                            worksheet.append_row(
                                [str(salary_date), "收入", "薪資", default_salary, "現金", "每月固定薪資"],
                                value_input_option="RAW",
                            )
                            clear_data_cache()
                            flash_and_rerun(f"成功入帳薪資 ${default_salary:,}！")
                        except Exception as e:
                            st.error(f"薪資入帳失敗: {e}")

        with tab_fixed:
            pend = pending_fixed(df, fixed_templates, TODAY)
            if pend:
                lines = "\n".join(
                    f"- {n} ${t['amount']:,.0f}（{d.strftime('%m/%d')}）" for n, t, d in pend
                )
                st.info("本月已到期、尚未記錄的固定支出：\n" + lines)
                if st.button(f"一鍵補登 {len(pend)} 筆", type="primary", **STRETCH):
                    try:
                        worksheet.append_rows(
                            [
                                [str(d), "支出", "每月固定費用", to_number(t["amount"]), t["pay"], n]
                                for n, t, d in pend
                            ],
                            value_input_option="RAW",
                        )
                        clear_data_cache()
                        flash_and_rerun(f"已補登 {len(pend)} 筆固定支出！")
                    except Exception as e:
                        st.error(f"補登失敗: {e}")

            with st.container(border=True):
                st.markdown("**手動扣款**")
                if fixed_templates:
                    selected_template = st.selectbox("選擇常用固定支出範本", list(fixed_templates.keys()))
                    default_val = fixed_templates[selected_template]
                else:
                    selected_template = "無範本"
                    default_val = {"amount": 0, "pay": "現金"}

                expense_note = st.text_input("支出項目名稱", value=selected_template)
                default_expense = st.number_input("預設支出金額", value=int(default_val["amount"]), step=100)
                default_pay_idx = PAY_OPTIONS.index(default_val["pay"]) if default_val["pay"] in PAY_OPTIONS else 0
                expense_pay = st.selectbox("付款方式", PAY_OPTIONS, index=default_pay_idx, key="exp_pay")
                expense_date = st.date_input("扣款日期", value=TODAY, key="exp_date")

                fixed_dup = already_recorded(df, expense_date.strftime("%Y-%m"), "每月固定費用", expense_note)
                allow_fixed_dup = True
                if fixed_dup:
                    st.warning(f"{expense_date.strftime('%Y-%m')} 已經記錄過【{expense_note.strip()}】了。")
                    allow_fixed_dup = st.checkbox("我確定要再扣一次", key=f"allow_fix_dup_{ver}")

                fx1, fx2 = st.columns(2)
                with fx1:
                    if st.button("扣款這筆", type="primary", **STRETCH):
                        if not allow_fixed_dup:
                            st.warning("本月已有相同項目，請先勾選「我確定要再扣一次」。")
                        else:
                            try:
                                worksheet.append_row(
                                    [str(expense_date), "支出", "每月固定費用", default_expense, expense_pay, clean_note_text(expense_note)],
                                    value_input_option="RAW",
                                )
                                clear_data_cache()
                                flash_and_rerun(f"成功記錄固定支出【{expense_note}】${default_expense:,}！")
                            except Exception as e:
                                st.error(f"支出記錄失敗: {e}")

                with fx2:
                    if fixed_templates and st.button("本月全部入帳", **STRETCH):
                        ym = expense_date.strftime("%Y-%m")
                        done = set()
                        if not df.empty:
                            done = set(df.loc[(df["年月"] == ym) & (df["分類"] == "每月固定費用"), "備註"])
                        new_rows = [
                            [str(expense_date), "支出", "每月固定費用", to_number(t["amount"]), t["pay"], name]
                            for name, t in fixed_templates.items()
                            if name not in done and t["amount"] > 0
                        ]
                        if not new_rows:
                            st.info("本月固定支出都已經記錄過了。")
                        else:
                            try:
                                worksheet.append_rows(new_rows, value_input_option="RAW")
                                clear_data_cache()
                                flash_and_rerun(f"已入帳 {len(new_rows)} 筆固定支出！")
                            except Exception as e:
                                st.error(f"批次入帳失敗: {e}")

            with st.expander("線上修改或新增固定支出清單"):
                st.caption("「扣款日」填每月幾號（1–31，可留空）；設定後，到期未記錄的項目會在上方提示並可一鍵補登。")
                if settings_ws:
                    df_settings = pd.DataFrame(settings_rows, columns=SETTINGS_HEADER)
                    edited_settings = st.data_editor(
                        df_settings,
                        num_rows="dynamic",
                        key=f"settings_editor_{ver}",
                        column_config={"扣款日": st.column_config.TextColumn("扣款日", help="每月幾號（1–31），可留空")},
                        **STRETCH,
                    )
                    if st.button("儲存範本修改"):
                        try:
                            clean_df = edited_settings.fillna("").astype(str)
                            clean_df = clean_df[clean_df["項目名稱"].str.strip() != ""]
                            new_data = [SETTINGS_HEADER] + clean_df.values.tolist()
                            old_len = len(settings_ws.get_all_values())
                            settings_ws.update(range_name="A1", values=new_data)
                            if old_len > len(new_data):
                                settings_ws.batch_clear([f"A{len(new_data) + 1}:D{old_len}"])
                            fetch_config_bundle.clear()
                            bump_editor()
                            flash_and_rerun("固定支出範本已成功更新！")
                        except Exception as e:
                            st.error(f"儲存失敗: {e}")

        with tab_settings:
            st.caption("設定每月支出上限。「總預算」是整個月的上限，也可以替個別分類另外設定。")
            if budget_ws:
                df_budget = pd.DataFrame(budget_rows, columns=BUDGET_HEADER)
                df_budget["每月上限"] = pd.to_numeric(
                    df_budget["每月上限"].astype(str).str.replace(",", "", regex=False), errors="coerce"
                )
                edited_budget = st.data_editor(
                    df_budget,
                    num_rows="dynamic",
                    hide_index=True,
                    key=f"budget_editor_{ver}",
                    column_config={
                        "分類": st.column_config.SelectboxColumn(
                            "分類", options=[TOTAL_KEY] + EXPENSE_CATS, required=True
                        ),
                        "每月上限": st.column_config.NumberColumn("每月上限", min_value=0, step=500, format="%d"),
                    },
                    **STRETCH,
                )
                if st.button("儲存預算"):
                    try:
                        clean_b = edited_budget.dropna(subset=["分類", "每月上限"])
                        clean_b = clean_b[clean_b["分類"].astype(str).str.strip() != ""]
                        clean_b = clean_b.drop_duplicates(subset="分類", keep="last")
                        new_data = [BUDGET_HEADER] + [
                            [str(a).strip(), to_number(b)] for a, b in clean_b.itertuples(index=False)
                        ]
                        old_len = len(budget_ws.get_all_values())
                        budget_ws.update(range_name="A1", values=new_data)
                        if old_len > len(new_data):
                            budget_ws.batch_clear([f"A{len(new_data) + 1}:B{old_len}"])
                        fetch_config_bundle.clear()
                        bump_editor()
                        flash_and_rerun("預算已儲存！")
                    except Exception as e:
                        st.error(f"預算儲存失敗: {e}")

            if config_ws:
                st.divider()
                goal_val = st.number_input(
                    "儲蓄目標金額（0 = 不使用）",
                    value=int(cfg_num(CFG_GOAL, 0)), min_value=0, step=10000, key=f"goal_{ver}",
                )
                if st.button("儲存儲蓄目標"):
                    try:
                        save_config(CFG_GOAL, goal_val)
                        bump_editor()
                        flash_and_rerun("儲蓄目標已儲存！")
                    except Exception as e:
                        st.error(f"儲存失敗: {e}")

            if cat_ws:
                st.divider()
                with st.expander("線上管理支出／收入分類", expanded=False):
                    st.caption("可直接新增、修改或刪除分類；系統會保留「其他支出」、「每月固定費用」與「薪資」等核心分類。")
                    cat_table = [["支出", c] for c in EXPENSE_CATS] + [["收入", c] for c in INCOME_CATS]
                    df_cats = pd.DataFrame(cat_table, columns=CAT_HEADER)
                    edited_cats = st.data_editor(
                        df_cats,
                        num_rows="dynamic",
                        hide_index=True,
                        key=f"cat_editor_{ver}",
                        column_config={
                            "類型": st.column_config.SelectboxColumn("類型", options=["支出", "收入"], required=True),
                            "分類": st.column_config.TextColumn("分類", required=True),
                        },
                        **STRETCH,
                    )
                    if st.button("儲存分類設定"):
                        try:
                            clean_c = edited_cats.fillna("").astype(str)
                            clean_c["類型"] = clean_c["類型"].str.strip()
                            clean_c["分類"] = clean_c["分類"].str.strip()
                            clean_c = clean_c[(clean_c["類型"].isin(["支出", "收入"])) & (clean_c["分類"] != "")]
                            clean_c = clean_c.drop_duplicates(subset=["類型", "分類"], keep="first")
                            new_data = [CAT_HEADER] + clean_c.values.tolist()
                            old_len = len(cat_ws.get_all_values())
                            cat_ws.update(range_name="A1", values=new_data)
                            if old_len > len(new_data):
                                cat_ws.batch_clear([f"A{len(new_data) + 1}:B{old_len}"])
                            fetch_config_bundle.clear()
                            bump_editor()
                            flash_and_rerun("分類設定已更新！")
                        except Exception as e:
                            st.error(f"分類儲存失敗：{e}")

            if rule_ws:
                st.divider()
                with st.expander("🤖 自動分類規則（關鍵字自動歸類「其他支出」）", expanded=False):
                    st.caption("「關鍵字」可用逗號 `,` 或頓號 `、` 隔開多個詞（不分大小寫）。明細頁的「其他支出」符合備註關鍵字時，就能一鍵批次歸類。")
                    df_rules = pd.DataFrame(rule_rows, columns=RULE_HEADER)
                    edited_rules = st.data_editor(
                        df_rules,
                        num_rows="dynamic",
                        hide_index=True,
                        key=f"rule_editor_{ver}",
                        column_config={
                            "關鍵字": st.column_config.TextColumn("關鍵字（逗號隔開）", required=True, width="large"),
                            "分類": st.column_config.SelectboxColumn("分類", options=EXPENSE_CATS, required=True),
                        },
                        **STRETCH,
                    )
                    if st.button("儲存自動分類規則"):
                        try:
                            clean_r = edited_rules.fillna("").astype(str)
                            clean_r["關鍵字"] = clean_r["關鍵字"].str.strip()
                            clean_r["分類"] = clean_r["分類"].str.strip()
                            clean_r = clean_r[(clean_r["關鍵字"] != "") & (clean_r["分類"].isin(EXPENSE_CATS))]
                            new_data = [RULE_HEADER] + clean_r.values.tolist()
                            old_len = len(rule_ws.get_all_values())
                            rule_ws.update(range_name="A1", values=new_data)
                            if old_len > len(new_data):
                                rule_ws.batch_clear([f"A{len(new_data) + 1}:B{old_len}"])
                            fetch_config_bundle.clear()
                            bump_editor()
                            flash_and_rerun("自動分類規則已更新！")
                        except Exception as e:
                            st.error(f"儲存失敗：{e}")

    # ---------- 記帳明細 ----------
    elif view_mode == MODE_LIST:
        search_all = st.toggle("搜尋全部月份（跨月統計）", value=False, key="list_search_all")
        if search_all:
            base_df = (
                df.sort_values(["日期_std", "_row"], ascending=False).reset_index(drop=True)
                if not df.empty else df_selected
            )
            scope_label = "全部月份"
        else:
            base_df = df_selected
            scope_label = selected_month

        st.subheader(f"{scope_label} 記帳明細")

        if not df.empty:
            dirty_df = df[df["_raw_note"] != df["備註"]]
            if not dirty_df.empty:
                c_msg, c_btn = st.columns([3, 1.5])
                c_msg.info(f"偵測到試算表底層有 {len(dirty_df)} 筆自動通知備註可清理並格式化（畫面已自動轉換）。")
                if c_btn.button("一鍵永久更新試算表", key="btn_clean_vars", **STRETCH):
                    try:
                        if not rows_still_match(worksheet, dirty_df):
                            st.error("雲端資料已被其他裝置更動，請重新整理頁面後再試一次。")
                            fetch_data.clear()
                        else:
                            updates = [
                                {"range": f"F{int(r['_row'])}", "values": [[r["備註"]]]}
                                for _, r in dirty_df.iterrows()
                            ]
                            worksheet.batch_update(updates, value_input_option="RAW")
                            clear_data_cache()
                            flash_and_rerun(f"已永久更新試算表中的 {len(updates)} 筆備註！")
                    except Exception as e:
                        st.error(f"更新失敗：{e}")

        if not base_df.empty:
            uncat_df = base_df[(base_df["類型"] == "支出") & (base_df["分類"] == "其他支出")]
            if not uncat_df.empty:
                auto_matches = {}
                for idx_u, row_u in uncat_df.iterrows():
                    guessed = match_auto_category(row_u["備註"], auto_rules, EXPENSE_CATS)
                    if guessed and guessed != "其他支出":
                        auto_matches[idx_u] = guessed

                with st.expander(f"🏷️ {scope_label}有 {len(uncat_df)} 筆「其他支出」待確認分類（點此快速歸類）", expanded=False):
                    if auto_matches:
                        preview_pairs = [
                            f"「{uncat_df.loc[i, '備註'] or '無備註'}」→ **{cat_g}**"
                            for i, cat_g in list(auto_matches.items())[:5]
                        ]
                        more_txt = f" 等共 {len(auto_matches)} 筆" if len(auto_matches) > 5 else ""
                        st.info("依關鍵字規則可自動歸類：" + "、".join(preview_pairs) + more_txt)
                        if st.button(f"一鍵依規則自動歸類（{len(auto_matches)} 筆）", type="primary", key="btn_auto_cat_apply", **STRETCH):
                            try:
                                target_rows = base_df.loc[list(auto_matches.keys())]
                                if not rows_still_match(worksheet, target_rows):
                                    st.error("雲端資料已被其他裝置更動，請重新整理頁面後再試一次。")
                                    fetch_data.clear()
                                else:
                                    updates = [
                                        {"range": f"C{int(base_df.loc[i, '_row'])}", "values": [[cat_g]]}
                                        for i, cat_g in auto_matches.items()
                                    ]
                                    worksheet.batch_update(updates, value_input_option="RAW")
                                    clear_data_cache()
                                    flash_and_rerun(f"已依關鍵字規則自動歸類 {len(updates)} 筆支出！")
                            except Exception as e:
                                st.error(f"自動歸類失敗：{e}")

                    st.caption("也可直接在下表下拉修改分類（已先帶入符合規則的建議分類），改好後按「套用分類修改」。")
                    quick_cat_disp = uncat_df[["日期", "金額", "付款方式", "備註", "分類"]].copy()
                    for idx_u, cat_g in auto_matches.items():
                        quick_cat_disp.loc[idx_u, "分類"] = cat_g
                    edited_quick_cat = st.data_editor(
                        quick_cat_disp,
                        hide_index=True,
                        disabled=["日期", "金額", "付款方式", "備註"],
                        key=f"quick_cat_{ver}_{scope_label}_{len(auto_matches)}",
                        column_config={
                            "分類": st.column_config.SelectboxColumn("分類", options=EXPENSE_CATS, required=True),
                        },
                        **STRETCH,
                    )
                    if st.button("套用分類修改", type="secondary" if auto_matches else "primary", key="btn_apply_quick_cat"):
                        try:
                            changed_q = [
                                i for i in edited_quick_cat.index
                                if str(edited_quick_cat.loc[i, "分類"]).strip() != "其他支出"
                            ]
                            if not changed_q:
                                st.info("尚未變更任何分類。")
                            elif not rows_still_match(worksheet, base_df.loc[changed_q]):
                                st.error("雲端資料已被其他裝置更動，請重新整理頁面後再試一次。")
                                fetch_data.clear()
                            else:
                                updates = [
                                    {"range": f"C{int(base_df.loc[i, '_row'])}", "values": [[str(edited_quick_cat.loc[i, "分類"]).strip()]]}
                                    for i in changed_q
                                ]
                                worksheet.batch_update(updates, value_input_option="RAW")
                                clear_data_cache()
                                flash_and_rerun(f"已將 {len(changed_q)} 筆支出歸類完成！")
                        except Exception as e:
                            st.error(f"更新分類失敗：{e}")

        if not base_df.empty:
            range_opt = "全部期間"
            if search_all:
                f0, f1, f2, f3 = st.columns([1.6, 2, 1.8, 2.8])
                range_opt = f0.selectbox("時間區間", ["全部期間", "今年", "近 3 個月", "近 1 年"], key="list_range_opt")
            else:
                f1, f2, f3 = st.columns([2, 2, 3])
            cat_filter = f1.multiselect("分類", ALL_CATS)
            pay_filter = f2.multiselect("付款方式", PAY_OPTIONS)
            kw = f3.text_input("搜尋備註（支援空白隔開多關鍵字）" if search_all else "搜尋備註")

            mask = pd.Series(True, index=base_df.index)
            if search_all and range_opt != "全部期間":
                if range_opt == "今年":
                    mask &= base_df["日期_std"].fillna("").str.startswith(f"{TODAY.year}-")
                elif range_opt == "近 3 個月":
                    cutoff = add_months(TODAY, -3).strftime("%Y-%m-%d")
                    mask &= base_df["日期_std"].fillna("") >= cutoff
                elif range_opt == "近 1 年":
                    cutoff = add_months(TODAY, -12).strftime("%Y-%m-%d")
                    mask &= base_df["日期_std"].fillna("") >= cutoff
            if cat_filter:
                mask &= base_df["分類"].isin(cat_filter)
            if pay_filter:
                mask &= base_df["付款方式"].isin(pay_filter)
            if kw.strip():
                for token in kw.strip().split():
                    mask &= base_df["備註"].str.contains(token, case=False, regex=False)

            view = base_df[mask]
            v_inc = view.loc[view["類型"] == "收入", "金額_num"].sum()
            v_exp = view.loc[view["類型"] == "支出", "金額_num"].sum()
            if search_all:
                v1, v2, v3, v4 = st.columns(4)
                v1.metric("符合筆數", f"{len(view)}")
                v2.metric("合計收入", f"${v_inc:,.0f}")
                v3.metric("合計支出", f"${v_exp:,.0f}")
                v4.metric("合計淨額", money(v_inc - v_exp))
            else:
                v1, v2, v3 = st.columns(3)
                v1.metric("筆數", f"{len(view)}")
                v2.metric("收入", f"${v_inc:,.0f}")
                v3.metric("支出", f"${v_exp:,.0f}")

            if search_all and not view.empty:
                with st.expander("查看符合條件的各月花費彙整", expanded=False):
                    m_agg = (
                        view.groupby(["年月", "類型"], as_index=False)["金額_num"]
                        .sum()
                        .pivot(index="年月", columns="類型", values="金額_num")
                        .fillna(0)
                        .sort_index(ascending=False)
                        .reset_index()
                    )
                    for col_t in ("收入", "支出"):
                        if col_t not in m_agg:
                            m_agg[col_t] = 0.0
                    m_agg["淨額"] = m_agg["收入"] - m_agg["支出"]
                    for col_t in ("收入", "支出", "淨額"):
                        m_agg[col_t] = m_agg[col_t].map(money)
                    st.dataframe(m_agg[["年月", "支出", "收入", "淨額"]], hide_index=True, **STRETCH)

            filter_sig = f"{int(search_all)}__{range_opt}__{'|'.join(cat_filter)}__{'|'.join(pay_filter)}__{kw.strip()}"

            def render_tx_editor(sub_df, tx_kind, key_suffix):
                if sub_df.empty:
                    return
                st.markdown(f"#### {tx_kind}明細（{len(sub_df)} 筆）")
                disp = sub_df[FIELDS].copy()
                disp.insert(0, "刪除", False)

                edited = st.data_editor(
                    disp,
                    hide_index=True,
                    key=f"table_{key_suffix}_{ver}_{filter_sig}",
                    column_config={
                        "刪除": st.column_config.CheckboxColumn("刪除", width="small"),
                        "日期": st.column_config.TextColumn("日期", width="small"),
                        "類型": st.column_config.SelectboxColumn("類型", options=["支出", "收入"], width="small", required=True),
                        "分類": st.column_config.SelectboxColumn("分類", options=ALL_CATS, width="small", required=True),
                        "金額": st.column_config.TextColumn("金額", width="small"),
                        "付款方式": st.column_config.SelectboxColumn("付款方式", options=PAY_OPTIONS, width="small", required=True),
                        "備註": st.column_config.TextColumn("備註", width="large"),
                    },
                    **STRETCH,
                )

                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"刪除所選{tx_kind}", key=f"btn_delete_{key_suffix}", icon=":material/delete:", **STRETCH):
                        checked = edited[edited["刪除"] == True].index.tolist()  # noqa: E712
                        if not checked:
                            st.warning("請先勾選您想要刪除的項目！")
                        else:
                            try:
                                targets = base_df.loc[checked]
                                if not rows_still_match(worksheet, targets):
                                    st.error("雲端資料已被其他裝置更動，請重新整理頁面後再試一次。")
                                    fetch_data.clear()
                                else:
                                    n_del = delete_rows(worksheet, targets["_row"])
                                    clear_data_cache()
                                    flash_and_rerun(f"成功刪除 {n_del} 筆項目！")
                            except Exception as e:
                                st.error(f"刪除失敗：{e}")

                with c2:
                    if st.button(f"儲存{tx_kind}修改", type="primary", key=f"btn_save_{key_suffix}", icon=":material/check:", **STRETCH):
                        try:
                            save_df = edited.drop(columns=["刪除"]).fillna("").astype(str)
                            orig_df = base_df.loc[save_df.index, FIELDS].astype(str)
                            changed_idx = [
                                i for i in save_df.index
                                if any(save_df.loc[i, c].strip() != orig_df.loc[i, c].strip() for c in FIELDS)
                            ]
                            if not changed_idx:
                                st.info("沒有偵測到任何修改。")
                            else:
                                error_lines = []
                                cleaned = {}
                                for i in changed_idx:
                                    errs, clean_row = validate_row(save_df.loc[i])
                                    n = int(base_df.loc[i, "_row"])
                                    if errs:
                                        error_lines.append(f"**試算表第 {n} 列**：" + "；".join(errs))
                                    else:
                                        cleaned[i] = (n, clean_row)

                                if error_lines:
                                    st.error("以下資料格式有問題，尚未儲存：\n\n" + "\n\n".join(error_lines))
                                elif not rows_still_match(worksheet, base_df.loc[changed_idx]):
                                    st.error("雲端資料已被其他裝置更動，請重新整理頁面後再試一次。")
                                    fetch_data.clear()
                                else:
                                    updates = [
                                        {"range": f"A{n}:F{n}", "values": [clean_row]}
                                        for n, clean_row in cleaned.values()
                                    ]
                                    worksheet.batch_update(updates, value_input_option="RAW")
                                    clear_data_cache()
                                    flash_and_rerun(f"已同步 {len(changed_idx)} 筆修改到 Google 試算表！")
                        except Exception as e:
                            st.error(f"儲存失敗：{e}")

            render_tx_editor(view[view["類型"] == "支出"], "支出", "exp")
            render_tx_editor(view[view["類型"] == "收入"], "收入", "inc")
        else:
            view = pd.DataFrame(columns=DF_COLS)
            st.info(f"所選範圍（{scope_label}）目前還沒有任何記錄！")

        st.divider()
        with st.container(key="csv_export_row"):
            dl1, dl2 = st.columns(2)
            dl1.download_button(
                "匯出篩選結果 CSV" if search_all else "匯出本月 CSV",
                view[FIELDS].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"記帳_篩選_{TODAY.strftime('%Y%m%d')}.csv" if search_all else f"記帳_{selected_month}.csv",
                mime="text/csv",
                icon=":material/download:",
                disabled=view.empty,
                **STRETCH,
            )
            dl2.download_button(
                "下載全部記帳資料（CSV）",
                df[FIELDS].to_csv(index=False).encode("utf-8-sig"),
                file_name="記帳_全部資料.csv",
                mime="text/csv",
                icon=":material/download:",
                disabled=df.empty,
                **STRETCH,
            )

    # ---------- 圖表分析（整合月度與年度） ----------
    elif view_mode == MODE_CHART:
        px = load_px()
        chart_scope = st.radio(
            "分析範圍",
            ["月度分析", "年度總結"],
            horizontal=True,
            label_visibility="collapsed",
            key="chart_scope",
        )

        if chart_scope == "月度分析":
            if not df.empty:
                # 僅統計截至本月的歷史紀錄，避免未來信用卡分期把近 12 個月趨勢圖拉歪
                valid = df[
                    df["年月"].str.fullmatch(r"\d{4}-\d{2}", na=False)
                    & (df["年月"] <= current_month_str)
                ]
                if not valid.empty:
                    trend = valid.pivot_table(
                        index="年月", columns="類型", values="金額_num", aggfunc="sum", fill_value=0
                    ).reset_index().sort_values("年月").tail(12)
                    for c in ("收入", "支出"):
                        if c not in trend:
                            trend[c] = 0
                    long = trend.melt(
                        id_vars="年月", value_vars=["收入", "支出"], var_name="類型", value_name="金額"
                    )
                    show(px.line(
                        long, x="年月", y="金額", color="類型", markers=True, title="近 12 個月收支趨勢（截至本月）",
                        line_shape="spline",
                        color_discrete_map={"收入": INCOME_COLOR, "支出": EXPENSE_COLOR},
                    ))

            st.subheader(f"{selected_month} 每月固定費用總覽")
            if not df_selected.empty:
                df_fixed = df_selected[df_selected["分類"] == "每月固定費用"]
                if not df_fixed.empty:
                    st.metric("固定開銷總計", f"${int(df_fixed['金額_num'].sum()):,}")
                    st.dataframe(df_fixed[["日期", "金額", "付款方式", "備註"]], hide_index=True, **STRETCH)
                else:
                    st.info("此月份尚無設定「每月固定費用」的紀錄。")
            else:
                st.info("此月份尚無資料。")

            st.subheader(f"{selected_month} 財務視覺化分析")
            if not df_selected.empty:
                df_expense = df_selected[df_selected["類型"] == "支出"]
                if not df_expense.empty:
                    show(px.pie(
                        df_expense, values="金額_num", names="分類",
                        title=f"{selected_month} 各類別支出佔比", hole=0.45,
                        color="分類", color_discrete_map=CAT_COLORS,
                    ))

                    daily = (
                        df_expense.groupby(["日期_std", "分類"], as_index=False)["金額_num"]
                        .sum()
                        .sort_values("日期_std")
                    )
                    daily["日"] = daily["日期_std"].apply(
                        lambda s: f"{int(s.split('-')[-1])}日"
                        if len(str(s).split("-")) == 3 and str(s).split("-")[-1].isdigit()
                        else str(s)
                    )
                    day_order = daily.drop_duplicates("日期_std")["日"].tolist()
                    fig_bar = px.bar(
                        daily, x="日", y="金額_num",
                        title=f"{selected_month} 每日總支出趨勢",
                        color="分類", color_discrete_map=CAT_COLORS,
                        labels={"日": "日期", "金額_num": "金額"},
                        category_orders={"日": day_order},
                    )
                    fig_bar.update_xaxes(type="category")
                    show(fig_bar)

                    pay_sum = df_expense.groupby("付款方式", as_index=False)["金額_num"].sum()
                    pay_sum["付款方式"] = pay_sum["付款方式"].replace("", "未填")
                    show(px.bar(
                        pay_sum, x="付款方式", y="金額_num", text_auto=True,
                        title=f"{selected_month} 各付款方式支出",
                        labels={"金額_num": "金額"},
                    ))

                    tmp = df_expense.copy()
                    tmp["週"] = pd.to_datetime(tmp["日期_std"], errors="coerce").dt.dayofweek
                    tmp = tmp.dropna(subset=["週"])
                    tmp["週"] = tmp["週"].astype(int)
                    wk = tmp.groupby("週")["金額_num"].sum().reindex(range(7), fill_value=0).reset_index()
                    wk["星期"] = [WEEKDAY_NAMES[int(i)] for i in wk["週"]]
                    show(px.bar(
                        wk, x="星期", y="金額_num", text_auto=True,
                        title=f"{selected_month} 每週各天支出合計",
                        labels={"金額_num": "金額"},
                    ))
                else:
                    st.info("此月份尚無支出紀錄可產出圖表。")

                df_income = df_selected[df_selected["類型"] == "收入"]
                if not df_income.empty:
                    show(px.pie(
                        df_income, values="金額_num", names="分類",
                        title=f"{selected_month} 收入來源佔比", hole=0.45,
                    ))

        else:
            valid_ym = df[df["年月"].fillna("").str.fullmatch(r"\d{4}-\d{2}")]
            years = sorted(
                set(valid_ym["年月"].str.slice(0, 4).tolist() + [str(TODAY.year)]),
                reverse=True,
            )
            sel_year = st.selectbox("選擇年份", years, key="year_sel")
            df_y = valid_ym[valid_ym["年月"].str.startswith(f"{sel_year}-")]

            y_inc, y_exp = sums(df_y)
            y_net = y_inc - y_exp

            prev_year = str(int(sel_year) - 1)
            df_prev_y = valid_ym[valid_ym["年月"].str.startswith(f"{prev_year}-")]
            py_inc, py_exp = sums(df_prev_y)
            has_prev_y = not df_prev_y.empty

            summary_card(
                f"{sel_year} 全年", y_inc, y_exp, y_net,
                d_inc=(y_inc - py_inc if has_prev_y else None),
                d_exp=(y_exp - py_exp if has_prev_y else None),
                d_net=(y_net - (py_inc - py_exp) if has_prev_y else None),
                rate=(y_net / y_inc if y_inc > 0 else None),
                sub_label="年度結餘",
                compare_label="較去年",
            )

            if not df_y.empty:
                all_12m = [f"{sel_year}-{m:02d}" for m in range(1, 13)]
                month_labels = [f"{m}月" for m in range(1, 13)]
                piv = df_y.pivot_table(
                    index="年月", columns="類型", values="金額_num", aggfunc="sum", fill_value=0
                ).reindex(all_12m, fill_value=0).reset_index()
                for c in ("收入", "支出"):
                    if c not in piv:
                        piv[c] = 0
                piv["月份"] = month_labels
                long_y = piv.melt(id_vars="月份", value_vars=["收入", "支出"], var_name="類型", value_name="金額")
                show(px.bar(
                    long_y, x="月份", y="金額", color="類型", barmode="group",
                    title=f"{sel_year} 年各月收支對比",
                    color_discrete_map={"收入": INCOME_COLOR, "支出": EXPENSE_COLOR},
                    category_orders={"月份": month_labels},
                ))

                y_exp_df = df_y[df_y["類型"] == "支出"]
                if not y_exp_df.empty:
                    show(px.pie(
                        y_exp_df, values="金額_num", names="分類",
                        title=f"{sel_year} 全年各類別支出佔比", hole=0.45,
                        color="分類", color_discrete_map=CAT_COLORS,
                    ))

                    cat_rank = (
                        y_exp_df.groupby("分類", as_index=False)["金額_num"]
                        .sum()
                        .sort_values("金額_num", ascending=True)
                    )
                    show(px.bar(
                        cat_rank, x="金額_num", y="分類", orientation="h", text_auto=True,
                        title=f"{sel_year} 全年分類花費排行",
                        color="分類", color_discrete_map=CAT_COLORS,
                        labels={"金額_num": "總金額", "分類": ""},
                    ))

                    st.markdown(f"#### {sel_year} 年度 Top 10 單筆最高支出")
                    top10 = y_exp_df.sort_values("金額_num", ascending=False).head(10).copy()
                    top10["金額顯示"] = top10["金額_num"].map(lambda x: f"${x:,.0f}")
                    st.dataframe(
                        top10[["日期_std", "分類", "金額顯示", "付款方式", "備註"]].rename(
                            columns={"日期_std": "日期", "金額顯示": "金額"}
                        ),
                        hide_index=True,
                        **STRETCH,
                    )
            else:
                st.info(f"{sel_year} 年目前尚無記帳資料。")

    # ---------- 預算與分期追蹤 ----------
    elif view_mode == MODE_BUDGET:
        st.subheader(f"{selected_month} 預算追蹤")
        if not budgets:
            st.info(f"尚未設定預算，請到「{MODE_ADD}」→「預算與設定」設定。")
        else:
            exp_df = df_selected[df_selected["類型"] == "支出"]
            items = []
            if TOTAL_KEY in budgets:
                items.append((TOTAL_KEY, total_expense))
            for cat in budgets:
                if cat != TOTAL_KEY:
                    items.append((cat, exp_df.loc[exp_df["分類"] == cat, "金額_num"].sum()))

            for name, spent in items:
                budget_card(name, spent, budgets[name])

            if selected_month == current_month_str and TOTAL_KEY in budgets:
                y, m = map(int, selected_month.split("-"))
                days_total = py_calendar.monthrange(y, m)[1]
                days_left = days_total - TODAY.day + 1
                remain = budgets[TOTAL_KEY] - total_expense
                if remain > 0:
                    st.info(f"本月還有 {days_left} 天（含今天），平均每天可花 ${remain / days_left:,.0f}")
                else:
                    st.warning("本月總預算已用完，建議接下來盡量不要再花錢。")

                projected = total_expense / TODAY.day * days_total
                if projected > budgets[TOTAL_KEY]:
                    st.warning(
                        f"照目前速度，月底預估花費 ${projected:,.0f}，"
                        f"會超出預算 ${projected - budgets[TOTAL_KEY]:,.0f}。"
                    )
                else:
                    st.success(f"月底預估花費 ${projected:,.0f}，仍在預算內。")

        st.markdown("#### 信用卡分期總覽")
        active_inst, future_inst_map = analyze_installments(df, current_month_str)
        total_rem_debt = sum(x["remain_amt"] for x in active_inst)
        if active_inst:
            next_m_str = add_months(TODAY, 1).strftime("%Y-%m")
            next_m_amt = future_inst_map.get(next_m_str, 0.0)
            ic1, ic2 = st.columns(2)
            ic1.metric("未清償分期總餘額", f"${total_rem_debt:,.0f}")
            ic2.metric(f"下月（{next_m_str}）分期應繳", f"${next_m_amt:,.0f}")

            for item in active_inst:
                installment_card(
                    item["title"], item["paid_cnt"], item["total_cnt"],
                    item["per_amt"], item["remain_amt"], item["end_ym"],
                )

            if future_inst_map:
                with st.expander("查看未來各月份分期應繳明細"):
                    fut_df = pd.DataFrame(
                        [{"月份": k, "分期預扣金額": f"${v:,.0f}"} for k, v in future_inst_map.items()]
                    )
                    st.dataframe(fut_df, hide_index=True, **STRETCH)
        else:
            st.caption("目前沒有進行中的分期帳單（在「記一筆」選信用卡並設定分期期數即可自動追蹤）。")

        st.markdown("#### 儲蓄目標")
        goal = cfg_num(CFG_GOAL, 0)
        today_iso = TODAY.strftime("%Y-%m-%d")
        df_to_date = df[df["日期_std"].fillna("") <= today_iso] if not df.empty else df
        realized_inc, realized_exp = sums(df_to_date)
        realized_net = realized_inc - realized_exp
        if goal and goal > 0:
            g_ratio = realized_net / goal
            st.progress(
                float(min(max(g_ratio, 0.0), 1.0)),
                text=f"{max(g_ratio, 0):.0%}（截至今日累計結餘 ${realized_net:,.0f} / 目標 ${goal:,.0f}）",
            )
            if realized_net >= goal:
                st.success("已達成儲蓄目標！")
            else:
                st.caption(f"還差 ${goal - realized_net:,.0f}")
            if total_rem_debt > 0:
                st.caption(f"若扣除尚未到期的信用卡分期（${total_rem_debt:,.0f}），淨結餘為 ${realized_net - total_rem_debt:,.0f}。")
        else:
            st.caption(f"尚未設定儲蓄目標，可到「{MODE_ADD}」→「預算與設定」設定。")

    # ---------- 月曆 ----------
    elif view_mode == MODE_CAL:
        st.subheader(f"{selected_month} 日曆視圖")

        try:
            year, month = map(int, selected_month.split("-"))
        except ValueError:
            year, month = TODAY.year, TODAY.month

        cal_style = st.radio("顯示方式", ["格狀月曆", "清單（手機建議）"], horizontal=True, index=1)

        if cal_style == "清單（手機建議）":
            if df_selected.empty:
                st.info("此月份尚無資料。")
            else:
                for d_str, g in df_selected.sort_values(["日期_std", "_row"]).groupby("日期_std"):
                    g_inc, g_exp = sums(g)
                    net_txt = md_escape(f"{g_inc - g_exp:+,.0f}")
                    ts = pd.to_datetime(d_str, errors="coerce")
                    wd = WEEKDAY_NAMES[int(ts.dayofweek)] if not pd.isna(ts) else ""
                    st.markdown(md_escape(f"{d_str}（{wd}）") + f" **淨 {net_txt}**")
                    for _, row in g.iterrows():
                        sign = "-" if row["類型"] == "支出" else "+"
                        amt_txt = md_escape(f"{sign}${row['金額_num']:,.0f}")
                        st.markdown(
                            f"- {amt_txt} {md_escape(row['分類'])} {md_escape(row['備註'])}"
                        )
        else:
            cal_matrix = py_calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
            weekdays = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"]
            by_day = {d: g for d, g in df_selected.groupby("日期_std")} if not df_selected.empty else {}
            today_str = TODAY.strftime("%Y-%m-%d")

            cells = ["".join(f"<div class='cal-wd'>{w}</div>" for w in weekdays)]
            for week in cal_matrix:
                for day in week:
                    if day == 0:
                        cells.append("<div class='cal-card empty'></div>")
                        continue
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    body, day_net, n_extra = "", 0, 0
                    g = by_day.get(date_str)
                    if g is not None:
                        for k, rec in enumerate(g[["類型", "分類", "備註", "金額_num"]].to_dict("records")):
                            is_exp = rec["類型"] == "支出"
                            color = EXPENSE_COLOR if is_exp else INCOME_COLOR
                            sign = "-" if is_exp else "+"
                            amt = rec["金額_num"]
                            day_net += -amt if is_exp else amt
                            if k >= 3:
                                n_extra += 1
                                continue
                            body += (
                                f"<div class='cal-item'>"
                                f"<span class='cal-amt' style='color:{color};'>"
                                f"{sign}${amt:,.0f} ({html.escape(str(rec['分類']))})</span>"
                                f"<span class='cal-note'>{html.escape(str(rec['備註']))}</span>"
                                f"</div>"
                            )
                    if n_extra:
                        body += f"<div class='cal-note'>另 {n_extra} 筆…</div>"
                    total_html = ""
                    if body:
                        net_color = INCOME_COLOR if day_net >= 0 else EXPENSE_COLOR
                        total_html = f"<span class='cal-day-total' style='color:{net_color};'>淨 {day_net:+,.0f}</span>"
                    today_cls = " today" if date_str == today_str else ""
                    cells.append(
                        f"<div class='cal-card{today_cls}'><div class='cal-day-header'>"
                        f"<span>{day}</span>{total_html}</div>{body}</div>"
                    )
            st.markdown(f"<div class='cal-grid'>{''.join(cells)}</div>", unsafe_allow_html=True)

else:
    st.markdown(HEADER_HTML, unsafe_allow_html=True)
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")
