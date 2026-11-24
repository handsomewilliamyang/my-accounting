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
        f"<div class='bud-sub'>${spent:,.0f} / ${limit:,.0f} {left_txt}</div>"
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
    """將日期往後推 offset 個月（自動處理月底日期，例如 1/31 + 1 個月 = 2/28）"""
    total_m = base_date.year * 12 + (base_date.month - 1) + offset
    y, m = divmod(total_m, 12)
    m += 1
    last_day = py_calendar.monthrange(y, m)[1]
    return date(y, m, min(base_date.day, last_day))


def split_installments(total_amt, months):
    """將總金額平分為 months 期（整數除法，餘數加在第一期）"""
    total_int = int(round(total_amt))
    base = total_int // months
    rem = total_int % months
    return [base + (1 if i < rem else 0) for i in range(months)]


def pad_row(row, n=6):
    return list(row[:n]) + [""] * max(0, n - len(row))


def to_number(v):
    s = str(v).strip().replace(",", "")
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return str(v).strip()


def flash_and_rerun(msg):
    st.session_state["flash"] = msg
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
    [["類型", "分類"]] + [["支出", c] for c in EXPENSE_CATS] + [["收入", c] for c in INCOME_CATS],
)
config_ws = get_ws("系統設定", 20, 2, [CONFIG_HEADER, [CFG_SALARY, 45000], [CFG_GOAL, 0]])

CFG_SHEETS = (
    ("固定支出設定", 4),
    ("預算設定", 2),
    ("分類設定", 2),
    ("系統設定", 2),
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


# ======================= 分類設定 =======================
_cat_rows = load_rows(cat_ws, "分類設定")
_exp = [c.strip() for t, c in _cat_rows if t.strip() == "支出" and c.strip()]
_inc = [c.strip() for t, c in _cat_rows if t.strip() == "收入" and c.strip()]
if _exp:
    EXPENSE_CATS = _exp
if _inc:
    INCOME_CATS = _inc
if "每月固定費用" not in EXPENSE_CATS:
    EXPENSE_CATS.append("每月固定費用")
if "薪資" not in INCOME_CATS:
    INCOME_CATS.append("薪資")


# ======================= 系統設定 =======================
config_rows = load_rows(config_ws, "系統設定")
config = {str(r[0]).strip(): r[1] for r in config_rows}


def cfg_num(key, default):
    v = to_number(config.get(key, default))
    return default if isinstance(v, str) else v


def save_config(key, value):
    data = config_ws.get_all_values()
    for i, r in enumerate(data[1:], start=2):
        if r and str(r[0]).strip() == key:
            config_ws.update(range_name=f"B{i}", values=[[value]])
            break
    else:
        config_ws.append_row([key, value])
    fetch_config_bundle.clear()


def render_budget_banner(df_month, total_spent, budgets, month_label):
    limit = budgets.get(TOTAL_KEY)
    if limit:
        ratio = total_spent / limit
        if ratio >= 1:
            st.error(f"已超出總預算 ${total_spent - limit:,.0f}！（${total_spent:,.0f} /${limit:,.0f}）")
        elif ratio >= 0.8:
            st.warning(f"總預算已使用 {ratio:.0%}，本月只剩 ${limit - total_spent:,.0f}。")

    over = []
    exp = df_month[df_month["類型"] == "支出"]
    for cat, lim in budgets.items():
        if cat == TOTAL_KEY or lim <= 0:
            continue
        spent = exp.loc[exp["分類"] == cat, "金額_num"].sum()
        if spent >= lim:
            over.append(f"{cat}（${spent:,.0f} /${lim:,.0f}）")
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
                f"（試算表第 {', '.join(map(str, bad_rows['_row']))} 列），不會出現在月份篩選
