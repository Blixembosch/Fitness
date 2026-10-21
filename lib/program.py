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
     "note": "Düşük etkili kardiyo — birini seç ya da kürek + eliptiği birleştir", "exercises": [],
     "cardio": [
         {"name": "Kürek (rower)", "type": "Kürek", "minutes": 20, "kcal": 200,
          "tip": "20 dk interval: 1 dk güçlü çek / 1 dk kolay. Sırt, bacak ve nefes bir arada."},
         {"name": "Eliptik", "type": "Eliptik", "minutes": 15, "kcal": 150,
          "tip": "15 dk orta tempo; eklem dostu, toparlanma kardiyosu — kürek sonrası ideal."},
         {"name": "Bisiklet", "type": "Bisiklet", "minutes": 25, "kcal": 220,
          "tip": "Alternatif: 25 dk sabit tempo ya da 5×(1 dk sprint / 2 dk kolay)."},
     ]},
    {"wd": 6, "key": "rest", "name": "Dinlenme", "focus": "rest", "tag": "", "note": "Toparlanma", "exercises": []},
]

# icon per cardio type (matches Cronometer's cleaned labels, so Stats auto-matches these sessions)
CARDIO_ICON = {"Kürek": "🚣", "Eliptik": "🏃", "Bisiklet": "🚴", "Kardiyo": "🔥"}

# --- 12-week periodization ---------------------------------------------------------------------
# The block runs in three 4-week phases. Volume (base sets) rises then holds while intensity (RPE)
# climbs, which is the muscle-sparing pattern that matters most in a GLP-1 (Wegovy) deficit:
# resistance volume + high protein protect lean mass while fat comes off. `base_sets` is the sets
# per lift that phase, `ell` the elliptical finisher minutes on every lifting day.
BASE_SETS = 3
PHASES = [
    {"weeks": (1, 4), "key": "temel", "name": "Temel · Adaptasyon", "base_sets": 3, "rpe": "6–7", "ell": 10,
     "note": "Hareketleri oturt, eklem/tendon adaptasyonu. GLP-1'de enerji düşebilir — teknik ve protein öncelik, yükü zorlamadan ilerlet."},
    {"weeks": (5, 8), "key": "gelisim", "name": "Gelişim · Yüklenme", "base_sets": 4, "rpe": "7–8", "ell": 12,
     "note": "Öncelikli kaslarda (sırt/göğüs/omuz/karın) hacmi artır; her lift'te +1 set. Yük veya tekrarı kademeli ilerlet (çift ilerleme)."},
    {"weeks": (9, 12), "key": "koruma", "name": "Koruma · Yoğunluk", "base_sets": 4, "rpe": "8", "ell": 15,
     "note": "Açık büyüdükçe kası koru: yoğunluğu tut, yük bırakma. Yorgunluk birikirse 1 hafta deload (set/yoğunluk −%40). Uyku + protein kritik."},
]
PROGRAM_WEEKS = 12


def phase_for(week: int) -> dict:
    """The phase config for a 1..12 week number (week 0/None → Phase 1 preview)."""
    w = max(1, int(week or 1))
    for p in PHASES:
        lo, hi = p["weeks"]
        if lo <= w <= hi:
            return p
    return PHASES[-1]


def phase_extra_sets(phase: dict) -> int:
    return int(phase["base_sets"]) - BASE_SETS


def lifting_finisher(day: dict, minutes: int) -> dict | None:
    """Elliptical finisher appended to every lifting day (low-impact fat-loss + recovery)."""
    if day.get("focus") in ("upper", "lower", "full"):
        return {"name": "Eliptik (bitiriş)", "type": "Eliptik", "minutes": int(minutes),
                "tip": f"Antrenman sonu {int(minutes)} dk orta tempo — yağ yakımı ve toparlanma; eklem dostu."}
    return None


TRAINING_DAYS = [d for d in DAYS if d["exercises"]]  # the 3 lifting days
SESSIONS_PER_WEEK = len([d for d in DAYS if d["focus"] in ("upper", "lower", "full")]) + 1  # +cardio = 4


def day_for(weekday: int) -> dict:
    return DAYS[weekday % 7]


def exercise_detail(entry: dict, extra_sets: int = 0) -> dict:
    """Catalogue fields for a program entry: name + primary/secondary muscles + groups. `extra_sets`
    applies the current phase's added volume (e.g. +1 set in the build/peak phases)."""
    ex = data.by_id().get(entry["id"], {})
    primary = [m for m in [ex.get("tg"), ex.get("mg")] if m]
    secondary = [m for m in (ex.get("sm") or []) if m not in primary]
    return {
        **entry, "sets": max(1, int(entry.get("sets", BASE_SETS)) + extra_sets),
        "name": ex.get("n", entry["id"]), "bp": ex.get("bp"), "eq": ex.get("eq"),
        "primary": primary, "secondary": secondary,
    }


def day_details(day: dict, extra_sets: int = 0) -> list[dict]:
    return [exercise_detail(e, extra_sets) for e in day["exercises"]]


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


def day_load(day: dict, extra_sets: int = 0) -> dict:
    sets = sum(int(e.get("sets", 0)) + extra_sets for e in day["exercises"]) if day["exercises"] else 0
    minutes = max(5, round(sets * 3 / 5) * 5) if sets else 0
    return {"exercises": len(day["exercises"]), "sets": sets, "minutes": minutes}


def day_cardio(day: dict) -> list[dict]:
    """Structured cardio actions for a day (rower / elliptical / bike), or [] for lifting/rest days."""
    return day.get("cardio", [])


def cardio_load(day: dict) -> dict:
    """{options, min_lo, min_hi} — number of cardio options and the min/max single-session minutes."""
    c = day_cardio(day)
    mins = [int(x.get("minutes", 0)) for x in c] or [0]
    return {"options": len(c), "min_lo": min(mins), "min_hi": max(mins)}


def day_muscles(day: dict):
    """(primary, secondary) muscle lists aggregated over the day's exercises — for the body map."""
    primary, secondary = [], []
    for e in day_details(day):
        primary += e["primary"]
        secondary += e["secondary"]
    return primary, secondary
