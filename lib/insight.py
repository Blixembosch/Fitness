"""A short, personalized coaching note for the Stats page. Uses Gemini when a key is configured
(st.secrets["GEMINI_API_KEY"]), otherwise a rule-based fallback that always works. Both produce
2–3 plain, prioritized, Turkish sentences from the user's numbers — general guidance, not medical."""
from __future__ import annotations
import json
import urllib.error
import urllib.request

from lib import metrics


def rule_based(m: dict) -> str:
    gkg = m.get("gkg")
    loss = m.get("loss") if m.get("loss") is not None else m.get("loss_pct_week")
    sets = m.get("avg_sets") if m.get("avg_sets") is not None else m.get("avg_sets_per_muscle")
    deficit = m.get("deficit") if m.get("deficit") is not None else m.get("deficit_kcal")
    tgt = m.get("protein_target")
    msgs = []
    if gkg is not None and gkg < metrics.PROTEIN_GKG[0]:
        msgs.append(f"Önceliğin protein: ~{gkg} g/kg düşük, günde ~{tgt} g'a çıkar — Wegovy'de kası korumanın en kritik adımı.")
    elif gkg is not None and gkg >= metrics.PROTEIN_GKG[0]:
        msgs.append(f"Protein iyi (~{gkg} g/kg) — böyle sürdür.")
    if loss is not None and loss > metrics.LOSS_PCT_WK[1]:
        msgs.append(f"Kilo kaybın %{loss}/hafta, hedefin biraz üstünde; kası korumak için ağırlık antrenmanını ve proteini aksatma.")
    elif loss is not None and 0 <= loss < 0.3:
        msgs.append("Kayıp yavaş; istersen açığı biraz artırabilirsin.")
    if sets and sets < metrics.SETS_PER_MUSCLE[0]:
        msgs.append(f"Kas başına ~{sets} set/hafta alt sınırda; vücut alıştıkça 10–15 sete çıkaralım.")
    if not msgs:
        msgs.append("Sayıların hedef aralıklarında görünüyor — istikrarı koru!")
    return " ".join(msgs[:2])


# Tried in order; model names drift over time, so fall through to the next on a 404/not-found.
# `gemini-flash-latest` is an alias that tracks the current flash model, so it's tried first.
MODELS = ["gemini-flash-latest", "gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]


def gemini(m: dict, api_key: str, model: str | None = None) -> str | None:
    prompt = (
        "Sen kanıta dayalı, destekleyici bir fitness koçusun. Kullanıcı Wegovy kullanıyor, kas "
        "koruyarak yağ vermek istiyor ve yeni başlayan biri. Aşağıdaki haftalık verilere bakıp "
        "EN FAZLA 3 kısa Türkçe cümleyle, önceliklendirilmiş ve uygulanabilir tavsiye ver. "
        "Tıbbi iddia yok, abartı yok. Veriler:\n" + json.dumps(m, ensure_ascii=False)
    )
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    candidates = ([model] if model else []) + [x for x in MODELS if x != model]
    for name in candidates:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{name}:generateContent?key={api_key}")
        try:
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                out = json.load(r)
            return out["candidates"][0]["content"]["parts"][0]["text"].strip()
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):  # model name not available here — try the next one
                continue
            return None
        except Exception:  # noqa: BLE001 — network/parse failure -> rule-based fallback
            return None
    return None


def coach_note(m: dict, api_key: str | None, model: str | None = None) -> tuple[str, bool]:
    """Returns (note, used_ai)."""
    if api_key:
        g = gemini(m, api_key, model)
        if g:
            return g, True
    return rule_based(m), False
