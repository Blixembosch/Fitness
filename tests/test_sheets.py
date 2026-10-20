import pandas as pd
from lib import sheets


def test_parse_weights():
    df = pd.DataFrame({"date": ["2026-10-18", "2026-10-19", "bad"], "weight_kg": [101.2, 100.6, 100]})
    out = sheets.parse_weights(df)
    assert {"date": "2026-10-18", "w": 101.2} in out
    assert len(out) == 2  # 'bad' date dropped


def test_parse_weights_rejects_out_of_range():
    df = pd.DataFrame({"date": ["2026-10-19"], "weight_kg": [5]})  # implausible
    assert sheets.parse_weights(df) == []


def test_parse_weights_empty():
    assert sheets.parse_weights(pd.DataFrame()) == []


def test_parse_weights_apple_date_format():
    # Apple Shortcuts often send "20 Oct 2026 at 09:08"
    df = pd.DataFrame({"date": ["20 Oct 2026 at 09:08"], "weight_kg": [100.5]})
    assert sheets.parse_weights(df) == [{"date": "2026-10-20", "w": 100.5}]


def test_parse_workouts_and_padel():
    df = pd.DataFrame({
        "date": ["2026-10-18", "2026-10-19"],
        "type": ["Padel", "Elliptical"],
        "minutes": [60, 30],
        "kcal": [500, 250],
    })
    wo = sheets.parse_workouts(df)
    assert list(wo.columns) == ["date", "type", "minutes", "kcal"]
    assert sheets.padel_dates(wo) == ["2026-10-18"]


def test_padel_matches_tennis_alias():
    df = pd.DataFrame({"date": ["2026-10-20"], "type": ["Tennis"]})
    assert sheets.padel_dates(sheets.parse_workouts(df)) == ["2026-10-20"]
