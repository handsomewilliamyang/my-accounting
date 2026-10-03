import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
import plotly.express as px
from streamlit_calendar import calendar

# 網頁標題與基本設定
st.set_page_config(page_title="我是有錢人", page_icon="💰", layout="wide")

st.title("💰 我是有錢人")
st.markdown("一天一塊錢 七天就有七塊錢")

# Google 試算表網址
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1DTNSXJUJE_7PQIi5yebsmt_mC8bIe1D82IF2FgDaPyM/edit?gid=0#gid=0"

# 連線 Google 試算表 (具備防呆與換行自動修復機制)
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

# 資料快取 (Data Caching) 提升效能 (強化日期與年月解析防呆版)
@st.cache_data(ttl=3600)
def fetch_data(_sh):
    if _sh:
        try:
            ws = _sh.get_worksheet(0)
            data = ws.get_all_records()
            df_temp = pd.DataFrame(data)
            
            if not df_temp.empty:
                df_temp.columns = df_temp.columns.astype(str).str.strip()
                
                # 強制確保日期欄位存在並透過字串切片安全建立「年月」欄位
                if "日期" in df_temp.columns:
                    df_temp["日期"] = df_temp["日期"].astype(str).str.strip()
                    date_series = df_temp["日期"].str.slice(0, 10)
                    df_temp["年月"] = date_series.str.slice(0, 7)
                    
            return df_temp
        except Exception as e:
            st.error(f"讀取資料發生錯誤：{e}")
            return pd.DataFrame()
    return pd.DataFrame()

df = fetch_data(sh)

if sh:
    # 確保金額格式正確
    if not df.empty and "金額" in df.columns:
        df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0)

    # ================= 側邊欄：月份篩選與一般新增 =================
    st.sidebar.header("📅 月份篩選")
    
    # 建立月份清單：結合資料庫所有的年月 + 確保當前系統月份絕對存在
    current_month_str = date.today().strftime("%Y-%m")
    
    if not df.empty and "年月" in df.columns:
        db_months = df["年月"].dropna().unique().tolist()
    else:
        db_months = []
        
    # 合併並排序（確保當月與所有歷史月份不遺漏，降冪排列最新在前）
    all_months = sorted(list(set(db_months + [current_month_str])), reverse=True)
    
    selected_month = st.sidebar.selectbox("選擇要檢視的月份", all_months, index=0)
    
    # 根據選定的月份過濾資料
    if not df.empty and "年月" in df.columns:
        df_selected = df[df["年月"] == selected_month]
    else:
        df_selected = pd.DataFrame()

    st.sidebar.divider()
    st.sidebar.header("➕ 一般新增記帳")
    
    amount = st.sidebar.number_input("金額", value=None, step=1, placeholder="請輸入金額...")
    category = st.sidebar.selectbox("分類", ["伙食", "交通", "購物", "娛樂", "每月固定費用", "其他支出", "薪資", "其他收入"])
    tx_type = st.sidebar.radio("類型", ["支出", "收入"])
    pay_method = st.sidebar.selectbox("付款方式", ["現金", "信用卡"])
    tx_date = st.sidebar.date_input("日期", value=date.today())
    note = st.sidebar.text_input("備註 (例如：鮮天下、加油)")
    
    submit_button = st.sidebar.button("送出記帳")

    if submit_button:
        if amount is not None and amount > 0:
            try:
                row = [str(tx_date), tx_type, category, amount, pay_method, note]
                worksheet.append_row(row)
                fetch_data.clear() # 清除快取
                st.sidebar.success("新增成功！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"寫入失敗: {e}")
        else:
            st.sidebar.warning("請輸入有效的金額！")

    # ================= 側邊欄設計：快速記帳專區 =================
    st.sidebar.divider()
    st.sidebar.header("⚡ 快速記帳專區")
    
    with st.sidebar.expander("📥 帶入固定薪資"):
        default_salary = st.number_input("預設月薪金額", value=45000, step=1000)
        salary_date = st.date_input("入帳日期", value=date.today(), key="sal_date")
        if st.button("📥 一鍵入帳本月薪資"):
            try:
                salary_row = [str(salary_date), "收入", "薪資", default_salary, "現金", "每月固定薪資"]
                worksheet.append_row(salary_row)
                fetch_data.clear()
                st.sidebar.success(f"成功入帳薪資 ${default_salary:,}！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"薪資入帳失敗: {e}")
                
    with st.sidebar.expander("📤 帶入固定支出"):
        expense_note = st.text_input("支出項目 (例: 房租/電信費)", value="房租")
        default_expense = st.number_input("預設支出金額", value=10000, step=500)
        expense_pay = st.selectbox("付款方式", ["現金", "信用卡"], key="exp_pay")
        expense_date = st.date_input("扣款日期", value=date.today(), key="exp_date")
        if st.button("📤 一鍵扣款固定支出"):
            try:
                expense_row = [str(expense_date), "支出", "每月固定費用", default_expense, expense_pay, expense_note]
                worksheet.append_row(expense_row)
                fetch_data.clear()
                st.sidebar.success(f"成功記錄固定支出 ${default_expense:,}！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"支出記錄失敗: {e}")

    # ================= 主畫面：針對「選定月份」計算收支 =================
    st.subheader(f"📅 目前檢視月份：{selected_month}")
    
    total_income = 0
    total_expense = 0
    
    if not df_selected.empty and "類型" in df_selected.columns:
        total_income = df_selected[df_selected["類型"] == "收入"]["金額"].sum()
        total_expense = df_selected[df_selected["類型"] == "支出"]["金額"].sum()

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(label=f"📈 {selected_month} 總收入", value=f"${total_income:,}")
    with col_m2:
        st.metric(label=f"📉 {selected_month} 總花費", value=f"${total_expense:,}")

    st.divider()

    # ================= 主畫面 偽分頁(Radio) 設計 =================
    view_mode = st.radio(
        "選擇檢視模式：", 
        ["📋 記帳明細列表", "📊 圖表與固定費用", "📅 月曆模式", "🗄️ 歷史月份收納區"], 
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.divider()

    # --- 模式 1: 記帳明細列表 (針對選定月份) ---
    if view_mode == "📋 記帳明細列表":
        st.subheader(f"📋 {selected_month} 記帳明細列表")
        if not df_selected.empty:
            df_display = df_selected.copy()
            if "年月" in df_display.columns:
                df_display = df_display.drop(columns=["年月"])
            df_display.insert(0, "刪除", False)
            
            edited_df = st.data_editor(
                df_display, 
                use_container_width=True,
                hide_index=True,
                key="expense_table"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️️ 刪除所選項目"):
                    rows_to_delete = edited_df[edited_df["刪除"] == True].index.tolist()
                    if rows_to_delete:
                        try:
                            for row_idx in sorted(rows_to_delete, reverse=True):
                                target_row = df_selected.iloc[row_idx]
                                original_index = df.index[(df["日期"] == target_row["日期"]) & 
                                                          (df["金額"] == target_row["金額"]) & 
                                                          (df["備註"] == target_row["備註"])].tolist()
                                if original_index:
                                    worksheet.delete_rows(original_index[0] + 2)
                                
                            fetch_data.clear()
                            st.success("已成功刪除選取的項目！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"刪除失敗：{e}")
                    else:
                        st.warning("請先勾選您想要刪除的項目！")
            
            with col2:
                if st.button("💾 儲存修改內容"):
                    try:
                        save_df = edited_df.drop(columns=["刪除"])
                        save_df = save_df.fillna("")
                        other_df = df[df["年月"] != selected_month].drop(columns=["年月"])
                        final_save_df = pd.concat([other_df, save_df], ignore_index=True)
                        
                        new_data = [final_save_df.columns.values.tolist()] + final_save_df.values.tolist()
                        worksheet.clear()
                        worksheet.update(range_name="A1", values=new_data)
                        
                        fetch_data.clear()
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
                total_fixed = df_fixed["金額"].sum()
                st.metric(label="💰 固定開銷總計", value=f"${total_fixed:,}")
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
                col1, col2 = st.columns(2)
                vivid_colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A8', '#FFBD33', '#33FFF2', '#A833FF']
                
                with col1:
                    fig_pie = px.pie(
                        df_expense, values='金額', names='分類', 
                        title=f'{selected_month} 各類別支出佔比', hole=0.4,
                        color_discrete_sequence=vivid_colors
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    df_daily = df_expense.groupby(['日期', '分類'], as_index=False)['金額'].sum()
                    fig_bar = px.bar(
                        df_daily, x='日期', y='金額', color='分類',
                        title=f'{selected_month} 每日總支出趨勢', text_auto=True,
                        color_discrete_sequence=vivid_colors
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("此月份尚無支出紀錄可產出圖表。")

    # --- 模式 3: 月曆模式 ---
    elif view_mode == "📅 月曆模式":
        st.subheader(f"📅 {selected_month} 月曆視圖")
        if not df_selected.empty:
            events = []
            for idx, row in df_selected.iterrows():
                event_color = "#FF3B30" if row["類型"] == "支出" else "#34C759"
                events.append({
                    "title": f"{row['分類']} ${row['金額']}",
                    "start": str(row["日期"]),
                    "backgroundColor": event_color,
                    "borderColor": event_color
                })
            
            calendar_options = {
                "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,timeGridWeek,timeGridDay"},
                "initialView": "dayGridMonth"
            }
            calendar(events=events, options=calendar_options)
        else:
            st.info("此月份尚無資料可顯示於月曆。")

    # --- 模式 4: 歷史月份收納區 (隨時可查看的縮合模式) ---
    elif view_mode == "🗄️ 歷史月份收納區":
        st.subheader("🗄️ 歷史月份收納與快速查閱")
        st.markdown("這裡自動將各月份的資料收納為摺疊清單，點擊即可隨時展開查看詳細紀錄與總結：")
        
        if not df.empty and "年月" in df.columns:
            sorted_months = sorted(df["年月"].dropna().unique().tolist(), reverse=True)
            
            for m in sorted_months:
                df_m = df[df["年月"] == m]
                m_income = df_m[df_m["類型"] == "收入"]["金額"].sum()
                m_expense = df_m[df_m["類型"] == "支出"]["金額"].sum()
                net_amount = m_income - m_expense
                
                with st.expander(f"📂 點擊展開：{m} 月份報表 (收入: ${m_income:,} | 支出: ${m_expense:,} | 結餘: ${net_amount:,})"):
                    col_ex1, col_ex2, col_ex3 = st.columns(3)
                    col_ex1.metric("總收入", f"${m_income:,}")
                    col_ex2.metric("總支出", f"${m_expense:,}")
                    col_ex3.metric("月結餘", f"${net_amount:,}")
                    
                    st.markdown(f"**{m} 詳細明細紀錄：**")
                    st.dataframe(df_m.drop(columns=["年月"]), use_container_width=True)
        else:
            st.info("目前尚無任何歷史資料。")

else:
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")
