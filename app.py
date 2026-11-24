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
    y_title = ""
    try:
        y_title = fig.layout.yaxis.title.text or ""
    except Exception:
        y_title = ""

    has_y_label = y_title in ("金額", "總金額")
    fig.update_layout(
        margin=dict(l=72 if has_y_label else 8, r=12, t=48, b=8),
        title=dict(font=dict(size=15), x=0, xanchor="left"),
        legend=dict(title_text="", orientation="h", y=-0.25, x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="PingFang TC, Microsoft JhengHei, Noto Sans TC, sans-serif", size=12),
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(title_text="", showgrid=False, linecolor="rgba(128,128,128,.3)")
    fig.update_yaxes(title_text="", gridcolor="rgba(128,128,128,.15)", zeroline=False)

    if has_y_label:
        fig.add_annotation(
            text="<br>".join(list(y_title)),
            xref="paper", yref="paper",
            x=0, y=0.5,
            xanchor="right", yanchor="middle",
            xshift=-48,
            textangle=0,
            showarrow=False,
            font=dict(size=12, color="rgba(140,148,166,0.95)"),
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
        f"<div class='bud-sub'>${spent:,.0f} / ${limit:,.0f} {left_txt}</div>"
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
EXPENSE_CATS = ["伙食", "交通", "購物", "娛樂", "醫療", "其他支出", "每月固定費用"]
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
        base_name = m.group(1).strip()
        cur_idx = int(m.group(2))
        tot_cnt = int(m.group(3))
        ym = str(r["年月"])
        amt = float(r["金額_num"])

        if ym > ref_ym:
            future_by_month[ym] = future_by_month.get(ym, 0.0) + amt

        key = (base_name, tot_cnt, r["分類"])
        g = groups.setdefault(key, {
            "title": base_name,
            "total_cnt": tot_cnt,
            "paid_cnt": 0,
            "remain_amt": 0.0,
            "per_amt": amt,
            "end_ym": ym,
        })
        if ym <= ref_ym:
            g["paid_cnt"] = max(g["paid_cnt"], cur_idx)
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

_missing_cats = []
if "醫療" not in EXPENSE_CATS:
    EXPENSE_CATS.append("醫療")
    _missing_cats.append(["支出", "醫療"])
if "其他支出" not in EXPENSE_CATS:
    EXPENSE_CATS.append("其他支出")
    _missing_cats.append(["支出", "其他支出"])
if "每月固定費用" not in EXPENSE_CATS:
    EXPENSE_CATS.append("每月固定費用")
    _missing_cats.append(["支出", "每月固定費用"])
if "薪資" not in INCOME_CATS:
    INCOME_CATS.append("薪資")
    _missing_cats.append(["收入", "薪資"])

EXPENSE_CATS = sort_expense_cats(EXPENSE_CATS)

if _missing_cats and cat_ws and _cat_rows:
    try:
        cat_ws.append_rows(_missing_cats)
        fetch_config_bundle.clear()
    except Exception:
        pass


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

    with st.container(key="month_nav"):
        nav1, nav2, nav3 = st.columns([1, 3, 1])
        nav1.button("", icon=":material/chevron_left:", help="上個月", key="btn_prev",
                    on_click=shift_month, args=(-1,), **STRETCH)
        nav2.selectbox("月份", all_months, key="month_sel", label_visibility="collapsed")
        nav3.button("", icon=":material/chevron_right:", help="下個月", key="btn_next",
                    on_click=shift_month, args=(1,), **STRETCH)
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
        tab_general, tab_salary, tab_fixed, tab_budget = st.tabs(["記一筆", "薪資", "固定", "預算設定"])

        @st.fragment
        def add_entry_form():
            for wkey, lkey in (("gen_type", "_last_type"), ("gen_cat", "_last_cat"), ("gen_pay", "_last_pay")):
                if wkey not in st.session_state and lkey in st.session_state:
                    st.session_state[wkey] = st.session_state[lkey]
            tx_type = st.radio("類型", ["支出", "收入"], horizontal=True, key="gen_type")
            cat_options = EXPENSE_CATS if tx_type == "支出" else INCOME_CATS
            if st.session_state.get("gen_cat") not in cat_options:
                st.session_state.pop("gen_cat", None)
            category = st.selectbox("分類", cat_options, key="gen_cat")
            amount = st.number_input("金額", value=None, step=1, min_value=0, placeholder="請輸入金額...", key=f"amt_{ver}")
            pay_method = st.selectbox("付款方式", PAY_OPTIONS, key="gen_pay")
            st.session_state.update(_last_type=tx_type, _last_cat=category, _last_pay=pay_method)

            installments = 1
            if tx_type == "支出" and pay_method == "信用卡":
                installments = st.number_input(
                    "分期期數（1 = 不分期）",
                    min_value=1, max_value=36, value=1, step=1,
                    key=f"inst_{ver}",
                )

            tx_date = st.date_input("日期（首期入帳日）" if installments > 1 else "日期", value=TODAY)
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

        with tab_budget:
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

    # ---------- 記帳明細 ----------
    elif view_mode == MODE_LIST:
        st.subheader(f"{selected_month} 記帳明細")

        if not df.empty:
            dirty_df = df[df["_raw_note"] != df["備註"]]
            if not dirty_df.empty:
                c_msg, c_btn = st.columns([3, 1.5])
                c_msg.info(f"偵測到試算表底層有 {len(dirty_df)} 筆自動通知備註可清理並格式化（畫面已自動轉換）。")
                if c_btn.button("一鍵永久更新試算表", key="btn_clean_vars", **STRETCH):
                    try:
                        updates = [
                            {"range": f"F{int(r['_row'])}", "values": [[r["備註"]]]}
                            for _, r in dirty_df.iterrows()
                        ]
                        worksheet.batch_update(updates, value_input_option="RAW")
                        clear_data_cache()
                        flash_and_rerun(f"已永久更新試算表中的 {len(updates)} 筆備註！")
                    except Exception as e:
                        st.error(f"更新失敗：{e}")

        if not df_selected.empty:
            uncat_df = df_selected[(df_selected["類型"] == "支出") & (df_selected["分類"] == "其他支出")]
            if not uncat_df.empty:
                with st.expander(f"🏷️ 本月有 {len(uncat_df)} 筆「其他支出」待確認分類（點此快速歸類）", expanded=False):
                    st.caption("直接下拉修改正確分類，改好後按「套用分類修改」即可。")
                    quick_cat_disp = uncat_df[["日期", "金額", "付款方式", "備註", "分類"]].copy()
                    edited_quick_cat = st.data_editor(
                        quick_cat_disp,
                        hide_index=True,
                        disabled=["日期", "金額", "付款方式", "備註"],
                        key=f"quick_cat_{ver}_{selected_month}",
                        column_config={
                            "分類": st.column_config.SelectboxColumn("分類", options=EXPENSE_CATS, required=True),
                        },
                        **STRETCH,
                    )
                    if st.button("套用分類修改", type="primary", key="btn_apply_quick_cat"):
                        try:
                            changed_q = [
                                i for i in edited_quick_cat.index
                                if str(edited_quick_cat.loc[i, "分類"]).strip() != "其他支出"
                            ]
                            if not changed_q:
                                st.info("尚未變更任何分類。")
                            else:
                                updates = [
                                    {"range": f"C{int(df_selected.loc[i, '_row'])}", "values": [[str(edited_quick_cat.loc[i, "分類"]).strip()]]}
                                    for i in changed_q
                                ]
                                worksheet.batch_update(updates, value_input_option="RAW")
                                clear_data_cache()
                                flash_and_rerun(f"已將 {len(changed_q)} 筆支出歸類完成！")
                        except Exception as e:
                            st.error(f"更新分類失敗：{e}")

        if not df_selected.empty:
            st.download_button(
                "匯出本月 CSV",
                df_selected[FIELDS].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"記帳_{selected_month}.csv",
                mime="text/csv",
                icon=":material/download:",
            )

            f1, f2, f3 = st.columns([2, 2, 3])
            cat_filter = f1.multiselect("分類", EXPENSE_CATS + INCOME_CATS)
            pay_filter = f2.multiselect("付款方式", PAY_OPTIONS)
            kw = f3.text_input("搜尋備註")

            mask = pd.Series(True, index=df_selected.index)
            if cat_filter:
                mask &= df_selected["分類"].isin(cat_filter)
            if pay_filter:
                mask &= df_selected["付款方式"].isin(pay_filter)
            if kw.strip():
                mask &= df_selected["備註"].str.contains(kw.strip(), case=False, regex=False)

            view = df_selected[mask]
            v1, v2, v3 = st.columns(3)
            v1.metric("筆數", f"{len(view)}")
            v2.metric("收入", f"${view.loc[view['類型'] == '收入', '金額_num'].sum():,.0f}")
            v3.metric("支出", f"${view.loc[view['類型'] == '支出', '金額_num'].sum():,.0f}")
            filter_sig = abs(hash((tuple(cat_filter), tuple(pay_filter), kw.strip())))

            def render_tx_editor(sub_df, tx_kind, cat_opts, key_suffix):
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
                        "分類": st.column_config.SelectboxColumn("分類", options=cat_opts, width="small", required=True),
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
                                targets = df_selected.loc[checked]
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
                            orig_df = df_selected.loc[save_df.index, FIELDS].astype(str)
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
                                    n = int(df_selected.loc[i, "_row"])
                                    if errs:
                                        error_lines.append(f"**試算表第 {n} 列**：" + "；".join(errs))
                                    else:
                                        cleaned[i] = (n, clean_row)

                                if error_lines:
                                    st.error("以下資料格式有問題，尚未儲存：\n\n" + "\n\n".join(error_lines))
                                elif not rows_still_match(worksheet, df_selected.loc[changed_idx]):
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

            render_tx_editor(view[view["類型"] == "支出"], "支出", EXPENSE_CATS, "exp")
            render_tx_editor(view[view["類型"] == "收入"], "收入", INCOME_CATS, "inc")
        else:
            st.info(f"所選月份 {selected_month} 目前還沒有任何記錄！")

        st.divider()
        st.download_button(
            "下載全部記帳資料（CSV）",
            df[FIELDS].to_csv(index=False).encode("utf-8-sig"),
            file_name="記帳_全部資料.csv",
            mime="text/csv",
            icon=":material/download:",
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
                valid = df[df["年月"].str.fullmatch(r"\d{4}-\d{2}", na=False)]
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
                        long, x="年月", y="金額", color="類型", markers=True, title="近 12 個月收支趨勢",
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
            st.info(f"尚未設定預算，請到「{MODE_ADD}」→「預算設定」設定。")
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
        if active_inst:
            total_rem_debt = sum(x["remain_amt"] for x in active_inst)
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
        all_inc, all_exp = sums(df)
        all_net = all_inc - all_exp
        if goal and goal > 0:
            g_ratio = all_net / goal
            st.progress(
                float(min(max(g_ratio, 0.0), 1.0)),
                text=f"{max(g_ratio, 0):.0%}（累計結餘 ${all_net:,.0f} / 目標 ${goal:,.0f}）",
            )
            if all_net >= goal:
                st.success("已達成儲蓄目標！")
            else:
                st.caption(f"還差 ${goal - all_net:,.0f}")
        else:
            st.caption(f"尚未設定儲蓄目標，可到「{MODE_ADD}」→「預算設定」設定。")

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
