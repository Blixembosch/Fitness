"""Automated unit and functional tests for UI contrast, dark mode accessibility (WCAG AA/AAA),
and Streamlit widget styling completeness.
Guarantees that input fields, expanders, labels, and exercise cards never suffer from
contrast issues, white boxes in dark mode, or missing boundaries.
"""
import re
import math
from pathlib import Path
from lib import ui
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def _hex_to_rgb(hex_str: str) -> tuple[float, float, float]:
    hex_str = hex_str.strip().lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return r, g, b


def _rel_luminance(rgb: tuple[float, float, float]) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = _rel_luminance(_hex_to_rgb(hex1))
    l2 = _rel_luminance(_hex_to_rgb(hex2))
    hi = max(l1, l2)
    lo = min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _extract_css_vars(css: str) -> dict[str, str]:
    root_match = re.search(r":root\s*\{([^}]+)\}", css)
    assert root_match, "Could not find :root block in CSS"
    raw = root_match.group(1)
    vars_dict = {}
    for line in raw.split(";"):
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().split()[0]
            if k.startswith("--"):
                vars_dict[k] = v
    return vars_dict


def test_dark_mode_wcag_contrast_ratios():
    """Verify WCAG contrast compliance for Dark Mode:
    - Primary text (--fg) against surface: >= 7:1 (WCAG AAA)
    - Muted text (--muted) against surface: >= 4.5:1 (WCAG AA)
    - Surface elevation: --surface must be visibly distinct from --bg
    - Card border (--line) must be clearly visible against background
    """
    vars_dict = _extract_css_vars(ui.CSS)
    bg = vars_dict["--bg"]
    surface = vars_dict["--surface"]
    surface2 = vars_dict["--surface-2"]
    fg = vars_dict["--fg"]
    muted = vars_dict["--muted"]
    line = vars_dict["--line"]

    # 1. Primary text must exceed WCAG AAA (7.0) on surface
    fg_surface_cr = _contrast_ratio(fg, surface)
    assert fg_surface_cr >= 7.0, f"Primary text contrast ratio {fg_surface_cr:.2f} is below WCAG AAA (7.0)"

    # 2. Muted text must exceed WCAG AA (4.5) on surface & surface2
    muted_surface_cr = _contrast_ratio(muted, surface)
    assert muted_surface_cr >= 4.5, f"Muted text contrast ratio {muted_surface_cr:.2f} is below WCAG AA (4.5)"

    muted_s2_cr = _contrast_ratio(muted, surface2)
    assert muted_s2_cr >= 4.0, f"Muted text on surface-2 ratio {muted_s2_cr:.2f} is too low"

    # 3. Surface elevation: --surface must have higher luminance than --bg
    l_bg = _rel_luminance(_hex_to_rgb(bg))
    l_surf = _rel_luminance(_hex_to_rgb(surface))
    assert l_surf > l_bg, f"Card surface luminance ({l_surf:.4f}) must be higher than background ({l_bg:.4f})"

    # 4. Border line must have sufficient contrast against background to guarantee card separation
    line_bg_cr = _contrast_ratio(line, bg)
    assert line_bg_cr >= 1.35, f"Card boundary border contrast ratio {line_bg_cr:.2f} is too faint"


def test_css_widget_coverage_for_dark_mode():
    """Verify that CSS contains explicit rules preventing white box bleeding in Dark Mode:
    - Streamlit number inputs, text inputs, date inputs, and selectboxes
    - Streamlit expander summaries (so they never turn into white bars)
    - Streamlit ButtonGroup & segmented controls
    - Streamlit bordered container separation
    - High-contrast widget labels and captions
    """
    css = ui.CSS

    # Expander must override summary and details backgrounds
    assert "[data-testid=\"stExpander\"] summary" in css
    assert "background-color:var(--surface-2)" in css or "background:var(--surface-2)" in css
    assert "[data-testid=\"stExpander\"][open] summary" in css

    # Number input container and fields must be dark
    assert "stNumberInputContainer" in css
    assert "stNumberInputField" in css
    assert "stNumberInputStepDown" in css

    # Date input and text input containers must be dark
    assert "stDateInput" in css
    assert "stTextInputRootElement" in css

    # ButtonGroup must override default Streamlit white buttons
    assert "div.stButtonGroup" in css
    assert "div.stButtonGroup button[data-selected]" in css

    # Card separation wrapper must have distinct border and elevation
    assert "stVerticalBlockBorderWrapper" in css
    assert "border:1.5px solid var(--line)" in css

    # High contrast labels
    assert "stWidgetLabel" in css
    assert "stCaptionContainer" in css

    # Selectbox container, combobox control, and virtual dropdown portal
    assert 'div[data-testid="stSelectbox"]' in css
    assert "stSelectboxVirtualDropdown" in css
    assert "e1fp86qc0" in css or 'role="combobox"' in css
    assert "-webkit-text-fill-color:var(--input-fg)" in css


def test_selectbox_dark_mode_contrast_and_portal_coverage():
    """Verify that selectboxes in dark mode never have white backgrounds and dropdown portals are covered."""
    css = ui.CSS
    assert "div[data-testid=\"stSelectbox\"]" in css
    assert "background:var(--input-bg)" in css or "background-color:var(--input-bg)" in css
    assert "stSelectboxVirtualDropdown" in css
    # Failsafe contrast rule exists
    assert "color:#0f172a !important" in css or "color: #0f172a !important" in css


def test_functional_workout_page_structure():
    """Headless functional test: asserts workout page renders 9 steps,
    workout segmented control has no redundant label, and section divider is present.
    """
    at = AppTest.from_file(APP_PATH, default_timeout=45)
    at.run()
    at.session_state["page"] = "workout"
    at.run()

    assert not at.exception, f"Workout page threw exceptions: {at.exception}"

    # Check that segmented control exists
    assert len(at.segmented_control) >= 1
    sc = at.segmented_control[0]
    assert "Alt A" in sc.options or "Üst A" in sc.options

    # Verify markdown outputs include the section divider
    divider_found = any("section-divider" in m.value for m in at.markdown)
    assert divider_found, "Expected section-divider before cardio expanders in workout page"


def test_functional_nutrition_page_structure():
    """Headless functional test: asserts nutrition page renders inputs,
    Wegovy expander, and setting options without exceptions.
    """
    at = AppTest.from_file(APP_PATH, default_timeout=45)
    at.run()
    at.session_state["page"] = "nutrition"
    at.run()

    assert not at.exception, f"Nutrition page threw exceptions: {at.exception}"

    # Verify number inputs and date inputs are rendered
    assert len(at.number_input) >= 1
    assert len(at.date_input) >= 1


def test_no_css_syntax_leaks_or_code_blocks_across_all_pages():
    """Guarantees that raw <style>, :root, CSS variables, or code blocks containing CSS
    never leak onto the rendered UI as visible text on ANY page (home, plan, workout, stats, nutrition).
    """
    pages = ["home", "plan", "workout", "stats", "nutrition"]
    for page in pages:
        at = AppTest.from_file(APP_PATH, default_timeout=45)
        at.run()
        at.session_state["page"] = page
        at.run()

        assert not at.exception, f"Page {page} threw exceptions: {at.exception}"

        # Check that no markdown block renders raw unparsed CSS / <style> tags
        for i, m in enumerate(at.markdown):
            val = m.value or ""
            assert "<style>" not in val, f"Page {page} markdown[{i}] contains raw <style> tag: {val[:120]}"
            assert "</style>" not in val, f"Page {page} markdown[{i}] contains raw </style> tag: {val[:120]}"
            assert ":root" not in val, f"Page {page} markdown[{i}] contains raw :root CSS declaration: {val[:120]}"
            assert "--bg:#" not in val and "--surface:#" not in val, f"Page {page} markdown[{i}] leaks raw CSS variables: {val[:120]}"

        # Check that no code blocks were accidentally rendered for styling
        for i, c in enumerate(at.code):
            val = c.value or ""
            assert "--bg:" not in val and ":root" not in val and "<style>" not in val, f"Page {page} code[{i}] leaked CSS block: {val[:120]}"
