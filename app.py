import hmac
import html
import re
import time
import calendar as py_calendar
from datetime import date

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st

# ======================= 基本設定 =======================
st.set_page_config(
    page_title="我是有錢人", page_icon="💰", layout="wide",
    initial_sidebar_state="collapsed",
)

# 試算表網址：只從 Streamlit Secrets 讀取（SPREADSHEET_URL = "..."）
SPREADSHEET_URL = str(st.secrets.get("SPREADSHEET_URL", "")).strip()

PAY_OPTIONS = ["現金", "信用卡", "行動支付"]
EXPENSE_CATS = ["伙食", "交通", "購物", "娛樂", "每月固定費用", "其他支出"]
INCOME_CATS = ["薪資", "其他收入"]
FIELDS = ["日期", "類型", "分類", "金額", "付款方式", "備註"]
SETTINGS_HEADER = ["項目名稱", "預設金額", "付款方式"]
BUDGET_HEADER = ["分類", "每月上限"]
TOTAL_KEY = "總預算"
CACHE_TTL = 60  # 快取秒數（多裝置同步）


def _ver_tuple():
    parts = []
    for p in st.__version__.split(".")[:2]:
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


# 新版 Streamlit 用 width="stretch"，舊版用 use_container_width
STRETCH = {"width": "stretch"} if _ver_tuple() >= (1, 50) else {"use_container_width": True}

# 樣式：深淺色相容 + 手機 / 平板 / 電腦響應式
st.markdown("""
<style>
    /* 含按鈕的橫列（上月/下月、刪除/儲存、重新整理/登出）手機上也維持並排 */
    @media (max-width: 640px) {
        div[data-testid="stHorizontalBlock"]:has(button) { flex-wrap: nowrap !important; gap: 0.5rem !important; }
        div[data-testid="stHorizontalBlock"]:has(button) > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"]:has(button) > div[data-testid="column"] {
            min-width: 0 !important; width: auto !important; flex: 1 1 0 !important;
        }
        .block-container { padding: 1rem 0.7rem 3rem !important; }
        .stButton button, .stDownloadButton button { min-height: 46px; }
        [data-testid="stMetricValue"] { font-size: 1.5rem; }
    }

    /* 月曆：單一 CSS Grid，手機不會被拆成直向長條 */
    .cal-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; }
    .cal-wk { text-align: center; font-weight: bold; padding: 4px 0; }
    .cal-card {
        background-color: rgba(128, 128, 128, 0.12);
        border: 1px solid rgba(128, 128, 128, 0.35);
        border-radius: 8px;
        padding: 8px;
        min-height: 110px;
        overflow: hidden;
    }
    .cal-empty { opacity: 0.2; }
    .cal-day-header {
        font-size: 15px; font-weight: bold; margin-bottom: 6px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.4); padding-bottom: 4px;
        display: flex; justify-content: space-between; gap: 4px;
    }
    .cal-day-total { font-size: 12px; font-weight: normal; opacity: 0.85; }
    .cal-item { margin-bottom: 6px; font-size: 13px; font-weight: bold; word-break: break-all; }
    .cal-note { font-size: 12px; font-weight: normal; opacity: 0.75; }
    @media (max-width: 900px) {
        .cal-grid { gap: 3px; }
        .cal-card { padding: 4px; min-height: 64px; }
        .cal-day-header { font-size: 13px; }
        .cal-item { font-size: 11px; }
        .cal-note { display: none; }
    }
    @media (max-width: 640px) {
        .cal-card { min-height: 52px; padding: 3px; }
        .cal-day-header { flex-direction: column; border: 0; margin: 0; padding: 0; gap: 2px; }
        .cal-day-total { font-size: 10px; }
        .cal-lbl, .cal-wk .wk, .cal-body { display: none; }
    }
</style>
""", unsafe_allow_html=True)

# ======================= 密碼登入 =======================
MAX_FAILS = 5
LOCK_SECONDS = 300
IDLE_SECONDS = 1800  # 閒置 30 分鐘自動登出


@st.cache_resource
def _login_tracker():
    return {"fails": 0, "locked_until": 0.0}


def require_login():
    expected = str(st.secrets.get("APP_PASSWORD", ""))
    if not expected:
        st.error("尚未設定 APP_PASSWORD，為了安全程式已停止。請到 Streamlit Secrets 加入：APP_PASSWORD = 「你的密碼」")
        st.stop()
    if st.session_state.get("authed"):
        if time.time() - st.session_state.get("last_active", 0) > IDLE_SECONDS:
            st.session_state.clear()
            st.warning("⏱️ 閒置過久，已自動登出，請重新登入。")
        else:
            st.session_state["last_active"] = time.time()
            return

    tracker = _login_tracker()
    st.title("🔒 我是有錢人")
    wait = tracker["locked_until"] - time.time()
    if wait > 0:
        st.error(f"錯誤次數過多，請 {int(wait // 60)} 分 {int(wait % 60)} 秒後再試。")
        st.stop()

    with st.form("login_form"):
        pwd = st.text_input("請輸入密碼", type="password")
        submitted = st.form_submit_button("登入")

    if submitted:
        if hmac.compare_digest(pwd.encode("utf-8"), expected.encode("utf-8")):
            tracker["fails"] = 0
            st.session_state["authed"] = True
            st.session_state["last_active"] = time.time()
            st.rerun()
        else:
            tracker["fails"] += 1
            if tracker["fails"] >= MAX_FAILS:
                tracker["locked_until"] = time.time() + LOCK_SECONDS
                tracker["fails"] = 0
                st.error("錯誤次數過多，已暫時鎖定 5 分鐘。")
            else:
                time.sleep(1)
                st.error(f"密碼錯誤（還有 {MAX_FAILS - tracker['fails']} 次機會）")
    st.stop()


require_login()

if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"), icon="✅")
if "editor_ver" not in st.session_state:
    st.session_state.editor_ver = 0

st.title("💰 我是有錢人")
st.markdown("一天一塊錢 七天就有七塊錢")


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
    try:
        return fn(arg)
    except Exception as e:
        st.warning(f"讀取「{label}」失敗：{e}（可按「🔄 重新整理」重試）")
        return default


def prev_month_str(ym):
    y, m = map(int, ym.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def sums(d):
    return (
        d.loc[d["類型"] == "收入", "金額_num"].sum(),
        d.loc[d["類型"] == "支出", "金額_num"].sum(),
    )


def show_chart(fig):
    """圖表手機友善：圖例放下方、關閉工具列與拖曳（避免擋住頁面捲動）"""
    fig.update_layout(
        dragmode=False,
        margin=dict(l=8, r=8, t=48, b=80),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0),
    )
    st.plotly_chart(fig, config={"displayModeBar": False}, **STRETCH)


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
def get_main_ws(_sh):
    # 快取工作表物件：避免每次操作都多打一次 Google API 查詢分頁資訊
    return _sh.get_worksheet(0)


worksheet = get_main_ws(sh) if sh else None


@st.cache_resource
def get_settings_worksheet(_sh):
    try:
        return _sh.worksheet("固定支出設定")
    except gspread.WorksheetNotFound:
        new_ws = _sh.add_worksheet(title="固定支出設定", rows=100, cols=3)
        new_ws.append_row(SETTINGS_HEADER)
        new_ws.append_row(["孝親費", "5000", "現金"])
        new_ws.append_row(["電信費", "599", "信用卡"])
        return new_ws


try:
    settings_ws = get_settings_worksheet(sh) if sh else None
except Exception as e:
    settings_ws = None
    st.warning(f"無法取得「固定支出設定」分頁：{e}")


@st.cache_data(ttl=CACHE_TTL)
def fetch_settings_rows(_settings_ws):
    if not _settings_ws:
        return []
    data = _settings_ws.get_all_values()
    return [pad_row(r, 3) for r in data[1:] if any(str(c).strip() for c in r)]


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
        templates[name] = {"amount": amt, "pay": pay}
    return templates


settings_rows = safe_load(fetch_settings_rows, settings_ws, [], "固定支出設定")
fixed_templates = build_templates(settings_rows)


# ======================= 預算設定 =======================
@st.cache_resource
def get_budget_worksheet(_sh):
    try:
        return _sh.worksheet("預算設定")
    except gspread.WorksheetNotFound:
        ws = _sh.add_worksheet(title="預算設定", rows=50, cols=2)
        ws.append_row(BUDGET_HEADER)
        ws.append_row([TOTAL_KEY, 30000])
        ws.append_row(["伙食", 8000])
        return ws


try:
    budget_ws = get_budget_worksheet(sh) if sh else None
except Exception as e:
    budget_ws = None
    st.warning(f"無法取得「預算設定」分頁：{e}")


@st.cache_data(ttl=CACHE_TTL)
def fetch_budget_rows(_budget_ws):
    if not _budget_ws:
        return []
    data = _budget_ws.get_all_values()
    rows = [pad_row(r, 2) for r in data[1:]]
    return [r for r in rows if str(r[0]).strip()]


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


budget_rows = safe_load(fetch_budget_rows, budget_ws, [], "預算設定")
budgets = build_budgets(budget_rows)


# ======================= 分類設定（從試算表讀取） =======================
@st.cache_resource
def get_category_worksheet(_sh):
    try:
        return _sh.worksheet("分類設定")
    except gspread.WorksheetNotFound:
        ws = _sh.add_worksheet(title="分類設定", rows=100, cols=2)
        ws.append_rows(
            [["類型", "分類"]]
            + [["支出", c] for c in EXPENSE_CATS]
            + [["收入", c] for c in INCOME_CATS]
        )
        return ws


@st.cache_data(ttl=CACHE_TTL)
def fetch_category_rows(_ws):
    if not _ws:
        return []
    return [pad_row(r, 2) for r in _ws.get_all_values()[1:]]


try:
    cat_ws = get_category_worksheet(sh) if sh else None
except Exception as e:
    cat_ws = None
    st.warning(f"無法取得「分類設定」分頁：{e}")

_cat_rows = safe_load(fetch_category_rows, cat_ws, [], "分類設定")
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


def render_budget_banner(df_month, total_spent, budgets, month_label):
    limit = budgets.get(TOTAL_KEY)
    if limit:
        ratio = total_spent / limit
        st.progress(
            float(min(ratio, 1.0)),
            text=f"🎯 {month_label} 總預算已使用 {ratio:.0%}（${total_spent:,.0f} / ${limit:,.0f}）",
        )
        if ratio >= 1:
            st.error(f"⚠️ 已超出總預算 ${total_spent - limit:,.0f}！")
        elif ratio >= 0.8:
            st.warning(f"⚡ 已使用 {ratio:.0%}，本月只剩 ${limit - total_spent:,.0f}。")

    over = []
    exp = df_month[df_month["類型"] == "支出"]
    for cat, lim in budgets.items():
        if cat == TOTAL_KEY or lim <= 0:
            continue
        spent = exp.loc[exp["分類"] == cat, "金額_num"].sum()
        if spent >= lim:
            over.append(f"{cat}（${spent:,.0f} / ${lim:,.0f}）")
    if over:
        st.error("⚠️ 以下分類已超出預算：" + "、".join(over))


# ======================= 讀取記帳主表 =======================
DF_COLS = ["_row"] + FIELDS + ["年月", "日期_std", "金額_num"]


@st.cache_data(ttl=CACHE_TTL)
def fetch_data(_sh):
    if not _sh:
        return pd.DataFrame(columns=DF_COLS)
    raw_data = get_main_ws(_sh).get_all_values()
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
    """寫入前確認雲端那幾列仍和畫面上一致"""
    ranges = [f"A{int(n)}:F{int(n)}" for n in df_rows["_row"]]
    got = ws.batch_get(ranges)
    for (_, r), vals in zip(df_rows.iterrows(), got):
        cloud = pad_row(vals[0] if vals else [])
        for i, col in enumerate(FIELDS):
            if str(cloud[i]).strip() != str(r[col]).strip():
                return False
    return True


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

    return errs, [date_ok, typ, cat, amt, pay, str(r["備註"])]


# ======================= 主程式 =======================
if sh and worksheet:
    df = safe_load(fetch_data, sh, pd.DataFrame(columns=DF_COLS), "記帳資料")
    ver = st.session_state.editor_ver

    if not df.empty:
        bad_rows = df[~df["年月"].fillna("").str.fullmatch(r"\d{4}-\d{2}")]
        if not bad_rows.empty:
            st.warning(
                f"⚠️ 有 {len(bad_rows)} 筆日期格式異常"
                f"（試算表第 {', '.join(map(str, bad_rows['_row']))} 列），不會出現在月份篩選中。"
            )

    # ---------- 頂部：重新整理 / 登出 ----------
    top1, top2 = st.columns(2)
    if top1.button("🔄 重新整理", **STRETCH):
        fetch_data.clear()
        fetch_settings_rows.clear()
        fetch_budget_rows.clear()
        fetch_category_rows.clear()
        bump_editor()
        st.rerun()
    if top2.button("🚪 登出", **STRETCH):
        st.session_state.clear()
        st.rerun()

    # ---------- 新增記帳（放主頁面，手機不用開側邊欄） ----------
    with st.expander("➕ 新增記帳", expanded=False):
        tab_general, tab_salary, tab_fixed, tab_budget = st.tabs(["一般", "💰薪資", "🏠固定", "🎯預算"])

        with tab_general:
            tx_type = st.radio("類型", ["支出", "收入"], horizontal=True)
            category = st.selectbox("分類", EXPENSE_CATS if tx_type == "支出" else INCOME_CATS)
            amount = st.number_input("金額", value=None, step=1, min_value=0, placeholder="請輸入金額...", key=f"amt_{ver}")
            pay_method = st.selectbox("付款方式", PAY_OPTIONS)
            tx_date = st.date_input("日期", value=date.today())
            note = st.text_input("備註 (例如：鮮天下、加油)", key=f"note_{ver}")

            if st.button("送出一般記帳", **STRETCH):
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
            default_salary = st.number_input("預設月薪金額", value=45000, step=1000)
            salary_date = st.date_input("入帳日期", value=date.today(), key="sal_date")

            salary_dup = False
            if not df.empty:
                salary_dup = bool(
                    ((df["年月"] == salary_date.strftime("%Y-%m")) & (df["分類"] == "薪資")).any()
                )
            allow_salary_dup = True
            if salary_dup:
                st.warning(f"⚠️ {salary_date.strftime('%Y-%m')} 已經有薪資紀錄了。")
                allow_salary_dup = st.checkbox("我確定要再入帳一次", key=f"allow_sal_dup_{ver}")

            if st.button("📥 一鍵入帳本月薪資", **STRETCH):
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
            expense_date = st.date_input("扣款日期", value=date.today(), key="exp_date")

            fixed_dup = False
            if not df.empty:
                fixed_dup = bool(
                    (
                        (df["年月"] == expense_date.strftime("%Y-%m"))
                        & (df["分類"] == "每月固定費用")
                        & (df["備註"] == expense_note.strip())
                    ).any()
                )
            allow_fixed_dup = True
            if fixed_dup:
                st.warning(f"⚠️ {expense_date.strftime('%Y-%m')} 已經記錄過【{expense_note.strip()}】了。")
                allow_fixed_dup = st.checkbox("我確定要再扣一次", key=f"allow_fix_dup_{ver}")

            if st.button("📤 一鍵扣款固定支出", **STRETCH):
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

            if fixed_templates and st.button("📦 本月固定支出全部入帳", **STRETCH):
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
            with st.expander("⚙️ 線上修改或新增固定支出清單"):
                if settings_ws:
                    df_settings = pd.DataFrame(settings_rows, columns=SETTINGS_HEADER)
                    edited_settings = st.data_editor(
                        df_settings,
                        num_rows="dynamic",
                        key=f"settings_editor_{ver}",
                        **STRETCH,
                    )
                    if st.button("💾 儲存範本修改", **STRETCH):
                        try:
                            clean_df = edited_settings.fillna("").astype(str)
                            clean_df = clean_df[clean_df["項目名稱"].str.strip() != ""]
                            new_data = [SETTINGS_HEADER] + clean_df.values.tolist()
                            old_len = len(settings_rows) + 1
                            settings_ws.update(range_name="A1", values=new_data)
                            if old_len > len(new_data):
                                settings_ws.batch_clear([f"A{len(new_data) + 1}:C{old_len}"])
                            fetch_settings_rows.clear()
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
                if st.button("💾 儲存預算", **STRETCH):
                    try:
                        clean_b = edited_budget.dropna(subset=["分類", "每月上限"])
                        clean_b = clean_b[clean_b["分類"].astype(str).str.strip() != ""]
                        clean_b = clean_b.drop_duplicates(subset="分類", keep="last")
                        new_data = [BUDGET_HEADER] + [
                            [str(a).strip(), to_number(b)] for a, b in clean_b.itertuples(index=False)
                        ]
                        old_len = len(budget_rows) + 1  # 用已快取的列數，省一次 API 讀取
                        budget_ws.update(range_name="A1", values=new_data)
                        if old_len > len(new_data):
                            budget_ws.batch_clear([f"A{len(new_data) + 1}:B{old_len + 20}"])
                        fetch_budget_rows.clear()
                        bump_editor()
                        flash_and_rerun("預算已儲存！")
                    except Exception as e:
                        st.error(f"預算儲存失敗: {e}")

    # ---------- 月份篩選（含上月／下月按鈕） ----------
    current_month_str = date.today().strftime("%Y-%m")
    if not df.empty:
        db_months = [m for m in df["年月"].dropna().unique().tolist() if re.fullmatch(r"\d{4}-\d{2}", str(m))]
    else:
        db_months = []
    all_months = sorted(set(db_months + [current_month_str]), reverse=True)

    if st.session_state.get("month_sel") not in all_months:
        st.session_state.month_sel = current_month_str

    def shift_month(step):
        i = all_months.index(st.session_state.month_sel) - step
        if 0 <= i < len(all_months):
            st.session_state.month_sel = all_months[i]

    nav1, nav2, nav3 = st.columns([1, 2, 1])
    nav1.button("◀", on_click=shift_month, args=(-1,), **STRETCH)
    nav2.selectbox("📅 月份", all_months, key="month_sel", label_visibility="collapsed")
    nav3.button("▶", on_click=shift_month, args=(1,), **STRETCH)
    selected_month = st.session_state.month_sel

    if not df.empty:
        df_selected = (
            df[df["年月"] == selected_month]
            .sort_values(["日期_std", "_row"], ascending=False)
            .reset_index(drop=True)
        )
    else:
        df_selected = pd.DataFrame(columns=DF_COLS)

    # ---------- 本月統計（含與上月比較） ----------
    total_income, total_expense = sums(df_selected)
    prev_income, prev_expense = sums(df[df["年月"] == prev_month_str(selected_month)])
    net_balance = total_income - total_expense
    prev_net = prev_income - prev_expense

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(
        f"📈 {selected_month} 總收入", f"${int(total_income):,}",
        delta=f"{int(total_income - prev_income):,}",
    )
    col_m2.metric(
        f"📉 {selected_month} 總花費", f"${int(total_expense):,}",
        delta=f"{int(total_expense - prev_expense):,}", delta_color="inverse",
    )
    col_m3.metric(
        f"💰 {selected_month} 本月結餘", f"${int(net_balance):,}",
        delta=f"{int(net_balance - prev_net):,}",
    )

    if total_income > 0:
        st.caption(f"💹 本月儲蓄率：{net_balance / total_income:.0%}（結餘 ÷ 收入）")

    render_budget_banner(df_selected, total_expense, budgets, selected_month)

    st.divider()

    view_mode = st.radio(
        "選擇檢視模式：",
        ["📋 記帳明細列表", "📊 圖表與固定費用", "🎯 預算追蹤", "📅 月曆模式"],
        horizontal=True,
        label_visibility="collapsed",
    )
    st.divider()

    # ---------- 模式 1：明細列表 ----------
    if view_mode == "📋 記帳明細列表":
        st.subheader(f"📋 {selected_month} 記帳明細列表")
        if not df_selected.empty:
            st.download_button(
                "⬇️ 匯出本月 CSV",
                df_selected[FIELDS].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"記帳_{selected_month}.csv",
                mime="text/csv",
            )

            f1, f2, f3 = st.columns([2, 2, 3])
            cat_filter = f1.multiselect("分類", EXPENSE_CATS + INCOME_CATS)
            pay_filter = f2.multiselect("付款方式", PAY_OPTIONS)
            kw = f3.text_input("🔍 搜尋備註")

            mask = pd.Series(True, index=df_selected.index)
            if cat_filter:
                mask &= df_selected["分類"].isin(cat_filter)
            if pay_filter:
                mask &= df_selected["付款方式"].isin(pay_filter)
            if kw.strip():
                mask &= df_selected["備註"].str.contains(kw.strip(), case=False, regex=False)

            view = df_selected[mask]
            st.caption(
                f"篩選後 {len(view)} 筆｜收入 ${view.loc[view['類型'] == '收入', '金額_num'].sum():,.0f}"
                f"｜支出 ${view.loc[view['類型'] == '支出', '金額_num'].sum():,.0f}"
            )
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
                    "備註": st.column_config.TextColumn("備註", width="medium"),
                },
                **STRETCH,
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🗑️ 刪除所選", **STRETCH):
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
                                row_nos = sorted([int(x) for x in targets["_row"]], reverse=True)
                                requests = [{
                                    "deleteDimension": {
                                        "range": {
                                            "sheetId": worksheet.id,
                                            "dimension": "ROWS",
                                            "startIndex": n - 1,
                                            "endIndex": n,
                                        }
                                    }
                                } for n in row_nos]
                                sh.batch_update({"requests": requests})
                                clear_data_cache()
                                flash_and_rerun(f"成功刪除 {len(row_nos)} 筆項目！")
                        except Exception as e:
                            st.error(f"刪除失敗：{e}")

            with col2:
                if st.button("💾 儲存修改", **STRETCH):
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

    # ---------- 模式 2：圖表 ----------
    elif view_mode == "📊 圖表與固定費用":
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
                show_chart(px.line(long, x="年月", y="金額", color="類型", markers=True, title="近 12 個月收支趨勢"))
                st.divider()

        st.subheader(f"📌 {selected_month} 每月固定費用總覽")
        if not df_selected.empty:
            df_fixed = df_selected[df_selected["分類"] == "每月固定費用"]
            if not df_fixed.empty:
                st.metric("💰 固定開銷總計", f"${int(df_fixed['金額_num'].sum()):,}")
                st.dataframe(df_fixed[["日期", "金額", "付款方式", "備註"]], hide_index=True, **STRETCH)
            else:
                st.info("此月份尚無設定「每月固定費用」的紀錄。")
        else:
            st.info("此月份尚無資料。")

        st.divider()
        st.subheader(f"📊 {selected_month} 財務視覺化分析")
        if not df_selected.empty:
            df_expense = df_selected[df_selected["類型"] == "支出"]
            if not df_expense.empty:
                color_map = {
                    "伙食": "#33ff57", "交通": "#3357ff", "購物": "#ff33a8",
                    "娛樂": "#ffbd33", "每月固定費用": "#ff5733", "其他支出": "#a833ff",
                }
                c1, c2 = st.columns(2)
                with c1:
                    show_chart(px.pie(
                        df_expense, values="金額_num", names="分類",
                        title=f"{selected_month} 各類別支出佔比", hole=0.4,
                        color="分類", color_discrete_map=color_map,
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
                        color="分類", color_discrete_map=color_map,
                        labels={"日期_std": "日期", "金額_num": "金額"},
                    )
                    fig_bar.update_xaxes(type="category", categoryorder="category ascending")
                    show_chart(fig_bar)
                pay_sum = df_expense.groupby("付款方式", as_index=False)["金額_num"].sum()
                pay_sum["付款方式"] = pay_sum["付款方式"].replace("", "未填")
                show_chart(px.bar(
                    pay_sum, x="付款方式", y="金額_num", text_auto=True,
                    title=f"{selected_month} 各付款方式支出",
                    labels={"金額_num": "金額"},
                ))
            else:
                st.info("此月份尚無支出紀錄可產出圖表。")

    # ---------- 模式 3：預算追蹤 ----------
    elif view_mode == "🎯 預算追蹤":
        st.subheader(f"🎯 {selected_month} 預算追蹤")
        if not budgets:
            st.info("尚未設定預算，請到上方「➕ 新增記帳 → 🎯預算」分頁設定。")
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
                st.markdown(f"{icon} **{name}**　${spent:,.0f} / ${limit:,.0f}　（{left_txt}）")
                st.progress(float(min(ratio, 1.0)), text=f"{ratio:.0%}")

            if selected_month == current_month_str and TOTAL_KEY in budgets:
                y, m = map(int, selected_month.split("-"))
                days_total = py_calendar.monthrange(y, m)[1]
                days_left = days_total - date.today().day + 1
                remain = budgets[TOTAL_KEY] - total_expense
                st.divider()
                if remain > 0:
                    st.info(f"💡 本月還有 {days_left} 天（含今天），平均每天可花 ${remain / days_left:,.0f}")
                else:
                    st.warning("💡 本月總預算已用完，建議接下來盡量不要再花錢。")

                projected = total_expense / date.today().day * days_total
                if projected > budgets[TOTAL_KEY]:
                    st.warning(
                        f"📈 照目前速度，月底預估花費 ${projected:,.0f}，"
                        f"會超出預算 ${projected - budgets[TOTAL_KEY]:,.0f}。"
                    )
                else:
                    st.success(f"📈 月底預估花費 ${projected:,.0f}，仍在預算內。")

    # ---------- 模式 4：月曆（單一 HTML Grid，手機也是 7 欄） ----------
    elif view_mode == "📅 月曆模式":
        st.subheader(f"📅 {selected_month} 日曆視圖")

        try:
            year, month = map(int, selected_month.split("-"))
        except ValueError:
            year, month = date.today().year, date.today().month

        cal_matrix = py_calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)

        # 先依日期分組，避免每格都重新篩選整張表
        by_day = {}
        if not df_selected.empty:
            for d_std, typ, amt, cat, nt in zip(
                df_selected["日期_std"], df_selected["類型"], df_selected["金額_num"],
                df_selected["分類"], df_selected["備註"],
            ):
                by_day.setdefault(d_std, []).append((typ, amt, cat, nt))

        parts = ["<div class='cal-grid'>"]
        for w in "日一二三四五六":
            parts.append(f"<div class='cal-wk'><span class='wk'>週</span>{w}</div>")

        for week in cal_matrix:
            for day in week:
                if day == 0:
                    parts.append("<div class='cal-card cal-empty'></div>")
                    continue
                recs = by_day.get(f"{year}-{month:02d}-{day:02d}", [])
                body, day_net = "", 0
                for typ, amt, cat, nt in recs:
                    is_exp = typ == "支出"
                    day_net += -amt if is_exp else amt
                    color = "#ff6b6b" if is_exp else "#51cf66"
                    body += (
                        f"<div class='cal-item' style='color:{color};'>"
                        f"{'-' if is_exp else '+'}${amt:,.0f} ({html.escape(str(cat))})<br>"
                        f"<span class='cal-note'>{html.escape(str(nt))}</span></div>"
                    )
                total_html = ""
                if recs:
                    tcolor = "#ff6b6b" if day_net < 0 else "#51cf66"
                    total_html = (
                        f"<span class='cal-day-total' style='color:{tcolor};'>"
                        f"<span class='cal-lbl'>淨 </span>{day_net:+,.0f}</span>"
                    )
                parts.append(
                    f"<div class='cal-card'><div class='cal-day-header'>"
                    f"<span>{day}</span>{total_html}</div>"
                    f"<div class='cal-body'>{body}</div></div>"
                )
        parts.append("</div>")
        st.markdown("".join(parts), unsafe_allow_html=True)
        st.caption("手機畫面較窄時月曆只顯示每日淨額；要看明細請切到「📋 記帳明細列表」。")

else:
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")
