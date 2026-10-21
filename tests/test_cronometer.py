from lib import cronometer as c
from lib import sheets


def test_detect():
    assert c.detect("Day,Time,Group,Exercise,Minutes,Calories Burned") == "exercises"
    assert c.detect("Day,Time,Group,Metric,Unit,Amount") == "biometrics"
    assert c.detect("Date,Group,Energy (kcal),Protein (g)") == "nutrition"
    assert c.detect("Name,Start,End") == ""


def test_parse_biometrics_weight():
    csv = "Day,Time,Group,Metric,Unit,Amount\n2026-10-20,08:00,Morning,Weight,kg,100.5\n"
    assert c.parse_biometrics(csv.encode()) == [{"date": "2026-10-20", "w": 100.5}]


def test_parse_biometrics_apple_health_suffix_and_dedup():
    # Real export: "Weight (Apple Health)" rows mixed with high-frequency heart-rate rows; the
    # last weigh-in for a day wins, and non-weight metrics are ignored.
    csv = ("Day,Time,Group,Metric,Unit,Amount\n"
           "2026-05-10,,Uncategorized,Weight,kg,102.1\n"
           "2026-05-15,7:36 AM,Uncategorized,Weight (Apple Health),kg,100.4\n"
           "2026-05-15,9:00 AM,Uncategorized,Weight (Apple Health),kg,100.2\n"
           "2026-05-15,7:36 AM,Uncategorized,Heart Rate (Apple Health),bpm,62\n")
    out = c.parse_biometrics(csv.encode())
    assert out == [{"date": "2026-05-10", "w": 102.1}, {"date": "2026-05-15", "w": 100.2}]


def test_parse_biometrics_lb_conversion_and_filter():
    csv = ("Day,Time,Group,Metric,Unit,Amount\n"
           "2026-10-20,08:00,,Weight,lbs,220\n"
           "2026-10-20,08:00,,Body Fat,%,22\n")  # non-weight metric ignored
    out = c.parse_biometrics(csv.encode())
    assert len(out) == 1 and 99 < out[0]["w"] < 100.5


def test_parse_biometrics_empty():
    assert c.parse_biometrics(b"Day,Time,Group,Metric,Unit,Amount\n") == []


def test_clean_type_and_is_padel():
    assert c.clean_type("Tennis (Apple Health)") == "Padel"
    assert c.clean_type("Cycling (Apple Health)") == "Bisiklet"
    assert c.clean_type("Road Biking") == "Bisiklet"
    assert c.clean_type("Elliptical (Apple Health)") == "Eliptik"
    assert c.clean_type("Functional Strength Training (Apple Health)") == "Güç"
    assert c.clean_type("Something Else") == "Something Else"
    assert c.is_padel("Tennis (Apple Health)") is True
    assert c.is_padel("Rowing (Apple Health)") is False


def test_category():
    # padel, strength (program workout), and everything else as cardio
    assert c.category("Padel") == "padel"
    assert c.category("Güç") == "strength"
    assert c.category("Bisiklet") == "cardio"
    assert c.category("Eliptik") == "cardio"


def test_parse_exercises_real_data():
    # Real rows: "(Apple Health)" suffix, Calories Burned stored negative, an "Active Energy
    # Balance" daily-total row that is NOT a workout.
    csv = ("Day,Time,Group,Exercise,Minutes,Calories Burned\n"
           "2026-05-12,10:01 PM,Uncategorized,Tennis (Apple Health),64.2,-505.10\n"
           "2026-05-13,06:00 PM,Uncategorized,Elliptical (Apple Health),30,-250\n"
           "2026-05-12,,Uncategorized,Active Energy Balance (Apple Health),114.0,-686.68\n")
    df = c.parse_exercises(csv.encode())
    assert list(df.columns) == ["date", "type", "cat", "padel", "minutes", "kcal"]
    assert len(df) == 2  # active-energy row excluded
    assert set(df["type"]) == {"Padel", "Eliptik"}
    assert (df["kcal"] >= 0).all()  # expenditure stored positive
    row = df[df["type"] == "Padel"].iloc[0]
    assert round(row["kcal"]) == 505 and row["padel"] and row["cat"] == "padel"
    assert sheets.padel_dates(df) == ["2026-05-12"]


def test_parse_exercises_strength_category():
    csv = ("Day,Time,Group,Exercise,Minutes,Calories Burned\n"
           "2026-11-02,06:30 PM,Uncategorized,Functional Strength Training (Apple Health),45,-320\n"
           "2026-11-03,07:00 PM,Uncategorized,Cycling (Apple Health),30,-280\n")
    df = c.parse_exercises(csv.encode())
    assert list(df[df["type"] == "Güç"]["cat"])[0] == "strength"
    assert list(df[df["type"] == "Bisiklet"]["cat"])[0] == "cardio"


def test_parse_active_energy():
    csv = ("Day,Time,Group,Exercise,Minutes,Calories Burned\n"
           "2026-05-11,,Uncategorized,Active Energy Balance (Apple Health),54.0,-225.29\n"
           "2026-05-12,,Uncategorized,Active Energy Balance (Apple Health),114.0,-686.68\n"
           "2026-05-12,10:01 PM,Uncategorized,Tennis (Apple Health),64.2,-505.10\n")
    out = c.parse_active_energy(csv.encode())
    assert out == [{"date": "2026-05-11", "kcal": 225}, {"date": "2026-05-12", "kcal": 687}]


def test_parse_exercises_empty():
    df = c.parse_exercises(b"Day,Time,Group,Exercise,Minutes,Calories Burned\n")
    assert df.empty
