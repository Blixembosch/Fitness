"""The auto-generated training program for the user's profile — not a manual builder.
Tailored to: home adjustable dumbbells + bench + water rower / elliptical, upper-body emphasis
to preserve muscle on Wegovy (back / chest / shoulders), fat loss, padel Tue/Thu, 4 sessions/wk.
Exercises reference the real catalogue by id, so each one's muscle map comes straight from the data.
"""
from __future__ import annotations
from lib import data

FOCUS_COLOR = {"upper": "var(--blue)", "lower": "var(--purple)", "cardio": "var(--green)",
               "full": "var(--teal)", "rest": "var(--faint)"}

import datetime as dt

WORKOUT_UPPER_A = {
    "key": "upperA", "name": "Üst A", "focus": "upper", "tag": "Üst · A", "note": "Göğüs, sırt, omuz, kol",
    "exercises": [
        {"id": "0289", "sets": 3, "reps": "8", "tip": "Göğüs; kontrollü indir, patlayarak it."},
        {"id": "0314", "sets": 3, "reps": "10", "tip": "Üst göğüs; bench ~30°."},
        {"id": "0293", "sets": 3, "reps": "10", "tip": "Sırt; dirseği gövdeye yakın çek, sık."},
        {"id": "9698", "sets": 3, "reps": "10", "tip": "Sırt; göğüs destekli, lat'ı sık."},
        {"id": "0334", "sets": 3, "reps": "12", "tip": "Omuz yanı; hafif ağırlık, salınımsız."},
        {"id": "0294", "sets": 3, "reps": "10", "tip": "Biceps; dirsek sabit."},
        {"id": "3449", "sets": 3, "reps": "12", "tip": "Yan karın; her yöne kontrollü rotasyon."},
    ]
}

WORKOUT_LOWER_A = {
    "key": "lowerA", "name": "Alt A", "focus": "lower", "tag": "Alt · A", "note": "Bacak, kalça, karın",
    "exercises": [
        {"id": "1760", "sets": 3, "reps": "10", "tip": "Ön bacak; göğüste dambıl, derine çök."},
        {"id": "1459", "sets": 3, "reps": "10", "tip": "Arka bacak/kalça; sırt düz, kalçayı geri it."},
        {"id": "2290", "sets": 3, "reps": "10", "tip": "Tek bacak; arka ayak bench'te."},
        {"id": "0417", "sets": 3, "reps": "12", "tip": "Baldır; tepede 1 sn dur, tam uzat."},
        {"id": "1163", "sets": 3, "reps": "12", "tip": "Alt karın; bel yere yapışık."},
        {"id": "4624", "sets": 3, "reps": "12", "tip": "Karın; nefes vererek sık."},
    ]
}

WORKOUT_UPPER_B = {
    "key": "upperB", "name": "Üst B", "focus": "upper", "tag": "Üst · B", "note": "Omuz, sırt, göğüs, kol",
    "exercises": [
        {"id": "0405", "sets": 3, "reps": "8", "tip": "Omuz; bench dik, çekirdek sıkı."},
        {"id": "0293", "sets": 3, "reps": "10", "tip": "Sırt; kürek kemiklerini birleştir."},
        {"id": "2982", "sets": 3, "reps": "10", "tip": "Göğüs; yerde, dirsek 45°."},
        {"id": "0378", "sets": 3, "reps": "12", "tip": "Arka omuz; gövde öne eğik."},
        {"id": "0313", "sets": 3, "reps": "10", "tip": "Ön kol/biceps; nötr tutuş."},
        {"id": "0430", "sets": 3, "reps": "12", "tip": "Triceps; tam aç."},
        {"id": "0407", "sets": 3, "reps": "12", "tip": "Yan karın; tek dambıl, kontrollü yana eğil."},
    ]
}

WORKOUT_CARDIO = {
    "key": "cardio", "name": "Kardiyo", "focus": "cardio", "tag": "Kardiyo",
    "note": "Tam-vücut kondisyon günü — kürek öncelikli", "exercises": [],
    "cardio": [
        {"name": "Kürek (rower)", "type": "Kürek", "minutes": 20, "kcal": 200, "role": "Kondisyon",
         "tip": "20 dk interval (1 dk güçlü / 1 dk kolay) · tam vücut kondisyon."},
        {"name": "Eliptik", "type": "Eliptik", "minutes": 15, "kcal": 150, "role": "Toparlanma",
         "tip": "15 dk kolay-orta · eklem dostu toparlanma."},
        {"name": "Bisiklet", "type": "Bisiklet", "minutes": 25, "kcal": 220, "role": "Dayanıklılık",
         "tip": "25 dk sabit tempo · alt vücut dayanıklılık."},
    ]
}

WORKOUT_REST = {
    "key": "rest", "name": "Dinlenme", "focus": "rest", "tag": "", "note": "Toparlanma", "exercises": []
}

WORKOUT_PADEL = {
    "key": "padel", "name": "Padel", "focus": "cardio", "tag": "Padel", "note": "Ders / maç · kardiyo", "exercises": []
}

# weekday 0=Mon … 6=Sun default template
DAYS = [
    {**WORKOUT_UPPER_A, "wd": 0},
    {**WORKOUT_PADEL, "wd": 1, "key": "padelTue", "note": "Ders 20:00 + maç · kardiyo"},
    {**WORKOUT_LOWER_A, "wd": 2},
    {**WORKOUT_PADEL, "wd": 3, "key": "padelThu", "note": "Olursa · kardiyo"},
    {**WORKOUT_UPPER_B, "wd": 4},
    {**WORKOUT_CARDIO, "wd": 5},
    {**WORKOUT_REST, "wd": 6},
]

# icon per cardio type (matches Cronometer's cleaned labels, so Stats auto-matches these sessions)
CARDIO_ICON = {"Kürek": "🚣", "Eliptik": "🏃", "Bisiklet": "🚴", "Kardiyo": "🔥"}

# --- 12-week periodization ---------------------------------------------------------------------
# The block runs in three 4-week phases. Volume (base sets) rises then holds while intensity (RPE)
# climbs, which is the muscle-sparing pattern that matters most in a GLP-1 (Wegovy) deficit:
# resistance volume + high protein protect lean mass while fat comes off. `base_sets` is the sets
# per lift that phase.
BASE_SETS = 3
PHASES = [
    {"weeks": (1, 4), "key": "temel", "name": "Temel · Adaptasyon", "base_sets": 3, "rpe": "6–7",
     "note": "Hareketleri oturt, eklem/tendon adaptasyonu. GLP-1'de enerji düşebilir — teknik ve protein öncelik, yükü zorlamadan ilerlet."},
    {"weeks": (5, 8), "key": "gelisim", "name": "Gelişim · Yüklenme", "base_sets": 4, "rpe": "7–8",
     "note": "Öncelikli kaslarda (sırt/göğüs/omuz/karın) hacmi artır; her lift'te +1 set. Tekrar sabit (8/10/12) — hedef tekrarı RPE'de tamamlayınca yükü artır."},
    {"weeks": (9, 12), "key": "koruma", "name": "Koruma · Yoğunluk", "base_sets": 4, "rpe": "8",
     "note": "Açık büyüdükçe kası koru: yoğunluğu tut, yük bırakma. Yorgunluk birikirse 1 hafta deload (set/yoğunluk −%40). Uyku + protein kritik."},
]
PROGRAM_WEEKS = 12

# Each cardio machine has a DISTINCT function, so they are not interchangeable:
#   • Elliptical — low-impact warm-up + recovery (every lift day, 5 min easy at the start)
#   • Bike       — lower-body fat-loss finisher after UPPER days (spares the trained upper body)
#   • Rower      — full-body conditioning / intervals, on its own cardio day (back + legs + pull)
WARMUP = {"name": "Eliptik — ısınma", "type": "Eliptik", "minutes": 5, "role": "Isınma",
          "tip": "5 dk kolay tempo · eklem ve dolaşım hazırlığı."}
_FINISHERS = {
    "upper": {"name": "Bisiklet — yağ yakım", "type": "Bisiklet", "minutes": 10, "role": "Bitiriş",
              "tip": "10 dk orta tempo · alt vücut yağ yakımı."},
    "lower": {"name": "Eliptik — toparlanma", "type": "Eliptik", "minutes": 10, "role": "Bitiriş",
              "tip": "10 dk kolay tempo · eklem dostu toparlanma."},
    "full": {"name": "Bisiklet — yağ yakım", "type": "Bisiklet", "minutes": 10, "role": "Bitiriş",
             "tip": "10 dk orta tempo · yağ yakımı."},
}


def lifting_warmup(day: dict) -> dict | None:
    """Elliptical warm-up at the START of every lift day (5 min easy, low-impact)."""
    return dict(WARMUP) if day.get("focus") in ("upper", "lower", "full") else None


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


def lifting_finisher(day: dict) -> dict | None:
    """Fat-loss finisher at the END of a lift day, picked by function: bike after upper days (spares
    the trained upper body), elliptical after the leg day (low-impact). Done after the lifts so
    strength quality + muscle sparing come first, then low-intensity cardio for fat oxidation."""
    f = _FINISHERS.get(day.get("focus"))
    return dict(f) if f else None


TRAINING_DAYS = [d for d in DAYS if d["exercises"]]  # the 3 lifting days
SESSIONS_PER_WEEK = len([d for d in DAYS if d["focus"] in ("upper", "lower", "full")]) + 1  # +cardio = 4


def day_for(weekday: int) -> dict:
    return DAYS[weekday % 7]


def dynamic_day_for_date(target_date: dt.date, cal_events: list[dict] | None = None, start_date: dt.date | None = None) -> dict:
    """Intelligently assign the workout / rest / padel session for a specific date,
    adapting to Google Calendar padel sessions, start date kickoff, and muscle recovery.
    """
    iso = target_date.strftime("%Y-%m-%d")
    s_date = start_date or dt.date(2026, 10, 25)
    s_iso = s_date.strftime("%Y-%m-%d")
    dow = target_date.weekday()

    # 1. Official Start Date Kickoff: If starting on Sunday (e.g. 2026-10-25), provide Upper A
    if iso == s_iso and dow == 6:
        d = dict(WORKOUT_UPPER_A)
        d["wd"] = 6
        d["tag"] = "🏁 Başlangıç · Üst A"
        d["note"] = "1. Gün Resmi Başlangıç · Göğüs, sırt, omuz, kol"
        return d

    # 2. Check Google Calendar for Padel on target date
    cal_ev = None
    if cal_events:
        for ev in cal_events:
            if ev.get("date") == iso and ev.get("is_padel", True):
                cal_ev = ev
                break

    # 3. Dynamic adjustment for week of 26 Oct – 1 Nov (when start was Sunday 25 Oct):
    # Sunday was Upper A.
    # Monday 26 Oct: Alt A (Lower body, fresh legs before padel).
    # Tuesday 27 Oct: Padel Training (20:00) + Wegovy 1st injection.
    # Wednesday 28 Oct: Padel with Isa & Robbert (19:00).
    # Thursday 29 Oct: Aktif Dinlenme (recovery after double padel).
    # Friday 30 Oct: Upper B.
    # Saturday 31 Oct: Cardio.
    # Sunday 1 Nov: Rest.
    if s_date == dt.date(2026, 10, 25):
        if iso == "2026-10-26":
            d = dict(WORKOUT_LOWER_A)
            d["wd"] = 0
            d["note"] = "Bacak, kalça, karın · Salı padeli öncesi taze bacaklar"
            return d
        elif iso == "2026-10-27":
            d = dict(WORKOUT_PADEL)
            d["wd"] = 1
            d["note"] = "Padel Training 20:00 · 💉 1. Doz Wegovy"
            return d
        elif iso == "2026-10-28":
            d = dict(WORKOUT_PADEL)
            d["wd"] = 2
            d["note"] = "✅ Padel with Isa & Robbert (19:00–20:30)"
            return d
        elif iso == "2026-10-29":
            d = dict(WORKOUT_REST)
            d["wd"] = 3
            d["note"] = "Aktif Toparlanma · Çift padel sonrası dinlenme"
            return d
        elif iso == "2026-10-30":
            d = dict(WORKOUT_UPPER_B)
            d["wd"] = 4
            return d
        elif iso == "2026-10-31":
            d = dict(WORKOUT_CARDIO)
            d["wd"] = 5
            return d
        elif iso == "2026-11-01":
            d = dict(WORKOUT_REST)
            d["wd"] = 6
            return d

    # General dynamic rule for other weeks:
    if cal_ev:
        d = dict(WORKOUT_PADEL)
        d["wd"] = dow
        t_str = f" ({cal_ev['start_time']})" if cal_ev.get("start_time") else ""
        d["note"] = f"{cal_ev.get('summary', 'Padel')}{t_str} · Google Takvim"
        return d

    # Fallback to standard template for that weekday
    d = dict(day_for(dow))
    d["wd"] = dow
    return d



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


def workout_steps(day: dict, extra_sets: int = 0) -> list[dict]:
    """Full numbered workout sequence (1..N) for a lifting day:
    1) Eliptik warm-up (5 min)
    2..K+1) Strength exercises (muscle preservation & growth)
    K+2) Kürek / Water Rower (10 min metabolic fat-burn & back/posterior chain conditioning)
    K+3) Eliptik Zone-2 finisher (10 min fat oxidation & joint-friendly cooldown)
    """
    if not day.get("exercises"):
        return []
    warm = {
        "id": "cardio_warmup_eliptik",
        "kind": "cardio",
        "type": "Eliptik",
        "role": "Isınma",
        "name": "Eliptik — Isınma",
        "sets": 1,
        "reps": "5 dk",
        "minutes": 5,
        "eq": "Eliptik",
        "primary": ["quads", "glutes"],
        "secondary": ["calves", "hamstrings"],
        "tip": "5 dk kolay tempo · eklem ve dolaşım hazırlığı.",
    }
    lifts = [{**e, "kind": "lift"} for e in day_details(day, extra_sets)]
    rower = {
        "id": "cardio_rower_fatburn",
        "kind": "cardio",
        "type": "Kürek",
        "role": "Yağ Yakım",
        "name": "Kürek (Rower) — Yağ Yakım",
        "sets": 1,
        "reps": "10 dk",
        "minutes": 10,
        "eq": "Su Küreği (Rower)",
        "primary": ["lats", "upper back", "quads"],
        "secondary": ["glutes", "biceps", "abs"],
        "tip": "10 dk canlı tempo · metabolik yağ yakımı.",
    }
    eliptik_fin = {
        "id": "cardio_finisher_eliptik",
        "kind": "cardio",
        "type": "Eliptik",
        "role": "Bitiriş",
        "name": "Eliptik — Yağ Yakım & Soğuma",
        "sets": 1,
        "reps": "10 dk",
        "minutes": 10,
        "eq": "Eliptik",
        "primary": ["quads", "glutes"],
        "secondary": ["hamstrings", "calves"],
        "tip": "10 dk Zone-2 · toparlanma ve yağ yakımı.",
    }
    return [warm, *lifts, rower, eliptik_fin]


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
