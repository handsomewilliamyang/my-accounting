import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import calendar as py_calendar
import plotly.express as px

# 網頁標題與基本設定
st.set_page_config(page_title="我是有錢人", page_icon="💰", layout="wide")

# 欄位寬度與日曆樣式 CSS
st.markdown("""
<style>
    div[data-testid="stDataEditor"] th:nth-child(1), div[data-testid="stDataEditor"] td:nth-child(1) { width: 50px !important; min-width: 50px !important; }   /* 刪除 */
    div[data-testid="stDataEditor"] th:nth-child(2), div[data-testid="stDataEditor"] td:nth-child(2) { width: 110px !important; min-width: 110px !important; } /* 日期 */
    div[data-testid="stDataEditor"] th:nth-child(3), div[data-testid="stDataEditor"] td:nth-child(3) { width: 70px !important; min-width: 70px !important; }   /* 類型 */
    div[data-testid="stDataEditor"] th:nth-child(4), div[data-testid="stDataEditor"] td:nth-child(4) { width: 90px !important; min-width: 90px !important; }   /* 分類 */
    div[data-testid="stDataEditor"] th:nth-child(5), div[data-testid="stDataEditor"] td:nth-child(5) { width: 80px !important; min-width: 80px !important; }   /* 金額 */
    div[data-testid="stDataEditor"] th:nth-child(6), div[data-testid="stDataEditor"] td:nth-child(6) { width: 100px !important; min-width: 100px !important; } /* 付款方式 */
    div[data-testid="stDataEditor"] th:nth-child(7), div[data-testid="stDataEditor"] td:nth-child(7) { width: auto !important; min-width: 250px !important; }  /* 備註 */

    .cal-card {
        background-color: #1e1e24;
        border: 1px solid #33333d;
        border-radius: 8px;
        padding: 10px;
        min-height: 120px;
        margin-bottom: 10px;
    }
    .cal-day-header {
        font-size: 16px;
        font-weight: bold;
        color: #ffffff;
        margin-bottom: 6px;
        border-bottom: 1px solid #444;
        padding-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("💰 我是有錢人")
st.markdown("一天一塊錢 七天就有七塊錢")

# Google 試算表網址
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1DTNSXJUJE_7PQIi5yebsmt_mC8bIe1D82IF2FgDaPyM/edit?gid=0#gid=0"

# 連線 Google 試算表
@st.cache_resource
def get_google_sheet():
    try:
        raw_key = st.secrets["gcp_service_account"]["private_key"]
        fixed_key = raw_key.replace("\\n", "\n")
        
        creds_dict = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": fixed_key,
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
            "universe_domain": st.secrets["gcp_service_account"].get("universe_domain", "googleapis.com")
        }
        
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_url(SPREADSHEET_URL)
        return sh
    except Exception as e:
        st.error(f"連線 Google 試算表失敗：{e}")
        return None

sh = get_google_sheet()
worksheet = sh.get_worksheet(0) if sh else None

# 取得「固定支出設定」分頁
def get_settings_worksheet(_sh):
    if not _sh:
        return None
    try:
        return _sh.worksheet("固定支出設定")
    except:
        try:
            new_ws = _sh.add_worksheet(title="固定支出設定", rows=100, cols=3)
            new_ws.append_row(["項目名稱", "預設金額", "付款方式"])
            new_ws.append_row(["孝親費", "5000", "現金"])
            new_ws.append_row(["電信費", "599", "信用卡"])
            return new_ws
        except Exception as e:
            return None

settings_ws = get_settings_worksheet(sh)

# 讀取固定支出設定範本
def fetch_fixed_templates(_settings_ws):
    if not _settings_ws:
        return {"孝親費": {"amount": 5000, "pay": "現金"}}
    try:
        data = _settings_ws.get_all_values()
        if len(data) < 2:
            return {}
        templates = {}
        for row in data[1:]:
            if len(row) >= 1 and row[0].strip():
                name = row[0].strip()
                try:
                    amt = float(row[1].strip().replace(",", "")) if len(row) > 1 and row[1].strip() else 0
                except:
                    amt = 0
                pay = row[2].strip() if len(row) > 2 and row[2].strip() else "現金"
                templates[name] = {"amount": amt, "pay": pay}
        return templates
    except Exception as e:
        return {"孝親費": {"amount": 5000, "pay": "現金"}}

fixed_templates = fetch_fixed_templates(settings_ws)

# 資料讀取函數 (記帳主表 - 標準帶標題列版)
@st.cache_data(ttl=300)
def fetch_data_v34(_sh):
    if not _sh:
        return pd.DataFrame()
    try:
        ws = _sh.get_worksheet(0)
        raw_data = ws.get_all_values()
        
        if len(raw_data) < 2:
            return pd.DataFrame()
            
        # 第 1 行是標題
        headers = [str(h).strip().replace('\u200b', '').replace('\n', '') for h in raw_data[0]][:6]
        
        data_rows = []
        # 從第 2 行開始 (索引 1) 是真實資料
        for r_idx, row in enumerate(raw_data[1:]):
            row_padded = row[:6] + [""] * max(0, 6 - len(row))
            data_rows.append({
                "excel_row": r_idx + 2,  # Google 試算表的真實行號 (第 2 行開始)
                "日期": str(row_padded[0]).strip(),
                "類型": str(row_padded[1]).strip(),
                "分類": str(row_padded[2]).strip(),
                "金額": str(row_padded[3]).strip(),
                "付款方式": str(row_padded[4]).strip(),
                "備註": str(row_padded[5]).strip()
            })
            
        df_temp = pd.DataFrame(data_rows)
        
        if not df_temp.empty and "日期" in df_temp.columns:
            clean_dates = df_temp["日期"].str.replace("/", "-")
            parsed = pd.to_datetime(clean_dates, errors="coerce")
            df_temp["年月"] = parsed.dt.strftime("%Y-%m")
            
            mask = df_temp["年月"].isna()
            if mask.any():
                df_temp.loc[mask, "年月"] = clean_dates[mask].str.slice(0, 7)
                
        return df_temp
    except Exception as e:
        st.error(f"資料讀取錯誤：{e}")
        return pd.DataFrame()

df = fetch_data_v34(sh)

if sh:
    if not df.empty and "金額" in df.columns:
        df["金額_num"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0)
    else:
        df["金額_num"] = 0

    if not df.empty and "類型" in df.columns:
        df["類型"] = df["類型"].astype(str).str.strip()

    # ================= 側邊欄：僅保留新增記帳與固定支出管理 =================
    st.sidebar.header("➕ 新增記帳")
    
    tab_general, tab_salary, tab_fixed = st.sidebar.tabs(["一般", "💰薪資", "🏠固定支出"])
    
    with tab_general:
        amount = st.number_input("金額", value=None, step=1, placeholder="請輸入金額...")
        category = st.selectbox("分類", ["伙食", "交通", "購物", "娛樂", "每月固定費用", "其他支出", "薪資", "其他收入"])
        tx_type = st.radio("類型", ["支出", "收入"], horizontal=True)
        pay_method = st.selectbox("付款方式", ["現金", "信用卡"])
        tx_date = st.date_input("日期", value=date.today())
        note = st.text_input("備註 (例如：鮮天下、加油)")
        
        if st.button("送出一般記帳"):
            if amount is not None and amount > 0:
                try:
                    row = [str(tx_date), tx_type, category, str(amount), pay_method, note]
                    worksheet.append_row(row)
                    fetch_data_v34.clear()
                    st.success("一般記帳新增成功！")
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"寫入失敗: {e}")
            else:
                st.sidebar.warning("請輸入有效的金額！")

    with tab_salary:
        default_salary = st.number_input("預設月薪金額", value=45000, step=1000)
        salary_date = st.date_input("入帳日期", value=date.today(), key="sal_date")
        if st.button("📥 一鍵入帳本月薪資"):
            try:
                salary_row = [str(salary_date), "收入", "薪資", str(default_salary), "現金", "每月固定薪資"]
                worksheet.append_row(salary_row)
                fetch_data_v34.clear()
                st.sidebar.success(f"成功入帳薪資 ${default_salary:,}！")
                st.rerun()
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
        
        pay_options = ["現金", "信用卡", "行動支付"]
        default_pay_idx = pay_options.index(default_val["pay"]) if default_val["pay"] in pay_options else 0
        expense_pay = st.selectbox("付款方式", pay_options, index=default_pay_idx, key="exp_pay")
        
        expense_date = st.date_input("扣款日期", value=date.today(), key="exp_date")
        
        if st.button("📤 一鍵扣款固定支出"):
            try:
                expense_row = [str(expense_date), "支出", "每月固定費用", str(default_expense), expense_pay, expense_note]
                worksheet.append_row(expense_row)
                fetch_data_v34.clear()
                st.sidebar.success(f"成功記錄固定支出 【{expense_note}】 ${default_expense:,}！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"支出記錄失敗: {e}")

        st.divider()
        with st.expander("⚙️ 線上修改或新增固定支出清單"):
            if settings_ws:
                raw_settings = settings_ws.get_all_values()
                if len(raw_settings) > 1:
                    df_settings = pd.DataFrame(raw_settings[1:], columns=raw_settings[0])
                else:
                    df_settings = pd.DataFrame(columns=["項目名稱", "預設金額", "付款方式"])
                
                edited_settings = st.data_editor(
                    df_settings,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="settings_editor"
                )
                
                if st.button("💾 儲存範本修改"):
                    try:
                        new_settings_data = [["項目名稱", "預設金額", "付款方式"]] + edited_settings.values.tolist()
                        settings_ws.clear()
                        settings_ws.update(range_name="A1", values=new_settings_data)
                        st.sidebar.success("固定支出範本已成功更新！")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"儲存失敗: {e}")

    # ================= 主畫面上方：月份篩選器 =================
    current_month_str = date.today().strftime("%Y-%m")
    
    if not df.empty and "年月" in df.columns:
        db_months = [m for m in df["年月"].dropna().unique().tolist() if len(str(m)) >= 7]
    else:
        db_months = []
        
    all_months = sorted(list(set(db_months + [current_month_str])), reverse=True)
    
    selected_month = st.selectbox("📅 選擇要檢視的月份", all_months, index=0)

    if not df.empty and "年月" in df.columns:
        df_selected = df[df["年月"] == selected_month]
    else:
        df_selected = pd.DataFrame()

    total_income = 0
    total_expense = 0
    
    if not df_selected.empty and "類型" in df_selected.columns:
        total_income = df_selected[df_selected["類型"] == "收入"]["金額_num"].sum()
        total_expense = df_selected[df_selected["類型"] == "支出"]["金額_num"].sum()

    net_balance = total_income - total_expense

    # 🔥 三欄排版：總收入、總花費、本月結餘
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label=f"📈 {selected_month} 總收入", value=f"${int(total_income):,}")
    with col_m2:
        st.metric(label=f"📉 {selected_month} 總花費", value=f"${int(total_expense):,}")
    with col_m3:
        st.metric(label=f"💰 {selected_month} 本月結餘", value=f"${int(net_balance):,}")

    st.divider()

    # ================= 主畫面 偽分頁(Radio) 設計 =================
    view_mode = st.radio(
        "選擇檢視模式：", 
        ["📋 記帳明細列表", "📊 圖表與固定費用", "📅 月曆模式"], 
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.divider()

    # --- 模式 1: 記帳明細列表 ---
    if view_mode == "📋 記帳明細列表":
        st.subheader(f"📋 {selected_month} 記帳明細列表")
        if not df_selected.empty:
            df_display = df_selected.copy()
            for col in ["excel_row", "年月", "金額_num"]:
                if col in df_display.columns:
                    df_display = df_display.drop(columns=[col])
                
            df_display.insert(0, "刪除", False)
            
            edited_df = st.data_editor(
                df_display, 
                use_container_width=True,
                hide_index=True,
                key="expense_table",
                column_config={
                    "刪除": st.column_config.CheckboxColumn("刪除", width="small"),
                    "日期": st.column_config.TextColumn("日期", width="small"),
                    "類型": st.column_config.TextColumn("類型", width="small"),
                    "分類": st.column_config.TextColumn("分類", width="small"),
                    "金額": st.column_config.TextColumn("金額", width="small"),
                    "付款方式": st.column_config.TextColumn("付款方式", width="small"),
                    "備註": st.column_config.TextColumn("備註", width="large")
                }
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ 刪除所選項目"):
                    rows_to_delete = edited_df[edited_df["刪除"] == True].index.tolist()
                    if rows_to_delete:
                        try:
                            excel_rows_to_remove = []
                            for r_idx in rows_to_delete:
                                target_excel_row = df_selected.iloc[r_idx]["excel_row"]
                                excel_rows_to_remove.append(target_excel_row)
                            
                            # 由大到小排序刪除，確保行號不會因為前面的刪除而位移
                            for r_num in sorted(excel_rows_to_remove, reverse=True):
                                worksheet.delete_rows(r_num)
                                
                            fetch_data_v34.clear()
                            st.success("已成功透過勾選從 Google 試算表刪除選取的項目！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"刪除失敗：{e}")
                    else:
                        st.warning("請先勾選您想要刪除的項目！")
            
            with col2:
                if st.button("💾 儲存修改內容"):
                    try:
                        save_df = edited_df.drop(columns=["刪除"]).fillna("")
                        
                        # 抓取全體資料並保留標題列
                        all_raw = worksheet.get_all_values()
                        header = all_raw[0] if all_raw else ["日期", "類型", "分類", "金額", "付款方式", "備註"]
                        
                        other_df_raw = []
                        for r in all_raw[1:]:
                            r_padded = r[:6] + [""] * max(0, 6 - len(r))
                            dt_str = str(r_padded[0]).replace("/", "-")
                            if not dt_str.startswith(selected_month):
                                other_df_raw.append(r_padded)
                                
                        new_month_rows = save_df.values.tolist()
                        final_all_rows = [header] + other_df_raw + new_month_rows
                        
                        worksheet.clear()
                        worksheet.update(range_name="A1", values=final_all_rows)
                        
                        fetch_data_v34.clear()
                        st.success("修改已成功同步至 Google 試算表！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"儲存失敗：{e}")
        else:
            st.info(f"所選月份 {selected_month} 目前還沒有任何記錄！")

    # --- 模式 2: 圖表分析與每月固定費用 ---
    elif view_mode == "📊 圖表與固定費用":
        st.subheader(f"📌 {selected_month} 每月固定費用總覽")
        if not df_selected.empty:
            df_fixed = df_selected[df_selected["分類"] == "每月固定費用"]
            if not df_fixed.empty:
                total_fixed = df_fixed["金額_num"].sum()
                st.metric(label="💰 固定開銷總計", value=f"${int(total_fixed):,}")
                st.dataframe(df_fixed[["日期", "金額", "付款方式", "備註"]], use_container_width=True)
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
                    "伙食": "#33ff57",
                    "交通": "#3357ff",
                    "購物": "#ff33a8",
                    "娛樂": "#ffbd33",
                    "每月固定費用": "#ff5733",
                    "其他支出": "#a833ff"
                }
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_pie = px.pie(
                        df_expense, values='金額_num', names='分類', 
                        title=f'{selected_month} 各類別支出佔比', hole=0.4,
                        color='分類',
                        color_discrete_map=color_map
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    fig_bar = px.bar(
                        df_expense.groupby(['日期', '分類'], as_index=False)['金額_num'].sum(),
                        x='日期', y='金額_num',
                        title=f'{selected_month} 每日總支出趨勢', text_auto=True,
                        color='分類',
                        color_discrete_map=color_map
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("此月份尚無支出紀錄可產出圖表。")

    # --- 模式 3: 月曆模式 ---
    elif view_mode == "📅 月曆模式":
        st.subheader(f"📅 {selected_month} 日曆視圖")
        
        try:
            year, month = map(int, selected_month.split("-"))
        except:
            year, month = date.today().year, date.today().month

        cal_matrix = py_calendar.monthcalendar(year, month)
        
        weekdays = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"]
        cols = st.columns(7)
        for i, day_name in enumerate(weekdays):
            cols[i].markdown(f"<h4 style='text-align: center; color: #ffffff;'>{day_name}</h4>", unsafe_allow_html=True)
            
        st.divider()
        
        for week in cal_matrix:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day == 0:
                        st.markdown("<div class='cal-card' style='opacity: 0.2;'><div class='cal-day-header'>-</div></div>", unsafe_allow_html=True)
                    else:
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        
                        card_html = f"<div class='cal-card'><div class='cal-day-header'>{day} 日</div>"
                        
                        if not df_selected.empty:
                            day_records = df_selected[df_selected["日期"].str.startswith(date_str)]
                            if not day_records.empty:
                                for _, row in day_records.iterrows():
                                    t_type = str(row["類型"]).strip()
                                    color = "#ff6b6b" if t_type == "支出" else "#51cf66"
                                    sign = "-" if t_type == "支出" else "+"
                                    
                                    card_html += (
                                        f"<div style='margin-bottom: 6px;'>"
                                        f"<span style='color:{color}; font-size:14px; font-weight:bold;'>"
                                        f"{sign}${row['金額']} ({row['分類']})"
                                        f"</span><br>"
                                        f"<span style='font-size:13px; color:#cccccc;'>"
                                        f"{row['備註']}"
                                        f"</span>"
                                        f"</div>"
                                    )
                        card_html += "</div>"
                        st.markdown(card_html, unsafe_allow_html=True)

else:
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")
