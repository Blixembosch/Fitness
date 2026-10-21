"""Evidence-based targets for a beginner in a fat-loss phase (and on a GLP-1 like Wegovy), plus
small helpers to score the user's numbers against them. Ranges reflect the common sports-science
consensus; sources are cited in the UI. These are general guidance, not medical advice."""
from __future__ import annotations
import pandas as pd

# (low, high) bands
PROTEIN_GKG = (1.6, 2.2)      # g per kg bodyweight/day — preserve muscle in a deficit
LOSS_PCT_WK = (0.5, 1.0)      # % of bodyweight lost per week — faster risks muscle loss
SETS_PER_MUSCLE = (10, 20)    # hard sets per muscle group per week for hypertrophy
DEFICIT_KCAL = (300, 600)     # daily calorie deficit for ~0.5–1%/wk


def band(value, lo, hi) -> str:
    """'low' | 'ok' | 'high' for a value against a band (None -> 'na')."""
    if value is None:
        return "na"
    if value < lo:
        return "low"
    if value > hi:
        return "high"
    return "ok"


def protein_per_kg(avg_protein, weight_kg):
    if not avg_protein or not weight_kg:
        return None
    return round(avg_protein / weight_kg, 2)


def weekly_loss_pct(df: pd.DataFrame, min_days: int = 6):
    """% of bodyweight lost per week from a weigh-in frame [date, w]; positive = losing.
    Requires at least `min_days` (default 6) between first and last weigh-in so that normal
    2–3 day hydration/water-weight fluctuations do not artificially blow up into an alarming weekly rate.
    """
    if df is None or len(df) < 2:
        return None
    first, last = float(df["w"].iloc[0]), float(df["w"].iloc[-1])
    days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    if not first or days < min_days:
        return None
    weeks = days / 7
    return round((first - last) / first * 100 / weeks, 2)


# status -> (css class, short word)
_VERDICT = {
    "ok": ("good", "hedefte"), "low": ("bad", "düşük"), "high": ("bad", "yüksek"),
    "na": ("", "veri yok"),
}


def verdict(status, low_word="düşük", high_word="yüksek"):
    cls, word = _VERDICT[status]
    if status == "low":
        word = low_word
    elif status == "high":
        word = high_word
    return cls, word
