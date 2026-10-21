"""Shared UI: CSS injection and small HTML builders (rings, tiles, cards, GitHub-style heatmap)
so the Streamlit app looks like our own cohesive design rather than default Streamlit chrome."""
from __future__ import annotations
import datetime as dt
import streamlit as st

MON_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DOW_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
/* dark is the default palette; light is applied automatically when the viewer's OS/browser
   is in light mode (prefers-color-scheme). Every surface/text uses these tokens so both flip together. */
:root{
  --bg:#070809; --surface:#14161d; --surface-2:#1c1f28; --line:rgba(255,255,255,.08);
  --fg:#f3f5fa; --muted:#9aa1ae; --faint:#6b7280;
  --blue:#0a84ff; --purple:#bf5af2; --orange:#ff9f0a; --green:#30d158; --teal:#40c8e0; --red:#ff6961;
  --track:#2a2e3a; --map1:#1f4e85; --map2:#1f6fd0; --map3:#0a84ff;
  --shadow:0 2px 6px rgba(0,0,0,.35);
  /* GitHub contribution heatmap levels (dark mode) */
  --gh-0:#1c212b; --gh-1:#0e4429; --gh-2:#006d32; --gh-3:#26a641; --gh-4:#39d353;
}
@media (prefers-color-scheme: light){
  :root{
    --bg:#f5f7fb; --surface:#ffffff; --surface-2:#eef1f7; --line:rgba(12,18,30,.10);
    --fg:#0d1320; --muted:#5a6475; --faint:#8a93a3;
    --blue:#0a7aff; --purple:#a63fe0; --orange:#f08a00; --green:#1fb24a; --teal:#1aa6c4; --red:#e3483f;
    --track:#e4e8f0; --map1:#bcd4f2; --map2:#5fa0ec; --map3:#0a7aff;
    --shadow:0 2px 8px rgba(12,18,30,.06);
    /* GitHub contribution heatmap levels (light mode — matches GitHub's exact greens) */
    --gh-0:#ebedf0; --gh-1:#9be9a8; --gh-2:#40c463; --gh-3:#30a14e; --gh-4:#216e39;
  }
}
html, body, [class*="css"], .stMarkdown, p, span, div { font-family:"Hanken Grotesk",system-ui,sans-serif; }
h1,h2,h3 { font-family:"Nunito",sans-serif !important; letter-spacing:-.02em; }
.stApp{ background:var(--bg); }
/* desktop-first: a wide, dense dashboard; Streamlit reflows it on phones automatically */
.block-container{ padding-top:1.2rem; padding-bottom:3rem; max-width:1180px; }
#MainMenu, header, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }

/* Unify Streamlit bordered containers (`st.container(border=True)`) with `.fcard` / `.exrow`
   so workout exercise cards, warm-up/finisher banners, and HTML cards share the exact same surface! */
[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--surface) !important;
  border:1px solid var(--line) !important;
  border-radius:20px !important;
  box-shadow:var(--shadow) !important;
  padding:15px 16px !important;
  transition:border-color .15s ease, transform .15s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover{
  border-color:color-mix(in srgb,var(--blue) 28%,var(--line)) !important;
}

/* Exercise card internal layout — guarantees uniform height across all 3 columns even when names wrap */
.excard-head{
  display:flex; align-items:flex-start; gap:14px;
  min-height:86px; margin-bottom:6px;
}
.excard-ring{
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  flex-shrink:0; width:56px;
}
.excard-info{
  flex:1; min-width:0; display:flex; flex-direction:column; justify-content:space-between;
  min-height:82px;
}
.excard-title{
  font-weight:700; font-size:15px; line-height:1.25; color:var(--fg);
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
  overflow:hidden; min-height:2.5em;
}
.excard-meta{
  display:flex; align-items:center; gap:8px; margin:3px 0 5px;
}

/* exercise grid — spread cards across the page instead of a single tall column */
.exgrid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:11px; margin-top:2px; }
.exrow{ display:flex; align-items:center; gap:13px; background:var(--surface); border:1px solid var(--line);
  border-radius:20px; padding:14px 16px; box-shadow:var(--shadow); }
/* tabs -> app-like segmented, scrollable on phone */
.stTabs [data-baseweb="tab-list"]{ gap:4px; background:var(--surface-2); padding:4px; border-radius:13px; overflow-x:auto; }
.stTabs [data-baseweb="tab"]{ height:auto; padding:8px 14px; border-radius:9px; color:var(--muted); font-weight:800; font-family:"Nunito"; }
.stTabs [aria-selected="true"]{ background:var(--surface); color:var(--fg); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{ display:none; }

.fcard{ background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:16px; margin-bottom:12px; box-shadow:var(--shadow); }
.eyebrow{ font-size:11.5px; text-transform:uppercase; letter-spacing:.11em; color:var(--faint); font-weight:800; margin:0 0 10px; }
.rings{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:10px; }
/* a bold start-date / streak counter for the top of Home */
.counter{ display:flex; align-items:center; gap:18px; background:
  radial-gradient(120% 140% at 0% 0%, color-mix(in srgb,var(--blue) 24%,transparent), transparent 55%),
  linear-gradient(160deg, var(--surface), var(--surface-2)); border:1px solid color-mix(in srgb,var(--blue) 24%,var(--line));
  border-radius:22px; padding:18px 22px; margin-bottom:12px; flex-wrap:wrap; box-shadow:var(--shadow); }
.counter .big{ font-family:"Nunito"; font-weight:900; font-size:46px; line-height:.9; }
.counter .big small{ font-size:16px; color:var(--faint); font-weight:800; }
.counter .lbl{ font-size:12px; color:var(--muted); font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.weekdots{ display:flex; gap:7px; margin-top:7px; }
.weekdots i{ width:11px; height:11px; border-radius:50%; background:var(--surface-2); border:1px solid var(--line); }
.weekdots i.on{ background:var(--green); border-color:var(--green); }
.ringcard{ background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:12px 3px 10px; text-align:center; box-shadow:var(--shadow); }
.ringcard .v{ font-family:"Nunito"; font-weight:800; font-size:13.5px; margin-top:6px; line-height:1; }
.ringcard .v small{ color:var(--faint); font-weight:700; font-size:.82em; }
.ringcard .k{ font-size:10.5px; color:var(--muted); font-weight:600; margin-top:3px; }
.hero{ border-radius:24px; padding:20px; margin-bottom:10px; position:relative; overflow:hidden; box-shadow:var(--shadow); }
.hero .kick{ font-size:11.5px; font-weight:800; text-transform:uppercase; letter-spacing:.1em; }
.hero h2{ font-size:26px; font-weight:900; margin:8px 0 4px; }
.chiprow{ display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 2px; }
.chip{ font-size:11.5px; font-weight:700; padding:3px 9px; border-radius:999px; background:var(--surface-2); color:var(--muted); }
.tiles{ display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr)); gap:11px; margin-bottom:12px; }
.tile{ background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:15px; box-shadow:var(--shadow); }
.tile .k{ font-size:11.5px; color:var(--muted); font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.tile .v{ font-family:"Nunito"; font-weight:900; font-size:26px; margin-top:7px; line-height:1; }
.tile .v small{ font-size:14px; color:var(--faint); font-weight:800; }
.tile .d{ font-size:12px; font-weight:700; margin-top:6px; color:var(--faint); }
.good{ color:var(--green)!important; } .bad{ color:var(--red)!important; }
.legend{ display:flex; gap:6px; align-items:center; justify-content:center; margin-top:8px; font-size:11px; color:var(--faint); font-weight:600; }
.legend i{ width:14px; height:9px; border-radius:3px; display:inline-block; }
.bars{ display:flex; flex-direction:column; gap:13px; }
.bar .bhead{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:5px; }
.bar .bl{ font-weight:700; } .bar.primary .bl{ font-size:1.06em; }
.bar .bv{ color:var(--muted); font-weight:600; font-size:13px; }
.btrack{ height:8px; border-radius:6px; background:var(--surface-2); overflow:hidden; }
.bar.primary .btrack{ height:11px; }
.bfill{ height:100%; border-radius:6px; }

/* GitHub-style Contribution Heatmap */
.gh-card{ background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:18px 20px; margin-bottom:12px; box-shadow:var(--shadow); }
.gh-top{ display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:10px; margin-bottom:12px; }
.gh-title{ font-family:"Nunito",sans-serif; font-weight:800; font-size:16px; color:var(--fg); }
.gh-pills{ display:flex; gap:8px; flex-wrap:wrap; font-size:12px; font-weight:700; color:var(--muted); }
.gh-pill{ background:var(--surface-2); padding:3px 10px; border-radius:999px; display:inline-flex; align-items:center; gap:5px; }
.gh-scroll{ overflow-x:auto; padding-bottom:4px; }
.gh-board{ min-width:680px; }
.gh-months{ display:grid; gap:3px; margin-left:34px; margin-bottom:5px; font-size:11.5px; color:var(--muted); font-weight:600; line-height:1; }
.gh-body{ display:flex; align-items:stretch; gap:6px; }
.gh-days{ display:grid; grid-template-rows:repeat(7,1fr); gap:3px; width:28px; font-size:11px; color:var(--muted); font-weight:600; text-align:left; }
.gh-days span{ display:flex; align-items:center; line-height:1; }
.gh-weeks{ flex:1; display:grid; grid-template-rows:repeat(7,1fr); grid-auto-flow:column; gap:3px; }
.gh-cell{ aspect-ratio:1/1; min-width:11px; border-radius:3px; background:var(--gh-0); outline:1px solid rgba(128,128,128,.08); transition:transform .1s ease; }
.gh-cell:hover{ transform:scale(1.22); z-index:2; outline:1px solid var(--fg); }
.gh-cell.l1{ background:var(--gh-1); }
.gh-cell.l2{ background:var(--gh-2); }
.gh-cell.l3{ background:var(--gh-3); }
.gh-cell.l4{ background:var(--gh-4); }
.gh-cell.today{ outline:2px solid var(--blue); outline-offset:1px; }
.gh-cell.future{ opacity:.32; }
.gh-foot{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-top:12px; padding-top:10px; border-top:1px solid var(--line); font-size:12px; color:var(--muted); }
.gh-scale{ display:flex; align-items:center; gap:4px; font-size:11.5px; color:var(--muted); font-weight:600; }
.gh-scale i{ width:11px; height:11px; border-radius:2.5px; display:inline-block; outline:1px solid rgba(128,128,128,.08); }

/* Modern Weekly & Monthly Target Strip */
.wk-strip{ display:grid; grid-template-columns:repeat(7,1fr); gap:8px; margin-top:10px; }
.wk-day{ background:var(--surface-2); border:1px solid var(--line); border-radius:14px; padding:10px 6px; text-align:center; transition:border-color .15s; }
.wk-day.today{ border-color:var(--blue); box-shadow:0 0 0 1px color-mix(in srgb,var(--blue) 35%,transparent); }
.wk-day.done{ background:color-mix(in srgb,var(--green) 11%,var(--surface-2)); border-color:color-mix(in srgb,var(--green) 38%,var(--line)); }

/* widget polish — consistent rounded controls in both themes */
.stButton>button{ border-radius:13px; font-weight:700; border-color:var(--line); background:var(--surface-2); }
.stButton>button[kind="primary"]{ background:var(--blue); color:#fff; border-color:var(--blue); }
.stButton>button:hover{ border-color:color-mix(in srgb,var(--blue) 50%,var(--line)); }
[data-testid="stExpander"]{ border-radius:14px !important; border-color:var(--line) !important; background:var(--surface-2) !important; }
[data-baseweb="segmented-control"]{ border-radius:13px; }
hr{ border-color:var(--line); }
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


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
        f'<div style="padding:12px 0;border-top:1px solid var(--line)">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">'
        f'<span style="font-weight:700;font-size:14px">{label}</span>'
        f'<span style="font-family:Nunito;font-weight:800;font-size:16px">{value}</span></div>'
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
    """Render a GitHub-style contribution heatmap over `weeks` ending on the current week.

    `day_records` maps ISO date 'YYYY-MM-DD' -> {
        'level': 0..4,
        'summary': str (tooltip text),
        'strength': bool,
        'padel': bool,
        'cardio': bool,
        'protein_ok': bool,
    }
    """
    # Anchor end to Sunday of the current week so the grid has full 7-day columns (Mon..Sun)
    this_monday = today - dt.timedelta(days=today.weekday())
    start_monday = this_monday - dt.timedelta(weeks=weeks - 1)

    # Month labels placed above the column where each month first appears
    month_spans = []
    last_month = None
    last_col = -99
    for w in range(weeks):
        col_date = start_monday + dt.timedelta(weeks=w)
        # Check if the 1st of a month falls in this week, else use Monday's month for col 0
        m_date = col_date
        for offset in range(7):
            cand = col_date + dt.timedelta(days=offset)
            if cand.day == 1:
                m_date = cand
                break
        m = m_date.month
        if m != last_month and (w - last_col >= 2):
            month_spans.append(f'<span style="grid-column:{w + 1}">{MON_TR[m - 1]}</span>')
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
        f'<span class="gh-pill">🏋️ {str_cnt} güç</span>'
        f'<span class="gh-pill">🎾 {pad_cnt} padel</span>'
        f'<span class="gh-pill">🚣 {crd_cnt} kardiyo</span>'
        f'<span class="gh-pill">🥩 {prot_cnt} protein hedefte</span>'
        '</div></div>'
        f'<div class="gh-scroll"><div class="gh-board">{months_html}<div class="gh-body">{days_html}{weeks_html}</div></div></div>'
        '<div class="gh-foot">'
        '<span>Renk yoğunluğu: <b>1</b> = aktivite/kayıt · <b>2</b> = kardiyo/protein hedefi · <b>3</b> = güç/padel · <b>4</b> = antrenman + protein hedefte</span>'
        '<div class="gh-scale"><span>Az</span>'
        '<i style="background:var(--gh-0)"></i>'
        '<i style="background:var(--gh-1)"></i>'
        '<i style="background:var(--gh-2)"></i>'
        '<i style="background:var(--gh-3)"></i>'
        '<i style="background:var(--gh-4)"></i>'
        '<span>Çok</span></div>'
        '</div></div>'
    )
