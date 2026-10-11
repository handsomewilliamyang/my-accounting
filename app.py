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
st.set_page_config(page_title="我是有錢人", page_icon="💰", layout="wide")

# 試算表網址：建議放進 Streamlit Secrets（SPREADSHEET_URL = "..."），沒設定時使用下面的預設值
DEFAULT_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1DTNSXJUJE_7PQIi5yebsmt_mC8bIe1D82IF2FgDaPyM/edit?gid=0#gid=0"
SPREADSHEET_URL = st.secrets.get("SPREADSHEET_URL", DEFAULT_SPREADSHEET_URL)

# 統一的選項清單
PAY_OPTIONS = ["現金", "信用卡", "行動支付"]
EXPENSE_CATS = ["伙食", "交通", "購物", "娛樂", "每月固定費用", "其他支出"]
INCOME_CATS = ["薪資", "其他收入"]
FIELDS = ["日期", "類型", "分類", "金額", "付款方式", "備註"]
SETTINGS_HEADER = ["項目名稱", "預設金額", "付款方式"]
BUDGET_HEADER = ["分類", "每月上限"]
TOTAL_KEY = "總預算"


def _ver_tuple():
    parts = []
    for p in st.__version__.split(".")[:2]:
        digits = "".join(c for c in p if c.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


# 新版 Streamlit 用 width="stretch"，舊版用 use_container_width
STRETCH = {"width": "stretch"} if _ver_tuple() >= (1, 50) else {"use_container_width": True}

# 樣式（同時相容深色 / 淺色主題）
st.markdown("""
<style>
    div[data-testid="stDataEditor"] th:nth-child(1), div[data-testid="stDataEditor"] td:nth-child(1) { width: 50px !important; min-width: 50px !important; }
    div[data-testid="stDataEditor"] th:nth-child(2), div[data-testid="stDataEditor"] td:nth-child(2) { width: 110px !important; min-width: 110px !important; }
    div[data-testid="stDataEditor"] th:nth-child(3), div[data-testid="stDataEditor"] td:nth-child(3) { width: 70px !important; min-width: 70px !important; }
    div[data-testid="stDataEditor"] th:nth-child(4), div[data-testid="stDataEditor"] td:nth-child(4) { width: 90px !important; min-width: 90px !important; }
    div[data-testid="stDataEditor"] th:nth-child(5), div[data-testid="stDataEditor"] td:nth-child(5) { width: 80px !important; min-width: 80px !important; }
    div[data-testid="stDataEditor"] th:nth-child(6), div[data-testid="stDataEditor"] td:nth-child(6) { width: 100px !important; min-width: 100px !important; }
    div[data-testid="stDataEditor"] th:nth-child(7), div[data-testid="stDataEditor"] td:nth-child(7) { width: auto !important; min-width: 250px !important; }

    .cal-card {
        background-color: rgba(128, 128, 128, 0.12);
        border: 1px solid rgba(128, 128, 128, 0.35);
        border-radius: 8px;
        padding: 10px;
        min-height: 120px;
        margin-bottom: 10px;
    }
    .cal-day-header {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 6px;
        border-bottom: 1px solid rgba(128, 128, 128, 0.4);
        padding-bottom: 4px;
        display: flex;
        justify-content: space-between;
    }
    .cal-day-total { font-size: 12px; font-weight: normal; opacity: 0.8; }
    .cal-note { font-size: 13px; opacity: 0.75; }
</style>
""", unsafe_allow_html=True)

# ======================= 密碼登入 =======================
# 密碼只存在「伺服器端」的 Streamlit Secrets（APP_PASSWORD）：
# 不在程式碼裡、不會傳到瀏覽器，用 F12 看不到；比對也是在伺服器上完成。
MAX_FAILS = 5
LOCK_SECONDS = 300


@st.cache_resource
def _login_tracker():
    # 全站共用的失敗計數（重新整理頁面也無法重置）
    return {"fails": 0, "locked_until": 0.0}


def require_login():
    expected = str(st.secrets.get("APP_PASSWORD", ""))
    if not expected:
        st.error("尚未設定 APP_PASSWORD，為了安全程式已停止。請到 Streamlit Secrets 加入：APP_PASSWORD = 「你的密碼」")
        st.stop()
    if st.session_state.get("authed"):
        return

    tracker = _login_tracker()
    st.title("🔒 我是有錢人")
    wait = tracker["locked_until"] - time.time()
    if wait > 0:
        st.error(f"錯誤次數過多，請 {int(wait // 60) + 1} 分鐘後再試。")
        st.stop()

    with st.form("login_form"):
        pwd = st.text_input("請輸入密碼", type="password")
        submitted = st.form_submit_button("登入")

    if submitted:
        if hmac.compare_digest(pwd.encode("utf-8"), expected.encode("utf-8")):
            tracker["fails"] = 0
            st.session_state["authed"] = True
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


# ======================= 連線 Google 試算表 =======================
@st.cache_resource
def get_google_sheet():
    # 失敗時直接丟出例外，cache_resource 不會把失敗結果存起來，下次會自動重試
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

worksheet = sh.get_worksheet(0) if sh else None


@st.cache_resource
def get_settings_worksheet(_sh):
    if not _sh:
        return None
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


@st.cache_data(ttl=300)
def fetch_settings_rows(_settings_ws):
    """固定支出設定（含快取，寫入後記得 .clear()）"""
    if not _settings_ws:
        return []
    try:
        data = _settings_ws.get_all_values()
        return [pad_row(r, 3) for r in data[1:] if any(str(c).strip() for c in r)]
    except Exception:
        return []


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


settings_rows = fetch_settings_rows(settings_ws)
fixed_templates = build_templates(settings_rows)


# ======================= 預算設定 =======================
@st.cache_resource
def get_budget_worksheet(_sh):
    if not _sh:
        return None
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


@st.cache_data(ttl=300)
def fetch_budget_rows(_budget_ws):
    if not _budget_ws:
        return []
    try:
        data = _budget_ws.get_all_values()
        rows = [pad_row(r, 2) for r in data[1:]]
        return [r for r in rows if str(r[0]).strip()]
    except Exception:
        return []


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


budget_rows = fetch_budget_rows(budget_ws)
budgets = build_budgets(budget_rows)


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
        if cat == TOTAL_KEY:
            continue
        spent = exp.loc[exp["分類"] == cat, "金額_num"].sum()
        if spent >= lim:
            over.append(f"{cat}（${spent:,.0f} / ${lim:,.0f}）")
    if over:
        st.error("⚠️ 以下分類已超出預算：" + "、".join(over))


# ======================= 讀取記帳主表 =======================
DF_COLS = ["_row"] + FIELDS + ["年月", "日期_std", "金額_num"]


@st.cache_data(ttl=300)
def fetch_data(_sh):
    if not _sh:
        return pd.DataFrame(columns=DF_COLS)
    try:
        ws = _sh.get_worksheet(0)
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
    except Exception as e:
        st.error(f"資料讀取錯誤：{e}")
        return pd.DataFrame(columns=DF_COLS)


def clear_data_cache():
    fetch_data.clear()
    st.session_state.editor_ver += 1


def rows_still_match(ws, df_rows):
    """寫入前確認雲端那幾列仍和畫面上一致，避免多人/多裝置同時操作時改錯列"""
    all_raw = ws.get_all_values()
    for _, r in df_rows.iterrows():
        n = int(r["_row"])
        if n - 1 >= len(all_raw):
            return False
        cloud = pad_row(all_raw[n - 1])
        for i, col in enumerate(FIELDS):
            if str(cloud[i]).strip() != str(r[col]).strip():
                return False
    return True


# ======================= 主程式 =======================
if sh and worksheet:
    df = fetch_data(sh)

    # ---------- 側邊欄：新增記帳 ----------
    if st.sidebar.button("🚪 登出"):
        st.session_state.clear()
        st.rerun()

    st.sidebar.header("➕ 新增記帳")
    tab_general, tab_salary, tab_fixed, tab_budget = st.sidebar.tabs(["一般", "💰薪資", "🏠固定", "🎯預算"])

    with tab_general:
        tx_type = st.radio("類型", ["支出", "收入"], horizontal=True)
        category = st.selectbox("分類", EXPENSE_CATS if tx_type == "支出" else INCOME_CATS)
        amount = st.number_input("金額", value=None, step=1, min_value=0, placeholder="請輸入金額...")
        pay_method = st.selectbox("付款方式", PAY_OPTIONS)
        tx_date = st.date_input("日期", value=date.today())
        note = st.text_input("備註 (例如：鮮天下、加油)")

        if st.button("送出一般記帳"):
            if amount is not None and amount > 0:
                try:
                    worksheet.append_row(
                        [str(tx_date), tx_type, category, amount, pay_method, note],
                        value_input_option="RAW",
                    )
                    clear_data_cache()
                    flash_and_rerun("一般記帳新增成功！")
                except Exception as e:
                    st.sidebar.error(f"寫入失敗: {e}")
            else:
                st.sidebar.warning("請輸入有效的金額！")

    with tab_salary:
        default_salary = st.number_input("預設月薪金額", value=45000, step=1000)
        salary_date = st.date_input("入帳日期", value=date.today(), key="sal_date")
        if st.button("📥 一鍵入帳本月薪資"):
            try:
                worksheet.append_row(
                    [str(salary_date), "收入", "薪資", default_salary, "現金", "每月固定薪資"],
                    value_input_option="RAW",
                )
                clear_data_cache()
                flash_and_rerun(f"成功入帳薪資 ${default_salary:,}！")
            except Exception as e:
                st.sidebar.error(f"薪資入帳失敗: {e}")

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

        if st.button("📤 一鍵扣款固定支出"):
            try:
                worksheet.append_row(
                    [str(expense_date), "支出", "每月固定費用", default_expense, expense_pay, expense_note],
                    value_input_option="RAW",
                )
                clear_data_cache()
                flash_and_rerun(f"成功記錄固定支出【{expense_note}】${default_expense:,}！")
            except Exception as e:
                st.sidebar.error(f"支出記錄失敗: {e}")

        st.divider()
        with st.expander("⚙️ 線上修改或新增固定支出清單"):
            if settings_ws:
                df_settings = pd.DataFrame(settings_rows, columns=SETTINGS_HEADER)
                edited_settings = st.data_editor(
                    df_settings,
                    num_rows="dynamic",
                    key="settings_editor",
                    **STRETCH,
                )
                if st.button("💾 儲存範本修改"):
                    try:
                        clean_df = edited_settings.fillna("").astype(str)
                        clean_df = clean_df[clean_df["項目名稱"].str.strip() != ""]
                        new_data = [SETTINGS_HEADER] + clean_df.values.tolist()
                        old_len = len(settings_rows) + 1
                        # 先寫入新內容，再清掉多出來的舊列（避免先 clear 後寫入失敗而全部遺失）
                        settings_ws.update(range_name="A1", values=new_data)
                        if old_len > len(new_data):
                            settings_ws.batch_clear([f"A{len(new_data) + 1}:C{old_len}"])
                        fetch_settings_rows.clear()
                        flash_and_rerun("固定支出範本已成功更新！")
                    except Exception as e:
                        st.sidebar.error(f"儲存失敗: {e}")

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
                key="budget_editor",
                column_config={
                    "分類": st.column_config.SelectboxColumn(
                        "分類", options=[TOTAL_KEY] + EXPENSE_CATS, required=True
                    ),
                    "每月上限": st.column_config.NumberColumn("每月上限", min_value=0, step=500, format="%d"),
                },
                **STRETCH,
            )
            if st.button("💾 儲存預算"):
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
                    fetch_budget_rows.clear()
                    flash_and_rerun("預算已儲存！")
                except Exception as e:
                    st.sidebar.error(f"預算儲存失敗: {e}")

    # ---------- 月份篩選 ----------
    current_month_str = date.today().strftime("%Y-%m")
    if not df.empty:
        db_months = [m for m in df["年月"].dropna().unique().tolist() if re.fullmatch(r"\d{4}-\d{2}", str(m))]
    else:
        db_months = []
    all_months = sorted(set(db_months + [current_month_str]), reverse=True)
    selected_month = st.selectbox(
        "📅 選擇要檢視的月份", all_months, index=all_months.index(current_month_str)
    )

    if not df.empty:
        df_selected = df[df["年月"] == selected_month].reset_index(drop=True)
    else:
        df_selected = pd.DataFrame(columns=DF_COLS)

    total_income = df_selected.loc[df_selected["類型"] == "收入", "金額_num"].sum() if not df_selected.empty else 0
    total_expense = df_selected.loc[df_selected["類型"] == "支出", "金額_num"].sum() if not df_selected.empty else 0
    net_balance = total_income - total_expense

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(f"📈 {selected_month} 總收入", f"${int(total_income):,}")
    col_m2.metric(f"📉 {selected_month} 總花費", f"${int(total_expense):,}")
    col_m3.metric(f"💰 {selected_month} 本月結餘", f"${int(net_balance):,}")

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
            df_display = df_selected[FIELDS].copy()
            df_display.insert(0, "刪除", False)

            edited_df = st.data_editor(
                df_display,
                hide_index=True,
                key=f"expense_table_{st.session_state.editor_ver}",
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

            # 刪除：依「列號」刪除，一次 API 呼叫完成，不再整張表清空重寫
            with col1:
                if st.button("🗑️ 刪除所選項目"):
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

            # 儲存：只更新「有被修改的列」，不動其他月份、不改變順序
            with col2:
                if st.button("💾 儲存修改內容"):
                    try:
                        save_df = edited_df.drop(columns=["刪除"]).fillna("").astype(str)
                        orig_df = df_selected[FIELDS].astype(str)
                        changed_idx = [
                            i for i in save_df.index
                            if any(save_df.loc[i, c].strip() != orig_df.loc[i, c].strip() for c in FIELDS)
                        ]
                        if not changed_idx:
                            st.info("沒有偵測到任何修改。")
                        elif not rows_still_match(worksheet, df_selected.loc[changed_idx]):
                            st.error("雲端資料已被其他裝置更動，請重新整理頁面後再試一次。")
                            fetch_data.clear()
                        else:
                            updates = []
                            for i in changed_idx:
                                n = int(df_selected.loc[i, "_row"])
                                r = save_df.loc[i]
                                updates.append({
                                    "range": f"A{n}:F{n}",
                                    "values": [[
                                        r["日期"].strip(), r["類型"].strip(), r["分類"].strip(),
                                        to_number(r["金額"]), r["付款方式"].strip(), r["備註"],
                                    ]],
                                })
                            worksheet.batch_update(updates, value_input_option="RAW")
                            clear_data_cache()
                            flash_and_rerun(f"已同步 {len(changed_idx)} 筆修改到 Google 試算表！")
                    except Exception as e:
                        st.error(f"儲存失敗：{e}")
        else:
            st.info(f"所選月份 {selected_month} 目前還沒有任何記錄！")

    # ---------- 模式 2：圖表 ----------
    elif view_mode == "📊 圖表與固定費用":
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
                    fig_pie = px.pie(
                        df_expense, values="金額_num", names="分類",
                        title=f"{selected_month} 各類別支出佔比", hole=0.4,
                        color="分類", color_discrete_map=color_map,
                    )
                    st.plotly_chart(fig_pie, **STRETCH)
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
                    st.plotly_chart(fig_bar, **STRETCH)
            else:
                st.info("此月份尚無支出紀錄可產出圖表。")

    # ---------- 模式 3：預算追蹤 ----------
    elif view_mode == "🎯 預算追蹤":
        st.subheader(f"🎯 {selected_month} 預算追蹤")
        if not budgets:
            st.info("尚未設定預算，請到左側「🎯預算」分頁設定。")
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
                ratio = spent / limit
                left = limit - spent
                left_txt = f"剩餘 ${left:,.0f}" if left >= 0 else f"超支 ${-left:,.0f}"
                icon = "🔴" if ratio >= 1 else ("🟠" if ratio >= 0.8 else "🟢")
                st.markdown(f"{icon} **{name}**　${spent:,.0f} / ${limit:,.0f}　（{left_txt}）")
                st.progress(float(min(ratio, 1.0)), text=f"{ratio:.0%}")

            if selected_month == current_month_str and TOTAL_KEY in budgets:
                y, m = map(int, selected_month.split("-"))
                days_left = py_calendar.monthrange(y, m)[1] - date.today().day + 1
                remain = budgets[TOTAL_KEY] - total_expense
                st.divider()
                if remain > 0:
                    st.info(f"💡 本月還有 {days_left} 天（含今天），平均每天可花 ${remain / days_left:,.0f}")
                else:
                    st.warning("💡 本月總預算已用完，建議接下來盡量不要再花錢。")

    # ---------- 模式 4：月曆 ----------
    elif view_mode == "📅 月曆模式":
        st.subheader(f"📅 {selected_month} 日曆視圖")

        try:
            year, month = map(int, selected_month.split("-"))
        except ValueError:
            year, month = date.today().year, date.today().month

        # firstweekday=6 → 週日為每週第一天，與標題列一致
        cal_matrix = py_calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)

        weekdays = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"]
        cols = st.columns(7)
        for i, day_name in enumerate(weekdays):
            cols[i].markdown(f"<h4 style='text-align: center;'>{day_name}</h4>", unsafe_allow_html=True)

        st.divider()

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
                            color = "#ff6b6b" if is_exp else "#51cf66"
                            sign = "-" if is_exp else "+"
                            amt = row["金額_num"]
                            day_net += -amt if is_exp else amt
                            body += (
                                f"<div style='margin-bottom: 6px;'>"
                                f"<span style='color:{color}; font-size:14px; font-weight:bold;'>"
                                f"{sign}${amt:,.0f} ({html.escape(str(row['分類']))})</span><br>"
                                f"<span class='cal-note'>{html.escape(str(row['備註']))}</span>"
                                f"</div>"
                            )
                    total_html = ""
                    if body:
                        total_html = f"<span class='cal-day-total'>淨 {day_net:+,.0f}</span>"
                    st.markdown(
                        f"<div class='cal-card'><div class='cal-day-header'>"
                        f"<span>{day} 日</span>{total_html}</div>{body}</div>",
                        unsafe_allow_html=True,
                    )

else:
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")
