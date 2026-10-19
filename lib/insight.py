"""A short, personalized coaching note for the Stats page. Uses Gemini when a key is configured
(st.secrets["GEMINI_API_KEY"]), otherwise a rule-based fallback that always works. Both produce
2–3 plain, prioritized, Turkish sentences from the user's numbers — general guidance, not medical."""
from __future__ import annotations
import json
import urllib.request

from lib import metrics


def rule_based(m: dict) -> str:
    gkg, loss, sets, deficit = m.get("gkg"), m.get("loss"), m.get("avg_sets"), m.get("deficit")
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


def gemini(m: dict, api_key: str) -> str | None:
    prompt = (
        "Sen kanıta dayalı, destekleyici bir fitness koçusun. Kullanıcı Wegovy kullanıyor, kas "
        "koruyarak yağ vermek istiyor ve yeni başlayan biri. Aşağıdaki haftalık verilere bakıp "
        "EN FAZLA 3 kısa Türkçe cümleyle, önceliklendirilmiş ve uygulanabilir tavsiye ver. "
        "Tıbbi iddia yok, abartı yok. Veriler:\n" + json.dumps(m, ensure_ascii=False)
    )
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-1.5-flash:generateContent?key=" + api_key)
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as r:
            out = json.load(r)
        return out["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:  # noqa: BLE001 — any failure falls back to rule-based
        return None


def coach_note(m: dict, api_key: str | None) -> tuple[str, bool]:
    """Returns (note, used_ai)."""
    if api_key:
        g = gemini(m, api_key)
        if g:
            return g, True
    return rule_based(m), False
