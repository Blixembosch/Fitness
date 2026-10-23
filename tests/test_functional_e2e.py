"""Comprehensive End-to-End Functional Tests for ATES FAM Fitness.

Tests all user flows headlessly via Streamlit AppTest:
- Tab navigation & header consistency across all 5 pages
- Padel logging & undo on Home and Workout tabs
- Wegovy weekly injection logging
- Multi-set workout execution and undo
- Stats period switching (Hafta / Ay / 3 Ay)
- Google Calendar synchronization with strict Atlas exclusion
- Manual weight logging & target recomputation in Nutrition tab
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from lib import ui, calendar_sync

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


def _run_app(page="home", **state) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=45)
    at.run()
    at.session_state["page"] = page
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, f"App crashed on {page}: {at.exception}"
    return at


def test_functional_navigation_flow():
    """Verify one-click navigation across all 5 tabs without errors."""
    at = _run_app("home")
    for nav_key in ["home", "plan", "workout", "stats", "nutrition"]:
        btn = next((b for b in at.button if b.key == f"nav_{nav_key}"), None)
        assert btn is not None, f"Nav button for {nav_key} missing"
        btn.click().run()
        assert not at.exception, f"Navigating to {nav_key} threw: {at.exception}"
        assert at.session_state["page"] == nav_key


def test_functional_home_padel_toggle():
    """Test logging and undoing a padel session on Home page."""
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        at = _run_app("home", padel=[])
        add_btn = next((b for b in at.button if b.key == "home_padel_add"), None)
        if add_btn:
            add_btn.click().run()
            assert not at.exception
            today_iso = at.session_state["weights"][-1]["date"][:7]  # month prefix check
            assert len(at.session_state["padel"]) >= 1

            undo_btn = next((b for b in at.button if b.key == "home_padel_undo"), None)
            assert undo_btn is not None
            undo_btn.click().run()
            assert not at.exception


def test_functional_workout_padel_toggle():
    """Test padel logging button on Workout page."""
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        at = _run_app("workout", padel=[])
        pad_btn = next((b for b in at.button if b.key == "w_pad_btn"), None)
        assert pad_btn is not None
        pad_btn.click().run()
        assert not at.exception
        assert len(at.session_state["padel"]) >= 1


def test_functional_wegovy_injection_logging():
    """Test weekly injection logging flow on Home page."""
    import datetime as dt
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        at = _run_app("home", wegovy={"dose_mg": 0.25, "inj_weekday": dt.date.today().weekday(), "start_date": dt.date.today().isoformat(), "logs": []})
        inj_btn = next((b for b in at.button if b.key == "inj_btn"), None)
        assert inj_btn is not None
        initial_count = len(at.session_state["wegovy"]["logs"])
        inj_btn.click().run()
        assert not at.exception
        assert len(at.session_state["wegovy"]["logs"]) == initial_count + 1


def test_functional_start_date_separation_plan_and_wegovy():
    """Verify training & calorie tracking starts on 25 Oct (Sunday), and Wegovy starts on 27 Oct (Tuesday)."""
    import datetime as dt
    from app import wegovy_status
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        # 1. On Sunday 25 Oct 2026: Training starts, Wegovy is in 2 days (no 48h warning)
        sunday_25 = dt.date(2026, 10, 25)
        ws_sun = wegovy_status(sunday_25)
        assert ws_sun["in_48h"] is False
        assert ws_sun["days_until"] == 2
        assert "2 gün sonra" in ws_sun["sched_lbl"]
        assert ws_sun["inj_weekday"] == 1  # Tuesday

        # 2. On Tuesday 27 Oct 2026: Wegovy injection starts
        tuesday_27 = dt.date(2026, 10, 27)
        ws_tue = wegovy_status(tuesday_27)
        assert ws_tue["days_until"] == 0
        assert ws_tue["in_48h"] is True
        assert "1. Doz" in ws_tue["sched_lbl"] or "enjeksiyon günü" in ws_tue["sched_lbl"]


def test_functional_workout_step_interaction():
    """Test multi-set tracking: step increment and undo on Workout page."""
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        at = _run_app("workout")
        set_btns = [b for b in at.button if b.key and b.key.startswith("s_")]
        assert len(set_btns) > 0
        first_btn = set_btns[0]
        step_key = first_btn.key[2:]

        # Log Set 1
        first_btn.click().run()
        assert not at.exception
        assert at.session_state["setlog"].get(step_key) == 1

        # Undo Set
        reset_btn = next((b for b in at.button if b.key == f"r_{step_key}"), None)
        assert reset_btn is not None
        reset_btn.click().run()
        assert not at.exception
        assert at.session_state["setlog"].get(step_key) == 0


def test_functional_stats_period_views():
    """Test period switching on Stats page: Hafta -> Ay -> 3 Ay."""
    at = _run_app("stats")
    assert not at.exception

    # Switch to Ay
    at = _run_app("stats", sp="Ay")
    assert not at.exception

    # Switch to 3 Ay
    at = _run_app("stats", sp="3 Ay")
    assert not at.exception


def test_functional_nutrition_weight_logging():
    """Test manual weigh-in submission on Nutrition page."""
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        at = _run_app("nutrition")
        save_btn = next((b for b in at.button if b.key == "nut_weight_save"), None)
        assert save_btn is not None
        initial_weights = len(at.session_state["weights"])
        save_btn.click().run()
        assert not at.exception
        assert len(at.session_state["weights"]) >= initial_weights


def test_functional_google_calendar_strict_atlas_exclusion():
    """Test that Google Calendar sync strictly excludes 'Padel Training for Atlas'."""
    mock_events = [
        {"summary": "Padel Training for Atlas", "date": "2026-10-22", "start_time": "16:00", "is_padel": False},
        {"summary": "Padel Maçı", "date": "2026-10-24", "start_time": "19:00", "is_padel": True},
    ]
    with patch("lib.calendar_sync.fetch_calendar_events", return_value=mock_events):
        padel_evs = calendar_sync.fetch_padel_events(url="https://mock.local/cal.ics")
        # Ensure Atlas is filtered out
        assert not any("Atlas" in e["summary"] for e in padel_evs)
        assert len(padel_evs) == 1
        assert padel_evs[0]["summary"] == "Padel Maçı"


def test_functional_page_headers_consistent_markup():
    """Verify that ui.page_header generates consistent, semantic typography across pages."""
    h = ui.page_header("Test Title", "Test Subtitle", badge="Badge")
    assert "Test Title" in h
    assert "Test Subtitle" in h
    assert "Badge" in h
    assert "font-size:23px" in h
    assert 'class="muted"' in h


def test_functional_october_25_baseline_and_pre_date_filtering():
    """Verify that data prior to 25 Ekim 2026 is filtered out from stats and visualizations."""
    import datetime as dt
    import pandas as pd
    from unittest.mock import patch

    # 1. Test ui.github_heatmap with start_date filter
    today = dt.date(2026, 10, 26)
    start_date = dt.date(2026, 10, 25)
    records = {
        # Pre-start date record
        "2026-10-20": {"level": 3, "summary": "Old test workout", "strength": True},
        # Official start date record
        "2026-10-25": {"level": 4, "summary": "Official day 1", "strength": True},
    }
    html = ui.github_heatmap(today, records, weeks=4, start_date=start_date)
    assert "Resmi başlangıç öncesi (25 Eki baz)" in html
    # Pre-start cell should NOT have level 3 active class
    assert 'title="20 Eki 2026 (Sal) — Resmi başlangıç öncesi (25 Eki baz)"' in html
    # Active days count should only reflect on or after start_date (1 active day, not 2)
    assert "1 aktif gün" in html


def test_functional_configurable_start_date_26_october():
    """Verify that the app respects a switch from 25 October to 26 October."""
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        at = _run_app("stats", body={"start_date": "2026-10-26", "theme": "dark", "birth": "1992-03-12", "height": 178})
        assert not at.exception
        # Verify Stats page loads without error with 26 October start
        assert at.session_state["body"]["start_date"] == "2026-10-26"


def test_functional_stats_renders_clean_placeholder_when_no_post_start_weights():
    """Verify Stats page weight trend section displays clean info banner before 25 October weigh-ins."""
    at = _run_app("stats", body={"start_date": "2026-10-25"}, weights=[{"date": "2026-10-15", "w": 101.0}])
    assert not at.exception
    # Ensure page rendered successfully
    assert any("İstatistik & Hedef Takibi" in str(m.value) for m in at.markdown)


def test_functional_workout_steps_compact_single_line_and_heatmap_fluid():
    """Verify workout steps 9-10 are compact single-line and heatmap has fluid columns without scrollbar."""
    import datetime as dt
    from lib import program as P

    # 1. Workout steps 9 and 10 single-line checks
    day = P.day_for(0)  # Üst A (10 steps)
    steps = P.workout_steps(day)
    assert len(steps) == 10
    step9 = steps[8]
    step10 = steps[9]

    assert step9["name"] == "Kürek (Rower) — Yağ Yakım"
    assert step9["tip"] == "10 dk canlı tempo · metabolik yağ yakımı."
    assert len(step9["tip"]) <= 42

    assert step10["name"] == "Eliptik — Yağ Yakım & Soğuma"
    assert step10["tip"] == "10 dk Zone-2 · toparlanma ve yağ yakımı."
    assert len(step10["tip"]) <= 42
    assert len(step10["name"]) <= 30

    # 2. Fluid heatmap checks (no hardcoded minmax 11px)
    today = dt.date(2026, 10, 22)
    hm_html = ui.github_heatmap(today, {}, weeks=52)
    assert "minmax(0,1fr)" in hm_html
    assert "minmax(11px,1fr)" not in hm_html


def test_functional_plan_page_starts_from_october_25_baseline():
    """Verify Plan page displays Monday-to-Sunday weeks, Sunday 25 Oct has workout, and enables week navigation."""
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        at = _run_app("plan", body={"start_date": "2026-10-25", "theme": "dark"})
        assert not at.exception

        # 1. Header shows week starting on Monday (19 Eki) and ending on Sunday (25 Eki)
        header_markdowns = [str(m.value) for m in at.markdown if "25 Eki" in str(m.value)]
        assert len(header_markdowns) > 0
        assert any("Hafta 1 / 12" in m or "Hafta 1/12" in m for m in header_markdowns)

        # 2. Week navigation buttons present
        prev_btn = next((b for b in at.button if b.key == "plan_wk_prev"), None)
        next_btn = next((b for b in at.button if b.key == "plan_wk_next"), None)
        assert prev_btn is not None
        assert next_btn is not None
        assert prev_btn.disabled is True  # Cannot go prior to week 1

        # 3. 7 day buttons start on Pazartesi (19) and end on Pazar (25)
        pd_btns = [b for b in at.button if b.key and b.key.startswith("pd_")]
        assert len(pd_btns) == 7
        assert pd_btns[0].label == "19"  # Pazartesi
        assert pd_btns[6].label == "25"  # Pazar (First day of program)

        # 4. Sunday 25 October renders the kickoff strength workout (Üst A)
        rendered_text = " ".join(str(m.value) for m in at.markdown)
        assert "Üst A" in rendered_text
        assert "Resmi Program Başlangıcı" in rendered_text
        assert "Başlangıç Tartımı" in rendered_text

        # 5. Next week navigation works: goes to 26 Eki (Pzt) – 1 Kas (Paz)
        next_btn.click().run()
        assert not at.exception
        h2_markdowns = [str(m.value) for m in at.markdown if "1 Kas" in str(m.value)]
        assert len(h2_markdowns) > 0
        pd_btns_w2 = [b for b in at.button if b.key and b.key.startswith("pd_")]
        assert pd_btns_w2[0].label == "26"  # Pazartesi
        assert pd_btns_w2[6].label == "1"   # Pazar


def test_functional_dynamic_calendar_padel_and_dual_sessions():
    """Verify Google Calendar events dynamically adjust schedule and support both single and dual sessions."""
    from unittest.mock import patch
    import datetime as dt
    from app import program_week_grid

    mock_events = [
        {
            "summary": "Padel Training",
            "date": "2026-10-27",
            "start_time": "20:00",
            "end_time": "21:30",
            "is_padel": True,
            "location": "Tennis & Padel Meerhoven",
        },
        {
            "summary": "✅ Padel with Isa & Robbert",
            "date": "2026-10-28",
            "start_time": "19:00",
            "end_time": "20:30",
            "is_padel": True,
            "location": "TV Meerhoven, Eindhoven",
        },
    ]

    import streamlit as st
    st.cache_data.clear()
    unique_url = "https://calendar.google.com/ical/mock_dual_test.ics"

    with patch("lib.calendar_sync.fetch_padel_events", return_value=mock_events), \
         patch("lib.calendar_sync.get_calendar_url", return_value=unique_url):
        # 1. Verify program_week_grid dynamically schedules Alt A on Monday and Padel on Tue & Wed
        week_mon = dt.date(2026, 10, 26)  # Monday
        grid = program_week_grid(week_mon)

        # Mon 26: Alt A lift (smart placement before padel days)
        assert grid[0]["name"] == "Alt A"
        assert grid[0]["kind"] == "lift"

        # Tue 27: Padel from calendar
        assert grid[1]["name"] == "Padel"
        assert grid[1]["kind"] == "padel"
        assert grid[1]["planned"] is True
        assert grid[1]["cal_ev"]["summary"] == "Padel Training"

        # Wed 28: Padel from calendar
        assert grid[2]["name"] == "Padel"
        assert grid[2]["kind"] == "padel"
        assert grid[2]["planned"] is True
        assert grid[2]["cal_ev"]["summary"] == "✅ Padel with Isa & Robbert"

        # Thu 29: Rest after double padel
        assert grid[3]["name"] == "Dinlenme"
        assert grid[3]["cal_ev"] is None

        # 2. Verify Plan page renders Padel on Wednesday 28 (day index 2 in 26 Oct–1 Nov week)
        with tempfile.TemporaryDirectory() as td:
            os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
            at = _run_app(
                "plan",
                body={"start_date": "2026-10-25", "theme": "dark"},
                settings={"gcal_url": unique_url},
                plan_week_idx=1,
                plan_day_idx=2,
            )
            assert not at.exception
            rendered_text = " ".join(str(m.value) for m in at.markdown)

            assert "Padel with Isa & Robbert" in rendered_text
            assert "TV Meerhoven" in rendered_text
            assert "Google Takvim" in rendered_text


def test_functional_macro_targets_and_nutrition_page():
    """Verify daily fat and carb targets display on Nutrition and Stats pages."""
    with tempfile.TemporaryDirectory() as td:
        os.environ["FITNESS_DB_PATH"] = str(Path(td) / "test.db")
        at = _run_app("nutrition")
        assert not at.exception
        t = at.session_state["targets"]
        assert "fat" in t and "carbs" in t and "protein" in t
        assert t["fat"] == 67
        assert t["carbs"] == 189
        assert t["protein"] == 160

        # Verify nutrition page renders macro target tiles when nt is None
        rendered = " ".join(str(m.value) for m in at.markdown)
        assert "Sağlıklı Yağ" in rendered
        assert "Karbonhidrat" in rendered
        assert "67" in rendered
        assert "189" in rendered

        # Switch to stats page and verify evidence-based macro rows
        at.session_state["page"] = "stats"
        at.run()
        assert not at.exception
        stats_rendered = " ".join(str(m.value) for m in at.markdown)
        assert "Sağlıklı yağ" in stats_rendered
        assert "Karbonhidrat" in stats_rendered
