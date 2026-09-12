import streamlit as st
import pandas as pd
import gspread
import json
from datetime import datetime, date
from streamlit_calendar import calendar
import plotly.express as px

# 網頁標題與基本設定
st.set_page_config(page_title="雲端記帳本", page_icon="💰", layout="wide")

st.title("💰 我是有錢人")
st.markdown("一天一塊錢 七天就有七塊錢")

# Google 試算表網址
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1DTNSXJUJE_7PQIi5yebsmt_mC8bIe1D82IF2FgDaPyM/edit?gid=0#gid=0"

# 使用 gspread 建立連線（支援本機 key.json 與雲端 st.secrets 雙模式）
def get_worksheet():
    if "gcp_service_account" in st.secrets:
        # 雲端環境：從 Streamlit Secrets 讀取憑證
        creds_dict = dict(st.secrets["gcp_service_account"])
        gc = gspread.service_account_from_dict(creds_dict)
    else:
        # 本機環境：從 key.json 檔案讀取
        gc = gspread.service_account(filename="key.json")
        
    sh = gc.open_by_url(SPREADSHEET_URL)
    return sh.get_worksheet(0)

# 讀取現有資料
try:
    worksheet = get_worksheet()
    all_values = worksheet.get_all_values()
    
    required_columns = ["日期", "類型", "分類", "金額", "付款方式", "備註"]
    
    if len(all_values) > 1:
        header = required_columns
        data_rows = all_values[1:]
        
        formatted_rows = []
        for row in data_rows:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            formatted_rows.append(row[:len(header)])
            
        df = pd.DataFrame(formatted_rows, columns=header)
    else:
        df = pd.DataFrame(columns=required_columns)

    if not df.empty:
        df["金額"] = pd.to_numeric(df["金額"], errors="coerce").fillna(0)
        df = df.dropna(subset=["日期"])
        df = df[df["日期"].astype(str).str.strip() != ""]
        
except Exception as e:
    st.error(f"連線 Google 試算表失敗：{e}")
    df = pd.DataFrame(columns=["日期", "類型", "分類", "金額", "付款方式", "備註"])

# --- 側邊欄：新增收支記錄（將類型移至表單外以實現即時連動） ---
st.sidebar.header("📝 新增收支記錄")

t_type = st.sidebar.selectbox("類型", ["支出", "收入"], key="t_type_select")

if t_type == "支出":
    category_options = ["伙食", "交通", "娛樂", "購物", "固定支出", "醫療", "其他"]
else:
    category_options = ["薪水", "投資股利", "獎金", "其他收入"]

with st.sidebar.form("expense_form", clear_on_submit=True):
    input_date = st.date_input("日期", value=datetime.today())
    category = st.selectbox("分類", category_options)
    pay_method = st.selectbox("付款方式", ["現金", "信用卡"])
    amount = st.number_input("金額", min_value=0.0, step=10.0)
    remark = st.text_input("備註 (例如：鼎泰豐、iPhone分3期)")
    
    submit_button = st.form_submit_button(label="送出並同步")

    if submit_button:
        new_row = [
            input_date.strftime("%Y-%m-%d"), 
            t_type, 
            category, 
            str(amount), 
            pay_method,
            remark
        ]
        try:
            worksheet.append_row(new_row)
            st.sidebar.success("新增成功並已同步至雲端！")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"寫入失敗：{e}")


# --- 主畫面排序：明細與搜尋放在第一層 ---
st.subheader("📊 財務總覽與記帳明細")

if df.empty:
    st.info("目前還沒有任何記錄，請從側邊欄新增您的第一筆帳目！")
else:
    df["日期_dt"] = pd.to_datetime(df["日期"], errors="coerce").dt.date

    # 頂部控制列：日期篩選與關鍵字搜尋
    col_filter1, col_filter2 = st.columns([1, 1])
    with col_filter1:
        today = date.today()
        first_day_of_month = date(today.year, today.month, 1)
        date_range = st.date_input(
            "選擇日期區間",
            value=(first_day_of_month, today),
            max_value=today
        )
    with col_filter2:
        search_keyword = st.text_input("🔍 關鍵字搜尋明細 (可查備註、分類等)", "")

    filtered_df = df.copy()
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        if start_date and end_date:
            filtered_df = df[(df["日期_dt"] >= start_date) & (df["日期_dt"] <= end_date)]

    # 關鍵字過濾
    if search_keyword.strip() != "":
        filtered_df = filtered_df[
            filtered_df.astype(str).apply(lambda row: row.str.contains(search_keyword, case=False).any(), axis=1)
        ]

    # 區間統計指標
    total_expense = filtered_df[filtered_df["類型"] == "支出"]["金額"].sum()
    total_income = filtered_df[filtered_df["類型"] == "收入"]["金額"].sum()
    balance = total_income - total_expense
    
    m_col1, m_col2, m_col3 = st.columns(3)
    m_col1.metric("區間總收入", f"${total_income:,.0f}")
    m_col2.metric("區間總支出", f"${total_expense:,.0f}")
    m_col3.metric("區間結餘", f"${balance:,.0f}")
    
    st.markdown("---")
    
    # 📋 第一層：記帳明細表格（支援直接勾選刪除與即時搜尋）
    st.markdown("### 📋 記帳明細列表 (可勾選並刪除)")
    
    editor_df = filtered_df.drop(columns=["日期_dt"], errors="ignore").copy()
    editor_df.insert(0, "刪除", False)
    
    edited_df = st.data_editor(
        editor_df,
        column_config={
            "刪除": st.column_config.CheckboxColumn(
                "勾選刪除",
                help="勾選你想移除的記錄",
                default=False,
            )
        },
        disabled=["日期", "類型", "分類", "金額", "付款方式", "備註"],
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("🗑️ 確認刪除勾選的記錄"):
        rows_to_delete = edited_df[edited_df["刪除"]]
        
        if rows_to_delete.empty:
            st.warning("您沒有勾選任何要刪除的項目！")
        else:
            try:
                all_vals = worksheet.get_all_values()
                rows_data = all_vals[1:]
                
                indices_to_delete = []
                for _, target_row in rows_to_delete.iterrows():
                    for idx, sheet_row in enumerate(rows_data):
                        if len(sheet_row) < 6:
                            sheet_row = sheet_row + [""] * (6 - len(sheet_row))
                            
                        if (sheet_row[0] == str(target_row["日期"]) and 
                            sheet_row[1] == str(target_row["類型"]) and 
                            float(sheet_row[3] if sheet_row[3] != '' else 0) == float(target_row["金額"]) and
                            sheet_row[5] == str(target_row["備註"])):
                            indices_to_delete.append(idx + 2)
                
                indices_to_delete = sorted(list(set(indices_to_delete)), reverse=True)
                for r_idx in indices_to_delete:
                    worksheet.delete_rows(r_idx)
                    
                st.success("成功刪除選中的記錄！")
                st.rerun()
            except Exception as e:
                st.error(f"刪除失敗：{e}")

    st.markdown("---")

    # 📅 獨立區塊：每日收支月曆
    st.markdown("### 🗓️ 每日收支月曆檢視")
    calendar_events = []
    daily_summary = df.groupby(["日期", "類型"])["金額"].sum().reset_index()
    
    for _, row in daily_summary.iterrows():
        d_str = str(row["日期"])
        t_type = row["類型"]
        amt = row["金額"]
        
        if t_type == "收入":
            title = f"🟢 +${amt:,.0f}"
            color = "#28a745"
        else:
            title = f"🔴 -${amt:,.0f}"
            color = "#dc3545"
            
        calendar_events.append({
            "title": title,
            "start": d_str,
            "allDay": True,
            "backgroundColor": color,
            "borderColor": color
        })
            
    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth"
        },
        "initialView": "dayGridMonth",
        "height": 500,
    }
    
    calendar(events=calendar_events, options=calendar_options)

    st.markdown("---")

    # 📊 收納式進階圖表分析
    with st.expander("📊 點擊展開：進階圖表分析（分類長條圖與付款佔比）"):
        analysis_type = st.radio("選擇要分析的類型", ["支出", "收入"], horizontal=True)
        target_df = filtered_df[filtered_df["類型"] == analysis_type]
        
        if not target_df.empty:
            if analysis_type == "支出":
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    st.markdown("#### 🏷️ 依支出分類統計")
                    cat_chart_data = target_df.groupby("分類")["金額"].sum().reset_index()
                    fig_bar = px.bar(cat_chart_data, x="分類", y="金額", color="分類", text_auto=True)
                    fig_bar.update_layout(xaxis_tickangle=0, margin=dict(t=20, b=20, l=20, r=20), height=350, showlegend=False)
                    st.plotly_chart(fig_bar, use_container_width=True)
                    
                with chart_col2:
                    st.markdown("#### 💳 依付款方式佔比（圓餅圖）")
                    pay_chart_data = target_df.groupby("付款方式")["金額"].sum().reset_index()
                    if not pay_chart_data.empty:
                        color_map = {"現金": "#00CC96", "信用卡": "#EF553B"}
                        fig_pie = px.pie(
                            pay_chart_data, 
                            names="付款方式", 
                            values="金額", 
                            hole=0.4,
                            color="付款方式",
                            color_discrete_map=color_map
                        )
                        fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
                        st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.markdown("#### 🏷️ 依收入分類統計")
                inc_chart_data = target_df.groupby("分類")["金額"].sum().reset_index()
                fig_inc = px.bar(inc_chart_data, x="分類", y="金額", color="分類", text_auto=True)
                fig_inc.update_layout(xaxis_tickangle=0, margin=dict(t=20, b=20, l=20, r=20), height=350, showlegend=False)
                st.plotly_chart(fig_inc, use_container_width=True)
        else:
            st.info(f"此區間尚無「{analysis_type}」資料可供繪製圖表。")