"""Parse Cronometer's other exports — biometrics (weight) and exercises (cardio/padel) — so the
user can upload them alongside dailysummary.csv and keep a single data source. Tolerant parsing;
nutrition's dailysummary parser stays in lib/nutrition.py."""
from __future__ import annotations
import io
import pandas as pd

LB_TO_KG = 0.45359237
_WEIGHT_METRICS = ("weight", "body mass", "vücut", "kilo")


def _read(file) -> pd.DataFrame:
    raw = file.read() if hasattr(file, "read") else file
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig", "replace")
    df = pd.read_csv(io.StringIO(raw))
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _lc(df):
    return {c.strip().lower(): c for c in df.columns}


def parse_biometrics(file) -> list[dict]:
    """[{date, w}] weight rows from Cronometer biometrics.csv (Day/Metric/Unit/Amount)."""
    df = _read(file)
    if df.empty:
        return []
    c = _lc(df)
    day, metric, unit, amt = c.get("day") or c.get("date"), c.get("metric"), c.get("unit"), c.get("amount")
    if not (day and metric and amt):
        return []
    out = {}
    for _, r in df.iterrows():
        m = str(r[metric]).strip().lower()
        if not any(k in m for k in _WEIGHT_METRICS):
            continue
        a = pd.to_numeric(r[amt], errors="coerce")
        d = pd.to_datetime(str(r[day]), errors="coerce")
        if pd.isna(a) or pd.isna(d):
            continue
        kg = float(a)
        if unit and any(x in str(r[unit]).lower() for x in ("lb", "pound")):
            kg *= LB_TO_KG
        if 30 < kg < 300:
            out[d.strftime("%Y-%m-%d")] = round(kg, 1)  # last row for a day wins
    return [{"date": k, "w": v} for k, v in out.items()]


def parse_exercises(file) -> pd.DataFrame:
    """[date, type, minutes, kcal] from Cronometer exercises.csv (Day/Exercise/Minutes/Calories)."""
    cols = ["date", "type", "minutes", "kcal"]
    df = _read(file)
    if df.empty:
        return pd.DataFrame(columns=cols)
    c = _lc(df)
    day, ex = c.get("day") or c.get("date"), c.get("exercise")
    mn, cal = c.get("minutes"), c.get("calories burned") or c.get("calories")
    if not (day and ex):
        return pd.DataFrame(columns=cols)
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[day], errors="coerce").dt.strftime("%Y-%m-%d")
    out["type"] = df[ex].astype(str)
    out["minutes"] = pd.to_numeric(df[mn], errors="coerce").fillna(0) if mn else 0
    out["kcal"] = pd.to_numeric(df[cal], errors="coerce").fillna(0) if cal else 0
    return out.dropna(subset=["date"]).reset_index(drop=True)


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
