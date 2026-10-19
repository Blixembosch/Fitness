import pandas as pd
from lib import metrics


def test_band():
    assert metrics.band(1.0, 1.6, 2.2) == "low"
    assert metrics.band(1.8, 1.6, 2.2) == "ok"
    assert metrics.band(2.5, 1.6, 2.2) == "high"
    assert metrics.band(None, 1.6, 2.2) == "na"


def test_protein_per_kg():
    assert metrics.protein_per_kg(180, 100) == 1.8
    assert metrics.protein_per_kg(0, 100) is None
    assert metrics.protein_per_kg(150, None) is None


def test_weekly_loss_pct():
    df = pd.DataFrame({"date": pd.to_datetime(["2026-10-05", "2026-10-19"]), "w": [102.0, 100.6]})
    # 1.4 kg over 14 days = 1 week-equivalent *2 weeks -> (1.4/102)/2 *100
    val = metrics.weekly_loss_pct(df)
    assert val is not None and 0.6 < val < 0.75


def test_weekly_loss_pct_needs_two_points():
    df = pd.DataFrame({"date": pd.to_datetime(["2026-10-05"]), "w": [102.0]})
    assert metrics.weekly_loss_pct(df) is None


def test_verdict_words():
    cls, word = metrics.verdict("low", "düşük", "yüksek")
    assert cls == "bad" and word == "düşük"
    cls, word = metrics.verdict("ok")
    assert cls == "good"
