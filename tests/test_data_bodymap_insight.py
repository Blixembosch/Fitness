from lib import data, bodymap, insight


# ---- data ----
def test_catalogue_loaded():
    assert len(data.all_exercises()) > 1000
    assert data.by_id()["0289"]["n"] == "dumbbell bench press"


def test_search_filters():
    res = data.search("bench press", bp=None, eq="dumbbell", limit=5)
    assert res and all(e["eq"] == "dumbbell" and "bench press" in e["n"].lower() for e in res)


def test_group_of():
    assert data.group_of("pectorals") == "Göğüs"
    assert data.group_of("lats") == "Sırt"
    assert data.group_of("delts") == "Omuz"
    assert data.group_of("quads") == "Bacak"
    assert data.group_of("unknown-muscle") is None


def test_muscle_tr():
    assert data.tr_muscle("pectorals") == "Göğüs"
    assert data.tr_bp("upper legs") == "Bacak"


# ---- bodymap ----
def test_weights_for_primary_secondary():
    w = bodymap.weights_for(["chest"], ["triceps"])
    assert w["chest"] == 3
    assert w["tricepL"] == 2 and w["tricepR"] == 2


def test_body_map_renders_two_svgs():
    svg = bodymap.body_map(["pectorals"], ["triceps", "shoulders"])
    assert svg.count("<svg") == 2 and "</svg>" in svg


# ---- insight (rule-based) ----
def test_insight_prioritizes_low_protein():
    note = insight.rule_based({"gkg": 1.05, "protein_target": 180, "loss": 0.7, "avg_sets": 12, "deficit": 450})
    assert "protein" in note.lower()


def test_insight_flags_fast_loss():
    note = insight.rule_based({"gkg": 1.9, "protein_target": 180, "loss": 1.5, "avg_sets": 12, "deficit": 450})
    assert "%1.5" in note or "hafta" in note


def test_insight_positive_when_on_track():
    note = insight.rule_based({"gkg": 1.9, "protein_target": 180, "loss": 0.7, "avg_sets": 12, "deficit": 450})
    assert note and "düşük" not in note
