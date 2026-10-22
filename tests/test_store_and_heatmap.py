import datetime as dt
import pathlib
import tempfile
import pandas as pd
from lib import store, ui, insight, nutrition


def test_sqlite_roundtrip_and_session_hydration(tmp_path=None):
    if tmp_path is None:
        tmp_path = pathlib.Path(tempfile.mkdtemp())
    db = tmp_path / "test_fitness.db"
    session1 = {
        "body": {"birth": "1992-03-12", "height": 178, "sex": "male", "activity": "light", "deficit": 500, "kcal_goal": 2100, "protein_mode": "adjusted"},
        "wegovy": {"dose_mg": 0.5, "inj_weekday": 5, "logs": [{"date": "2026-10-17", "dose": 0.5, "site": "Sol karın"}]},
        "weights": [{"date": "2026-10-21", "w": 99.8}],
        "workouts": [{"date": "2026-10-21", "key": "lowerA", "name": "Alt A", "primary": ["quads"], "secondary": ["glutes"]}],
        "padel": ["2026-10-20"],
        "cron_ex": [],
        "active_kcal": {"2026-10-21": 520},
        "setlog": {"2026-10-21|lowerA|1760": 3},
        "loadlog": {"1760": 20.0},
        "nutrition": pd.DataFrame([{"date": "2026-10-21", "kcal": 2050.0, "protein": 165.0, "carbs": 160.0, "fat": 70.0, "fiber": 28.0}]),
    }
    store.persist_session(session1, db_path=db)

    # Simulate a page refresh (F5): new session state starts with default 1900 kcal_goal
    session2 = {
        "body": {"birth": "1992-03-12", "height": 178, "sex": "male", "activity": "light", "deficit": 500, "kcal_goal": 1900},
        "wegovy": {"dose_mg": 0.25, "inj_weekday": 5, "logs": []},
        "weights": [],
        "workouts": [],
        "padel": [],
        "cron_ex": [],
        "active_kcal": {},
        "setlog": {},
        "loadlog": {},
        "nutrition": None,
    }
    hydrated = store.hydrate_session(session2, db_path=db)
    assert hydrated is True
    assert session2["body"]["kcal_goal"] == 2100
    assert session2["wegovy"]["dose_mg"] == 0.5
    assert len(session2["wegovy"]["logs"]) == 1
    assert session2["weights"] == [{"date": "2026-10-21", "w": 99.8}]
    assert session2["setlog"]["2026-10-21|lowerA|1760"] == 3
    assert session2["loadlog"]["1760"] == 20.0
    assert isinstance(session2["nutrition"], pd.DataFrame) and len(session2["nutrition"]) == 1


def test_adjusted_protein_band():
    # At 100.5 kg and 178 cm (BMI > 31), adjusted protein band is in the sustainable 150-181 g range
    b_adj = nutrition.protein_band(100.5, 178, mode="adjusted")
    assert 145 <= b_adj["min"] <= 155
    assert 155 <= b_adj["target"] <= 165
    assert b_adj["max"] == 181
    assert b_adj["eff_weight"] < 100.5

    b_strict = nutrition.protein_band(100.5, 178, mode="strict")
    assert b_strict["target"] == 181
    assert b_strict["mode"] == "strict"


def test_github_heatmap_renders_52_weeks():
    today = dt.date(2026, 10, 21)
    records = {
        "2026-10-19": {"level": 3, "summary": "🏋️ Üst A", "strength": True, "padel": False, "cardio": False, "protein_ok": False},
        "2026-10-20": {"level": 4, "summary": "🎾 Padel · 🥩 185g protein", "strength": False, "padel": True, "cardio": False, "protein_ok": True},
    }
    html = ui.github_heatmap(today, records, weeks=52)
    assert "gh-card" in html
    assert "2 aktif gün" in html
    assert "gh-cell l3" in html
    assert "gh-cell l4" in html
    assert html.count('class="gh-cell') == 52 * 7


def test_insight_accepts_app_payload_keys():
    # app.py sends loss_pct_week, avg_sets_per_muscle, deficit_kcal
    note = insight.rule_based({
        "gkg": 1.9,
        "protein_target": 160,
        "loss_pct_week": 1.4,
        "avg_sets_per_muscle": 8,
        "deficit_kcal": 500,
    })
    assert "1.4" in note or "set/hafta" in note


def test_sql_dump_and_restore(tmp_path=None):
    if tmp_path is None:
        tmp_path = pathlib.Path(tempfile.mkdtemp())
    db1 = tmp_path / "origin.db"
    db2 = tmp_path / "restored.db"

    data = {"body": {"kcal_goal": 2000, "theme": "dark"}, "weights": [{"date": "2026-10-22", "w": 100.2}]}
    store.save_raw(data, db_path=db1, sync_cloud=False)

    sql = store.dump_sql(db1)
    assert "CREATE TABLE kv" in sql
    assert "2000" in sql

    ok = store.restore_sql(sql, db2)
    assert ok is True

    loaded = store.load_all(db_path=db2)
    assert loaded["body"]["kcal_goal"] == 2000
    assert loaded["weights"][0]["w"] == 100.2

