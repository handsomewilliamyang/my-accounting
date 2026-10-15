import hmac
import html
import re
import time
import calendar as py_calendar
from datetime import date, datetime, timedelta, timezone

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

# ======================= 基本設定 =======================
st.set_page_config(page_title="我是有錢人", page_icon="💰", layout="wide")


def get_secret(name, default=""):
    """讀取 Secrets（不分大小寫：SPREADSHEET_URL / spreadsheet_url 都可以）"""
    for k in (name, name.lower(), name.upper()):
        if k in st.secrets:
            return st.secrets[k]
    return default


# 試算表網址：只從 Streamlit Secrets 讀取，不把網址寫在程式碼裡
SPREADSHEET_URL = str(get_secret("SPREADSHEET_URL", "")).strip()

# 台灣時區（伺服器通常是 UTC，凌晨記帳時 date.today() 會差一天）
TW_TZ = timezone(timedelta(hours=8))


def today():
    return datetime.now(TW_TZ).date()


TODAY = today()

# ----- 視覺風格：統一色票（收入綠、支出紅、強調藍，其餘低彩度） -----
ACCENT = "#4C78A8"
INCOME_COLOR = "#4FB286"
EXPENSE_COLOR = "#E06C75"
PALETTE = [ACCENT, "#4FB286", "#E9A23B", "#E06C75", "#9B7FD1", "#4DB6C4", "#C2A878"]
CAT_COLORS = {
    "伙食": "#4FB286", "交通": "#5B8DEF", "購物": "#C879A6",
    "娛樂": "#E9A23B", "每月固定費用": "#E06C75", "其他支出": "#9B7FD1",
}
px.defaults.color_discrete_sequence = PALETTE

# 統一的選項清單（支出/收入分類之後會被「分類設定」分頁覆蓋）
PAY_OPTIONS = ["現金", "信用卡", "行動支付"]
EXPENSE_CATS = ["伙食", "交通", "購物", "娛樂", "每月固定費用", "其他支出"]
INCOME_CATS = ["薪資", "其他收入"]
FIELDS = ["日期", "類型", "分類", "金額", "付款方式", "備註"]
SETTINGS_HEADER = ["項目名稱", "預設金額", "付款方式", "扣款日"]
BUDGET_HEADER = ["分類", "每月上限"]
TRASH_HEADER = FIELDS + ["刪除時間"]
TRASH_COLS = ["_row"] + TRASH_HEADER
CONFIG_HEADER = ["項目", "值"]
CFG_SALARY = "預設月薪"
CFG_GOAL = "儲蓄目標"
WEEKDAY_NAMES = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
TOTAL_KEY = "總預算"
CACHE_TTL = 60  # 記帳資料的快取秒數（多裝置同步更快）
CACHE_TTL_CFG = 600  # 設定類分頁很少改，快取久一點（儲存時會手動清除；其他裝置改的最多 10 分鐘後同步）

# 檢視模式名稱（統一定義，避免各處字串不一致）
MODE_ADD = "新增與設定"
MODE_LIST = "記帳明細"
MODE_CHART = "圖表分析"
MODE_BUDGET = "預算追蹤"
MODE_CAL = "月曆"
MODE_COMPARE = "比較與年度"


def _ver_tuple():
    parts = []
    for p in st.__version__.split(".")[:2]:
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


# 新版 Streamlit 用 width="stretch"，舊版用 use_container_width
STRETCH = {"width": "stretch"} if _ver_tuple() >= (1, 50) else {"use_container_width": True}

# 樣式（同時相容深色 / 淺色主題；顏色一律用半透明灰，自動跟隨主題）
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;600&display=swap');

    .stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        font-family: "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
    }

    /* 版面：限制最大寬度，置中 */
    div.block-container, div[data-testid="stMainBlockContainer"] {
        max-width: 1180px;
        padding-top: 2.2rem;
        padding-bottom: 4rem;
    }

    /* 標題區 */
    .app-header { margin: 0 0 1.4rem; }
    .app-header h1 { font-size: 1.85rem; font-weight: 600; letter-spacing: .02em; margin: 0; padding: 0; }
    .app-header p { margin: .25rem 0 0; opacity: .6; font-size: .95rem; }

    /* 各區塊標題 */
    .stApp h3 { font-size: 1.15rem; font-weight: 600; padding-top: .4rem; }
    .stApp h4 { font-size: 1.02rem; font-weight: 600; }

    /* 分隔線變淡 */
    .stApp hr { border-color: rgba(128, 128, 128, 0.25) !important; margin: 1.2rem 0; }

    /* 統計卡片 */
    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 12px;
        padding: 14px 18px;
    }
    div[data-testid="stMetricLabel"] { opacity: .7; font-size: .85rem; }
    div[data-testid="stMetricValue"] { font-weight: 600; }

    /* 按鈕：統一圓角與字重 */
    .stButton > button, .stDownloadButton > button {
        border-radius: 10px;
        font-weight: 500;
        padding: .45rem 1.1rem;
        border: 1px solid rgba(128, 128, 128, 0.35);
        transition: border-color .15s, background-color .15s;
    }
    .stButton > button:hover, .stDownloadButton > button:hover { border-color: #4C78A8; }
    .stButton > button[kind="primary"] { background-color: #4C78A8; border-color: #4C78A8; color: #fff; }
    .stButton > button[kind="primary"]:hover { filter: brightness(1.08); }

    /* 提示訊息、輸入元件 */
    div[data-testid="stAlert"] { border-radius: 10px; }
    div[data-baseweb="select"] > div, div[data-baseweb="input"], div[data-baseweb="base-input"] { border-radius: 10px; }
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { border-radius: 10px; overflow: hidden; }
    div[data-testid="stExpander"] { border-radius: 10px; border-color: rgba(128, 128, 128, 0.25); }

    /* 分頁標籤 */
    button[data-baseweb="tab"] { font-weight: 500; }

    /* 主導覽列：膠囊樣式（只作用在 key="view_mode" 的 radio） */
    .st-key-view_mode div[role="radiogroup"] { gap: 8px; flex-wrap: wrap; }
    .st-key-view_mode label {
        background: rgba(128, 128, 128, 0.10);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 999px;
        padding: 6px 18px;
        margin: 0;
        cursor: pointer;
        transition: background-color .15s;
    }
    .st-key-view_mode label:hover { background: rgba(128, 128, 128, 0.18); }
    .st-key-view_mode label > div:first-child { display: none; }
    .st-key-view_mode label:has(input:checked) { background: #4C78A8; border-color: #4C78A8; }
    .st-key-view_mode label:has(input:checked) p { color: #fff; }

    /* 月曆卡片 */
    .cal-card {
        background-color: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 10px;
        padding: 10px;
        min-height: 120px;
        margin-bottom: 10px;
    }
    .cal-card.today { border-color: #4C78A8; box-shadow: 0 0 0 1px #4C78A8; }
    .cal-day-header {
        font-size: 15px;
        font-weight: 600;
        margin-bottom: 6px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.3);
        padding-bottom: 4px;
        display: flex;
        justify-content: space-between;
    }
    .cal-day-total { font-size: 12px; font-weight: 400; opacity: 0.75; }
    .cal-note { font-size: 13px; opacity: 0.7; }

    /* 登入頁：標題置中、表單限寬置中 */
    div[data-testid="stHeading"] h1 { text-align: center; font-weight: 600; margin-top: 8vh; }
    div[data-testid="stForm"] { max-width: 420px; margin: 0 auto; border-radius: 12px; padding: 1.4rem; }

    /* 帶邊框的容器（預算卡片等） */
    div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px; }

    /* 手機版：縮小邊距、標題與導覽按鈕 */
    @media (max-width: 640px) {
        div.block-container, div[data-testid="stMainBlockContainer"] {
            padding-left: 1rem; padding-right: 1rem; padding-top: 1.2rem;
        }
        .app-header h1 { font-size: 1.5rem; }
        .st-key-view_mode label { padding: 5px 12px; font-size: .9rem; }
        div[data-testid="stMetric"] { padding: 10px 14px; }
        .cal-card { min-height: 90px; padding: 6px; }
    }
</style>
""", unsafe_allow_html=True)


def show(fig):
    """統一的圖表呈現：一致的邊距、標題大小，並隱藏圖例標題"""
    fig.update_layout(margin=dict(l=10, r=10, t=56, b=10), title_font_size=15, legend_title_text="")
    st.plotly_chart(fig, **STRETCH)


# ======================= 密碼登入 =======================
# 密碼只存在「伺服器端」的 Streamlit Secrets（APP_PASSWORD）：
# 不在程式碼裡、不會傳到瀏覽器，用 F12 看不到；比對也是在伺服器上完成。
MAX_FAILS = 5
LOCK_SECONDS = 300
IDLE_SECONDS = 1800  # 閒置 30 分鐘自動登出


@st.cache_resource
def _login_tracker():
    # 全站共用的失敗計數（重新整理頁面也無法重置）
    return {"fails": 0, "locked_until": 0.0}


REMEMBER_DAYS = 30
COOKIE_NAME = "wealth_auth"


def _sign(expiry, key):
    return hmac.new(key.encode("utf-8"), str(expiry).encode("utf-8"), "sha256").hexdigest()


def make_token(key):
    # 憑證 = 到期時間 + 用密碼簽的簽章；沒有密碼就偽造不出來，換密碼後舊憑證全部失效
    exp = int(time.time()) + REMEMBER_DAYS * 86400
    return f"{exp}.{_sign(exp, key)}"


def token_valid(token, key):
    try:
        exp_s, sig = str(token).split(".", 1)
        return int(exp_s) > time.time() and hmac.compare_digest(sig, _sign(int(exp_s), key))
    except (ValueError, TypeError):
        return False


def set_cookie_js(value, days):
    # 在瀏覽器寫入 / 清除 cookie（days=0 代表刪除）；HTTPS 下會加 Secure
    components.html(
        f"<script>document.cookie = '{COOKIE_NAME}={value}; max-age={days * 86400}; path=/; SameSite=Strict'"
        f" + (location.protocol === 'https:' ? '; Secure' : '');</script>",
        height=0,
    )


def require_login():
    expected = str(get_secret("APP_PASSWORD", ""))
    if not expected:
        st.error("尚未設定 APP_PASSWORD，為了安全程式已停止。請到 Streamlit Secrets 加入：APP_PASSWORD = 「你的密碼」")
        st.stop()

    # 已登入：「記住我」的裝置不會閒置登出；其他裝置閒置超過 30 分鐘自動登出
    if st.session_state.get("authed"):
        idle = time.time() - st.session_state.get("last_active", 0) > IDLE_SECONDS
        if idle and not st.session_state.get("remember"):
            st.session_state.clear()
            st.warning("閒置過久，已自動登出，請重新登入。")
        else:
            st.session_state["last_active"] = time.time()
            if "set_cookie" in st.session_state:
                set_cookie_js(st.session_state.pop("set_cookie"), REMEMBER_DAYS)
            return

    # 瀏覽器帶著有效憑證 → 直接登入（剛按過登出的這個連線除外）
    if not st.session_state.get("no_autologin"):
        try:
            tok = st.context.cookies.get(COOKIE_NAME)
        except Exception:
            tok = None
        if tok and token_valid(tok, expected):
            st.session_state.update(authed=True, remember=True, last_active=time.time())
            return

    if st.session_state.pop("clear_cookie", False):
        set_cookie_js("", 0)

    tracker = _login_tracker()
    st.title("我是有錢人")
    wait = tracker["locked_until"] - time.time()
    if wait > 0:
        st.error(f"錯誤次數過多，請 {int(wait // 60)} 分 {int(wait % 60)} 秒後再試。")
        st.stop()

    with st.form("login_form"):
        pwd = st.text_input("請輸入密碼", type="password")
        remember = st.checkbox(f"在這台裝置記住我（{REMEMBER_DAYS} 天內免登入）", value=True)
        submitted = st.form_submit_button("登入")

    if submitted:
        if hmac.compare_digest(pwd.encode("utf-8"), expected.encode("utf-8")):
            tracker["fails"] = 0
            st.session_state.pop("no_autologin", None)
            st.session_state.update(authed=True, remember=remember, last_active=time.time())
            if remember:
                st.session_state["set_cookie"] = make_token(expected)
            st.rerun()
        else:
            tracker["fails"] += 1
            if tracker["fails"] >= MAX_FAILS:
                tracker["locked_until"] = time.time() + LOCK_SECONDS
                tracker["fails"] = 0
                st.error("錯誤次數過多，已暫時鎖定 5 分鐘。")
            else:
                time.sleep(1)  # 拖慢暴力猜測
                st.error(f"密碼錯誤（還有 {MAX_FAILS - tracker['fails']} 次機會）")
    st.stop()


require_login()

# 操作成功訊息（rerun 後仍能顯示）
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"), icon="✅")
if "editor_ver" not in st.session_state:
    st.session_state.editor_ver = 0

st.markdown(
    "<div class='app-header'><h1>我是有錢人</h1><p>一天一塊錢　七天就有七塊錢</p></div>",
    unsafe_allow_html=True,
)


# ======================= 工具函數 =======================
def pad_row(row, n=6):
    return list(row[:n]) + [""] * max(0, n - len(row))


def to_number(v):
    """能轉成數字就轉成數字（寫入試算表時金額才會是數字而非文字）"""
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
    """讀取失敗時顯示錯誤並回傳預設值（失敗的結果不會被快取，下次操作會自動重試）"""
    try:
        return fn(arg)
    except Exception as e:
        st.warning(f"讀取「{label}」失敗：{e}（可按「重新整理」重試）")
        return default


def prev_month_str(ym):
    y, m = map(int, ym.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def md_escape(s):
    # 跳脫備註等使用者輸入的文字，避免被當成 Markdown 語法（含 $ 公式）
    return re.sub(r"([\\`*_{}\[\]()#+\-!|~$<>])", r"\\\1", str(s))


def sums(d):
    """回傳 (總收入, 總支出)；空表也安全"""
    return (
        d.loc[d["類型"] == "收入", "金額_num"].sum(),
        d.loc[d["類型"] == "支出", "金額_num"].sum(),
    )


# ======================= 連線 Google 試算表 =======================
@st.cache_resource
def get_google_sheet():
    # 失敗時直接丟出例外，cache_resource 不會把失敗結果存起來，下次會自動重試
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
def get_main_ws(_sh):
    return _sh.get_worksheet(0)


worksheet = get_main_ws(sh) if sh else None


@st.cache_resource
def _open_ws(_sh, title, rows, cols, init_rows):
    # 找得到分頁就直接用；找不到就建立並寫入初始內容
    try:
        return _sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = _sh.add_worksheet(title=title, rows=rows, cols=cols)
        ws.append_rows(init_rows)
        return ws


def get_ws(title, rows, cols, init_rows):
    if not sh:
        return None
    try:
        return _open_ws(sh, title, rows, cols, init_rows)
    except Exception as e:
        st.warning(f"無法取得「{title}」分頁：{e}")
        return None


# 先確保各分頁都存在（找不到會自動建立）
settings_ws = get_ws(
    "固定支出設定", 100, 4,
    [SETTINGS_HEADER, ["孝親費", "5000", "現金", "5"], ["電信費", "599", "信用卡", "10"]],
)
budget_ws = get_ws("預算設定", 50, 2, [BUDGET_HEADER, [TOTAL_KEY, 30000], ["伙食", 8000]])
cat_ws = get_ws(
    "分類設定", 100, 2,
    [["類型", "分類"]] + [["支出", c] for c in EXPENSE_CATS] + [["收入", c] for c in INCOME_CATS],
)
trash_ws = get_ws("垃圾桶", 500, 7, [TRASH_HEADER])
config_ws = get_ws("系統設定", 20, 2, [CONFIG_HEADER, [CFG_SALARY, 45000], [CFG_GOAL, 0]])

CFG_SHEETS = (("固定支出設定", 4), ("預算設定", 2), ("分類設定", 2), ("系統設定", 2))


@st.cache_data(ttl=CACHE_TTL_CFG)
def fetch_config_bundle(_sh):
    # 一次 API 呼叫讀完 4 個設定分頁（原本要 4 次）。失敗時丟出例外，不會被快取；寫入後記得 fetch_config_bundle.clear()
    ranges = [f"'{t}'!A:Z" for t, _ in CFG_SHEETS]
    try:
        value_ranges = [vr.get("values", []) for vr in _sh.values_batch_get(ranges).get("valueRanges", [])]
    except AttributeError:  # 舊版 gspread 沒有這個方法時，退回逐頁讀取
        value_ranges = [_sh.worksheet(t).get_all_values() for t, _ in CFG_SHEETS]
    out = {}
    for (title, n), values in zip(CFG_SHEETS, value_ranges):
        rows = [pad_row(r, n) for r in values[1:]]
        out[title] = [r for r in rows if str(r[0]).strip()]
    return out


_cfg_loaded = {}


def load_rows(ws, label):
    # 設定類分頁共用同一份快取資料；第一次呼叫時才實際讀取
    if not ws:
        return []
    if "data" not in _cfg_loaded:
        _cfg_loaded["data"] = safe_load(fetch_config_bundle, sh, {}, "設定分頁")
    return _cfg_loaded["data"].get(label, [])


def parse_day(v):
    # 扣款日：1–31 的整數，其他（含空白）一律視為「未設定」
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


# ======================= 分類設定（從試算表讀取） =======================
_cat_rows = load_rows(cat_ws, "分類設定")
_exp = [c.strip() for t, c in _cat_rows if t.strip() == "支出" and c.strip()]
_inc = [c.strip() for t, c in _cat_rows if t.strip() == "收入" and c.strip()]
if _exp:
    EXPENSE_CATS = _exp
if _inc:
    INCOME_CATS = _inc
# 程式邏輯依賴這兩個分類，缺少時自動補上
if "每月固定費用" not in EXPENSE_CATS:
    EXPENSE_CATS.append("每月固定費用")
if "薪資" not in INCOME_CATS:
    INCOME_CATS.append("薪資")


# ======================= 垃圾桶（刪除後可還原） =======================
@st.cache_data(ttl=CACHE_TTL)
def fetch_trash(_trash_ws):
    if not _trash_ws:
        return pd.DataFrame(columns=TRASH_COLS)
    raw = _trash_ws.get_all_values()
    rows = []
    for i, row in enumerate(raw[1:]):
        p = pad_row(row, 7)
        if not any(str(c).strip() for c in p):
            continue
        rec = {"_row": i + 2}
        for name, val in zip(TRASH_HEADER, p):
            rec[name] = str(val).strip()
        rows.append(rec)
    if not rows:
        return pd.DataFrame(columns=TRASH_COLS)
    return pd.DataFrame(rows)


# ======================= 系統設定（預設月薪、儲蓄目標） =======================
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
        st.progress(
            float(min(ratio, 1.0)),
            text=f"{month_label} 總預算已使用 {ratio:.0%}（${total_spent:,.0f} / ${limit:,.0f}）",
        )
        if ratio >= 1:
            st.error(f"已超出總預算 ${total_spent - limit:,.0f}！")
        elif ratio >= 0.8:
            st.warning(f"已使用 {ratio:.0%}，本月只剩 ${limit - total_spent:,.0f}。")

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
DF_COLS = ["_row"] + FIELDS + ["年月", "日期_std", "金額_num"]


@st.cache_data(ttl=CACHE_TTL)
def fetch_data(_sh):
    """讀取記帳主表。讀取失敗時直接丟出例外（失敗結果不會被快取）。"""
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
            continue  # 空白列略過（但列號仍照實際位置計算）
        rec = {"_row": r_idx + 2}  # 試算表實際列號（標題為第 1 列）
        for name, val in zip(FIELDS, p):
            rec[name] = str(val).strip()
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
    """讓所有 data_editor 換一個新的 key，清掉舊的編輯狀態（避免儲存後重複新增或顯示錯亂）"""
    st.session_state.editor_ver += 1


def clear_data_cache():
    fetch_data.clear()
    bump_editor()


def rows_still_match(ws, df_rows):
    """寫入前確認雲端那幾列仍和畫面上一致（只讀取需要的列，速度較快）"""
    ranges = [f"A{int(n)}:F{int(n)}" for n in df_rows["_row"]]
    got = ws.batch_get(ranges)
    for (_, r), vals in zip(df_rows.iterrows(), got):
        cloud = pad_row(vals[0] if vals else [])
        for i, col in enumerate(FIELDS):
            if str(cloud[i]).strip() != str(r[col]).strip():
                return False
    return True


def delete_rows(ws, row_nos):
    """依列號刪除（由下往上，一次 API 呼叫完成）"""
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
    # 該月份是否已有這個分類（以及相同備註）的紀錄
    m = (df_all["年月"] == ym) & (df_all["分類"] == cat)
    if note is not None:
        m &= df_all["備註"] == note.strip()
    return bool(m.any())


def pending_fixed(df_all, templates, ref_date):
    # 本月已到扣款日、但還沒記錄的固定支出（以「備註 = 項目名稱」判斷是否已記錄）
    ym = ref_date.strftime("%Y-%m")
    last = py_calendar.monthrange(ref_date.year, ref_date.month)[1]
    sub = df_all[(df_all["年月"] == ym) & (df_all["分類"] == "每月固定費用")]
    done = set(sub["備註"].str.strip()) if not sub.empty else set()
    out = []
    for name, t in templates.items():
        d = t.get("day")
        if not d or t["amount"] <= 0:
            continue
        due = min(d, last)  # 例如設 31 號，2 月就算 28/29 號
        if due <= ref_date.day and name not in done:
            out.append((name, t, date(ref_date.year, ref_date.month, due)))
    return out


def validate_row(r):
    """檢查單列資料。回傳 (錯誤清單, 整理後可寫入的一列資料)"""
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

    return errs, [date_ok, typ, cat, amt, pay, str(r["備註"])]


# ======================= 主程式 =======================
if sh and worksheet:
    df = safe_load(fetch_data, sh, pd.DataFrame(columns=DF_COLS), "記帳資料")
    ver = st.session_state.editor_ver

    # 日期格式異常提示（避免資料悄悄從月份篩選中消失）
    if not df.empty:
        bad_rows = df[~df["年月"].fillna("").str.fullmatch(r"\d{4}-\d{2}")]
        if not bad_rows.empty:
            st.warning(
                f"有 {len(bad_rows)} 筆日期格式異常"
                f"（試算表第 {', '.join(map(str, bad_rows['_row']))} 列），不會出現在月份篩選中。"
            )

    # ---------- 工具列 ----------
    side_c1, side_c2, _ = st.columns([1, 1, 6])
    if side_c1.button("重新整理", **STRETCH):
        fetch_data.clear()
        fetch_config_bundle.clear()
        fetch_trash.clear()
        bump_editor()
        st.rerun()
    if side_c2.button("登出", **STRETCH):
        st.session_state.clear()
        # 清掉這台裝置的「記住我」憑證，並避免剛登出又被舊憑證自動登入
        st.session_state.update(clear_cookie=True, no_autologin=True)
        st.rerun()

    # ---------- 月份篩選（含上月／下月按鈕） ----------
    current_month_str = TODAY.strftime("%Y-%m")
    db_months = [m for m in df["年月"].dropna().unique().tolist() if re.fullmatch(r"\d{4}-\d{2}", str(m))]
    all_months = sorted(set(db_months + [current_month_str]), reverse=True)  # 新到舊

    if st.session_state.get("month_sel") not in all_months:
        st.session_state.month_sel = current_month_str

    def shift_month(step):
        i = all_months.index(st.session_state.month_sel) - step
        if 0 <= i < len(all_months):
            st.session_state.month_sel = all_months[i]

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    nav1.button("‹ 上月", on_click=shift_month, args=(-1,), **STRETCH)
    nav2.selectbox("月份", all_months, key="month_sel", label_visibility="collapsed")
    nav3.button("下月 ›", on_click=shift_month, args=(1,), **STRETCH)
    selected_month = st.session_state.month_sel

    df_selected = (
        df[df["年月"] == selected_month]
        .sort_values(["日期_std", "_row"], ascending=False)  # 預設新到舊
        .reset_index(drop=True)
    )

    # ---------- 本月統計（含與上月比較） ----------
    total_income, total_expense = sums(df_selected)
    prev_income, prev_expense = sums(df[df["年月"] == prev_month_str(selected_month)])
    net_balance = total_income - total_expense
    prev_net = prev_income - prev_expense

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(
        f"{selected_month} 總收入", f"${int(total_income):,}",
        delta=f"{int(total_income - prev_income):,}",
    )
    col_m2.metric(
        f"{selected_month} 總花費", f"${int(total_expense):,}",
        delta=f"{int(total_expense - prev_expense):,}", delta_color="inverse",
    )
    col_m3.metric(
        f"{selected_month} 本月結餘", f"${int(net_balance):,}",
        delta=f"{int(net_balance - prev_net):,}",
    )

    if total_income > 0:
        st.caption(f"本月儲蓄率：{net_balance / total_income:.0%}（結餘 ÷ 收入）")

    render_budget_banner(df_selected, total_expense, budgets, selected_month)
    n_pend = len(pending_fixed(df, fixed_templates, TODAY))
    if n_pend:
        st.info(f"有 {n_pend} 筆固定支出已到扣款日、尚未記錄，請到「{MODE_ADD}」→「固定」補登。")

    st.divider()

    view_mode = st.radio(
        "選擇檢視模式：",
        [MODE_ADD, MODE_LIST, MODE_CHART, MODE_BUDGET, MODE_CAL, MODE_COMPARE],
        horizontal=True,
        label_visibility="collapsed",
        key="view_mode",
    )
    st.divider()

    # ---------- 新增與設定 ----------
    if view_mode == MODE_ADD:
        tab_general, tab_salary, tab_fixed, tab_budget = st.tabs(["記一筆", "薪資", "固定", "預算"])

        with tab_general:
            tx_type = st.radio("類型", ["支出", "收入"], horizontal=True)
            category = st.selectbox("分類", EXPENSE_CATS if tx_type == "支出" else INCOME_CATS)
            amount = st.number_input("金額", value=None, step=1, min_value=0, placeholder="請輸入金額...", key=f"amt_{ver}")
            pay_method = st.selectbox("付款方式", PAY_OPTIONS)
            tx_date = st.date_input("日期", value=TODAY)
            note = st.text_input("備註 (例如：鮮天下、加油)", key=f"note_{ver}")

            if st.button("送出記帳", type="primary"):
                if amount is not None and amount > 0:
                    try:
                        worksheet.append_row(
                            [str(tx_date), tx_type, category, amount, pay_method, note],
                            value_input_option="RAW",
                        )
                        clear_data_cache()
                        flash_and_rerun("一般記帳新增成功！")
                    except Exception as e:
                        st.error(f"寫入失敗: {e}")
                else:
                    st.warning("請輸入有效的金額！")

        with tab_salary:
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

            # 重複入帳提醒：該月份已有「薪資」紀錄時，需勾選確認才能再記一次
            salary_dup = already_recorded(df, salary_date.strftime("%Y-%m"), "薪資")
            allow_salary_dup = True
            if salary_dup:
                st.warning(f"{salary_date.strftime('%Y-%m')} 已經有薪資紀錄了。")
                allow_salary_dup = st.checkbox("我確定要再入帳一次", key=f"allow_sal_dup_{ver}")

            if st.button("入帳本月薪資", type="primary"):
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
            # 到期未記錄的固定支出（需先在下方清單設定「扣款日」）
            pend = pending_fixed(df, fixed_templates, TODAY)
            if pend:
                lines = "\n".join(
                    f"- {n}　${t['amount']:,.0f}（{d.strftime('%m/%d')}）" for n, t, d in pend
                )
                st.info("本月已到期、尚未記錄的固定支出：\n" + lines)
                if st.button(f"一鍵補登 {len(pend)} 筆", type="primary"):
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
                st.divider()

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

            # 重複扣款提醒：同月份已有同名的固定支出時，需勾選確認才能再記一次
            fixed_dup = already_recorded(df, expense_date.strftime("%Y-%m"), "每月固定費用", expense_note)
            allow_fixed_dup = True
            if fixed_dup:
                st.warning(f"{expense_date.strftime('%Y-%m')} 已經記錄過【{expense_note.strip()}】了。")
                allow_fixed_dup = st.checkbox("我確定要再扣一次", key=f"allow_fix_dup_{ver}")

            fx1, fx2 = st.columns(2)
            with fx1:
                if st.button("扣款這筆固定支出", type="primary", **STRETCH):
                    if not allow_fixed_dup:
                        st.warning("本月已有相同項目，請先勾選「我確定要再扣一次」。")
                    else:
                        try:
                            worksheet.append_row(
                                [str(expense_date), "支出", "每月固定費用", default_expense, expense_pay, expense_note],
                                value_input_option="RAW",
                            )
                            clear_data_cache()
                            flash_and_rerun(f"成功記錄固定支出【{expense_note}】${default_expense:,}！")
                        except Exception as e:
                            st.error(f"支出記錄失敗: {e}")

            # 本月固定支出全部入帳（自動略過本月已記過的項目）
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

            st.divider()
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
                            # 先寫入新內容，再清掉多出來的舊列（避免先 clear 後寫入失敗而全部遺失）
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
        if not df_selected.empty:
            st.download_button(
                "匯出本月 CSV",
                df_selected[FIELDS].to_csv(index=False).encode("utf-8-sig"),  # utf-8-sig 讓 Excel 開啟不亂碼
                file_name=f"記帳_{selected_month}.csv",
                mime="text/csv",
            )

            # 搜尋與篩選（篩選後仍保留原本的 index，刪除與儲存邏輯不受影響）
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
            # 篩選條件改變時重置編輯狀態，避免修改套錯列
            filter_sig = abs(hash((tuple(cat_filter), tuple(pay_filter), kw.strip())))

            df_display = view[FIELDS].copy()
            df_display.insert(0, "刪除", False)

            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                key=f"expense_table_{ver}_{filter_sig}",
                column_config={
                    "刪除": st.column_config.CheckboxColumn("刪除", width="small"),
                    "日期": st.column_config.TextColumn("日期", width="small"),
                    "類型": st.column_config.SelectboxColumn("類型", options=["支出", "收入"], width="small"),
                    "分類": st.column_config.SelectboxColumn(
                        "分類", options=EXPENSE_CATS + INCOME_CATS, width="small"
                    ),
                    "金額": st.column_config.TextColumn("金額", width="small"),
                    "付款方式": st.column_config.SelectboxColumn("付款方式", options=PAY_OPTIONS, width="small"),
                    "備註": st.column_config.TextColumn("備註", width="large"),
                },
                **STRETCH,
            )

            col1, col2 = st.columns(2)

            # 刪除：先放進「垃圾桶」分頁（可還原），再依列號從主表刪除
            with col1:
                if st.button("刪除所選項目", **STRETCH):
                    checked = edited_df[edited_df["刪除"] == True].index.tolist()  # noqa: E712
                    if not checked:
                        st.warning("請先勾選您想要刪除的項目！")
                    else:
                        try:
                            targets = df_selected.loc[checked]
                            if not rows_still_match(worksheet, targets):
                                st.error("雲端資料已被其他裝置更動，請重新整理頁面後再試一次。")
                                fetch_data.clear()
                            else:
                                if trash_ws:
                                    now_s = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M:%S")
                                    trash_ws.append_rows(
                                        [
                                            [r["日期"], r["類型"], r["分類"], to_number(r["金額"]),
                                             r["付款方式"], r["備註"], now_s]
                                            for _, r in targets.iterrows()
                                        ],
                                        value_input_option="RAW",
                                    )
                                    fetch_trash.clear()
                                n_del = delete_rows(worksheet, targets["_row"])
                                clear_data_cache()
                                flash_and_rerun(f"成功刪除 {n_del} 筆項目（可到下方「垃圾桶」還原）！")
                        except Exception as e:
                            st.error(f"刪除失敗：{e}")

            # 儲存：只更新「有被修改的列」，不動其他月份、不改變順序（儲存前會先檢查格式）
            with col2:
                if st.button("儲存修改內容", type="primary", **STRETCH):
                    try:
                        save_df = edited_df.drop(columns=["刪除"]).fillna("").astype(str)
                        orig_df = df_selected[FIELDS].astype(str)
                        changed_idx = [
                            i for i in save_df.index
                            if any(save_df.loc[i, c].strip() != orig_df.loc[i, c].strip() for c in FIELDS)
                        ]
                        if not changed_idx:
                            st.info("沒有偵測到任何修改。")
                        else:
                            # 1) 格式檢查：有任何問題就整批不儲存，並指出是哪一列
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
        else:
            st.info(f"所選月份 {selected_month} 目前還沒有任何記錄！")

        # ----- 垃圾桶：還原或永久刪除 -----
        st.divider()
        show_trash = st.toggle("顯示垃圾桶（還原已刪除的項目）", key="show_trash")
        if show_trash:
            trash_df = safe_load(fetch_trash, trash_ws, pd.DataFrame(columns=TRASH_COLS), "垃圾桶")
            if trash_df.empty:
                st.caption("垃圾桶是空的。")
            else:
                td = trash_df[TRASH_HEADER].copy()
                td.insert(0, "選取", False)
                edited_trash = st.data_editor(
                    td,
                    hide_index=True,
                    key=f"trash_table_{ver}",
                    disabled=TRASH_HEADER,
                    column_config={"選取": st.column_config.CheckboxColumn("選取", width="small")},
                    **STRETCH,
                )
                t1, t2 = st.columns(2)
                with t1:
                    if st.button("還原所選項目", **STRETCH):
                        sel = edited_trash[edited_trash["選取"] == True].index.tolist()  # noqa: E712
                        if not sel:
                            st.warning("請先勾選要還原的項目！")
                        else:
                            try:
                                tgt = trash_df.loc[sel]
                                if not rows_still_match(trash_ws, tgt):
                                    st.error("垃圾桶資料已變動，請重新整理後再試一次。")
                                    fetch_trash.clear()
                                else:
                                    worksheet.append_rows(
                                        [
                                            [r["日期"], r["類型"], r["分類"], to_number(r["金額"]),
                                             r["付款方式"], r["備註"]]
                                            for _, r in tgt.iterrows()
                                        ],
                                        value_input_option="RAW",
                                    )
                                    delete_rows(trash_ws, tgt["_row"])
                                    fetch_trash.clear()
                                    clear_data_cache()
                                    flash_and_rerun(f"已還原 {len(sel)} 筆項目！")
                            except Exception as e:
                                st.error(f"還原失敗：{e}")
                with t2:
                    if st.button("永久刪除所選項目", **STRETCH):
                        sel = edited_trash[edited_trash["選取"] == True].index.tolist()  # noqa: E712
                        if not sel:
                            st.warning("請先勾選要永久刪除的項目！")
                        else:
                            try:
                                tgt = trash_df.loc[sel]
                                if not rows_still_match(trash_ws, tgt):
                                    st.error("垃圾桶資料已變動，請重新整理後再試一次。")
                                    fetch_trash.clear()
                                else:
                                    delete_rows(trash_ws, tgt["_row"])
                                    fetch_trash.clear()
                                    bump_editor()
                                    flash_and_rerun(f"已永久刪除 {len(sel)} 筆項目。")
                            except Exception as e:
                                st.error(f"永久刪除失敗：{e}")

    # ---------- 圖表分析 ----------
    elif view_mode == MODE_CHART:
        # 近 12 個月收支趨勢
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
                    color_discrete_map={"收入": INCOME_COLOR, "支出": EXPENSE_COLOR},
                ))
                st.divider()

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

        st.divider()
        st.subheader(f"{selected_month} 財務視覺化分析")
        if not df_selected.empty:
            df_expense = df_selected[df_selected["類型"] == "支出"]
            if not df_expense.empty:
                c1, c2 = st.columns(2)
                with c1:
                    show(px.pie(
                        df_expense, values="金額_num", names="分類",
                        title=f"{selected_month} 各類別支出佔比", hole=0.45,
                        color="分類", color_discrete_map=CAT_COLORS,
                    ))
                with c2:
                    daily = (
                        df_expense.groupby(["日期_std", "分類"], as_index=False)["金額_num"]
                        .sum()
                        .sort_values("日期_std")
                    )
                    fig_bar = px.bar(
                        daily, x="日期_std", y="金額_num",
                        title=f"{selected_month} 每日總支出趨勢", text_auto=True,
                        color="分類", color_discrete_map=CAT_COLORS,
                        labels={"日期_std": "日期", "金額_num": "金額"},
                    )
                    fig_bar.update_xaxes(type="category", categoryorder="category ascending")
                    show(fig_bar)
                pay_sum = df_expense.groupby("付款方式", as_index=False)["金額_num"].sum()
                pay_sum["付款方式"] = pay_sum["付款方式"].replace("", "未填")
                show(px.bar(
                    pay_sum, x="付款方式", y="金額_num", text_auto=True,
                    title=f"{selected_month} 各付款方式支出",
                    labels={"金額_num": "金額"},
                ))

                # 每週各天支出合計（看出哪一天最容易花錢）
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

    # ---------- 預算追蹤 ----------
    elif view_mode == MODE_BUDGET:
        st.subheader(f"{selected_month} 預算追蹤")
        if not budgets:
            st.info(f"尚未設定預算，請到「{MODE_ADD}」→「預算」設定。")
        else:
            exp_df = df_selected[df_selected["類型"] == "支出"]
            items = []
            if TOTAL_KEY in budgets:
                items.append((TOTAL_KEY, total_expense))
            for cat in budgets:
                if cat != TOTAL_KEY:
                    items.append((cat, exp_df.loc[exp_df["分類"] == cat, "金額_num"].sum()))

            for name, spent in items:
                limit = budgets[name]
                ratio = spent / limit if limit > 0 else 0
                left = limit - spent
                left_txt = f"剩餘 ${left:,.0f}" if left >= 0 else f"超支 ${-left:,.0f}"
                icon = "🔴" if ratio >= 1 else ("🟠" if ratio >= 0.8 else "🟢")
                with st.container(border=True):
                    st.markdown(f"{icon} **{name}**　${spent:,.0f} / ${limit:,.0f}　（{left_txt}）")
                    st.progress(float(min(ratio, 1.0)), text=f"{ratio:.0%}")

            if selected_month == current_month_str and TOTAL_KEY in budgets:
                y, m = map(int, selected_month.split("-"))
                days_total = py_calendar.monthrange(y, m)[1]
                days_left = days_total - TODAY.day + 1
                remain = budgets[TOTAL_KEY] - total_expense
                st.divider()
                if remain > 0:
                    st.info(f"本月還有 {days_left} 天（含今天），平均每天可花 ${remain / days_left:,.0f}")
                else:
                    st.warning("本月總預算已用完，建議接下來盡量不要再花錢。")

                # 月底超支預測
                projected = total_expense / TODAY.day * days_total
                if projected > budgets[TOTAL_KEY]:
                    st.warning(
                        f"照目前速度，月底預估花費 ${projected:,.0f}，"
                        f"會超出預算 ${projected - budgets[TOTAL_KEY]:,.0f}。"
                    )
                else:
                    st.success(f"月底預估花費 ${projected:,.0f}，仍在預算內。")

        # 儲蓄目標（累計結餘 = 所有月份的收入 − 支出）
        st.divider()
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
            st.caption(f"尚未設定儲蓄目標，可到「{MODE_ADD}」→「預算」設定。")

    # ---------- 月曆 ----------
    elif view_mode == MODE_CAL:
        st.subheader(f"{selected_month} 日曆視圖")

        try:
            year, month = map(int, selected_month.split("-"))
        except ValueError:
            year, month = TODAY.year, TODAY.month

        cal_style = st.radio("顯示方式", ["格狀月曆", "清單（手機建議）"], horizontal=True)

        if cal_style == "清單（手機建議）":
            if df_selected.empty:
                st.info("此月份尚無資料。")
            else:
                for d_str, g in df_selected.sort_values(["日期_std", "_row"]).groupby("日期_std"):
                    g_inc, g_exp = sums(g)
                    net_txt = md_escape(f"{g_inc - g_exp:+,.0f}")
                    ts = pd.to_datetime(d_str, errors="coerce")
                    wd = WEEKDAY_NAMES[int(ts.dayofweek)] if not pd.isna(ts) else ""
                    st.markdown(md_escape(f"{d_str}（{wd}）") + f"　**淨 {net_txt}**")
                    for _, row in g.iterrows():
                        is_exp = row["類型"] == "支出"
                        dot = "🔴" if is_exp else "🟢"
                        sign = "-" if is_exp else "+"
                        amt_txt = md_escape(f"{sign}${row['金額_num']:,.0f}")
                        st.markdown(
                            f"- {dot} {amt_txt}　{md_escape(row['分類'])}　{md_escape(row['備註'])}"
                        )
        else:
            # firstweekday=6 → 週日為每週第一天，與標題列一致
            cal_matrix = py_calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)

            weekdays = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"]
            cols = st.columns(7)
            for i, day_name in enumerate(weekdays):
                cols[i].markdown(
                    f"<div style='text-align:center; font-weight:600; opacity:.7; font-size:.9rem;'>{day_name}</div>",
                    unsafe_allow_html=True,
                )

            st.divider()

            today_str = TODAY.strftime("%Y-%m-%d")
            for week in cal_matrix:
                cols = st.columns(7)
                for i, day in enumerate(week):
                    with cols[i]:
                        if day == 0:
                            st.markdown(
                                "<div class='cal-card' style='opacity: 0.2;'><div class='cal-day-header'>-</div></div>",
                                unsafe_allow_html=True,
                            )
                            continue

                        date_str = f"{year}-{month:02d}-{day:02d}"
                        body = ""
                        day_net = 0
                        if not df_selected.empty:
                            day_records = df_selected[df_selected["日期_std"] == date_str]
                            for _, row in day_records.iterrows():
                                is_exp = row["類型"] == "支出"
                                color = EXPENSE_COLOR if is_exp else INCOME_COLOR
                                sign = "-" if is_exp else "+"
                                amt = row["金額_num"]
                                day_net += -amt if is_exp else amt
                                body += (
                                    f"<div style='margin-bottom: 6px;'>"
                                    f"<span style='color:{color}; font-size:14px; font-weight:600;'>"
                                    f"{sign}${amt:,.0f} ({html.escape(str(row['分類']))})</span><br>"
                                    f"<span class='cal-note'>{html.escape(str(row['備註']))}</span>"
                                    f"</div>"
                                )
                        total_html = ""
                        if body:
                            total_html = f"<span class='cal-day-total'>淨 {day_net:+,.0f}</span>"
                        today_cls = " today" if date_str == today_str else ""
                        st.markdown(
                            f"<div class='cal-card{today_cls}'><div class='cal-day-header'>"
                            f"<span>{day}</span>{total_html}</div>{body}</div>",
                            unsafe_allow_html=True,
                        )

    # ---------- 比較與年度 ----------
    elif view_mode == MODE_COMPARE:
        prev_month = prev_month_str(selected_month)
        df_prev = df[df["年月"] == prev_month]

        st.subheader(f"{selected_month} vs {prev_month}（各分類支出）")
        cur = df_selected[df_selected["類型"] == "支出"].groupby("分類")["金額_num"].sum()
        prv = df_prev[df_prev["類型"] == "支出"].groupby("分類")["金額_num"].sum()
        cmp_df = pd.concat([cur.rename(selected_month), prv.rename(prev_month)], axis=1).fillna(0)
        if cmp_df.empty:
            st.info("這兩個月都沒有支出紀錄可比較。")
        else:
            cmp_df.index.name = "分類"
            cmp_df = cmp_df.reset_index()
            cmp_df["差額"] = cmp_df[selected_month] - cmp_df[prev_month]
            cmp_df["變化%"] = cmp_df.apply(
                lambda r: round(r["差額"] / r[prev_month] * 100, 1) if r[prev_month] > 0 else None, axis=1
            )
            cmp_df = cmp_df.sort_values("差額", ascending=False)
            top = cmp_df.iloc[0]
            if top["差額"] > 0:
                st.info(f"「{top['分類']}」比上月多花 ${top['差額']:,.0f}，是增加最多的分類。")
            st.dataframe(cmp_df, hide_index=True, **STRETCH)
            melted = cmp_df.melt(
                id_vars="分類", value_vars=[selected_month, prev_month], var_name="月份", value_name="金額"
            )
            show(px.bar(melted, x="分類", y="金額", color="月份", barmode="group", title="各分類支出比較"))

        # ----- 年度總覽 -----
        st.divider()
        st.subheader("年度總覽")
        years = sorted({str(m)[:4] for m in all_months}, reverse=True)
        sel_year = st.selectbox(
            "選擇年度", years, key="year_sel",
            index=years.index(selected_month[:4]) if selected_month[:4] in years else 0,
        )
        df_year = df[df["年月"].astype(str).str.startswith(sel_year)]
        months12 = [f"{sel_year}-{i:02d}" for i in range(1, 13)]
        inc_m = (
            df_year[df_year["類型"] == "收入"].groupby("年月")["金額_num"].sum()
            .reindex(months12, fill_value=0).astype(float)
        )
        exp_m = (
            df_year[df_year["類型"] == "支出"].groupby("年月")["金額_num"].sum()
            .reindex(months12, fill_value=0).astype(float)
        )
        yr = pd.DataFrame({"月份": months12, "收入": inc_m.values, "支出": exp_m.values})
        yr["結餘"] = yr["收入"] - yr["支出"]

        y1, y2, y3 = st.columns(3)
        y1.metric(f"{sel_year} 總收入", f"${int(yr['收入'].sum()):,}")
        y2.metric(f"{sel_year} 總支出", f"${int(yr['支出'].sum()):,}")
        y3.metric(f"{sel_year} 總結餘", f"${int(yr['結餘'].sum()):,}")

        fig_year = px.bar(
            yr.melt(id_vars="月份", value_vars=["收入", "支出"], var_name="類型", value_name="金額"),
            x="月份", y="金額", color="類型", barmode="group", title=f"{sel_year} 每月收入與支出",
            color_discrete_map={"收入": INCOME_COLOR, "支出": EXPENSE_COLOR},
        )
        fig_year.add_scatter(
            x=yr["月份"], y=yr["結餘"], mode="lines+markers", name="結餘", line=dict(color=ACCENT)
        )
        show(fig_year)

        year_exp = df_year[df_year["類型"] == "支出"]
        if not year_exp.empty:
            show(px.pie(
                year_exp, values="金額_num", names="分類", hole=0.45,
                title=f"{sel_year} 各類別支出佔比",
                color="分類", color_discrete_map=CAT_COLORS,
            ))

        st.dataframe(yr, hide_index=True, **STRETCH)
        st.download_button(
            "下載全部記帳資料（CSV）",
            df[FIELDS].to_csv(index=False).encode("utf-8-sig"),
            file_name="記帳_全部資料.csv",
            mime="text/csv",
        )

else:
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")
