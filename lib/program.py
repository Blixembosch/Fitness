"""The auto-generated training program for the user's profile — not a manual builder.
Tailored to: home adjustable dumbbells + bench + water rower / elliptical, upper-body emphasis
to preserve muscle on Wegovy (back / chest / shoulders), fat loss, padel Tue/Thu, 4 sessions/wk.
Exercises reference the real catalogue by id, so each one's muscle map comes straight from the data.
"""
from __future__ import annotations
from lib import data

FOCUS_COLOR = {"upper": "var(--blue)", "lower": "var(--purple)", "cardio": "var(--green)",
               "full": "var(--teal)", "rest": "var(--faint)"}

# weekday 0=Mon … 6=Sun
DAYS = [
    {"wd": 0, "key": "upperA", "name": "Üst A", "focus": "upper", "tag": "Üst · A", "note": "Göğüs, sırt, omuz, kol",
     "exercises": [
         {"id": "0289", "sets": 3, "reps": "8–12", "tip": "Göğüs; kontrollü indir, patlayarak it."},
         {"id": "0314", "sets": 3, "reps": "10–12", "tip": "Üst göğüs; bench ~30°."},
         {"id": "0293", "sets": 3, "reps": "10–12", "tip": "Sırt; dirseği gövdeye yakın çek, sık."},
         {"id": "9698", "sets": 3, "reps": "10–12", "tip": "Sırt (göğüs destekli); belini korur, lat'ı sık."},
         {"id": "0334", "sets": 3, "reps": "12–15", "tip": "Omuz yanı; hafif ağırlık, salınımsız."},
         {"id": "0294", "sets": 3, "reps": "10–12", "tip": "Biceps; dirsek sabit."},
         {"id": "3449", "sets": 3, "reps": "20", "tip": "Bel/yan karın; gövdeyi döndür, kontrollü."},
     ]},
    {"wd": 1, "key": "padelTue", "name": "Padel", "focus": "cardio", "tag": "Padel",
     "note": "Ders 20:00 + maç · kardiyo", "exercises": []},
    {"wd": 2, "key": "lowerA", "name": "Alt A", "focus": "lower", "tag": "Alt · A", "note": "Bacak, kalça, karın",
     "exercises": [
         {"id": "1760", "sets": 3, "reps": "10–12", "tip": "Ön bacak; göğüste dambıl, derine çök."},
         {"id": "1459", "sets": 3, "reps": "10–12", "tip": "Arka bacak/kalça; sırt düz, kalçayı geri it."},
         {"id": "2290", "sets": 3, "reps": "10–12", "tip": "Tek bacak; arka ayak bench'te."},
         {"id": "0417", "sets": 3, "reps": "15–20", "tip": "Baldır; tepede 1 sn dur."},
         {"id": "1163", "sets": 3, "reps": "12–15", "tip": "Alt karın; bel yere yapışık."},
         {"id": "4624", "sets": 3, "reps": "15", "tip": "Karın; nefes vererek sık."},
     ]},
    {"wd": 3, "key": "padelThu", "name": "Padel", "focus": "cardio", "tag": "Padel",
     "note": "Olursa · kardiyo", "exercises": []},
    {"wd": 4, "key": "upperB", "name": "Üst B", "focus": "upper", "tag": "Üst · B", "note": "Omuz, sırt, göğüs, kol",
     "exercises": [
         {"id": "0405", "sets": 3, "reps": "8–12", "tip": "Omuz; bench dik, çekirdek sıkı."},
         {"id": "0293", "sets": 3, "reps": "10–12", "tip": "Sırt; kürek kemiklerini birleştir."},
         {"id": "2982", "sets": 3, "reps": "10–12", "tip": "Göğüs; yerde, dirsek 45°."},
         {"id": "0378", "sets": 3, "reps": "12–15", "tip": "Arka omuz; gövde öne eğik."},
         {"id": "0313", "sets": 3, "reps": "10–12", "tip": "Ön kol/biceps; nötr tutuş."},
         {"id": "0430", "sets": 3, "reps": "12–15", "tip": "Triceps; tam aç."},
         {"id": "0407", "sets": 3, "reps": "15/yön", "tip": "Bel/yan karın; tek dambıl, yana eğil."},
     ]},
    {"wd": 5, "key": "cardio", "name": "Kardiyo", "focus": "cardio", "tag": "Kardiyo",
     "note": "Kürek 20 dk interval + eliptik 10 dk", "exercises": []},
    {"wd": 6, "key": "rest", "name": "Dinlenme", "focus": "rest", "tag": "", "note": "Toparlanma", "exercises": []},
]

TRAINING_DAYS = [d for d in DAYS if d["exercises"]]  # the 3 lifting days
SESSIONS_PER_WEEK = len([d for d in DAYS if d["focus"] in ("upper", "lower", "full")]) + 1  # +cardio = 4


def day_for(weekday: int) -> dict:
    return DAYS[weekday % 7]


def exercise_detail(entry: dict) -> dict:
    """Catalogue fields for a program entry: name + primary/secondary muscles + groups."""
    ex = data.by_id().get(entry["id"], {})
    primary = [m for m in [ex.get("tg"), ex.get("mg")] if m]
    secondary = [m for m in (ex.get("sm") or []) if m not in primary]
    return {
        **entry, "name": ex.get("n", entry["id"]), "bp": ex.get("bp"), "eq": ex.get("eq"),
        "primary": primary, "secondary": secondary,
    }


def day_details(day: dict) -> list[dict]:
    return [exercise_detail(e) for e in day["exercises"]]


_GROUP_ORDER = ["Göğüs", "Sırt", "Omuz", "Kol", "Bacak", "Baldır", "Karın"]


def day_groups(day: dict, limit: int = 4) -> list[str]:
    """Coarse muscle groups a day trains (Göğüs, Sırt…), in body-region order — for the chips."""
    present: set[str] = set()
    for e in day_details(day):
        for m in e["primary"]:
            g = data.group_of(m)
            if g and g != "Kardiyo":
                present.add(g)
    ordered = [g for g in _GROUP_ORDER if g in present]
    return ordered[:limit]


def day_load(day: dict) -> dict:
    sets = sum(int(e.get("sets", 0)) for e in day["exercises"])
    minutes = max(5, round(sets * 3 / 5) * 5) if sets else 0
    return {"exercises": len(day["exercises"]), "sets": sets, "minutes": minutes}


def day_muscles(day: dict):
    """(primary, secondary) muscle lists aggregated over the day's exercises — for the body map."""
    primary, secondary = [], []
    for e in day_details(day):
        primary += e["primary"]
        secondary += e["secondary"]
    return primary, secondary
