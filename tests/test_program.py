from lib import program as P, data


def test_every_program_exercise_resolves_in_catalogue():
    idx = data.by_id()
    missing = [e["id"] for d in P.DAYS for e in d["exercises"] if e["id"] not in idx]
    assert missing == [], f"unknown exercise ids: {missing}"


def test_four_sessions_per_week():
    assert P.SESSIONS_PER_WEEK == 4
    assert len(P.TRAINING_DAYS) == 3  # 3 lifting days + cardio


def test_day_load():
    d = P.DAYS[0]  # Üst A
    load = P.day_load(d)
    assert load["exercises"] == len(d["exercises"])
    assert load["sets"] == sum(int(e["sets"]) for e in d["exercises"])
    assert load["minutes"] % 5 == 0


def test_day_groups_in_region_order_and_nonempty():
    groups = P.day_groups(P.DAYS[0])
    assert groups and groups[0] == "Göğüs"           # fixed region order, chest first on Üst A
    assert "Kardiyo" not in groups


def test_day_muscles_nonempty_for_training_day():
    prim, sec = P.day_muscles(P.DAYS[0])
    assert prim and "pectorals" in prim


def test_rest_day_has_no_exercises():
    rest = P.DAYS[6]
    assert rest["focus"] == "rest" and rest["exercises"] == []


def test_cardio_day_has_actions():
    from lib import program as P
    cardio = next((d for d in P.DAYS if P.day_cardio(d)), None)
    assert cardio is not None, "there should be a day with structured cardio actions"
    types = {c["type"] for c in P.day_cardio(cardio)}
    assert {"Kürek", "Eliptik", "Bisiklet"} <= types
    load = P.cardio_load(cardio)
    assert load["options"] >= 3 and load["min_lo"] > 0 and load["min_hi"] >= load["min_lo"]


def test_lifting_days_have_no_cardio():
    from lib import program as P
    for d in P.TRAINING_DAYS:
        assert P.day_cardio(d) == []
