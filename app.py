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

    # ================= 側邊欄設計 =================
    st.sidebar.header("➕ 新增記帳")
    with st.sidebar.form("add_form"):
        # 金額預設為空，點擊直接輸入整數
        amount = st.number_input("金額", value=None, step=1, placeholder="請輸入金額...")
        category = st.selectbox("分類", ["伙食", "交通", "購物", "娛樂", "固定支出", "其他支出", "薪資", "其他收入"])
        tx_type = st.radio("類型", ["支出", "收入"])
        pay_method = st.selectbox("付款方式", ["現金", "信用卡"])
        tx_date = st.date_input("日期", value=date.today())
        note = st.text_input("備註")
        
        submit_button = st.form_submit_button(label="送出記帳")

    if submit_button:
        if amount is not None and amount > 0:
            try:
                # 確保寫入的欄位順序對應你的試算表：日期, 類型, 分類, 金額, 付款方式, 備註
                row = [str(tx_date), tx_type, category, amount, pay_method, note]
                worksheet.append_row(row)
                st.sidebar.success("新增成功！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"寫入失敗: {e}")
        else:
            st.sidebar.warning("請輸入有效的金額！")

    # ================= 主畫面 Tabs 設計 =================
    # 建立三個分頁
    tab1, tab2, tab3 = st.tabs(["📋 記帳明細列表", "📊 圖表分析", "📅 月曆模式"])

    # --- Tab 1: 記帳明細列表 ---
    with tab1:
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
        else:
            st.info("目前還沒有任何記錄，請從側邊欄新增您的第一筆帳目！")

    # --- Tab 2: 圖表分析 ---
    with tab2:
        st.subheader("📊 財務視覺化分析")
        if not df.empty:
            df_expense = df[df["類型"] == "支出"]
            if not df_expense.empty:
                col1, col2 = st.columns(2)
                
                # 定義一組高對比的鮮豔顏色
                vivid_colors = ['#FF5733', '#33FF57', '#3357FF', '#FF33A8', '#FFBD33', '#33FFF2', '#A833FF']
                
                with col1:
                    # 支出分類圓餅圖
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
                    # 每日支出長條圖
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
        else:
            st.info("目前尚無資料可產出圖表。")

    # --- Tab 3: 月曆模式 ---
    with tab3:
        st.subheader("📅 月曆視圖")
        if not df.empty:
            events = []
            for idx, row in df.iterrows():
                # 支出用鮮紅色，收入用鮮綠色，增加對比度
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
            
            # 顯示月曆
            calendar(events=events, options=calendar_options)
        else:
            st.info("目前尚無資料可顯示於月曆。")

else:
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")