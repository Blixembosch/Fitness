"""Shared UI: CSS injection and small HTML builders (rings, tiles, cards) so the Streamlit app
looks like our own design rather than the default Streamlit chrome."""
from __future__ import annotations
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
:root{
  --bg:#070809; --surface:#14161d; --surface-2:#1c1f28; --line:rgba(255,255,255,.08);
  --fg:#f3f5fa; --muted:#9aa1ae; --faint:#6b7280;
  --blue:#0a84ff; --purple:#bf5af2; --orange:#ff9f0a; --green:#30d158; --teal:#40c8e0; --red:#ff6961;
  --track:#2a2e3a; --map1:#1f4e85; --map2:#1f6fd0; --map3:#0a84ff;
}
html, body, [class*="css"], .stMarkdown, p, span, div { font-family:"Hanken Grotesk",system-ui,sans-serif; }
h1,h2,h3 { font-family:"Nunito",sans-serif !important; letter-spacing:-.02em; }
/* desktop-first: a wide, dense dashboard; Streamlit reflows it on phones automatically */
.block-container{ padding-top:1.2rem; padding-bottom:3rem; max-width:1120px; }
#MainMenu, header, footer { visibility:hidden; }
/* tabs -> app-like segmented, scrollable on phone */
.stTabs [data-baseweb="tab-list"]{ gap:4px; background:var(--surface-2); padding:4px; border-radius:13px; overflow-x:auto; }
.stTabs [data-baseweb="tab"]{ height:auto; padding:8px 14px; border-radius:9px; color:var(--muted); font-weight:800; font-family:"Nunito"; }
.stTabs [aria-selected="true"]{ background:var(--surface); color:var(--fg); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{ display:none; }

.fcard{ background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:16px; margin-bottom:12px; }
.eyebrow{ font-size:11.5px; text-transform:uppercase; letter-spacing:.11em; color:var(--faint); font-weight:800; margin:0 0 10px; }
.rings{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:8px; }
/* a bold start-date / streak counter for the top of Home */
.counter{ display:flex; align-items:center; gap:18px; background:
  radial-gradient(120% 140% at 0% 0%, color-mix(in srgb,var(--blue) 24%,transparent), transparent 55%),
  linear-gradient(160deg, var(--surface), var(--surface-2)); border:1px solid color-mix(in srgb,var(--blue) 24%,var(--line));
  border-radius:22px; padding:18px 22px; margin-bottom:12px; flex-wrap:wrap; }
.counter .big{ font-family:"Nunito"; font-weight:900; font-size:46px; line-height:.9; }
.counter .big small{ font-size:16px; color:var(--faint); font-weight:800; }
.counter .lbl{ font-size:12px; color:var(--muted); font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.weekdots{ display:flex; gap:7px; margin-top:7px; }
.weekdots i{ width:11px; height:11px; border-radius:50%; background:var(--surface-2); border:1px solid var(--line); }
.weekdots i.on{ background:var(--green); border-color:var(--green); }
.ringcard{ background:var(--surface); border:1px solid var(--line); border-radius:17px; padding:12px 3px 10px; text-align:center; }
.ringcard .v{ font-family:"Nunito"; font-weight:800; font-size:13.5px; margin-top:6px; line-height:1; }
.ringcard .v small{ color:var(--faint); font-weight:700; font-size:.82em; }
.ringcard .k{ font-size:10.5px; color:var(--muted); font-weight:600; margin-top:3px; }
.hero{ border-radius:24px; padding:20px; margin-bottom:8px; position:relative; overflow:hidden; }
.hero .kick{ font-size:11.5px; font-weight:800; text-transform:uppercase; letter-spacing:.1em; }
.hero h2{ font-size:26px; font-weight:900; margin:8px 0 4px; }
.chiprow{ display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 2px; }
.chip{ font-size:12px; font-weight:700; padding:4px 10px; border-radius:999px; background:var(--surface-2); color:var(--muted); }
.tiles{ display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr)); gap:11px; }
.tile{ background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:15px; }
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
