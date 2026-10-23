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


def test_estimate_targets_fat_and_carbs_distribution():
    # 2000 kcal, 100 kg, 1.6 g/kg protein = 160g protein (640 kcal)
    # Balanced (30% fat): 2000 * 0.30 = 600 kcal / 9 = ~67g fat
    # Carbs: (2000 - 640 - 600) / 4 = 760 / 4 = 190g carbs
    t_bal = n.estimate_targets(100, 178, 34, protein_per_kg=1.6, fat_pct=0.30, kcal=2000)
    assert t_bal["kcal"] == 2000
    assert t_bal["protein"] == 160
    assert t_bal["fat"] == 67
    assert t_bal["carbs"] == 189

    # Low fat (25% fat): 2000 * 0.25 = 500 kcal / 9 = ~56g fat
    # Carbs: (2000 - 640 - 504) / 4 = ~214g carbs
    t_low = n.estimate_targets(100, 178, 34, protein_per_kg=1.6, fat_pct=0.25, kcal=2000)
    assert t_low["fat"] == 56
    assert t_low["carbs"] == 214


def test_day_summary_all_macros():
    entry = {"kcal": 1800, "protein": 150, "carbs": 170, "fat": 60}
    targets = {"kcal": 2000, "protein": 160, "carbs": 190, "fat": 67}
    ds = n.day_summary(entry, targets)
    assert ds["kcal"]["remaining"] == 200
    assert ds["protein"]["remaining"] == 10
    assert ds["carbs"]["remaining"] == 20
    assert ds["fat"]["remaining"] == 7
    assert ds["protein"]["pct"] == round(150 / 160 * 100)
    assert ds["carbs"]["pct"] == round(170 / 190 * 100)
    assert ds["fat"]["pct"] == round(60 / 67 * 100)

