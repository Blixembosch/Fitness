"""Exercise catalogue: the data we keep from openGym (names, which muscle each move works,
equipment). The proprietary Gym-Visual animations are NOT bundled — we show our own muscle map
instead. Pure data access; the UI formats what these return."""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "exercises.json"

# --- Turkish labels for the catalogue's English keys (body parts, muscles, equipment) ---
BP_TR = {
    "back": "Sırt", "cardio": "Kardiyo", "chest": "Göğüs", "full body": "Tüm vücut",
    "lower arms": "Ön kol", "lower legs": "Baldır", "neck": "Boyun", "shoulders": "Omuz",
    "upper arms": "Kol", "upper legs": "Bacak", "waist": "Karın",
}
MUSCLE_TR = {
    "abs": "Karın", "biceps": "Biceps", "calves": "Baldır", "cardiovascular system": "Kardiyo",
    "chest": "Göğüs", "pectorals": "Göğüs", "upper chest": "Üst göğüs", "core": "Core",
    "delts": "Omuz", "shoulders": "Omuz", "rear deltoids": "Arka omuz", "rotator cuff": "Rotator",
    "forearms": "Ön kol", "brachialis": "Brachialis",
    "glutes": "Kalça", "hamstrings": "Arka bacak", "hip flexors": "Kalça fleksörü",
    "lats": "Kanat (lat)", "lower back": "Bel", "upper back": "Üst sırt", "rhomboids": "Rhomboid",
    "traps": "Trapez", "trapezius": "Trapez",
    "triceps": "Triceps", "quads": "Ön bacak", "quadriceps": "Ön bacak", "adductors": "İç bacak",
    "abductors": "Dış bacak", "spine": "Omurga", "serratus anterior": "Serratus",
    "levator scapulae": "Boyun", "ankles": "Ayak bileği", "feet": "Ayak", "neck": "Boyun",
    "sartorius": "Sartorius", "soleus": "Soleus", "lower abs": "Alt karın", "obliques": "Yan karın",
}

# muscle -> coarse training group (for day chips / weekly volume)
_GROUP = {
    "Göğüs": {"chest", "pectorals", "upper chest", "serratus anterior"},
    "Sırt": {"lats", "upper back", "trapezius", "traps", "rhomboids", "lower back", "spine"},
    "Omuz": {"shoulders", "delts", "rear deltoids", "rotator cuff"},
    "Kol": {"biceps", "triceps", "forearms", "brachialis"},
    "Bacak": {"quads", "quadriceps", "glutes", "hamstrings", "adductors", "abductors", "hip flexors", "sartorius"},
    "Baldır": {"calves", "soleus"},
    "Karın": {"abs", "core", "lower abs", "obliques"},
    "Kardiyo": {"cardiovascular system"},
}
_GROUP_OF = {m: g for g, ms in _GROUP.items() for m in ms}


def group_of(muscle: str) -> str | None:
    return _GROUP_OF.get(muscle)
EQ_TR = {
    "body weight": "Vücut ağırlığı", "dumbbell": "Dambıl", "barbell": "Halter", "cable": "Kablo",
    "machine": "Makine", "kettlebell": "Kettlebell", "band": "Direnç bandı", "smith machine": "Smith",
    "ez barbell": "EZ bar", "leverage machine": "Kaldıraçlı makine", "stability ball": "Pilates topu",
    "medicine ball": "Sağlık topu", "resistance band": "Direnç bandı", "rope": "İp", "wheel roller": "Tekerlek",
    "weighted": "Ağırlıklı", "assisted": "Destekli", "bosu ball": "Bosu", "trap bar": "Trap bar",
    "roller": "Roller", "sled machine": "Kızak",
}

def tr_bp(k: str) -> str: return BP_TR.get(k, (k or "").title())
def tr_muscle(k: str) -> str: return MUSCLE_TR.get(k, (k or "").title())
def tr_eq(k: str) -> str: return EQ_TR.get(k, (k or "").title())


@lru_cache(maxsize=1)
def all_exercises() -> list[dict]:
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def by_id() -> dict[str, dict]:
    return {e["id"]: e for e in all_exercises()}


@lru_cache(maxsize=1)
def body_parts() -> list[str]:
    return sorted({e["bp"] for e in all_exercises()})


@lru_cache(maxsize=1)
def equipment() -> list[str]:
    return sorted({e["eq"] for e in all_exercises() if e.get("eq")})


def muscles_of(ex: dict) -> list[str]:
    """Primary first, then secondary, de-duplicated — the muscles a move trains."""
    out: list[str] = []
    for m in [ex.get("tg"), ex.get("mg"), *(ex.get("sm") or [])]:
        if m and m not in out:
            out.append(m)
    return out


def search(query: str = "", bp: str | None = None, eq: str | None = None, limit: int = 60) -> list[dict]:
    q = (query or "").strip().lower()
    out = []
    for e in all_exercises():
        if bp and e["bp"] != bp:
            continue
        if eq and e.get("eq") != eq:
            continue
        if q and q not in e["n"].lower():
            continue
        out.append(e)
        if len(out) >= limit:
            break
    return out
