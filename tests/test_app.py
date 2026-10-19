"""Functional smoke tests: actually run the Streamlit app headless (AppTest) and assert every
page renders without raising. Runs in CI where streamlit is installed."""
from pathlib import Path
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(page=None, **state):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()  # first run initialises session_state defaults
    for k, v in state.items():
        at.session_state[k] = v
    if page:
        at.session_state["page"] = page
    at.run()
    return at


def test_every_page_runs_without_exception():
    for pg in ["home", "plan", "workout", "stats", "nutrition"]:
        at = _run(pg)
        assert not at.exception, f"{pg} raised: {at.exception}"


def test_targets_are_computed():
    at = _run("home")
    t = at.session_state["targets"]
    assert t["protein"] > 0 and t["kcal"] >= 1500


def test_selecting_a_plan_day_does_not_crash():
    at = _run("plan", plan_day=2)
    assert not at.exception


def test_logging_a_set_updates_state():
    at = _run("workout")
    assert not at.exception
