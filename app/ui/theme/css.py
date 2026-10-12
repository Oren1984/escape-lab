"""ESCAPE LAB visual theme: tokens and scoped CSS for the Streamlit shell."""

from __future__ import annotations

import streamlit as st

# Design tokens, shared with the Plotly charts and the chamber SVG.
BG = "#060b16"
SURFACE = "#0b1424"
SURFACE_2 = "#101c31"
BORDER = "#1c2c47"
TEXT = "#dbe7f5"
MUTED = "#8ea3bf"
FAINT = "#5d7291"
CYAN = "#22d3ee"
BLUE = "#4c9aff"
AMBER = "#f5a524"
RED = "#f0524f"
GREEN = "#34c38f"

# Categorical series colours, validated for the dark surface (CVD and contrast).
# Fixed order, never cycled. Status colours above are never used as series.
SERIES = ("#12a5b5", "#d55181", "#3987e5", "#9085e9")

FONT = '"Inter", "Segoe UI", system-ui, -apple-system, sans-serif'
MONO = '"JetBrains Mono", "Cascadia Code", Consolas, "SFMono-Regular", monospace'

CSS = f"""
<style>
:root {{
  --bg:{BG}; --surface:{SURFACE}; --surface-2:{SURFACE_2}; --border:{BORDER};
  --text:{TEXT}; --muted:{MUTED}; --faint:{FAINT};
  --cyan:{CYAN}; --blue:{BLUE}; --amber:{AMBER}; --red:{RED}; --green:{GREEN};
}}
html, body, .stApp {{ font-family:{FONT}; }}
.stApp {{
  background:
    radial-gradient(1100px 520px at 78% -8%, rgba(34,211,238,.07), transparent 60%),
    radial-gradient(900px 500px at 0% 0%, rgba(76,154,255,.06), transparent 55%),
    var(--bg);
}}
.block-container {{ padding-top:2.2rem; padding-bottom:3rem; max-width:1320px; }}
header[data-testid="stHeader"] {{ background:transparent; }}
h1, h2, h3 {{ letter-spacing:-.01em; }}

/* Sidebar */
section[data-testid="stSidebar"] {{ background:#070d1a; border-right:1px solid var(--border); }}
.st-key-view div[role="radiogroup"] {{ gap:.15rem; }}
.st-key-view div[role="radiogroup"] > label {{
  padding:.5rem .7rem; border-radius:10px; border:1px solid transparent; width:100%;
  transition:background .15s ease, border-color .15s ease;
}}
.st-key-view div[role="radiogroup"] > label:hover {{ background:var(--surface-2); }}
.st-key-view div[role="radiogroup"] > label:has(input:checked) {{
  background:linear-gradient(90deg, rgba(34,211,238,.14), rgba(34,211,238,.02));
  border-color:rgba(34,211,238,.35);
}}
.st-key-view div[role="radiogroup"] > label > div:first-child {{ display:none; }}
.st-key-view, .st-key-view > div, .st-key-view div[role="radiogroup"] {{ width:100%; }}

/* Buttons */
.stButton > button, .stDownloadButton > button {{
  border-radius:10px; border:1px solid var(--border); background:var(--surface-2); color:var(--text);
  font-weight:600; transition:border-color .15s ease, box-shadow .15s ease, transform .05s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
  border-color:rgba(34,211,238,.6); color:#fff; box-shadow:0 0 0 3px rgba(34,211,238,.10);
}}
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible {{
  outline:2px solid var(--cyan); outline-offset:2px;
}}
.stButton > button:active {{ transform:translateY(1px); }}
.stButton > button[kind="primary"] {{
  background:linear-gradient(180deg, #2bd9f2, #12a8c6); color:#04121c; border-color:transparent;
}}
.stButton > button[kind="primary"]:hover {{ color:#04121c; box-shadow:0 0 18px rgba(34,211,238,.35); }}
.stButton > button:disabled {{ opacity:.45; }}
[class*="st-key-estop"] button {{
  background:linear-gradient(180deg, #f2625f, #c93532) !important; color:#fff !important;
  border-color:transparent !important; letter-spacing:.04em;
}}
[class*="st-key-estop"] button:hover {{ box-shadow:0 0 20px rgba(240,82,79,.45) !important; }}
[class*="st-key-estop"] button:disabled {{ background:var(--surface-2) !important; color:var(--faint) !important; }}

/* Containers and inputs */
div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:14px; }}
div[data-testid="stExpander"] details {{ border-radius:12px; border-color:var(--border); background:rgba(11,20,36,.6); }}
.stTabs [data-baseweb="tab-list"] {{ gap:.25rem; border-bottom:1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{ padding:.55rem .9rem; border-radius:10px 10px 0 0; }}
div[data-testid="stDataFrame"] {{ border:1px solid var(--border); border-radius:12px; overflow:hidden; }}

/* Brand and page headers */
.el-brand {{ display:flex; align-items:center; gap:.7rem; margin:.1rem 0 .9rem; }}
.el-brand-mark {{
  width:34px; height:34px; border-radius:10px; flex:none;
  background:radial-gradient(circle at 50% 50%, var(--cyan) 0 18%, transparent 20%),
             radial-gradient(circle at 50% 50%, transparent 0 46%, rgba(34,211,238,.9) 48% 54%, transparent 56%), #0b1b2e;
  box-shadow:0 0 16px rgba(34,211,238,.28), inset 0 0 0 1px rgba(34,211,238,.35);
}}
.el-brand-name {{ font-weight:800; letter-spacing:.2em; font-size:.98rem; color:#fff; line-height:1.1; }}
.el-brand-sub {{ font-size:.68rem; color:var(--muted); letter-spacing:.05em; }}
.el-head {{ margin-bottom:1.1rem; }}
.el-eyebrow {{ font-family:{MONO}; font-size:.7rem; letter-spacing:.2em; text-transform:uppercase; color:var(--cyan); }}
.el-title {{ font-size:clamp(1.5rem, 2.6vw, 2.1rem); font-weight:750; color:#fff; margin:.15rem 0 .25rem; line-height:1.15; }}
.el-lede {{ color:var(--muted); max-width:70ch; font-size:.96rem; line-height:1.5; }}
.el-section {{ font-family:{MONO}; font-size:.72rem; letter-spacing:.16em; text-transform:uppercase;
  color:var(--muted); margin:1.2rem 0 .55rem; display:flex; align-items:center; gap:.6rem; }}
.el-section::after {{ content:""; flex:1; height:1px; background:linear-gradient(90deg, var(--border), transparent); }}

/* Cards */
.el-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:.7rem; }}
.el-card {{
  background:linear-gradient(180deg, rgba(16,28,49,.92), rgba(11,20,36,.92));
  border:1px solid var(--border); border-radius:14px; padding:.8rem .95rem; min-width:0;
  box-shadow:0 1px 0 rgba(255,255,255,.03) inset, 0 10px 30px -18px rgba(0,0,0,.9);
}}
.el-card-label {{ font-size:.68rem; letter-spacing:.11em; text-transform:uppercase; color:var(--muted); }}
.el-card-value {{ font-size:1.55rem; font-weight:700; color:#fff; font-variant-numeric:tabular-nums;
  line-height:1.25; overflow-wrap:anywhere; }}
.el-card-value.sm {{ font-size:1.02rem; padding-top:.2rem; }}
.el-card-hint {{ font-size:.74rem; color:var(--faint); margin-top:.1rem; }}
.el-card.ok {{ border-color:rgba(52,195,143,.38); }}
.el-card.warn {{ border-color:rgba(245,165,36,.45); }}
.el-card.crit {{ border-color:rgba(240,82,79,.6); box-shadow:0 0 22px -8px rgba(240,82,79,.6); }}
.el-card.accent {{ border-color:rgba(34,211,238,.38); }}

/* Pills: always icon + word, never colour alone */
.el-pill {{ display:inline-flex; align-items:center; gap:.38rem; padding:.2rem .6rem; border-radius:999px;
  font-size:.72rem; font-weight:650; letter-spacing:.04em; border:1px solid var(--border);
  background:var(--surface-2); color:var(--text); white-space:nowrap; }}
.el-pill.ok {{ border-color:rgba(52,195,143,.5); color:#8fe6c3; }}
.el-pill.warn {{ border-color:rgba(245,165,36,.55); color:#ffd08a; }}
.el-pill.crit {{ border-color:rgba(240,82,79,.6); color:#ffb1af; }}
.el-pill.info {{ border-color:rgba(34,211,238,.5); color:#9eeaf7; }}
.el-pill.dim {{ color:var(--muted); }}
.el-pills {{ display:flex; flex-wrap:wrap; gap:.4rem; }}

.el-banner {{ border:1px dashed rgba(142,163,191,.35); border-radius:10px; padding:.45rem .75rem;
  color:var(--muted); font-size:.78rem; background:rgba(11,20,36,.5); }}
.el-note {{ border-left:2px solid rgba(34,211,238,.55); padding:.3rem 0 .3rem .8rem; margin:.45rem 0;
  color:var(--text); font-size:.92rem; line-height:1.5; }}
.el-note.crit {{ border-left-color:var(--red); }}
.el-empty {{ border:1px dashed var(--border); border-radius:14px; padding:1.6rem 1.2rem; text-align:center;
  color:var(--muted); background:rgba(11,20,36,.45); }}
.el-empty b {{ color:var(--text); display:block; margin-bottom:.25rem; }}

/* Event feed */
.el-feed {{ border:1px solid var(--border); border-radius:14px; background:rgba(8,14,26,.75);
  font-family:{MONO}; font-size:.74rem; max-height:300px; overflow-y:auto; }}
.el-feed-row {{ display:grid; grid-template-columns:3.2rem minmax(0,1.5fr) 5.4rem minmax(0,1.3fr); gap:.5rem;
  padding:.36rem .7rem; border-bottom:1px solid rgba(28,44,71,.6); align-items:baseline; }}
.el-feed-row:last-child {{ border-bottom:0; }}
.el-feed-row > span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.el-feed .t {{ color:var(--faint); }} .el-feed .why {{ color:var(--muted); }}
.el-feed .ALLOW {{ color:#8fe6c3; }} .el-feed .DENY {{ color:#ffd08a; }} .el-feed .STOP {{ color:#ffb1af; }}
.el-feed .ctl {{ color:#9eeaf7; }}

/* Containment chamber */
.st-key-chamber {{ border:1px solid var(--border); border-radius:18px; overflow:hidden;
  background:radial-gradient(ellipse at 50% 42%, #0e2038 0%, #081120 58%, #050a14 100%); }}
.st-key-chamber img {{ display:block; width:100%; height:auto; }}
.st-key-chamber [data-testid="stImageContainer"] {{ width:100%; }}
.st-key-chamber button {{ display:none; }}
.el-sr {{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }}
.el-chamber-cap {{ display:flex; justify-content:space-between; gap:.3rem 1rem; flex-wrap:wrap;
  padding:.5rem .2rem 0; font-family:{MONO}; font-size:.72rem; color:var(--muted); }}
/* Narrow screens */
@media (max-width: 640px) {{
  .block-container {{ padding-left:1rem; padding-right:1rem; padding-top:3.2rem; }}
  .el-grid {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }}
  .el-card-value {{ font-size:1.25rem; }}
  .el-feed-row {{ grid-template-columns:2.6rem minmax(0,1fr) 4.4rem; }}
  .el-feed-row .why {{ display:none; }}
}}
</style>
"""


def inject() -> None:
    st.html(CSS)
