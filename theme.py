"""theme.py — 「我是有錢人」視覺主題（手機優先、深色優先，淺色跟隨系統）
放在 app 同一個資料夾，主程式用 `import theme` 即可。
"""
import streamlit as st

# ---------- Python 端色票（圖表用；深色版亮度，淺色背景下仍可讀） ----------
ACCENT = "#6FA3D8"
INCOME_COLOR = "#52C29A"
EXPENSE_COLOR = "#E88078"
WARN_COLOR = "#E3A93C"
PALETTE = [ACCENT, INCOME_COLOR, "#D9A441", EXPENSE_COLOR, "#B48EAD", "#7BAE9A", "#8A94A6"]
CAT_COLORS = {
    "伙食": "#5B8FB9", "交通": "#7BAE9A", "購物": "#B48EAD",
    "娛樂": "#D4A76A", "每月固定費用": "#8A94A6", "其他支出": "#A9B8C9",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+TC:wght@400;500;600&display=swap');

:root {
  --primary:#6FA3D8; --primary-hover:#8DB8E4; --primary-soft:#1E2A38; --on-primary:#0F1419;
  --income:#52C29A; --expense:#E88078; --warning:#E3A93C; --accent:#E3B561;
  --bg:#0F1419; --surface:#171D25; --border:#2A323C; --nav-bg:rgba(15,20,25,.92);
  --text:#E8ECF0; --muted:#98A2B3; --shadow:0 4px 12px rgba(0,0,0,.35);
  --r:10px; --r-lg:14px;
}
@media (prefers-color-scheme: light) {
  :root {
    --primary:#2F5D8A; --primary-hover:#244B71; --primary-soft:#E8EEF5; --on-primary:#fff;
    --income:#2E8B6A; --expense:#C2554D; --warning:#C98A1B; --accent:#D9A441;
    --bg:#F6F7F9; --surface:#fff; --border:#E3E6EA; --nav-bg:rgba(255,255,255,.92);
    --text:#1B2430; --muted:#667085; --shadow:0 4px 12px rgba(16,24,40,.08);
  }
}

/* ---------- 基礎 ---------- */
.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp textarea,
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {
  font-family:"Inter","Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
}
.stApp { background:var(--bg); color:var(--text); font-size:15px; line-height:1.65; }
header[data-testid="stHeader"] { background:transparent; }
footer { display:none; }
div.block-container, div[data-testid="stMainBlockContainer"] {
  max-width:1080px; padding:1.5rem 1rem 7rem;   /* 底部留給固定導覽列 */
}
.stApp h3 { font-size:1.125rem; font-weight:600; line-height:1.4; padding-top:.25rem; }
.stApp h4 { font-size:.95rem; font-weight:600; color:var(--muted); }
.stApp hr { border-color:var(--border) !important; margin:1.5rem 0; }

/* ---------- 標題列（左標題、右小圖示鈕，手機也不換行） ---------- */
.app-header h1 { font-size:1.5rem; font-weight:600; line-height:1.3; margin:0; padding:0; }
.app-header p { margin:.2rem 0 0; color:var(--muted); font-size:.85rem; }
.st-key-topbar div[data-testid="stHorizontalBlock"],
.st-key-month_nav div[data-testid="stHorizontalBlock"] {
  flex-direction:row !important; flex-wrap:nowrap !important; align-items:center; gap:8px;
}
.st-key-topbar div[data-testid="stColumn"], .st-key-month_nav div[data-testid="stColumn"] { min-width:0 !important; }

/* ---------- 總覽卡（結餘為主角） ---------- */
.hero {
  background:var(--surface); border:1px solid var(--border); border-radius:var(--r-lg);
  padding:18px 20px; margin:12px 0 8px; font-variant-numeric:tabular-nums;
}
.hero-label { color:var(--muted); font-size:.8rem; font-weight:500; letter-spacing:.04em; }
.hero-amount { font-size:2.1rem; font-weight:600; line-height:1.2; letter-spacing:-.01em; margin:2px 0 4px; }
.hero-delta { font-size:.8rem; color:var(--muted); }
.hero-row { display:flex; gap:12px; margin-top:14px; padding-top:14px; border-top:1px solid var(--border); }
.hero-col { flex:1; min-width:0; }
.hero-col .v { font-size:1.15rem; font-weight:600; }
.pos { color:var(--income); } .neg { color:var(--expense); }

/* ---------- 預算卡（取代 emoji 與預設進度條） ---------- */
.bud { background:var(--surface); border:1px solid var(--border); border-radius:var(--r-lg);
       padding:14px 16px; margin-bottom:10px; font-variant-numeric:tabular-nums; }
.bud-top { display:flex; justify-content:space-between; gap:8px; font-size:.95rem; }
.bud-top b { font-weight:600; }
.bud-sub { color:var(--muted); font-size:.8rem; margin:2px 0 10px; }
.bud-bar { height:8px; border-radius:999px; background:var(--primary-soft); overflow:hidden; }
.bud-bar > i { display:block; height:100%; border-radius:999px; }
.bud-ok > i { background:var(--income); } .bud-warn > i { background:var(--warning); }
.bud-over > i { background:var(--expense); }
.t-ok { color:var(--income); } .t-warn { color:var(--warning); } .t-over { color:var(--expense); font-weight:600; }

/* ---------- 其他元件 ---------- */
div[data-testid="stMetric"] { background:var(--surface); border:1px solid var(--border);
  border-radius:var(--r-lg); padding:14px 16px; }
div[data-testid="stMetricLabel"] p { color:var(--muted); font-size:.8rem; }
div[data-testid="stMetricValue"] { font-size:1.4rem; font-weight:600; font-variant-numeric:tabular-nums; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:var(--r-lg); border-color:var(--border); }
div[data-testid="stAlert"], div[data-testid="stExpander"] { border-radius:var(--r); }
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] { border-radius:var(--r); overflow:hidden; }
button[data-baseweb="tab"] { font-weight:500; }

/* 按鈕（觸控高度 44px） */
.stButton > button, .stDownloadButton > button {
  min-height:44px; border-radius:var(--r); font-weight:500; font-size:.9rem;
  background:var(--surface); color:var(--text); border:1px solid var(--border);
  transition:background-color .15s, border-color .15s;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  background:var(--primary-soft); border-color:var(--primary); color:var(--primary);
}
.stButton > button:active { transform:translateY(1px); }
.stButton > button:focus-visible { outline:none; box-shadow:0 0 0 3px color-mix(in srgb, var(--primary) 30%, transparent); }
.stButton > button[kind="primary"] { background:var(--primary); border-color:var(--primary); color:var(--on-primary); }
.stButton > button[kind="primary"]:hover { background:var(--primary-hover); border-color:var(--primary-hover); color:var(--on-primary); }
.st-key-btn_delete button { color:var(--expense); border-color:color-mix(in srgb, var(--expense) 45%, transparent); }
.st-key-btn_delete button:hover { background:color-mix(in srgb, var(--expense) 12%, transparent); border-color:var(--expense); color:var(--expense); }

/* 輸入框 */
div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div {
  background:var(--surface) !important; border:1px solid var(--border) !important;
  border-radius:var(--r) !important; min-height:44px; transition:border-color .15s, box-shadow .15s;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"]:focus-within > div {
  border-color:var(--primary) !important; box-shadow:0 0 0 3px color-mix(in srgb, var(--primary) 22%, transparent);
}

/* ---------- 底部固定導覽（手機拇指區） ---------- */
.st-key-view_mode {
  position:fixed; left:0; right:0; bottom:0; z-index:999;
  background:var(--nav-bg); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  border-top:1px solid var(--border);
  padding:6px 8px calc(6px + env(safe-area-inset-bottom));
}
.st-key-view_mode div[role="radiogroup"] {
  display:flex; flex-wrap:nowrap; gap:4px; max-width:560px; margin:0 auto;
}
.st-key-view_mode label {
  flex:1; justify-content:center; margin:0; padding:9px 0; border-radius:12px;
  cursor:pointer; color:var(--muted); transition:background-color .15s;
}
.st-key-view_mode label > div:first-child { display:none; }
.st-key-view_mode label p { font-size:.85rem; color:inherit; margin:0; }
.st-key-view_mode label:hover { background:var(--primary-soft); }
.st-key-view_mode label:has(input:checked) { background:var(--primary-soft); color:var(--primary); }
.st-key-view_mode label:has(input:checked) p { font-weight:600; }

/* ---------- 月曆 ---------- */
.cal-card { background:var(--surface); border:1px solid var(--border); border-radius:var(--r);
            padding:8px 10px; height:132px; overflow:hidden; margin-bottom:8px; }
.cal-card.today { border-color:var(--primary); box-shadow:0 0 0 1px var(--primary); }
.cal-day-header { font-size:.8rem; font-weight:600; color:var(--muted); border-bottom:1px solid var(--border);
                  padding-bottom:4px; margin-bottom:6px; display:flex; justify-content:space-between; }
.cal-card.today .cal-day-header span:first-child { color:var(--primary); }
.cal-day-total { font-size:.75rem; font-weight:500; font-variant-numeric:tabular-nums; }
.cal-note { font-size:.75rem; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:block; }

/* ---------- 登入頁 ---------- */
div[data-testid="stHeading"] h1 { text-align:center; font-weight:600; margin-top:8vh; }
div[data-testid="stForm"] { max-width:420px; margin:0 auto; border-radius:var(--r-lg); padding:1.4rem; }

/* ---------- 桌面 ---------- */
@media (min-width:900px) {
  div.block-container, div[data-testid="stMainBlockContainer"] { padding:2rem 1.5rem 7rem; }
  .app-header h1 { font-size:1.75rem; }
  .hero-amount { font-size:2.4rem; }
}
@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def show(fig, stretch):
    """統一圖表：透明底（跟隨深淺色）、淡格線、圖例置底"""
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


def _delta(v, invert=False):
    good = (v <= 0) if invert else (v >= 0)
    return f"<span class='{'pos' if good else 'neg'}'>{v:+,.0f}</span>"


def summary_card(month, income, expense, net, d_inc, d_exp, d_net):
    """總覽卡：結餘放大，收入／支出並排；delta 為與上月差額"""
    cls = "pos" if net >= 0 else "neg"
    st.markdown(
        f"<div class='hero'>"
        f"<div class='hero-label'>{month} 本月結餘</div>"
        f"<div class='hero-amount {cls}'>${net:,.0f}</div>"
        f"<div class='hero-delta'>較上月 {_delta(d_net)}</div>"
        f"<div class='hero-row'>"
        f"<div class='hero-col'><div class='hero-label'>收入</div><div class='v'>${income:,.0f}</div>"
        f"<div class='hero-delta'>{_delta(d_inc)}</div></div>"
        f"<div class='hero-col'><div class='hero-label'>支出</div><div class='v'>${expense:,.0f}</div>"
        f"<div class='hero-delta'>{_delta(d_exp, invert=True)}</div></div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )


def budget_card(name, spent, limit):
    """預算卡：進度條依狀態變色（<80% 綠、80–100% 橘、≥100% 紅）"""
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
