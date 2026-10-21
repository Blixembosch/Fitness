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


def test_parse_biometrics_lb_conversion_and_filter():
    csv = ("Day,Time,Group,Metric,Unit,Amount\n"
           "2026-10-20,08:00,,Weight,lbs,220\n"
           "2026-10-20,08:00,,Body Fat,%,22\n")  # non-weight metric ignored
    out = c.parse_biometrics(csv.encode())
    assert len(out) == 1 and 99 < out[0]["w"] < 100.5


def test_parse_biometrics_empty():
    assert c.parse_biometrics(b"Day,Time,Group,Metric,Unit,Amount\n") == []


def test_parse_exercises_and_padel():
    csv = ("Day,Time,Group,Exercise,Minutes,Calories Burned\n"
           "2026-10-20,20:00,,Tennis,90,600\n"
           "2026-10-21,18:00,,Elliptical,30,250\n")
    df = c.parse_exercises(csv.encode())
    assert list(df.columns) == ["date", "type", "minutes", "kcal"]
    assert len(df) == 2
    assert sheets.padel_dates(df) == ["2026-10-20"]


def test_parse_exercises_empty():
    df = c.parse_exercises(b"Day,Time,Group,Exercise,Minutes,Calories Burned\n")
    assert df.empty
