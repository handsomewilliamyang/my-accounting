import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, date

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

    # 側邊欄：新增記帳
    st.sidebar.header("➕ 新增記帳")
    with st.sidebar.form("add_form"):
        amount = st.number_input("金額", value=None, step=1, placeholder="請輸入金額...")
        category = st.selectbox("類別", ["餐飲", "交通", "購物", "娛樂", "居住", "薪資", "其他"])
        tx_type = st.radio("類型", ["支出", "收入"])
        tx_date = st.date_input("日期", value=date.today())
        note = st.text_input("備註")
        
        submit_button = st.form_submit_button(label="送出記帳")

    if submit_button:
        if amount is not None and amount > 0:
            try:
                row = [str(tx_date), tx_type, category, amount, note]
                worksheet.append_row(row)
                st.sidebar.success("新增成功！")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"寫入失敗: {e}")
        else:
            st.sidebar.warning("請輸入有效的金額！")

    # 主畫面顯示：記帳明細列表（可勾選刪除）
    st.subheader("📋 記帳明細列表 (可勾選並刪除)")
    
    if not df.empty:
        # 在 DataFrame 前面加上一個「刪除」的勾選欄位
        df_display = df.copy()
        df_display.insert(0, "刪除", False)
        
        # 使用 data_editor 讓使用者可以勾選
        edited_df = st.data_editor(
            df_display, 
            use_container_width=True,
            hide_index=True,
            key="expense_table"
        )
        
        # 檢查是否有勾選刪除的項目
        if st.button("🗑️ 刪除所選項目"):
            # 找出被勾選為 True 的列索引
            rows_to_delete = edited_df[edited_df["刪除"] == True].index.tolist()
            
            if rows_to_delete:
                try:
                    # 因為 Google 試算表第一列是標題列（Header），資料從第 2 列開始
                    # 倒序刪除才不會影響後面列數的對應序號
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

else:
    st.warning("請先設定好 Streamlit Secrets 的 GCP 憑證，才能正常讀寫資料庫喔！")