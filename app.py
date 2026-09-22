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

# 連線 Google 試算表
@st.cache_resource
def get_google_sheet():
    try:
        secret_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(secret_dict)
        sh = gc.open_by_url(SPREADSHEET_URL)
        return sh
    except Exception as e:
        st.error(f"連線 Google 試算表失敗：{e}")
        return None

sh = get_google_sheet()

if sh:
    try:
        worksheet = sh.get_worksheet(0) # 取得第一個分頁
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
    except Exception as e:
        df = pd.DataFrame()

    # ================= 計算財務指標 (總收入、總花費) =================
    total_income = 0
    total_expense = 0
    
    if not df.empty and "類型" in df.columns and "金額" in df.columns:
        df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0)
        
        total_income = df[df["類型"] == "收入"]["金額"].sum()
        total_expense = df[df["類型"] == "支出"]["金額"].sum()

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric(label="📈 總收入", value=f"${total_income:,}")
    with col_m2:
        st.metric(label="📉 總花費", value=f"${total_expense:,}")

    st.divider()

    # ================= 側邊欄設計 =================
    st.sidebar.header("➕ 新增記帳")
    
    amount = st.sidebar.number_input("金額", value=None, step=1, placeholder="請輸入金額...")
    category = st.sidebar.selectbox("分類", ["每月固定費用", "伙食", "交通", "購物", "娛樂", "其他支出", "薪資", "其他收入"])
    tx_type = st.sidebar.radio("類型", ["支出", "收入"])
    pay_method = st.sidebar.selectbox("付款方式", ["現金", "信用卡"])
    tx_date = st.sidebar.date_input("日期", value=date.today())
    note = st.sidebar.text_input("備註 (例如：房租、Netflix 訂閱)")
    
    submit_button = st.sidebar.button("送出記帳")

    if submit_button:
        if amount is not None and amount > 0:
            try:
                row = [str(tx_date), tx_type, category, amount, pay_method, note]
                worksheet.append_row(row)
                st.sidebar.success("新增成功！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"寫入失敗: {e}")
        else:
            st.sidebar.warning("請輸入有效的金額！")

    # --- 快速記帳（固定薪資循環專區） ---
    st.sidebar.divider()
    st.sidebar.header("⚡ 快速固定收入")
    with st.sidebar.expander("設定與帶入固定薪資"):
        default_salary = st.number_input("預設月薪金額", value=45000, step=1000)
        salary_date = st.date_input("入帳日期", value=date.today(), key="sal_date")
        
        if st.button("📥 一鍵入帳本月薪資"):
            try:
                salary_row = [str(salary_date), "收入", "薪資", default_salary, "現金", "每月固定薪資"]
                worksheet.append_row(salary_row)
                st.sidebar.success(f"成功入帳薪資 ${default_salary:,}！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"薪資入帳失敗: {e}")

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
        st.subheader("📋 記帳明細列表")
        if not df.empty:
            df_display = df.copy()
            df_display.insert(0, "刪除", False)
            
            edited_df = st.data_editor(
                df_display, 
                use_container_width=True,
                hide_index=True,
                key="expense_table"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ 刪除所選項目"):
                    rows_to_delete = edited_df[edited_df["刪除"] == True].index.tolist()
                    if rows_to_delete:
                        try:
                            for row_idx in sorted(rows_to_delete, reverse=True):
                                worksheet.delete_rows(row_idx + 2)
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
                        new_data = [save_df.columns.values.tolist()] + save_df.values.tolist()
                        
                        worksheet.clear()
                        worksheet.update(range_name="A1", values=new_data)
                        
                        st.success("修改已成功同步至 Google 試算表！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"儲存失敗：{e}")
        else:
            st.info("目前還沒有任何記錄，請從側邊欄新增您的第一筆帳目！")

    # --- 模式 2: 圖表分析與每月固定費用 ---
    elif view_mode == "📊 圖表與固定費用":
        st.subheader("📌 每月固定費用總覽")
        if not df.empty:
            df_fixed = df[df["分類"] == "每月固定費用"]
            if not df_fixed.empty:
                total_fixed = df_fixed["金額"].sum()
                st.metric(label="💰 每月固定開銷總計", value=f"${total_fixed:,}")
                st.dataframe(df_fixed[["日期", "金額", "付款方式", "備註"]], use_container_width=True)
            else:
                st.info("目前尚無設定「每月固定費用」的紀錄。")
        else:
            st.info("目前尚無資料。")

        st.divider()
        
        st.subheader("📊 財務視覺化分析")
        if not df.empty:
            df_expense = df[df["類型"] == "支出"]
            if not df_expense.empty:
                col1, col2 = st.columns(2)
                
                vivid_colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A8', '#FFBD33', '#33FFF2', '#A833FF']
                
                with col1:
                    fig_pie = px.pie(
                        df_expense, 
                        values='金額', 
                        names='分類', 
                        title='各類別支出佔比', 
                        hole=0.4,
                        color_discrete_sequence=vivid_colors
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    df_daily = df_expense.groupby(['日期', '分類'], as_index=False)['金額'].sum()
                    fig_bar = px.bar(
                        df_daily, 
                        x='日期', 
                        y='金額', 
                        color='分類',
                        title='每日總支出趨勢', 
                        text_auto=True,
                        color_discrete_sequence=vivid_colors
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("目前尚無支出紀錄可產出圖表。")

    # --- 模式 3: 月曆模式 ---
    elif view_mode == "📅 月曆模式":
        st.subheader("📅 月曆視圖")
        if not df.empty:
            events = []
            for idx, row in df.iterrows():
                event_color = "#FF3B30" if row["類型"] == "支出" else "#34C759"
                events.append({
                    "title": f"{row['分類']} ${row['金額']}",
                    "start": str(row["日期"]),
                    "backgroundColor": event_color,
                    "borderColor": event_color
                })
            
            calendar_options = {
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek,timeGridDay"
                },
                "initialView": "dayGridMonth"
            }
            
            calendar(events=events, options=calendar_options)
        else:
            st.info("目前尚無資料可顯示於月曆。")

else:
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")