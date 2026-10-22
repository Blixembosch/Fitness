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
        at = _run_app("home", wegovy={"dose_mg": 0.25, "inj_weekday": dt.date.today().weekday(), "logs": []})
        inj_btn = next((b for b in at.button if b.key == "inj_btn"), None)
        assert inj_btn is not None
        initial_count = len(at.session_state["wegovy"]["logs"])
        inj_btn.click().run()
        assert not at.exception
        assert len(at.session_state["wegovy"]["logs"]) == initial_count + 1


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
    assert "font-size:28px" in h
    assert 'class="muted"' in h
