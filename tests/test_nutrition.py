import io
import pandas as pd
from lib import nutrition as n


def test_estimate_targets_known_values():
    t = n.estimate_targets(100, 178, 34, "male", "light", deficit=500, protein_per_kg=1.8)
    assert t["protein"] == 180              # 1.8 * 100
    assert t["tdee"] > t["kcal"]            # deficit applied
    assert t["kcal"] >= 1500                # floor respected


def test_estimate_targets_floor():
    t = n.estimate_targets(45, 150, 70, "female", "sedentary", deficit=2000, floor=1500)
    assert t["kcal"] == 1500


def test_estimate_targets_manual_kcal():
    # a manual calorie goal overrides TDEE − deficit; the implied daily deficit is reported
    t = n.estimate_targets(100.5, 178, 34, "male", "light", protein_per_kg=1.8, kcal=1900)
    assert t["kcal"] == 1900
    assert t["deficit"] == t["tdee"] - 1900
    assert t["protein"] == 181            # 1.8 * 100.5


def test_weekly_loss():
    assert n.weekly_loss(0) == 0
    assert n.weekly_loss(500) == round(500 * 7 / 7700, 2)   # ~0.45 kg/week
    assert 0.7 < n.weekly_loss(833) < 0.8                    # ~0.76 kg/week at a 1900 kcal goal


def test_parse_cronometer_keeps_only_total_rows_and_sums_duplicates():
    csv = (
        "Date,Group,Energy (kcal),Protein (g),Carbs (g),Fat (g),Fiber (g)\n"
        "2026-10-18,Breakfast,500,40,50,20,5\n"       # meal row — must be ignored
        "2026-10-18,Total,1500,140,120,50,20\n"       # the day total
        "2026-10-19,Total,1700,130,160,55,18\n"
        "2026-10-19,Total,100,10,10,5,2\n"            # split total — summed with the above
        "2026-10-20,Total,,,,,\n"                      # empty day — dropped
    )
    df = n.parse_cronometer(io.BytesIO(csv.encode()))
    assert list(df["date"]) == ["2026-10-18", "2026-10-19"]
    r18 = df[df["date"] == "2026-10-18"].iloc[0]
    assert r18["kcal"] == 1500 and r18["protein"] == 140      # NOT 2000 (meal row excluded)
    r19 = df[df["date"] == "2026-10-19"].iloc[0]
    assert r19["kcal"] == 1800 and r19["protein"] == 140      # 1700+100, 130+10


def test_parse_cronometer_without_group_column():
    csv = "Date,Energy (kcal),Protein (g)\n2026-10-18,1600,150\n"
    df = n.parse_cronometer(io.BytesIO(csv.encode()))
    assert len(df) == 1 and df.iloc[0]["kcal"] == 1600


def test_day_summary():
    ds = n.day_summary({"kcal": 1500, "protein": 140}, {"kcal": 1800, "protein": 152})
    assert ds["kcal"]["remaining"] == 300
    assert ds["protein"]["pct"] == round(140 / 152 * 100)


def test_protein_adherence():
    df = pd.DataFrame({"protein": [160, 120, 155], "kcal": [1500, 1600, 1700]})
    ad = n.protein_adherence(df, 152)
    assert ad["days"] == 3 and ad["met"] == 2
    assert ad["avg_protein"] == 145
