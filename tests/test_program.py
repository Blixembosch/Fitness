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


def test_phase_for_12_weeks():
    from lib import program as P
    assert P.phase_for(0)["key"] == "temel"      # not started -> phase 1 preview
    assert P.phase_for(1)["key"] == "temel"
    assert P.phase_for(4)["key"] == "temel"
    assert P.phase_for(5)["key"] == "gelisim"
    assert P.phase_for(8)["key"] == "gelisim"
    assert P.phase_for(9)["key"] == "koruma"
    assert P.phase_for(12)["key"] == "koruma"
    assert P.phase_for(99)["key"] == "koruma"    # clamps to last phase


def test_phase_extra_sets_and_volume():
    from lib import program as P
    assert P.phase_extra_sets(P.phase_for(1)) == 0     # base 3 sets
    assert P.phase_extra_sets(P.phase_for(6)) == 1     # build adds a set
    d = P.TRAINING_DAYS[0]
    base = P.day_load(d, 0)["sets"]
    assert P.day_load(d, 1)["sets"] == base + len(d["exercises"])
    # per-exercise sets reflect the phase
    assert P.day_details(d, 1)[0]["sets"] == P.day_details(d, 0)[0]["sets"] + 1


def test_lifting_finisher_elliptical_every_lift_day():
    from lib import program as P
    for d in P.TRAINING_DAYS:
        fin = P.lifting_finisher(d, 10)
        assert fin and fin["type"] == "Eliptik" and fin["minutes"] == 10
    # non-lifting days get no finisher
    rest = next(d for d in P.DAYS if d["focus"] == "rest")
    assert P.lifting_finisher(rest, 10) is None


def test_reps_are_net_values():
    from lib import program as P
    allowed = {"8", "10", "12"}
    for d in P.TRAINING_DAYS:
        for e in d["exercises"]:
            assert str(e["reps"]) in allowed, f"{e['id']} has non-net reps {e['reps']!r}"


def test_finisher_offers_elliptical_or_rower():
    from lib import program as P
    fin = P.lifting_finisher(P.TRAINING_DAYS[0], 12)
    assert "kürek" in fin["name"].lower() and "eliptik" in fin["name"].lower()
    assert fin["minutes"] == 12
