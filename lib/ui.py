"""Shared UI: CSS injection with automatic system Dark/Light theme detection (prefers-color-scheme)
and cohesive HTML builders (rings, tiles, cards, GitHub-style heatmap, and monthly/annual views)."""
from __future__ import annotations
import datetime as dt
import streamlit as st

MON_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DOW_TR = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');

/* Automatic System Themes: Dark is default for dark OS; Light flips automatically when viewer OS is in light mode */
:root {
  --bg:#0b0f19; --surface:#151d2d; --surface-2:#1e293b; --surface-elevated:#27354d;
  --line:#2e3d5b; --line-strong:#475569;
  --fg:#ffffff; --muted:#cbd5e1; --faint:#94a3b8;
  --blue:#3898ff; --purple:#c084fc; --orange:#fb923c; --green:#34d399; --teal:#22d3ee; --red:#f87171;
  --track:#242c3e; --map1:#1e40af; --map2:#2563eb; --map3:#3898ff;
  --shadow:0 6px 22px rgba(0,0,0,.60);
  --gh-0:#1e293b; --gh-1:#0e4429; --gh-2:#006d32; --gh-3:#26a641; --gh-4:#39d353;
  --seg-bg:#1e293b; --seg-btn:transparent; --seg-btn-hover:#27354d; --seg-active:#3898ff;
  --input-bg:#151d2d; --input-fg:#ffffff;
}

@media (prefers-color-scheme: light) {
  :root {
    --bg:#f4f6fb; --surface:#ffffff; --surface-2:#eef2f8; --surface-elevated:#f8fafc;
    --line:#cbd5e1; --line-strong:#94a3b8;
    --fg:#0f172a; --muted:#334155; --faint:#64748b;
    --blue:#0a7aff; --purple:#9333ea; --orange:#ea580c; --green:#16a34a; --teal:#0891b2; --red:#dc2626;
    --track:#e2e8f0; --map1:#bfdbfe; --map2:#60a5fa; --map3:#0a7aff;
    --shadow:0 2px 12px rgba(15,23,42,.08);
    --gh-0:#ebedf0; --gh-1:#9be9a8; --gh-2:#40c463; --gh-3:#30a14e; --gh-4:#216e39;
    --seg-bg:#eef2f8; --seg-btn:transparent; --seg-btn-hover:#e2e8f0; --seg-active:#0a7aff;
    --input-bg:#ffffff; --input-fg:#0f172a;
  }
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background:var(--bg) !important;
  color:var(--fg) !important;
  font-family:"Hanken Grotesk",system-ui,sans-serif;
  font-size:13.5px;
}
.stMarkdown, [data-testid="stMarkdownContainer"], p, span, div, label {
  font-family:"Hanken Grotesk",system-ui,sans-serif;
  color:inherit;
}
.stMarkdown p, [data-testid="stMarkdownContainer"] p {
  font-size:13px;
  line-height:1.5;
}
h1 {
  font-family:"Nunito",sans-serif !important;
  letter-spacing:-.02em;
  font-size:22px !important;
  color:var(--fg) !important;
}
h2 {
  font-family:"Nunito",sans-serif !important;
  letter-spacing:-.02em;
  font-size:18px !important;
  color:var(--fg) !important;
}
h3 {
  font-family:"Nunito",sans-serif !important;
  letter-spacing:-.02em;
  font-size:15px !important;
  color:var(--fg) !important;
}
h4 {
  font-family:"Nunito",sans-serif !important;
  letter-spacing:-.02em;
  font-size:13.5px !important;
  color:var(--fg) !important;
}
.block-container{ padding-top:1.1rem; padding-bottom:3rem; max-width:1180px; }
#MainMenu, header, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }

/* Unified Card Architecture across all pages (Plan, Workout, Stats, Nutrition) */
.exrow,
.fcard,
.tile,
.hero,
.gh-card,
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--surface) !important;
  border:1.5px solid var(--line) !important;
  border-radius:20px !important;
  box-shadow:var(--shadow) !important;
  color:var(--fg) !important;
  transition:border-color .15s ease, box-shadow .15s ease, transform .15s ease;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  padding:16px !important;
  margin-bottom:12px !important;
}

.exrow:hover,
.fcard:hover,
.tile:hover,
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color:color-mix(in srgb,var(--blue) 55%,var(--line)) !important;
  box-shadow:0 8px 24px rgba(0,0,0,.60) !important;
}

/* FIX: Segmented control & ButtonGroup (st.segmented_control / st.pills for Üst A / Alt A / Üst B & Hafta / Ay) */
div.stButtonGroup,
div[data-testid="stButtonGroup"],
div[data-testid="stSegmentedControl"],
div[data-baseweb="button-group"] {
  background:var(--seg-bg) !important;
  border:1px solid var(--line) !important;
  border-radius:14px !important;
  padding:4px !important;
  gap:4px !important;
}
div.stButtonGroup button,
div.stButtonGroup [role="button"],
div[data-testid="stButtonGroup"] button,
div[data-testid="stButtonGroup"] [role="button"],
div[data-testid="stSegmentedControl"] button,
div[data-baseweb="button-group"] button {
  background:var(--seg-btn) !important;
  color:var(--muted) !important;
  border:1px solid transparent !important;
  border-radius:10px !important;
  font-family:"Nunito",sans-serif !important;
  font-weight:800 !important;
  font-size:12.5px !important;
  padding:5px 14px !important;
  transition:all .15s ease !important;
}
div.stButtonGroup button:hover,
div.stButtonGroup [role="button"]:hover,
div[data-testid="stButtonGroup"] button:hover,
div[data-testid="stButtonGroup"] [role="button"]:hover,
div[data-testid="stSegmentedControl"] button:hover,
div[data-baseweb="button-group"] button:hover {
  background:var(--seg-btn-hover) !important;
  color:var(--fg) !important;
}
div.stButtonGroup button[data-selected],
div.stButtonGroup button[aria-checked="true"],
div.stButtonGroup button[aria-pressed="true"],
div.stButtonGroup [data-selected="true"],
div.stButtonGroup [role="button"][data-selected],
div[data-testid="stButtonGroup"] button[data-selected],
div[data-testid="stButtonGroup"] button[aria-checked="true"],
div[data-testid="stButtonGroup"] button[aria-pressed="true"],
div[data-testid="stButtonGroup"] [data-selected="true"],
div[data-testid="stButtonGroup"] [role="button"][data-selected],
div[data-testid="stSegmentedControl"] button[aria-checked="true"],
div[data-testid="stSegmentedControl"] button[aria-pressed="true"],
div[data-baseweb="button-group"] button[aria-checked="true"],
div[data-baseweb="button-group"] button[aria-pressed="true"] {
  background:var(--seg-active) !important;
  color:#ffffff !important;
  border-color:var(--seg-active) !important;
  box-shadow:0 2px 8px rgba(0,0,0,.25) !important;
}
div.stButtonGroup button *,
div.stButtonGroup [role="button"] *,
div[data-testid="stButtonGroup"] button *,
div[data-testid="stButtonGroup"] [role="button"] * {
  color:inherit !important;
}

/* FIX: Number inputs, Text inputs, Date inputs, Selectboxes — NO MORE WHITE BOXES! */
div.stSelectbox,
div[data-testid="stSelectbox"] {
  color:var(--input-fg) !important;
}

/* Outer combobox wrapper / control box - covers both old BaseWeb and new Streamlit React-Aria */
div[data-testid="stSelectbox"] > div,
div[data-testid="stSelectbox"] > div > div,
div[data-testid="stSelectbox"] > div > div > div,
div[data-testid="stSelectbox"] [role="combobox"],
div[data-testid="stSelectbox"] div[class*="e1fp86qc0"],
div[data-testid="stSelectbox"] div[data-focus-within],
div[data-testid="stSelectbox"] [data-baseweb="select"],
div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background:var(--input-bg) !important;
  background-color:var(--input-bg) !important;
  color:var(--input-fg) !important;
  border:1px solid var(--line) !important;
  border-radius:12px !important;
  box-shadow:none !important;
}

/* Selectbox input field & rendered value text */
div[data-testid="stSelectbox"] input,
div[data-testid="stSelectbox"] input[type="text"],
div[data-testid="stSelectbox"] input[role="combobox"],
div[data-testid="stSelectbox"] [data-baseweb="select"] span,
div[data-testid="stSelectbox"] [data-baseweb="select"] div,
div[data-testid="stSelectbox"] div[class*="e1fp86qc1"] {
  background:transparent !important;
  background-color:transparent !important;
  color:var(--input-fg) !important;
  -webkit-text-fill-color:var(--input-fg) !important;
  font-family:"Hanken Grotesk",system-ui,sans-serif !important;
  font-size:13px !important;
  font-weight:600 !important;
}

/* Selectbox arrow icon and buttons */
div[data-testid="stSelectbox"] button,
div[data-testid="stSelectbox"] svg,
div[data-testid="stSelectbox"] [aria-label="Open"],
div[data-testid="stSelectbox"] div[class*="e1fp86qc2"] {
  color:var(--muted) !important;
  fill:var(--muted) !important;
  background:transparent !important;
}

/* Dropdown Menus / Virtual Dropdowns (rendered in body portals) */
div[data-testid="stSelectboxVirtualDropdown"],
div[data-testid="stSelectboxVirtualDropdown"] > div,
ul[data-testid="stSelectboxVirtualDropdown"],
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
div[data-baseweb="menu"],
ul[role="listbox"] {
  background:var(--surface) !important;
  background-color:var(--surface) !important;
  color:var(--fg) !important;
  border:1px solid var(--line) !important;
  border-radius:12px !important;
  box-shadow:0 10px 30px rgba(0,0,0,.5) !important;
  overflow:hidden !important;
}

div[data-testid="stSelectboxVirtualDropdown"] *,
div[data-baseweb="popover"] *,
div[data-baseweb="menu"] *,
ul[role="listbox"] * {
  color:var(--fg) !important;
}

div[data-testid="stSelectboxVirtualDropdown"] [role="option"],
div[data-testid="stSelectboxVirtualDropdown"] li,
div[data-testid="stSelectboxVirtualDropdown"] div[class*="e1fp86qc7"],
div[data-testid="stSelectboxVirtualDropdown"] div[class*="e1fp86qc8"],
ul[role="listbox"] [role="option"],
ul[role="listbox"] li {
  color:var(--fg) !important;
  font-family:"Hanken Grotesk",system-ui,sans-serif !important;
  font-size:12.5px !important;
  font-weight:600 !important;
  padding:6px 12px !important;
  cursor:pointer !important;
}

div[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
div[data-testid="stSelectboxVirtualDropdown"] [data-hovered] [data-item-hl],
div[data-testid="stSelectboxVirtualDropdown"] [data-focused] [data-item-hl],
div[data-testid="stSelectboxVirtualDropdown"] [aria-selected="true"],
ul[role="listbox"] [role="option"]:hover,
ul[role="listbox"] [aria-selected="true"] {
  background:var(--surface-elevated) !important;
  background-color:var(--surface-elevated) !important;
  color:var(--blue) !important;
}

/* Number inputs, Text inputs, Date inputs */
div.stNumberInput,
div.stTextInput,
div.stDateInput,
div[data-testid="stNumberInput"],
div[data-testid="stTextInput"],
div[data-testid="stDateInput"] {
  color:var(--input-fg) !important;
}

div[data-testid="stNumberInputContainer"],
div[data-testid="stTextInputRootElement"],
div[data-testid="stDateInputField"],
div[data-testid="stDateInput"] > div,
div[data-testid="stDateInput"] [data-baseweb="input"],
div[data-baseweb="input"],
div[data-baseweb="base-input"] {
  background:var(--input-bg) !important;
  background-color:var(--input-bg) !important;
  color:var(--input-fg) !important;
  border:1px solid var(--line) !important;
  border-radius:12px !important;
}

input,
input[type="text"],
input[type="number"],
div[data-testid="stNumberInputField"],
div[data-testid="stTextInputField"],
div[data-testid="stDateInputField"] input,
[data-baseweb="input"] input {
  background:transparent !important;
  background-color:transparent !important;
  color:var(--input-fg) !important;
  -webkit-text-fill-color:var(--input-fg) !important;
  font-size:13px !important;
}

/* Number input increment/decrement buttons */
[data-testid="stNumberInputStepDown"],
[data-testid="stNumberInputStepUp"] {
  color:var(--input-fg) !important;
  background:var(--surface-2) !important;
  border-color:var(--line) !important;
}
[data-testid="stNumberInputStepDown"]:hover,
[data-testid="stNumberInputStepUp"]:hover {
  background:var(--surface-elevated) !important;
  color:var(--fg) !important;
}

/* Date Input Calendar Popup */
div[data-testid="stDateInputCalendar"],
div[data-testid="stDateInputCalendar"] > div {
  background:var(--surface) !important;
  background-color:var(--surface) !important;
  color:var(--fg) !important;
  border:1px solid var(--line) !important;
  border-radius:14px !important;
  box-shadow:0 10px 30px rgba(0,0,0,.5) !important;
}
div[data-testid="stDateInputCalendar"] * {
  color:var(--fg) !important;
}
div[data-testid="stDateInputCalendar"] button {
  background:transparent !important;
  color:var(--fg) !important;
}
div[data-testid="stDateInputCalendar"] button:hover {
  background:var(--surface-elevated) !important;
  color:var(--blue) !important;
}

/* Fail-Safe Contrast Guarantee:
   If ANY container or element renders with white background in dark mode,
   force dark text so it is NEVER white-on-white! */
div[style*="background-color: rgb(255, 255, 255)"],
div[style*="background-color: #ffffff"],
div[style*="background-color:#ffffff"],
div[style*="background: rgb(255, 255, 255)"],
div[style*="background: #ffffff"],
div[style*="background:#ffffff"] {
  color:#0f172a !important;
}
div[style*="background-color: rgb(255, 255, 255)"] *,
div[style*="background-color:#ffffff"] *,
div[style*="background: rgb(255, 255, 255)"] *,
div[style*="background:#ffffff"] * {
  color:#0f172a !important;
  -webkit-text-fill-color:#0f172a !important;
}

/* High contrast for all widget labels */
label,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
div[data-testid="stCheckbox"] label span {
  color:var(--fg) !important;
  font-weight:700 !important;
  font-size:12.5px !important;
}

/* Exercise card internal layout */
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
  font-weight:800; font-size:13.5px; line-height:1.25; color:var(--fg) !important;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
  overflow:hidden; min-height:2.5em;
}
.excard-meta{
  display:flex; align-items:center; gap:8px; margin:3px 0 5px;
}

/* Section divider separating workout cards from bottom utilities */
.section-divider{
  display:flex; align-items:center; gap:14px; margin:20px 0 12px;
  color:var(--faint); font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:.09em;
}
.section-divider::before, .section-divider::after{
  content:""; flex:1; height:1px; background:var(--line);
}

.exgrid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:11px; margin-top:2px; }
.exrow{ display:flex; align-items:center; gap:13px; background:var(--surface); border:1px solid var(--line);
  border-radius:20px; padding:14px 16px; box-shadow:var(--shadow); color:var(--fg); }

.fcard{ background:var(--surface); border:1px solid var(--line); border-radius:20px; padding:16px; margin-bottom:12px; box-shadow:var(--shadow); color:var(--fg); }
.eyebrow{ font-size:10.5px; text-transform:uppercase; letter-spacing:.11em; color:var(--faint) !important; font-weight:800; margin:0 0 10px; }
.muted{ color:var(--muted) !important; }
.rings{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:10px; }

.counter{ display:flex; align-items:center; gap:18px; background:
  radial-gradient(120% 140% at 0% 0%, color-mix(in srgb,var(--blue) 26%,transparent), transparent 58%),
  linear-gradient(160deg, var(--surface), var(--surface-2)); border:1px solid color-mix(in srgb,var(--blue) 35%,var(--line));
  border-radius:22px; padding:16px 20px; margin-bottom:12px; flex-wrap:wrap; box-shadow:var(--shadow); color:var(--fg); }
.counter .big{ font-family:"Nunito"; font-weight:900; font-size:34px; line-height:.9; color:var(--fg) !important; }
.counter .big small{ font-size:13px; color:var(--muted) !important; font-weight:800; }
.counter .lbl{ font-size:11px; color:var(--muted) !important; font-weight:700; text-transform:uppercase; letter-spacing:.08em; margin-top:4px; }
.weekdots{ display:flex; gap:7px; margin-top:7px; }
.weekdots i{ width:11px; height:11px; border-radius:50%; background:var(--surface-2); border:1px solid var(--line); }
.weekdots i.on{ background:var(--green); border-color:var(--green); }

.ringcard{ background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:12px 3px 10px; text-align:center; box-shadow:var(--shadow); color:var(--fg); }
.ringcard .v{ font-family:"Nunito"; font-weight:800; font-size:13px; margin-top:6px; line-height:1; color:var(--fg) !important; }
.ringcard .v small{ color:var(--muted) !important; font-weight:700; font-size:.82em; }
.ringcard .k{ font-size:10.5px; color:var(--muted) !important; font-weight:600; margin-top:4px; }

.hero{ border-radius:24px; padding:18px; margin-bottom:10px; position:relative; overflow:hidden; box-shadow:var(--shadow); color:var(--fg); }
.hero .kick{ font-size:10.5px; font-weight:800; text-transform:uppercase; letter-spacing:.1em; }
.hero h2{ font-size:20px; font-weight:900; margin:6px 0 4px; color:var(--fg) !important; }
.chiprow{ display:flex; flex-wrap:wrap; gap:6px; margin:6px 0 2px; }
.chip{ font-size:10.5px; font-weight:700; padding:3px 8px; border-radius:999px; background:var(--surface-2); color:var(--muted); border:1px solid var(--line); }

.tiles{ display:grid; grid-template-columns:repeat(auto-fit,minmax(148px,1fr)); gap:11px; margin-bottom:12px; }
.tile{ background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:14px; box-shadow:var(--shadow); color:var(--fg); }
.tile .k{ font-size:10.5px; color:var(--muted) !important; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
.tile .v{ font-family:"Nunito"; font-weight:900; font-size:21px; margin-top:6px; line-height:1; color:var(--fg) !important; }
.tile .v small{ font-size:12.5px; color:var(--muted) !important; font-weight:800; }
.tile .d{ font-size:11px; font-weight:700; margin-top:5px; color:var(--muted); }
.good{ color:var(--green)!important; } .bad{ color:var(--red)!important; }

.legend{ display:flex; gap:6px; align-items:center; justify-content:center; margin-top:8px; font-size:10.5px; color:var(--muted); font-weight:600; }
.legend i{ width:14px; height:9px; border-radius:3px; display:inline-block; }
.bars{ display:flex; flex-direction:column; gap:13px; }
.bar .bhead{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:5px; }
.bar .bl{ font-weight:700; color:var(--fg); } .bar.primary .bl{ font-size:1.06em; }
.bar .bv{ color:var(--muted); font-weight:600; font-size:12px; }
.btrack{ height:8px; border-radius:6px; background:var(--surface-2); overflow:hidden; }
.bar.primary .btrack{ height:11px; }
.bfill{ height:100%; border-radius:6px; }

/* GitHub-style Contribution Heatmap - fluid, responsive, fits page without scrollbar */
.gh-card{ background:var(--surface); border:1px solid var(--line); border-radius:18px; padding:14px 16px; margin-bottom:12px; box-shadow:var(--shadow); color:var(--fg); }
.gh-top{ display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:10px; margin-bottom:10px; }
.gh-title{ font-family:"Nunito",sans-serif; font-weight:800; font-size:14px; color:var(--fg); }
.gh-pills{ display:flex; gap:8px; flex-wrap:wrap; font-size:11px; font-weight:700; color:var(--fg); }
.gh-pill{ background:var(--surface-2); border:1px solid var(--line); padding:3px 10px; border-radius:999px; display:inline-flex; align-items:center; gap:6px; }
.gh-dot{ width:8px; height:8px; border-radius:50%; display:inline-block; }
.gh-scroll{ overflow-x:auto; overflow-y:hidden; width:100%; padding:2px 2px 4px; scrollbar-width:none; -ms-overflow-style:none; }
.gh-scroll::-webkit-scrollbar{ display:none; }
.gh-board{ width:100%; min-width:0; }
.gh-months{ display:grid; gap:2px; margin-left:27px; margin-bottom:5px; font-size:10px; color:var(--muted); font-weight:700; line-height:1; }
.gh-months span{ white-space:nowrap; overflow:visible; }
.gh-body{ display:flex; align-items:stretch; gap:5px; }
.gh-days{ display:grid; grid-template-rows:repeat(7,1fr); gap:2px; width:22px; font-size:9.5px; color:var(--muted); font-weight:600; text-align:left; }
.gh-days span{ display:flex; align-items:center; line-height:1; }
.gh-weeks{ flex:1; display:grid; grid-template-rows:repeat(7,1fr); grid-auto-flow:column; gap:2px; padding:2px; }
.gh-cell{ aspect-ratio:1/1; min-width:0; width:100%; border-radius:2.5px; background:var(--gh-0); outline:1px solid rgba(128,128,128,.10); transition:transform .1s ease; box-sizing:border-box; }
.gh-cell:hover{ transform:scale(1.22); z-index:2; outline:1px solid var(--fg); }
.gh-cell.l1{ background:var(--gh-1); }
.gh-cell.l2{ background:var(--gh-2); }
.gh-cell.l3{ background:var(--gh-3); }
.gh-cell.l4{ background:var(--gh-4); }
.gh-cell.today{ outline:2px solid var(--blue); outline-offset:0px; box-shadow:0 0 0 1px var(--blue); }
.gh-cell.future{ opacity:.30; }
.gh-foot{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-top:10px; padding-top:8px; border-top:1px solid var(--line); font-size:11px; color:var(--muted); }
.gh-scale{ display:flex; align-items:center; gap:4px; font-size:10.5px; color:var(--muted); font-weight:600; }
.gh-scale i{ width:11px; height:11px; border-radius:2.5px; display:inline-block; outline:1px solid rgba(128,128,128,.12); }

/* Weekly, Monthly & Calendar Strips */
.wk-strip{ display:grid; grid-template-columns:repeat(7,1fr); gap:8px; margin-top:10px; }
.wk-day{
  background:var(--surface-2) !important;
  border:1.5px solid var(--line) !important;
  border-radius:16px !important;
  padding:12px 6px !important;
  text-align:center !important;
  color:var(--fg) !important;
  box-shadow:var(--shadow) !important;
  transition:all .15s ease !important;
}
.wk-day.today{
  border-color:var(--blue) !important;
  box-shadow:0 0 0 1.5px var(--blue), var(--shadow) !important;
}
.wk-day.done{
  background:color-mix(in srgb,var(--green) 18%,var(--surface-2)) !important;
  border-color:var(--green) !important;
}

.mo-grid{ display:grid; grid-template-columns:repeat(7,1fr); gap:6px; margin-top:10px; }
.mo-cell{
  background:var(--surface-2) !important;
  border:1.5px solid var(--line) !important;
  border-radius:14px !important;
  padding:10px 8px !important;
  text-align:center !important;
  font-size:11.5px !important;
  color:var(--fg) !important;
  transition:all .15s ease !important;
}
.mo-cell.today{
  border-color:var(--blue) !important;
  box-shadow:0 0 0 1.5px var(--blue) !important;
}
.mo-cell.done{
  background:color-mix(in srgb,var(--green) 18%,var(--surface-2)) !important;
  border-color:var(--green) !important;
}

/* Streamlit Button & Expander Contrast */
.stButton>button{
  border-radius:13px !important; font-weight:700 !important;
  border:1.5px solid var(--line) !important;
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

/* Sleek, modern, compact workout card buttons & strict vertical alignment */
div[data-testid="column"]:has(.wo-step-box) {
  display: flex !important;
  flex-direction: column !important;
}

div[data-testid="column"] > div[data-testid="stVerticalBlock"]:has(.wo-step-box) {
  height: 100% !important;
  display: flex !important;
  flex-direction: column !important;
  flex: 1 1 auto !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.wo-step-box) {
  padding: 14px 16px !important;
  margin-bottom: 12px !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: space-between !important;
  min-height: 172px !important;
  height: 100% !important;
  flex: 1 1 auto !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.wo-step-box) > div[data-testid="stVerticalBlock"] {
  display: flex !important;
  flex-direction: column !important;
  justify-content: space-between !important;
  height: 100% !important;
  flex: 1 1 auto !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.wo-done-marker) {
  border-color: color-mix(in srgb, var(--green) 45%, var(--line)) !important;
  background: radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,var(--green) 12%,transparent), transparent 60%), var(--surface) !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.wo-step-box) .stButton > button {
  min-height: 32px !important;
  height: 32px !important;
  padding: 2px 10px !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  border-radius: 10px !important;
  border: 1px solid var(--line) !important;
  background: var(--surface-2) !important;
  color: var(--fg) !important;
  letter-spacing: .01em !important;
  transition: all .15s ease !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.wo-step-box) .stButton > button:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--blue) 55%, var(--line)) !important;
  background: var(--surface-elevated) !important;
  color: #ffffff !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.wo-done-marker) .stButton:first-child > button {
  background: color-mix(in srgb, var(--green) 14%, var(--surface-2)) !important;
  border-color: color-mix(in srgb, var(--green) 40%, var(--line)) !important;
  color: var(--green) !important;
  font-weight: 800 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.wo-done-marker) .stButton:first-child > button:hover {
  background: color-mix(in srgb, var(--green) 22%, var(--surface-2)) !important;
  border-color: var(--green) !important;
  color: #ffffff !important;
}
/* FIX: Expander — header summary must NEVER turn white in Dark Mode! */
[data-testid="stExpander"]{
  border-radius:16px !important;
  border:1.5px solid var(--line) !important;
  background:var(--surface) !important;
  color:var(--fg) !important;
  overflow:hidden !important;
  box-shadow:var(--shadow) !important;
  margin-bottom:12px !important;
}
[data-testid="stExpander"] details{
  background:var(--surface) !important;
}
[data-testid="stExpander"] summary{
  background:var(--surface-2) !important;
  background-color:var(--surface-2) !important;
  color:var(--fg) !important;
  padding:12px 16px !important;
  border:none !important;
  transition:background .15s ease !important;
}
[data-testid="stExpander"] summary:hover,
[data-testid="stExpander"] summary:focus,
[data-testid="stExpander"] summary:active,
[data-testid="stExpander"][open] summary{
  background:var(--surface-elevated) !important;
  background-color:var(--surface-elevated) !important;
  color:var(--fg) !important;
}
[data-testid="stExpander"] summary *,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary div{
  color:var(--fg) !important;
  font-weight:700 !important;
}
[data-testid="stExpanderDetails"]{
  background:var(--surface) !important;
  border-top:1px solid var(--line) !important;
  padding:16px !important;
  color:var(--fg) !important;
}

/* File uploader styling */
[data-testid="stFileUploader"] section {
  background:var(--surface) !important;
  border:1.5px dashed var(--line) !important;
  border-radius:14px !important;
  color:var(--fg) !important;
  padding:10px 14px !important;
}
[data-testid="stFileUploader"] button {
  background:var(--surface-2) !important;
  color:var(--fg) !important;
  border:1px solid var(--line) !important;
  font-size:12px !important;
  padding:4px 12px !important;
  border-radius:8px !important;
}
[data-testid="stFileUploader"] small {
  font-size:11px !important;
  color:var(--muted) !important;
}

/* Captions and explanatory text — bright, readable silver, NOT faint dark grey */
[data-testid="stCaptionContainer"],
.stCaption,
.stCaption p,
.stCaption span,
.stCaption div {
  color:var(--muted) !important;
  font-weight:600 !important;
  font-size:11.5px !important;
  line-height:1.4 !important;
}

/* Alert boxes (st.info, st.success, st.warning) - compact, ergonomic card style */
[data-testid="stAlert"] {
  background:var(--surface-2) !important;
  border:1px solid var(--line) !important;
  border-radius:12px !important;
  color:var(--fg) !important;
  padding:8px 14px !important;
  font-size:12px !important;
  line-height:1.4 !important;
  margin-bottom:8px !important;
}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p,
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] span,
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] div,
[data-testid="stAlert"] * {
  color:var(--fg) !important;
  font-size:12px !important;
  line-height:1.4 !important;
}
[data-testid="stAlert"] svg {
  width:16px !important;
  height:16px !important;
}

/* Buttons */
.stButton button,
div[data-testid="stButton"] button {
  font-size:12.5px !important;
  font-weight:700 !important;
  padding:6px 14px !important;
  border-radius:10px !important;
}
hr{ border-color:var(--line); }
</style>
"""


DARK_ROOT_CSS = """
:root {
  --bg:#0b0f19 !important; --surface:#151d2d !important; --surface-2:#1e293b !important; --surface-elevated:#27354d !important;
  --line:#2e3d5b !important; --line-strong:#475569 !important;
  --fg:#ffffff !important; --muted:#cbd5e1 !important; --faint:#94a3b8 !important;
  --blue:#3898ff !important; --purple:#c084fc !important; --orange:#fb923c !important; --green:#34d399 !important; --teal:#22d3ee !important; --red:#f87171 !important;
  --track:#242c3e !important; --map1:#1e40af !important; --map2:#2563eb !important; --map3:#3898ff !important;
  --shadow:0 6px 22px rgba(0,0,0,.60) !important;
  --gh-0:#1e293b !important; --gh-1:#0e4429 !important; --gh-2:#006d32 !important; --gh-3:#26a641 !important; --gh-4:#39d353 !important;
  --seg-bg:#1e293b !important; --seg-btn:transparent !important; --seg-btn-hover:#27354d !important; --seg-active:#3898ff !important;
  --input-bg:#151d2d !important; --input-fg:#ffffff !important;
}
""".strip()

LIGHT_ROOT_CSS = """
:root {
  --bg:#f4f6fb !important; --surface:#ffffff !important; --surface-2:#eef2f8 !important; --surface-elevated:#f8fafc !important;
  --line:#cbd5e1 !important; --line-strong:#94a3b8 !important;
  --fg:#0f172a !important; --muted:#334155 !important; --faint:#64748b !important;
  --blue:#0a7aff !important; --purple:#9333ea !important; --orange:#ea580c !important; --green:#16a34a !important; --teal:#0891b2 !important; --red:#dc2626 !important;
  --track:#e2e8f0 !important; --map1:#bfdbfe !important; --map2:#60a5fa !important; --map3:#0a7aff !important;
  --shadow:0 2px 12px rgba(15,23,42,.08) !important;
  --gh-0:#ebedf0 !important; --gh-1:#9be9a8 !important; --gh-2:#40c463 !important; --gh-3:#30a14e !important; --gh-4:#216e39 !important;
  --seg-bg:#eef2f8 !important; --seg-btn:transparent !important; --seg-btn-hover:#e2e8f0 !important; --seg-active:#0a7aff !important;
  --input-bg:#ffffff !important; --input-fg:#0f172a !important;
}
""".strip()


def inject(theme: str | None = None):
    """Inject CSS with explicit theme enforcement.
    Uses st.html (or unindented clean CSS) so the browser natively parses the stylesheet
    without CommonMark ever rendering raw <style> text as a code block.
    """
    override = ""
    if theme == "dark":
        override = DARK_ROOT_CSS
    elif theme == "light":
        override = LIGHT_ROOT_CSS

    full_css = CSS
    if override:
        if "</style>" in full_css:
            full_css = full_css.replace("</style>", f"\n{override}\n</style>")
        else:
            full_css = f"<style>\n{override}\n</style>\n" + full_css

    if hasattr(st, "html"):
        st.html(full_css)
    else:
        st.markdown(full_css, unsafe_allow_html=True)


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


def page_header(title: str, subtitle: str = "", badge: str = "") -> str:
    """Standardized page header used uniformly across all 5 dashboard tabs."""
    badge_html = f'<span class="chip" style="font-size:10.5px;color:var(--teal);margin-inline-start:8px">{badge}</span>' if badge else ""
    sub_html = f'<div class="muted" style="font-size:12.5px;margin-top:2px">{subtitle}</div>' if subtitle else ""
    return (
        f'<div style="margin-bottom:12px">'
        f'<div style="display:flex;align-items:center"><h1 style="margin:0 0 2px;font-size:23px">{title}</h1>{badge_html}</div>'
        f'{sub_html}</div>'
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
        f'<div style="padding:10px 0;border-top:1px solid var(--line);color:var(--fg)">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">'
        f'<span style="font-weight:700;font-size:13px;color:var(--fg)">{label}</span>'
        f'<span style="font-family:Nunito;font-weight:800;font-size:14.5px;color:var(--fg)">{value}</span></div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:3px">'
        f'<span class="muted" style="font-size:11.5px">{note}</span>'
        f'<span style="font-size:11px;font-weight:700;color:{dot};white-space:nowrap">'
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
    start_date: dt.date | None = None,
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
            is_pre = (start_date is not None) and (cur < start_date)
            if not is_future and not is_pre and lvl > 0:
                active_days += 1
                if iso.startswith(month_iso_prefix):
                    this_month_active += 1
            if not is_future and not is_pre:
                if rec.get("strength"):
                    str_cnt += 1
                if rec.get("padel"):
                    pad_cnt += 1
                if rec.get("cardio"):
                    crd_cnt += 1
                if rec.get("protein_ok"):
                    prot_cnt += 1

            cls = f"gh-cell l{lvl}" if (lvl > 0 and not is_future and not is_pre) else "gh-cell"
            if cur == today:
                cls += " today"
            elif is_future:
                cls += " future"

            date_lbl = f"{cur.day} {MON_TR[cur.month - 1]} {cur.year} ({DOW_TR[d_idx]})"
            if is_pre:
                detail = f"Resmi başlangıç öncesi ({start_date.day} {MON_TR[start_date.month - 1]} baz)"
            elif is_future:
                detail = "Gelecek gün"
            else:
                detail = rec.get("summary") or "Kayıt yok"
            tip = f"{date_lbl} — {detail}".replace('"', "&quot;")
            cells.append(f'<div class="{cls}" title="{tip}"></div>')

    months_html = (
        f'<div class="gh-months" style="grid-template-columns:repeat({weeks},minmax(0,1fr))">'
        + "".join(month_spans)
        + "</div>"
    )
    days_html = (
        '<div class="gh-days">'
        '<span>Pzt</span><span></span><span>Çar</span><span></span><span>Cum</span><span></span><span></span>'
        '</div>'
    )
    weeks_html = (
        f'<div class="gh-weeks" style="grid-template-columns:repeat({weeks},minmax(0,1fr))">'
        + "".join(cells)
        + "</div>"
    )

    return (
        '<div class="gh-card">'
        '<div class="gh-top">'
        f'<div class="gh-title">{active_days} aktif gün <span style="color:var(--muted);font-weight:600;font-size:12.5px">· son 1 yılda (bu ay {this_month_active} gün)</span></div>'
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
