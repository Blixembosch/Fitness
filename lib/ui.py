"""Shared UI: CSS injection with dynamic Dark/Light theme switching and HTML builders (rings, tiles,
cards, GitHub-style heatmap, and monthly/12-week views)."""
from __future__ import annotations
import datetime as dt
import streamlit as st

MON_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DOW_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

_PALETTES = {
    "dark": """
  --bg:#0b0e14; --surface:#151922; --surface-2:#1e2431; --line:rgba(255,255,255,.12);
  --fg:#f8fafc; --muted:#cbd5e1; --faint:#94a3b8;
  --blue:#3898ff; --purple:#c084fc; --orange:#fb923c; --green:#34d399; --teal:#22d3ee; --red:#f87171;
  --track:#262d3d; --map1:#1e40af; --map2:#2563eb; --map3:#3898ff;
  --shadow:0 4px 14px rgba(0,0,0,.45);
  --gh-0:#1e2431; --gh-1:#0e4429; --gh-2:#006d32; --gh-3:#26a641; --gh-4:#39d353;
""",
    "light": """
  --bg:#f4f6fb; --surface:#ffffff; --surface-2:#eef2f8; --line:rgba(15,23,42,.11);
  --fg:#0f172a; --muted:#475569; --faint:#64748b;
  --blue:#0a7aff; --purple:#9333ea; --orange:#ea580c; --green:#16a34a; --teal:#0891b2; --red:#dc2626;
  --track:#e2e8f0; --map1:#bfdbfe; --map2:#60a5fa; --map3:#0a7aff;
  --shadow:0 2px 10px rgba(15,23,42,.06);
  --gh-0:#ebedf0; --gh-1:#9be9a8; --gh-2:#40c463; --gh-3:#30a14e; --gh-4:#216e39;
""",
}

CSS_BODY = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background:var(--bg) !important;
  color:var(--fg) !important;
  font-family:"Hanken Grotesk",system-ui,sans-serif;
}
/* Force high-contrast foreground text on all Streamlit markdown/containers so Streamlit's default
   charcoal (#31333F) never bleeds into dark mode! */
.stMarkdown, [data-testid="stMarkdownContainer"], p, span, div, label {
  font-family:"Hanken Grotesk",system-ui,sans-serif;
  color:inherit;
}
h1, h2, h3, h4 {
  font-family:"Nunito",sans-serif !important;
  letter-spacing:-.02em;
  color:var(--fg) !important;
}
.block-container{ padding-top:1.1rem; padding-bottom:3rem; max-width:1180px; }
#MainMenu, header, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }

/* Unify Streamlit bordered containers (`st.container(border=True)`) with `.fcard` / `.exrow` */
[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--surface) !important;
  border:1px solid var(--line) !important;
  border-radius:20px !important;
  box-shadow:var(--shadow) !important;
  padding:15px 16px !important;
  color:var(--fg) !important;
  transition:border-color .15s ease, transform .15s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover{
  border-color:color-mix(in srgb,var(--blue) 35%,var(--line)) !important;
}

/* Exercise card internal layout — guarantees uniform height across all 3 columns */
.excard-head{
  display:flex; align-items:flex-start; gap:14px;
  min-height:88px; margin-bottom:6px; color:var(--fg);
}
.excard-ring{
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  flex-shrink:0; width:56px; color:var(--fg);
}
.excard-info{
  flex:1; min-width:0; display:flex; flex-direction:column; justify-content:space-between;
  min-height:84px;
}
.excard-title{
  font-weight:800; font-size:15px; line-height:1.25; color:var(--fg) !important;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
  overflow:hidden; min-height:2.5em;
}
.excard-meta{
  display:flex; align-items:center; gap:8px; margin:3px 0 5px;
}

/* exercise grid — spread cards across the page */
.exgrid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:11px; margin-top:2px; }
.exrow{ display:flex; align-items:center; gap:13px; background:var(--surface); border:1px solid var(--line);
  border-radius:20px; padding:14px 16px; box-shadow:var(--shadow); color:var(--fg); }

.fcard{ background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:16px; margin-bottom:12px; box-shadow:var(--shadow); color:var(--fg); }
.eyebrow{ font-size:11.5px; text-transform:uppercase; letter-spacing:.11em; color:var(--faint) !important; font-weight:800; margin:0 0 10px; }
.muted{ color:var(--muted) !important; }
.rings{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:10px; }

.counter{ display:flex; align-items:center; gap:18px; background:
  radial-gradient(120% 140% at 0% 0%, color-mix(in srgb,var(--blue) 26%,transparent), transparent 58%),
  linear-gradient(160deg, var(--surface), var(--surface-2)); border:1px solid color-mix(in srgb,var(--blue) 32%,var(--line));
  border-radius:22px; padding:18px 22px; margin-bottom:12px; flex-wrap:wrap; box-shadow:var(--shadow); color:var(--fg); }
.counter .big{ font-family:"Nunito"; font-weight:900; font-size:46px; line-height:.9; color:var(--fg) !important; }
.counter .big small{ font-size:16px; color:var(--muted) !important; font-weight:800; }
.counter .lbl{ font-size:12px; color:var(--muted) !important; font-weight:700; text-transform:uppercase; letter-spacing:.08em; margin-top:4px; }
.weekdots{ display:flex; gap:7px; margin-top:7px; }
.weekdots i{ width:11px; height:11px; border-radius:50%; background:var(--surface-2); border:1px solid var(--line); }
.weekdots i.on{ background:var(--green); border-color:var(--green); }

.ringcard{ background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:12px 3px 10px; text-align:center; box-shadow:var(--shadow); color:var(--fg); }
.ringcard .v{ font-family:"Nunito"; font-weight:800; font-size:14px; margin-top:6px; line-height:1; color:var(--fg) !important; }
.ringcard .v small{ color:var(--muted) !important; font-weight:700; font-size:.82em; }
.ringcard .k{ font-size:11px; color:var(--muted) !important; font-weight:600; margin-top:4px; }

.hero{ border-radius:24px; padding:20px; margin-bottom:10px; position:relative; overflow:hidden; box-shadow:var(--shadow); color:var(--fg); }
.hero .kick{ font-size:11.5px; font-weight:800; text-transform:uppercase; letter-spacing:.1em; }
.hero h2{ font-size:26px; font-weight:900; margin:8px 0 4px; color:var(--fg) !important; }
.chiprow{ display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 2px; }
.chip{ font-size:11.5px; font-weight:700; padding:3px 9px; border-radius:999px; background:var(--surface-2); color:var(--muted); border:1px solid var(--line); }

.tiles{ display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr)); gap:11px; margin-bottom:12px; }
.tile{ background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:15px; box-shadow:var(--shadow); color:var(--fg); }
.tile .k{ font-size:11.5px; color:var(--muted) !important; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.tile .v{ font-family:"Nunito"; font-weight:900; font-size:26px; margin-top:7px; line-height:1; color:var(--fg) !important; }
.tile .v small{ font-size:14px; color:var(--muted) !important; font-weight:800; }
.tile .d{ font-size:12px; font-weight:700; margin-top:6px; color:var(--muted); }
.good{ color:var(--green)!important; } .bad{ color:var(--red)!important; }

.legend{ display:flex; gap:6px; align-items:center; justify-content:center; margin-top:8px; font-size:11px; color:var(--muted); font-weight:600; }
.legend i{ width:14px; height:9px; border-radius:3px; display:inline-block; }
.bars{ display:flex; flex-direction:column; gap:13px; }
.bar .bhead{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:5px; }
.bar .bl{ font-weight:700; color:var(--fg); } .bar.primary .bl{ font-size:1.06em; }
.bar .bv{ color:var(--muted); font-weight:600; font-size:13px; }
.btrack{ height:8px; border-radius:6px; background:var(--surface-2); overflow:hidden; }
.bar.primary .btrack{ height:11px; }
.bfill{ height:100%; border-radius:6px; }

/* GitHub-style Contribution Heatmap */
.gh-card{ background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:18px 20px; margin-bottom:12px; box-shadow:var(--shadow); color:var(--fg); }
.gh-top{ display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:10px; margin-bottom:12px; }
.gh-title{ font-family:"Nunito",sans-serif; font-weight:800; font-size:16px; color:var(--fg); }
.gh-pills{ display:flex; gap:8px; flex-wrap:wrap; font-size:12px; font-weight:700; color:var(--fg); }
.gh-pill{ background:var(--surface-2); border:1px solid var(--line); padding:3px 10px; border-radius:999px; display:inline-flex; align-items:center; gap:6px; }
.gh-dot{ width:8px; height:8px; border-radius:50%; display:inline-block; }
.gh-scroll{ overflow-x:auto; padding-bottom:4px; }
.gh-board{ min-width:680px; }
.gh-months{ display:grid; gap:3px; margin-left:34px; margin-bottom:6px; font-size:11.5px; color:var(--muted); font-weight:700; line-height:1; }
.gh-months span{ white-space:nowrap; overflow:visible; }
.gh-body{ display:flex; align-items:stretch; gap:6px; }
.gh-days{ display:grid; grid-template-rows:repeat(7,1fr); gap:3px; width:28px; font-size:11px; color:var(--muted); font-weight:600; text-align:left; }
.gh-days span{ display:flex; align-items:center; line-height:1; }
.gh-weeks{ flex:1; display:grid; grid-template-rows:repeat(7,1fr); grid-auto-flow:column; gap:3px; }
.gh-cell{ aspect-ratio:1/1; min-width:11px; border-radius:3px; background:var(--gh-0); outline:1px solid rgba(128,128,128,.10); transition:transform .1s ease; }
.gh-cell:hover{ transform:scale(1.22); z-index:2; outline:1px solid var(--fg); }
.gh-cell.l1{ background:var(--gh-1); }
.gh-cell.l2{ background:var(--gh-2); }
.gh-cell.l3{ background:var(--gh-3); }
.gh-cell.l4{ background:var(--gh-4); }
.gh-cell.today{ outline:2px solid var(--blue); outline-offset:1px; }
.gh-cell.future{ opacity:.30; }
.gh-foot{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-top:12px; padding-top:10px; border-top:1px solid var(--line); font-size:12px; color:var(--muted); }
.gh-scale{ display:flex; align-items:center; gap:4px; font-size:11.5px; color:var(--muted); font-weight:600; }
.gh-scale i{ width:11px; height:11px; border-radius:2.5px; display:inline-block; outline:1px solid rgba(128,128,128,.12); }

/* Modern Weekly, Monthly & 12-Week Strips */
.wk-strip{ display:grid; grid-template-columns:repeat(7,1fr); gap:8px; margin-top:10px; }
.wk-day{ background:var(--surface-2); border:1px solid var(--line); border-radius:14px; padding:10px 6px; text-align:center; color:var(--fg); }
.wk-day.today{ border-color:var(--blue); box-shadow:0 0 0 1px color-mix(in srgb,var(--blue) 45%,transparent); }
.wk-day.done{ background:color-mix(in srgb,var(--green) 14%,var(--surface-2)); border-color:color-mix(in srgb,var(--green) 45%,var(--line)); }

.mo-grid{ display:grid; grid-template-columns:repeat(7,1fr); gap:6px; margin-top:10px; }
.mo-cell{ background:var(--surface-2); border:1px solid var(--line); border-radius:11px; padding:7px 6px; text-align:center; font-size:11.5px; color:var(--fg); }
.mo-cell.today{ border-color:var(--blue); box-shadow:0 0 0 1px var(--blue); }
.mo-cell.done{ background:color-mix(in srgb,var(--green) 16%,var(--surface-2)); border-color:color-mix(in srgb,var(--green) 45%,var(--line)); }

/* Streamlit Widget Contrast Fixes for Both Dark & Light Themes */
.stButton>button{
  border-radius:13px !important; font-weight:700 !important;
  border:1px solid var(--line) !important;
  background:var(--surface-2) !important;
  color:var(--fg) !important;
}
.stButton>button[kind="primary"]{
  background:var(--blue) !important;
  color:#ffffff !important;
  border-color:var(--blue) !important;
}
.stButton>button:disabled{
  opacity:.48 !important;
  color:var(--muted) !important;
}
.stButton>button:hover:not(:disabled){
  border-color:color-mix(in srgb,var(--blue) 60%,var(--line)) !important;
}
[data-testid="stExpander"]{
  border-radius:14px !important;
  border:1px solid var(--line) !important;
  background:var(--surface-2) !important;
  color:var(--fg) !important;
}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span {
  color:var(--fg) !important; font-weight:700 !important;
}
/* Segmented control, number/text/date inputs, selectboxes & file uploader */
[data-baseweb="button-group"]{
  background:var(--surface-2) !important; padding:3px !important; border-radius:12px !important; border:1px solid var(--line) !important;
}
[data-baseweb="button-group"] button{
  background:transparent !important; color:var(--muted) !important; border-radius:9px !important; font-weight:700 !important;
}
[data-baseweb="button-group"] button[aria-checked="true"],
[data-baseweb="button-group"] button[aria-pressed="true"]{
  background:var(--blue) !important; color:#ffffff !important;
}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div {
  background:var(--surface-2) !important; color:var(--fg) !important; border-color:var(--line) !important; border-radius:11px !important;
}
[data-baseweb="input"] input, [data-baseweb="select"] span, [data-baseweb="select"] div {
  color:var(--fg) !important;
}
[data-testid="stNumberInputStepDown"], [data-testid="stNumberInputStepUp"] {
  color:var(--fg) !important; background:var(--surface) !important;
}
[data-testid="stFileUploader"] section {
  background:var(--surface) !important; border:1px dashed var(--line) !important; border-radius:16px !important; color:var(--fg) !important;
}
[data-testid="stFileUploader"] button {
  background:var(--surface-2) !important; color:var(--fg) !important; border:1px solid var(--line) !important;
}
[data-testid="stCaptionContainer"], .stCaption {
  color:var(--muted) !important;
}
hr{ border-color:var(--line); }
"""


def inject(theme: str = "dark"):
    palette = _PALETTES.get(theme, _PALETTES["dark"])
    st.markdown(f"<style>:root{{{palette}}}\n{CSS_BODY}</style>", unsafe_allow_html=True)


def ring_svg(pct: float, color: str, size: int = 54) -> str:
    c = 144
    off = c * (1 - max(0, min(1, pct)))
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 58 58">'
        f'<circle cx="29" cy="29" r="23" fill="none" stroke="var(--track)" stroke-width="6"/>'
        f'<circle cx="29" cy="29" r="23" fill="none" stroke="{color}" stroke-width="6" '
        f'stroke-linecap="round" stroke-dasharray="{c}" stroke-dashoffset="{off}" '
        f'transform="rotate(-90 29 29)"/></svg>'
    )


def ring(pct: float, color: str, value_html: str, label: str, size: int = 54) -> str:
    return (f'<div class="ringcard">{ring_svg(pct, color, size)}'
            f'<div class="v">{value_html}</div><div class="k">{label}</div></div>')


def tile(label: str, value_html: str, sub: str = "", sub_cls: str = "") -> str:
    d = f'<div class="d {sub_cls}">{sub}</div>' if sub else ""
    return f'<div class="tile"><div class="k">{label}</div><div class="v">{value_html}</div>{d}</div>'


def bar(label: str, value: str, pct: float, color: str, primary: bool = False) -> str:
    w = max(0, min(100, pct))
    cls = "bar primary" if primary else "bar"
    return (
        f'<div class="{cls}"><div class="bhead"><span class="bl">{label}</span>'
        f'<span class="bv">{value}</span></div><div class="btrack">'
        f'<div class="bfill" style="width:{w}%;background:{color}"></div></div></div>'
    )


def metric_row(label: str, value: str, target: str, cls: str, verdict: str, note: str) -> str:
    dot = {"good": "var(--green)", "bad": "var(--red)", "": "var(--faint)"}.get(cls, "var(--faint)")
    return (
        f'<div style="padding:12px 0;border-top:1px solid var(--line);color:var(--fg)">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">'
        f'<span style="font-weight:700;font-size:14px;color:var(--fg)">{label}</span>'
        f'<span style="font-family:Nunito;font-weight:800;font-size:16px;color:var(--fg)">{value}</span></div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:3px">'
        f'<span class="muted" style="font-size:12px">{note}</span>'
        f'<span style="font-size:11.5px;font-weight:700;color:{dot};white-space:nowrap">'
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{dot};margin-inline-end:5px"></span>'
        f'{verdict} · hedef {target}</span></div></div>'
    )


def legend(color: str) -> str:
    return (
        '<div class="legend"><span>Az</span>'
        '<i style="background:var(--track)"></i>'
        '<i style="background:var(--map1)"></i>'
        '<i style="background:var(--map2)"></i>'
        f'<i style="background:{color}"></i><span>Çok</span></div>'
    )


def github_heatmap(
    today: dt.date,
    day_records: dict[str, dict],
    weeks: int = 52,
) -> str:
    """Render a GitHub-style contribution heatmap over `weeks` ending on the current week."""
    this_monday = today - dt.timedelta(days=today.weekday())
    start_monday = this_monday - dt.timedelta(weeks=weeks - 1)

    month_spans = []
    last_month = None
    last_col = -99
    for w in range(weeks):
        col_date = start_monday + dt.timedelta(weeks=w)
        m_date = col_date
        for offset in range(7):
            cand = col_date + dt.timedelta(days=offset)
            if cand.day == 1:
                m_date = cand
                break
        m = m_date.month
        if m != last_month and (w - last_col >= 3):
            # Span 3 columns so 3-letter month names (Kas, Ara, Oca) never wrap onto two lines
            span_end = min(weeks + 1, w + 4)
            month_spans.append(f'<span style="grid-column:{w + 1} / {span_end}">{MON_TR[m - 1]}</span>')
            last_month = m
            last_col = w

    cells = []
    active_days = 0
    str_cnt = pad_cnt = crd_cnt = prot_cnt = 0
    month_iso_prefix = today.strftime("%Y-%m")
    this_month_active = 0

    for w in range(weeks):
        w_mon = start_monday + dt.timedelta(weeks=w)
        for d_idx in range(7):
            cur = w_mon + dt.timedelta(days=d_idx)
            iso = cur.strftime("%Y-%m-%d")
            rec = day_records.get(iso, {})
            lvl = int(rec.get("level", 0))
            is_future = cur > today
            if not is_future and lvl > 0:
                active_days += 1
                if iso.startswith(month_iso_prefix):
                    this_month_active += 1
            if not is_future:
                if rec.get("strength"):
                    str_cnt += 1
                if rec.get("padel"):
                    pad_cnt += 1
                if rec.get("cardio"):
                    crd_cnt += 1
                if rec.get("protein_ok"):
                    prot_cnt += 1

            cls = f"gh-cell l{lvl}" if (lvl > 0 and not is_future) else "gh-cell"
            if cur == today:
                cls += " today"
            elif is_future:
                cls += " future"

            date_lbl = f"{cur.day} {MON_TR[cur.month - 1]} {cur.year} ({DOW_TR[d_idx]})"
            detail = rec.get("summary") or ("Gelecek gün" if is_future else "Kayıt yok")
            tip = f"{date_lbl} — {detail}".replace('"', "&quot;")
            cells.append(f'<div class="{cls}" title="{tip}"></div>')

    months_html = (
        f'<div class="gh-months" style="grid-template-columns:repeat({weeks},minmax(11px,1fr))">'
        + "".join(month_spans)
        + "</div>"
    )
    days_html = (
        '<div class="gh-days">'
        '<span>Pzt</span><span></span><span>Çar</span><span></span><span>Cum</span><span></span><span></span>'
        '</div>'
    )
    weeks_html = (
        f'<div class="gh-weeks" style="grid-template-columns:repeat({weeks},minmax(11px,1fr))">'
        + "".join(cells)
        + "</div>"
    )

    return (
        '<div class="gh-card">'
        '<div class="gh-top">'
        f'<div class="gh-title">{active_days} aktif gün <span style="color:var(--muted);font-weight:600;font-size:13.5px">· son 1 yılda (bu ay {this_month_active} gün)</span></div>'
        '<div class="gh-pills">'
        f'<span class="gh-pill"><i class="gh-dot" style="background:var(--blue)"></i>{str_cnt} güç</span>'
        f'<span class="gh-pill"><i class="gh-dot" style="background:var(--teal)"></i>{pad_cnt} padel</span>'
        f'<span class="gh-pill"><i class="gh-dot" style="background:var(--green)"></i>{crd_cnt} kardiyo</span>'
        f'<span class="gh-pill"><i class="gh-dot" style="background:var(--orange)"></i>{prot_cnt} protein hedefte</span>'
        '</div></div>'
        f'<div class="gh-scroll"><div class="gh-board">{months_html}<div class="gh-body">{days_html}{weeks_html}</div></div></div>'
        '<div class="gh-foot">'
        '<span>Yoğunluk: <b>1</b> = tartım/aktivite · <b>2</b> = kardiyo/protein · <b>3</b> = güç/padel · <b>4</b> = antrenman + protein hedefte</span>'
        '<div class="gh-scale"><span>Az</span>'
        '<i style="background:var(--gh-0)"></i>'
        '<i style="background:var(--gh-1)"></i>'
        '<i style="background:var(--gh-2)"></i>'
        '<i style="background:var(--gh-3)"></i>'
        '<i style="background:var(--gh-4)"></i>'
        '<span>Çok</span></div>'
        '</div></div>'
    )
