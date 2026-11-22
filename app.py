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
PALETTE = [ACCENT, INCOME_COLOR, "#D9A441", EXPENSE_COLOR, "#B48EAD", "#7BAE9A", "#8A94A6"]
CAT_COLORS = {
    "伙食": "#5B8FB9", "交通": "#7BAE9A", "購物": "#B48EAD",
    "娛樂": "#D4A76A", "每月固定費用": "#8A94A6", "其他支出": "#A9B8C9",
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
.st-key-btn_delete button { color:var(--expense) !important; border-color:var(--expense) !important; }
.st-key-btn_delete button:hover { background:var(--expense-soft) !important; }

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

/* ---------- 預算卡 ---------- */
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
.t-ok { color:var(--income); font-weight:600; } .t-warn { color:var(--warning); font-weight:600; } .t-over { color:var(--expense); font-weight:700; }
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
    fig.update_layout(
        margin=dict(l=8, r=8, t=48, b=8),
        title=dict(font=dict(size=15), x=0, xanchor="left"),
        legend=dict(title_text="", orientation="h", y=-0.2, x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="PingFang TC, Microsoft JhengHei, Noto Sans TC, sans-serif", size=12),
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor="rgba(128,128,128,.3)")
    fig.update_yaxes(gridcolor="rgba(128,128,128,.15)", zeroline=False)
    st.plotly_chart(fig, theme="streamlit", **stretch)


def money(n):
    return f"-${abs(n):,.0f}" if n < 0 else f"${n:,.0f}"


def _delta(v, invert=False):
    if round(v) == 0:
        return "<span class='pill zero'>±0</span>"
    good = (v <= 0) if invert else (v >= 0)
    sign = "+" if v > 0 else "-"
    return f"<span class='pill {'pos' if good else 'neg'}'>{sign}{abs(v):,.0f}</span>"


def summary_card(month, income, expense, net, d_inc, d_exp, d_net, rate=None):
    cls = "pos" if net >= 0 else "neg"
    rate_html = ""
    if rate is not None:
        rate_html = f"<span class='pill rate {'pos' if rate >= 0 else 'neg'}'>儲蓄率 {rate:.0%}</span>"
    st.markdown(
        f"<div class='hero'>"
        f"<div class='hero-top'><div class='hero-label'>{month} 本月結餘</div>{rate_html}</div>"
        f"<div class='hero-amount {cls}'>{money(net)}</div>"
        f"<div class='hero-delta'><span class='mut'>較上月</span> {_delta(d_net)}</div>"
        f"<div class='hero-row'>"
        f"<div class='hero-col'><div class='hero-label'>收入</div><div class='v'>{money(income)}</div>"
        f"<div class='hero-delta'>{_delta(d_inc)}</div></div>"
        f"<div class='hero-col'><div class='hero-label'>支出</div><div class='v'>{money(expense)}</div>"
        f"<div class='hero-delta'>{_delta(d_exp, invert=True)}</div></div>"
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
EXPENSE_CATS = ["伙食", "交通", "購物", "娛樂", "每月固定費用", "其他支出"]
INCOME_CATS = ["薪資", "其他收入"]
FIELDS = ["日期", "類型", "分類", "金額", "付款方式", "備註"]
SETTINGS_HEADER = ["項目名稱", "預設金額", "付款方式", "扣款日"]
BUDGET_HEADER = ["分類", "每月上限"]
CONFIG_HEADER = ["項目", "值"]
CFG_SALARY = "預設月薪"
CFG_GOAL = "儲蓄目標"
WEEKDAY_NAMES = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
TOTAL_KEY = "總預算"
CACHE_TTL = 60
CACHE_TTL_CFG = 600

MODE_ADD = "記帳"
MODE_LIST = "明細"
MODE_CHART = "圖表"
MODE_BUDGET = "預算"
MODE_CAL = "月曆"


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
    "<div class='app-header'><h1>我是有錢人</h1>"
    "<p>一天一塊錢，七天就有七塊錢</p></div>"
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

    # 檢查 redirect_uri 是否包含 /oauth2callback，避免觸發 Internal server error
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
if "editor_ver" not in st.
