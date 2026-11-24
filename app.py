import html
import re
import calendar as py_calendar
from datetime import date, datetime, timedelta, timezone

import gspread
import pandas as pd
import streamlit as st

# ======================= 視覺主題 =======================
ACCENT = "#6FA3D8"
INCOME_COLOR = "#3FAF86"
EXPENSE_COLOR = "#E0675F"
WARN_COLOR = "#E0A030"
PALETTE = [ACCENT, INCOME_COLOR, "#D9A441", EXPENSE_COLOR, "#B48EAD", "#7BAE9A", "#66B2B2", "#8A94A6"]
CAT_COLORS = {
    "伙食": "#5B8FB9", "交通": "#7BAE9A", "購物": "#B48EAD",
    "娛樂": "#D4A76A", "醫療": "#66B2B2", "其他支出": "#A9B8C9", "每月固定費用": "#8A94A6",
}

CSS = """
<style>
:root {
  --primary:#6FA3D8; --primary-soft:rgba(111,163,216,.16);
  --primary-strong:#33619B;
  --income:#3FAF86;  --income-soft:rgba(63,175,134,.14);
  --expense:#E0675F; --expense-soft:rgba(224,103,95,.14);
  --warning:#E0A030;
  --line:rgba(128,128,128,.22);
  --card:rgba(128,128,128,.08);
  --card-hover:rgba(128,128,128,.13);
  --track:rgba(128,128,128,.22);
  --r-sm:10px; --r-md:14px; --r-lg:20px;
  --shadow-card:0 1px 2px rgba(0,0,0,.12), 0 4px 14px rgba(0,0,0,.10), inset 0 1px 0 rgba(255,255,255,.05);
  --shadow-lift:0 6px 20px rgba(0,0,0,.22);
  --ease:cubic-bezier(.2,.7,.2,1);
}

.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
  font-family:"PingFang TC","Microsoft JhengHei","Noto Sans TC",system-ui,-apple-system,"Segoe UI",sans-serif;
  -webkit-font-smoothing:antialiased;
}
footer { display:none; }
div.block-container, div[data-testid="stMainBlockContainer"] {
  max-width:1080px; padding:4.5rem 1rem 4rem;
}
.stApp h3 { font-size:1.125rem; font-weight:600; letter-spacing:.01em; margin-top:.5rem; }
.stApp h4 { font-size:.9rem; font-weight:600; opacity:.7; letter-spacing:.04em; }
.stApp hr { border-color:var(--line) !important; margin:1.5rem 0; }
.stApp [data-testid="stCaptionContainer"] { opacity:.65; }

/* ---------- 標題 ---------- */
.app-header h1 { font-size:1.5rem; font-weight:700; line-height:1.3; margin:0; padding:0; letter-spacing:.01em; }
.app-header p { margin:.2rem 0 0; opacity:.55; font-size:.85rem; }
.st-key-topbar div[data-testid="stHorizontalBlock"],
.st-key-month_nav div[data-testid="stHorizontalBlock"] {
  flex-direction:row !important; flex-wrap:nowrap !important; align-items:center; gap:8px;
}
.st-key-topbar div[data-testid="stColumn"], .st-key-month_nav div[data-testid="stColumn"] { min-width:0 !important; }

/* ---------- 按鈕 ---------- */
.stButton button, .stDownloadButton button {
  min-height:44px; font-weight:500; border-radius:var(--r-md);
  border:1px solid var(--line);
  transition:transform .15s var(--ease), box-shadow .15s var(--ease), background .15s var(--ease), border-color .15s var(--ease);
}
.stButton button:hover, .stDownloadButton button:hover {
  border-color:var(--primary); transform:translateY(-1px); box-shadow:var(--shadow-lift);
}
.stButton button:active, .stDownloadButton button:active { transform:translateY(0) scale(.98); box-shadow:none; }
.stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {
  background:linear-gradient(135deg,#4177BA 0%,#33619B 100%) !important;
  border:none !important; color:#fff !important; font-weight:600;
  box-shadow:0 2px 10px rgba(51,97,155,.40);
}
.stButton button[kind="primary"] p, .stButton button[data-testid="stBaseButton-primary"] p { color:#fff !important; }
.stButton button[kind="primary"]:hover, .stButton button[data-testid="stBaseButton-primary"]:hover {
  filter:brightness(1.1); box-shadow:0 6px 18px rgba(51,97,155,.50);
}
.stButton button:focus-visible, .stDownloadButton button:focus-visible {
  outline:2px solid var(--primary); outline-offset:2px;
}
.st-key-btn_delete button,
.st-key-btn_delete_exp button,
.st-key-btn_delete_inc button { color:var(--expense) !important; border-color:var(--expense) !important; }
.st-key-btn_delete button:hover,
.st-key-btn_delete_exp button:hover,
.st-key-btn_delete_inc button:hover { background:var(--expense-soft) !important; }

/* ---------- 表單元件 ---------- */
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
  border-radius:var(--r-sm) !important;
}
div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
  border-radius:var(--r-sm) !important;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
  box-shadow:0 0 0 2px var(--primary-soft) !important;
}
.stApp label p { font-size:.85rem; font-weight:500; opacity:.8; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:var(--r-md) !important; }

/* ---------- 分頁籤 ---------- */
.stTabs [data-baseweb="tab-list"] { gap:4px; border-bottom:1px solid var(--line); }
.stTabs [data-baseweb="tab"] { height:44px; padding:0 14px; border-radius:var(--r-sm) var(--r-sm) 0 0; font-weight:500; }
.stTabs [aria-selected="true"] { font-weight:600; }
.stTabs [data-baseweb="tab-highlight"] { background:var(--primary) !important; height:3px; border-radius:3px; }

/* ---------- 內建 metric 卡 ---------- */
div[data-testid="stMetric"] {
  background:var(--card); border:1px solid var(--line); border-radius:var(--r-md);
  padding:12px 14px; font-variant-numeric:tabular-nums;
}
div[data-testid="stMetricLabel"] p { font-size:.8rem; opacity:.65; }
div[data-testid="stMetricValue"] { font-weight:600; font-variant-numeric:tabular-nums; }

/* ---------- 提示框、進度條、表格 ---------- */
div[data-testid="stAlert"] { border-radius:var(--r-md); border:1px solid var(--line); }
div[data-testid="stProgress"] > div > div { border-radius:999px; }
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
  border:1px solid var(--line); border-radius:var(--r-md); overflow:hidden;
}
div[data-testid="stExpander"] { border-radius:var(--r-md); border:1px solid var(--line); }

/* ---------- 總覽卡（Hero） ---------- */
.hero {
  background:
    radial-gradient(120% 140% at 0% 0%, rgba(111,163,216,.22) 0%, rgba(111,163,216,0) 60%),
    var(--card);
  border:1px solid var(--line); border-radius:var(--r-lg);
  padding:20px 22px; margin:16px 0 12px; box-shadow:var(--shadow-card);
  font-variant-numeric:tabular-nums;
}
.hero-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.hero-label { opacity:.6; font-size:.8rem; letter-spacing:.04em; }
.hero-amount { font-size:2.25rem; font-weight:700; line-height:1.15; margin:4px 0 8px; letter-spacing:-.01em; }
.hero-delta { font-size:.8rem; }
.hero-delta .mut { opacity:.6; margin-right:4px; }
.hero-row { display:flex; gap:12px; margin-top:16px; padding-top:16px; border-top:1px solid var(--line); }
.hero-col { flex:1; min-width:0; }
.hero-col .v { font-size:1.2rem; font-weight:600; margin:2px 0 4px; }
.pos { color:var(--income); } .neg { color:var(--expense); }
.pill { display:inline-block; padding:1px 8px; border-radius:999px; font-weight:600; font-size:.78rem; }
.pill.pos { background:var(--income-soft); }
.pill.neg { background:var(--expense-soft); }
.pill.zero { background:var(--card); color:inherit; opacity:.7; }
.pill.rate { opacity:1; font-weight:600; white-space:nowrap; }

/* ---------- 預算與分期進度卡 ---------- */
.bud {
  background:var(--card); border:1px solid var(--line); border-radius:var(--r-md);
  padding:14px 16px; margin-bottom:10px; font-variant-numeric:tabular-nums;
  transition:background .15s var(--ease), border-color .15s var(--ease);
}
.bud:hover { background:var(--card-hover); border-color:rgba(128,128,128,.4); }
.bud-top { display:flex; justify-content:space-between; gap:8px; font-size:.95rem; }
.bud-sub { opacity:.6; font-size:.8rem; margin:2px 0 10px; }
.bud-bar { height:8px; border-radius:999px; background:var(--track); overflow:hidden; }
.bud-bar > i { display:block; height:100%; border-radius:999px; animation:grow .7s var(--ease) both; transform-origin:left; }
.bud-ok > i   { background:linear-gradient(90deg,#3FAF86,#5CCBA3); }
.bud-warn > i { background:linear-gradient(90deg,#E0A030,#F0BE5A); }
.bud-over > i { background:linear-gradient(90deg,#E0675F,#F08A83); }
.bud-inst > i { background:linear-gradient(90deg,#6FA3D8,#4177BA); }
.t-ok { color:var(--income); font-weight:600; } .t-warn { color:var(--warning); font-weight:600; } .t-over { color:var(--expense); font-weight:700; }
.t-inst { color:var(--primary); font-weight:600; }
@keyframes grow { from { transform:scaleX(0); } to { transform:scaleX(1); } }

/* ---------- 主導覽 ---------- */
.st-key-view_mode { margin:8px 0 20px; }
.st-key-view_mode button { min-height:44px; font-weight:500; }

/* ---------- 月曆 ---------- */
.cal-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:8px; }
.cal-card {
  background:var(--card); border:1px solid var(--line); border-radius:var(--r-sm);
  padding:8px 10px; height:132px; overflow:hidden; margin-bottom:8px;
  transition:background .15s var(--ease);
}
.cal-grid .cal-card { margin-bottom:0; }
.cal-card:hover { background:var(--card-hover); }
.cal-card.empty { opacity:.2; background:transparent; border-style:dashed; }
.cal-card.today { border-color:var(--primary); box-shadow:0 0 0 1px var(--primary), 0 0 14px var(--primary-soft); }
.cal-day-header {
  font-size:.8rem; font-weight:600; border-bottom:1px solid var(--line);
  padding-bottom:4px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;
}
.cal-card.today .cal-day-header > span:first-child {
  background:var(--primary-strong); color:#fff; border-radius:999px; padding:0 7px; min-width:22px; text-align:center;
}
.cal-day-total { font-size:.75rem; font-weight:600; font-variant-numeric:tabular-nums; }
.cal-amt { font-size:.8rem; font-weight:600; font-variant-numeric:tabular-nums; }
.cal-item { margin-bottom:6px; }
.cal-note { font-size:.75rem; opacity:.6; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:block; }
.cal-wd { text-align:center; font-weight:600; opacity:.65; font-size:.85rem; padding:4px 0; }

/* ---------- 登入頁 ---------- */
div[data-testid="stHeading"] h1 { text-align:center; font-weight:700; margin-top:8vh; }

@media (max-width:640px) {
  .hero { padding:16px; border-radius:var(--r-md); }
  .hero-amount { font-size:1.9rem; }
  .hero-col .v { font-size:1.05rem; }
  .cal-grid { gap:4px; }
  .cal-card { height:96px; padding:6px; }
  .cal-amt, .cal-day-total, .cal-note { font-size:.65rem; }
}

@media (min-width:900px) {
  html { font-size:18px; }
  div.block-container, div[data-testid="stMainBlockContainer"] { max-width:1180px; padding:4.5rem 1.5rem 4rem; }
  .cal-card { height:150px; }
  .hero-label, .hero-delta, .bud-sub, .cal-day-total, .cal-note { font-size:.9rem; }
  .app-header h1 { font-size:1.75rem; }
  .hero-amount { font-size:2.6rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition:none !important; animation:none !important; }
}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def theme_show(fig, stretch):
    # 將 Y 軸標題轉為直排（例如「金額」->「金<br>額」），避免橫躺難閱讀
    y_title = ""
    try:
        y_title = fig.layout.yaxis.title.text or ""
    except Exception:
        y_title = ""
    if y_title and "<br>" not in y_title and not y_title.isascii():
        y_title = "<br>".join(list(y_title))

    fig.update_layout(
        margin=dict(l=8, r=8, t=48, b=8),
        title=dict(font=dict(size=15), x=0, xanchor="left"),
        legend=dict(title_text="", orientation="h", y=-0.2, x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="PingFang TC, Microsoft JhengHei, Noto Sans TC, sans-serif", size=12),
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor="rgba(128,128,128,.3)")
    fig.update_yaxes(
        title_text=y_title,
        gridcolor="rgba(128,128,128,.15)",
        zeroline=False,
    )
    st.plotly_chart(fig, theme="streamlit", **stretch)


def money(n):
    return f"-${abs(n):,.0f}" if n < 0 else f"${n:,.0f}"


def _delta(v, invert=False):
    if round(v) == 0:
        return "<span class='pill zero'>±0</span>"
    good = (v <= 0) if invert else (v >= 0)
    sign = "+" if v > 0 else "-"
    return f"<span class='pill {'pos' if good else 'neg'}'>{sign}{abs(v):,.0f}</span>"


def summary_card(period_label, income, expense, net, d_inc=None, d_exp=None, d_net=None, rate=None, sub_label="本月結餘", compare_label="較上月"):
    cls = "pos" if net >= 0 else "neg"
    rate_html = ""
    if rate is not None:
        rate_html = f"<span class='pill rate {'pos' if rate >= 0 else 'neg'}'>儲蓄率 {rate:.0%}</span>"
    delta_top = f"<div class='hero-delta'><span class='mut'>{compare_label}</span> {_delta(d_net)}</div>" if d_net is not None else ""
    delta_inc_html = f"<div class='hero-delta'>{_delta(d_inc)}</div>" if d_inc is not None else ""
    delta_exp_html = f"<div class='hero-delta'>{_delta(d_exp, invert=True)}</div>" if d_exp is not None else ""
    st.markdown(
        f"<div class='hero'>"
        f"<div class='hero-top'><div class='hero-label'>{period_label} {sub_label}</div>{rate_html}</div>"
        f"<div class='hero-amount {cls}'>{money(net)}</div>"
        f"{delta_top}"
        f"<div class='hero-row'>"
        f"<div class='hero-col'><div class='hero-label'>收入</div><div class='v'>{money(income)}</div>"
        f"{delta_inc_html}</div>"
        f"<div class='hero-col'><div class='hero-label'>支出</div><div class='v'>{money(expense)}</div>"
        f"{delta_exp_html}</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


def budget_card(name, spent, limit):
    ratio = spent / limit if limit > 0 else 0
    status = "over" if ratio >= 1 else ("warn" if ratio >= 0.8 else "ok")
    left = limit - spent
    left_txt = f"剩餘 ${left:,.0f}" if left >= 0 else f"超支 ${-left:,.0f}"
    st.markdown(
        f"<div class='bud'>"
        f"<div class='bud-top'><b>{html.escape(str(name))}</b><span class='t-{status}'>{ratio:.0%}</span></div>"
        f"<div class='bud-sub'>${spent:,.0f} /${limit:,.0f} {left_txt}</div>"
        f"<div class='bud-bar bud-{status}'><i style='width:{min(ratio, 1) * 100:.1f}%'></i></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def installment_card(title, paid_cnt, total_cnt, per_amt, remain_amt, end_ym):
    ratio = paid_cnt / total_cnt if total_cnt > 0 else 0
    rem_cnt = max(0, total_cnt - paid_cnt)
    st.markdown(
        f"<div class='bud'>"
        f"<div class='bud-top'><b>{html.escape(str(title))}</b><span class='t-inst'>已繳 {paid_cnt}/{total_cnt} 期（剩 {rem_cnt} 期）</span></div>"
        f"<div class='bud-sub'>每期 ${per_amt:,.0f} 未清償餘額 ${remain_amt:,.0f} 預計 {end_ym} 繳清</div>"
        f"<div class='bud-bar bud-inst'><i style='width:{min(ratio, 1) * 100:.1f}%'></i></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ======================= 基本設定 =======================
st.set_page_config(page_title="我是有錢人", page_icon="💰", layout="wide")


def get_secret(name, default=""):
    for k in (name, name.lower(), name.upper()):
        if k in st
