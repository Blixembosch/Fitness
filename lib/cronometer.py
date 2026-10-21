"""Parse Cronometer's other exports — biometrics (weight) and exercises (cardio/padel/activity) — so
the user can upload them alongside dailysummary.csv and keep a single data source. Cronometer's
exercises export already mirrors Apple Health workouts, so this is the one source of truth for
cardio, padel and daily active energy. Tolerant parsing; nutrition's dailysummary parser stays in
lib/nutrition.py."""
from __future__ import annotations
import io
import re
import pandas as pd

LB_TO_KG = 0.45359237
_WEIGHT_METRICS = ("weight", "body mass", "vücut", "kilo")
_APPLE = re.compile(r"\s*\(apple health\)\s*$", re.I)
# Active-energy rows are a daily total, not a discrete workout — kept out of the session list.
_ACTIVE_ENERGY = "active energy"

# Normalised English type -> short Turkish label + whether it counts as a padel session.
TYPE_LABELS = {
    "tennis": "Padel",
    "cycling": "Bisiklet",
    "road biking": "Bisiklet",
    "walking": "Yürüyüş",
    "elliptical": "Eliptik",
    "rowing": "Kürek",
    "mixed cardio": "Kardiyo",
    "mix cardio": "Kardiyo",
    "functional strength training": "Güç",
    "traditional strength training": "Güç",
    "strength training": "Güç",
    "core training": "Güç",
    "gardening": "Bahçe",
}
_PADEL = ("tennis", "padel", "racquet", "raket")
# Apple Health strength-type sessions that count as a program (strength) workout — Cronometer
# only carries duration + kcal, so the match with our plan is at the session level, not per set.
_STRENGTH_LABELS = {"Güç"}


def category(label: str) -> str:
    """'padel' | 'strength' | 'cardio' for a cleaned type label."""
    if is_padel(label):
        return "padel"
    if label in _STRENGTH_LABELS:
        return "strength"
    return "cardio"


def _read(file) -> pd.DataFrame:
    raw = file.read() if hasattr(file, "read") else file
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig", "replace")
    df = pd.read_csv(io.StringIO(raw))
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _lc(df):
    return {c.strip().lower(): c for c in df.columns}


def clean_type(name: str) -> str:
    """Strip the '(Apple Health)' suffix and map to a short Turkish label."""
    base = _APPLE.sub("", str(name)).strip()
    return TYPE_LABELS.get(base.lower(), base)


def is_padel(name: str) -> bool:
    n = _APPLE.sub("", str(name)).strip().lower()
    return any(k in n for k in _PADEL)


def parse_biometrics(file) -> list[dict]:
    """[{date, w}] weight rows from Cronometer biometrics.csv (Day/Metric/Unit/Amount).

    The export mixes high-frequency heart-rate rows in with a handful of weight rows, so filter
    to weight metrics up front before doing any per-row work."""
    df = _read(file)
    if df.empty:
        return []
    c = _lc(df)
    day, metric, unit, amt = c.get("day") or c.get("date"), c.get("metric"), c.get("unit"), c.get("amount")
    if not (day and metric and amt):
        return []
    m = df[metric].astype(str).str.lower()
    mask = m.apply(lambda s: any(k in s for k in _WEIGHT_METRICS))
    w = df[mask]
    if w.empty:
        return []
    out = {}
    for _, r in w.iterrows():
        a = pd.to_numeric(r[amt], errors="coerce")
        d = pd.to_datetime(str(r[day]), errors="coerce")
        if pd.isna(a) or pd.isna(d):
            continue
        kg = float(a)
        if unit and any(x in str(r[unit]).lower() for x in ("lb", "pound")):
            kg *= LB_TO_KG
        if 30 < kg < 300:
            out[d.strftime("%Y-%m-%d")] = round(kg, 1)  # last row for a day wins
    return [{"date": k, "w": v} for k, v in sorted(out.items())]


def parse_exercises(file) -> pd.DataFrame:
    """[date, type, padel, minutes, kcal] workout sessions from Cronometer exercises.csv.

    Names are cleaned of the '(Apple Health)' suffix and mapped to short labels; Calories Burned
    is stored as a positive number (the export logs expenditure as negative). Daily
    'Active Energy Balance' rows are NOT sessions — use parse_active_energy for those."""
    cols = ["date", "type", "cat", "padel", "minutes", "kcal"]
    df = _read(file)
    if df.empty:
        return pd.DataFrame(columns=cols)
    c = _lc(df)
    day, ex = c.get("day") or c.get("date"), c.get("exercise")
    mn, cal = c.get("minutes"), c.get("calories burned") or c.get("calories")
    if not (day and ex):
        return pd.DataFrame(columns=cols)
    raw = df[ex].astype(str)
    keep = ~raw.str.lower().str.contains(_ACTIVE_ENERGY)
    df = df[keep]
    if df.empty:
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[day], errors="coerce").dt.strftime("%Y-%m-%d")
    out["type"] = df[ex].map(clean_type)
    out["cat"] = out["type"].map(category)
    out["padel"] = out["cat"] == "padel"
    out["minutes"] = pd.to_numeric(df[mn], errors="coerce").abs().fillna(0) if mn else 0
    out["kcal"] = pd.to_numeric(df[cal], errors="coerce").abs().fillna(0) if cal else 0
    return out.dropna(subset=["date"]).reset_index(drop=True)


def parse_active_energy(file) -> list[dict]:
    """[{date, kcal}] daily active energy from the 'Active Energy Balance' rows (kcal positive)."""
    df = _read(file)
    if df.empty:
        return []
    c = _lc(df)
    day, ex = c.get("day") or c.get("date"), c.get("exercise")
    cal = c.get("calories burned") or c.get("calories")
    if not (day and ex and cal):
        return []
    mask = df[ex].astype(str).str.lower().str.contains(_ACTIVE_ENERGY)
    a = df[mask]
    if a.empty:
        return []
    out = {}
    for _, r in a.iterrows():
        d = pd.to_datetime(str(r[day]), errors="coerce")
        k = pd.to_numeric(r[cal], errors="coerce")
        if pd.isna(d) or pd.isna(k):
            continue
        out[d.strftime("%Y-%m-%d")] = round(abs(float(k)))
    return [{"date": k, "kcal": v} for k, v in sorted(out.items())]


def detect(header_text: str) -> str:
    """Guess a Cronometer file from its header line: 'nutrition' | 'biometrics' | 'exercises' | ''."""
    h = header_text.lower()
    if "exercise" in h and ("minutes" in h or "calories burned" in h):
        return "exercises"
    if "metric" in h and "amount" in h:
        return "biometrics"
    if "energy (kcal)" in h or ("protein" in h and "group" in h):
        return "nutrition"
    return ""
