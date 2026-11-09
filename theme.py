"""theme.py — 底色、文字、按鈕、輸入框交給 .streamlit/config.toml 的主題處理；
這裡只補：排版、總覽卡、預算卡、月曆、底部導覽。顏色一律用半透明灰，深淺主題都自動適應。
"""
import streamlit as st

ACCENT = "#5B93D3"
INCOME_COLOR = "#3FAF86"
EXPENSE_COLOR = "#E0675F"
WARN_COLOR = "#E0A030"
PALETTE = [ACCENT, INCOME_COLOR, "#D9A441", EXPENSE_COLOR, "#B48EAD", "#7BAE9A", "#8A94A6"]
CAT_COLORS = {
    "伙食": "#5B8FB9", "交通": "#7BAE9A", "購物": "#B48EAD",
    "娛樂": "#D4A76A", "每月固定費用": "#8A94A6", "其他支出": "#A9B8C9",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;600&display=swap');

:root {
  --income:#3FAF86; --expense:#E0675F; --warning:#E0A030; --primary:#5B93D3;
  --line:rgba(128,128,128,.28); --card:rgba(128,128,128,.09); --track:rgba(128,128,128,.25);
}

.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
  font-family:"Inter","Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
}
footer { display:none; }
div.block-container, div[data-testid="stMainBlockContainer"] {
  max-width:1080px; padding:1.5rem 1rem 4rem;
}
.stApp h3 { font-size:1.125rem; font-weight:600; }
.stApp h4 { font-size:.95rem; font-weight:600; opacity:.7; }
.stApp hr { border-color:var(--line) !important; margin:1.5rem 0; }

/* 標題 */
.app-header h1 { font-size:1.5rem; font-weight:600; line-height:1.3; margin:0; padding:0; }
.app-header p { margin:.2rem 0 0; opacity:.6; font-size:.85rem; }
.st-key-topbar div[data-testid="stHorizontalBlock"],
.st-key-month_nav div[data-testid="stHorizontalBlock"] {
  flex-direction:row !important; flex-wrap:nowrap !important; align-items:center; gap:8px;
}
.st-key-topbar div[data-testid="stColumn"], .st-key-month_nav div[data-testid="stColumn"] { min-width:0 !important; }

/* 觸控高度 */
.stButton > button, .stDownloadButton > button { min-height:44px; font-weight:500; }
.st-key-btn_delete button { color:var(--expense) !important; border-color:var(--expense) !important; }

/* 總覽卡 */
.hero { background:var(--card); border:1px solid var(--line); border-radius:16px;
        padding:18px 20px; margin:14px 0 10px; font-variant-numeric:tabular-nums; }
.hero-label { opacity:.65; font-size:.8rem; }
.hero-amount { font-size:2.1rem; font-weight:600; line-height:1.2; margin:2px 0 4px; }
.hero-delta { font-size:.8rem; opacity:.9; }
.hero-delta .mut { opacity:.65; }
.hero-row { display:flex; gap:12px; margin-top:14px; padding-top:14px; border-top:1px solid var(--line); }
.hero-col { flex:1; min-width:0; }
.hero-col .v { font-size:1.15rem; font-weight:600; }
.pos { color:var(--income); } .neg { color:var(--expense); }

/* 預算卡 */
.bud { background:var(--card); border:1px solid var(--line); border-radius:14px;
       padding:14px 16px; margin-bottom:10px; font-variant-numeric:tabular-nums; }
.bud-top { display:flex; justify-content:space-between; gap:8px; font-size:.95rem; }
.bud-sub { opacity:.65; font-size:.8rem; margin:2px 0 10px; }
.bud-bar { height:8px; border-radius:999px; background:var(--track); overflow:hidden; }
.bud-bar > i { display:block; height:100%; border-radius:999px; }
.bud-ok > i { background:var(--income); } .bud-warn > i { background:var(--warning); } .bud-over > i { background:var(--expense); }
.t-ok { color:var(--income); } .t-warn { color:var(--warning); } .t-over { color:var(--expense); font-weight:600; }

/* 主導覽（st.segmented_control，全部使用原生配色，不覆蓋顏色） */
.st-key-view_mode { margin:8px 0 20px; }
.st-key-view_mode button { min-height:44px; }

/* 月曆 */
.cal-card { background:var(--card); border:1px solid var(--line); border-radius:10px;
            padding:8px 10px; height:132px; overflow:hidden; margin-bottom:8px; }
.cal-card.today { border-color:var(--primary); box-shadow:0 0 0 1px var(--primary); }
.cal-day-header { font-size:.8rem; font-weight:600; border-bottom:1px solid var(--line);
                  padding-bottom:4px; margin-bottom:6px; display:flex; justify-content:space-between; }
.cal-day-total { font-size:.75rem; font-weight:500; font-variant-numeric:tabular-nums; }
.cal-note { font-size:.75rem; opacity:.65; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:block; }

/* 登入頁 */
div[data-testid="stHeading"] h1 { text-align:center; font-weight:600; margin-top:8vh; }

@media (min-width:900px) {
  div.block-container, div[data-testid="stMainBlockContainer"] { padding:2rem 1.5rem 4rem; }
  .app-header h1 { font-size:1.75rem; }
  .hero-amount { font-size:2.4rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def show(fig, stretch):
    """統一圖表：透明底、淡格線、圖例置底"""
    fig.update_layout(
        margin=dict(l=8, r=8, t=48, b=8),
        title=dict(font=dict(size=15), x=0, xanchor="left"),
        legend=dict(title_text="", orientation="h", y=-0.2, x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Noto Sans TC, sans-serif", size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor="rgba(128,128,128,.3)")
    fig.update_yaxes(gridcolor="rgba(128,128,128,.15)", zeroline=False)
    st.plotly_chart(fig, theme="streamlit", **stretch)


def money(n):
    return f"-${abs(n):,.0f}" if n < 0 else f"${n:,.0f}"


def _delta(v, invert=False):
    good = (v <= 0) if invert else (v >= 0)
    sign = "+" if v > 0 else ("-" if v < 0 else "")
    return f"<span class='{'pos' if good else 'neg'}'>{sign}{abs(v):,.0f}</span>"


def summary_card(month, income, expense, net, d_inc, d_exp, d_net):
    cls = "pos" if net >= 0 else "neg"
    st.markdown(
        f"<div class='hero'>"
        f"<div class='hero-label'>{month} 本月結餘</div>"
        f"<div class='hero-amount {cls}'>{money(net)}</div>"
        f"<div class='hero-delta'><span class='mut'>較上月</span> {_delta(d_net)}</div>"
        f"<div class='hero-row'>"
        f"<div class='hero-col'><div class='hero-label'>收入</div><div class='v'>{money(income)}</div>"
        f"<div class='hero-delta'>{_delta(d_inc)}</div></div>"
        f"<div class='hero-col'><div class='hero-label'>支出</div><div class='v'>{money(expense)}</div>"
        f"<div class='hero-delta'>{_delta(d_exp, invert=True)}</div></div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


def budget_card(name, spent, limit):
    import html
    ratio = spent / limit if limit > 0 else 0
    status = "over" if ratio >= 1 else ("warn" if ratio >= 0.8 else "ok")
    left = limit - spent
    left_txt = f"剩餘 ${left:,.0f}" if left >= 0 else f"超支 ${-left:,.0f}"
    st.markdown(
        f"<div class='bud'>"
        f"<div class='bud-top'><b>{html.escape(str(name))}</b><span class='t-{status}'>{ratio:.0%}</span></div>"
        f"<div class='bud-sub'>${spent:,.0f} / ${limit:,.0f}　{left_txt}</div>"
        f"<div class='bud-bar bud-{status}'><i style='width:{min(ratio, 1) * 100:.1f}%'></i></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
