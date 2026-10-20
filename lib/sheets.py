"""Read the user's Google Sheet (weight + workouts pushed from Apple Health via a Shortcut).
Reads the published CSV of each tab over HTTPS — no OAuth, no service account — and parses it
tolerantly. All network/parse failures degrade to empty, so the app works with no sync too."""
from __future__ import annotations
import io
import urllib.request
import pandas as pd

# The user's sheet (override with st.secrets["SHEET_ID"]).
DEFAULT_SHEET_ID = "1GnfbwWETyrNXJm_t5x0MrxrW_CmclH2MiQS8UuZf42M"


def csv_url(sheet_id: str, tab: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={tab}"


def fetch_tab(sheet_id: str, tab: str, timeout: int = 8) -> pd.DataFrame:
    try:
        with urllib.request.urlopen(csv_url(sheet_id, tab), timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
        df = pd.read_csv(io.StringIO(raw))
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception:  # noqa: BLE001 — unreachable / tab missing / not shared -> no sync
        return pd.DataFrame()


def _col(df: pd.DataFrame, *names):
    for n in names:
        if n in df.columns:
            return n
    return None


def _to_date(value):
    """Parse dates tolerantly, including Apple's '20 Oct 2026 at 09:08'. Returns a Timestamp or NaT."""
    s = str(value).replace(" at ", " ")
    return pd.to_datetime(s, errors="coerce")


def parse_weights(df: pd.DataFrame) -> list[dict]:
    """[{date 'YYYY-MM-DD', w float}] from a Weight tab (date + weight_kg/weight/kg)."""
    if df is None or df.empty:
        return []
    dcol = _col(df, "date", "day", "tarih")
    wcol = _col(df, "weight_kg", "weight", "kg", "kilo", "ağırlık")
    if not dcol or not wcol:
        return []
    out = []
    for _, row in df.iterrows():
        d = _to_date(row[dcol])
        w = pd.to_numeric(row[wcol], errors="coerce")
        if pd.notna(d) and pd.notna(w) and 30 < float(w) < 300:
            out.append({"date": d.strftime("%Y-%m-%d"), "w": round(float(w), 1)})
    return out


# workout types we count as padel (Apple Health often logs it as Tennis)
_PADEL = ("padel", "tennis", "racquet", "raket")


def parse_workouts(df: pd.DataFrame) -> pd.DataFrame:
    """Normalised [date, type, minutes, kcal] from a Workouts tab; empty frame if unusable."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "type", "minutes", "kcal"])
    dcol = _col(df, "date", "day", "tarih")
    tcol = _col(df, "type", "workout", "activity", "tür", "aktivite")
    mcol = _col(df, "minutes", "duration", "dakika", "süre")
    kcol = _col(df, "kcal", "energy", "calories", "kalori")
    if not dcol:
        return pd.DataFrame(columns=["date", "type", "minutes", "kcal"])
    out = pd.DataFrame()
    out["date"] = df[dcol].apply(_to_date).dt.strftime("%Y-%m-%d")
    out["type"] = df[tcol].astype(str) if tcol else ""
    out["minutes"] = pd.to_numeric(df[mcol], errors="coerce").fillna(0) if mcol else 0
    out["kcal"] = pd.to_numeric(df[kcol], errors="coerce").fillna(0) if kcol else 0
    return out.dropna(subset=["date"]).reset_index(drop=True)


def padel_dates(workouts: pd.DataFrame) -> list[str]:
    if workouts is None or workouts.empty:
        return []
    mask = workouts["type"].astype(str).str.lower().apply(lambda s: any(k in s for k in _PADEL))
    return sorted(set(workouts.loc[mask, "date"]))
