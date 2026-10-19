"""Fitness — our own Streamlit interface over the openGym exercise data.
5 pages, Home centered. The training program is auto-generated for the user's profile
(lib/program.py); Plan and Antrenman render it (no manual building). Phase 1: session data +
Cronometer CSV + manual weight. Persistence (Google Sheets) + Apple Health sync come next."""
from __future__ import annotations
import datetime as dt
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from lib import data, nutrition, bodymap, ui, program as P, metrics, insight

st.set_page_config(page_title="Fitness", page_icon="💪", layout="centered", initial_sidebar_state="collapsed")
ui.inject()

# ---------------- state ----------------
S = st.session_state
S.setdefault("page", "home")
# Body stats drive the targets. Age is an editable assumption (not in the data); everything else
# we know. Protein is fixed at a muscle-preservation 1.8 g/kg; calories = TDEE − deficit.
S.setdefault("body", {"birth": "1992-03-12", "height": 178, "sex": "male", "activity": "light", "deficit": 500})
PROTEIN_PER_KG = 1.8
S.setdefault("weights", [{"date": "2026-10-12", "w": 101.1}, {"date": "2026-10-16", "w": 101.1}, {"date": "2026-10-19", "w": 100.5}])
S.setdefault("workouts", [])          # [{date, key, name, muscles:(primary,secondary)}]
S.setdefault("padel", [])             # [iso date]
S.setdefault("setlog", {})            # "date|daykey|exid" -> completed set count
S.setdefault("nutrition", None)       # DataFrame or None

TODAY = dt.date.today()
NOW = dt.datetime.now()
GREET = "İyi geceler" if NOW.hour < 6 else "Günaydın" if NOW.hour < 12 else "İyi günler" if NOW.hour < 18 else "İyi akşamlar"
MON = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DOW = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
DOW_LONG = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
WEEK_START = TODAY - dt.timedelta(days=TODAY.weekday())
WEEK_ISO = WEEK_START.strftime("%Y-%m-%d")


# ---------------- helpers ----------------
def weights_df():
    df = pd.DataFrame(S["weights"])
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def latest_weight():
    df = weights_df()
    return (round(float(df["w"].iloc[-1]), 1), df["date"].iloc[-1]) if not df.empty else (None, None)


def nutrition_today():
    df = S["nutrition"]
    if df is None or df.empty:
        return None
    iso = TODAY.strftime("%Y-%m-%d")
    row = df[df["date"] == iso]
    return (row.iloc[0] if not row.empty else df.iloc[-1]).to_dict()


def workouts_week():
    return [w for w in S["workouts"] if w["date"] >= WEEK_ISO]


def padel_week():
    return [d for d in S["padel"] if d >= WEEK_ISO]


def navigate(page):
    S["page"] = page


def age_from(birth: str) -> int:
    try:
        b = dt.date.fromisoformat(birth)
        return max(16, (TODAY - b).days // 365)
    except Exception:  # noqa: BLE001
        return 35


def compute_targets():
    """Targets derived from the latest bodyweight + body stats, so they track as weight changes.
    Protein at 1.8 g/kg (muscle preservation in a deficit); calories = TDEE − deficit, floor 1500."""
    w = latest_weight()[0] or 100.0
    b = S["body"]
    age = age_from(b["birth"]) if b.get("birth") else b.get("age", 35)
    t = nutrition.estimate_targets(w, b["height"], age, b["sex"], b["activity"], b["deficit"],
                                   floor=1500, protein_per_kg=PROTEIN_PER_KG)
    S["targets"] = {k: t[k] for k in ("kcal", "protein", "carbs", "fat")}
    S["tdee"] = t["tdee"]


compute_targets()


@st.cache_data(show_spinner=False, ttl=3600)
def _coach_note(payload_key: str):
    """Cached so Gemini is called at most once per unique metric set per hour."""
    m = json.loads(payload_key)
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:  # noqa: BLE001 — no secrets file configured
        key = None
    return insight.coach_note(m, key)


# ---------------- pages ----------------
def page_home():
    st.markdown(
        f"<h1 style='margin:0 0 2px;font-size:27px'>{GREET}, Anıl</h1>"
        f"<div style='color:var(--muted);font-size:13.5px;margin-bottom:16px'>{DOW_LONG[TODAY.weekday()]} · {TODAY.day} {MON[TODAY.month-1]}</div>",
        unsafe_allow_html=True,
    )
    nt = nutrition_today()
    prot = int(nt["protein"]) if nt else 0
    kcal = int(nt["kcal"]) if nt else 0
    t = S["targets"]
    wk = len(workouts_week())
    pad = len(padel_week())

    # four rings = the week at a glance (antrenman / padel / protein / kalori)
    pad_t = 2  # planned padel days/week
    r1 = ui.ring(wk / 3 if wk else 0, "var(--blue)", f"{wk}<small>/3</small>", "Antrenman", 44)
    r2 = ui.ring(pad / pad_t if pad_t else 0, "var(--teal)", f"{pad}<small>/{pad_t}</small>", "Padel", 44)
    r3 = ui.ring(prot / t["protein"] if t["protein"] else 0, "var(--orange)", f"{prot}<small>/{t['protein']}</small>", "Protein", 44)
    r4 = ui.ring(kcal / t["kcal"] if t["kcal"] else 0, "var(--green)", f"{kcal}<small>/{t['kcal']}</small>", "Kalori", 44)
    st.markdown(f"<div class='rings'>{r1}{r2}{r3}{r4}</div>", unsafe_allow_html=True)

    # today hero from the program
    day = P.day_for(TODAY.weekday())
    color = P.FOCUS_COLOR[day["focus"]]
    st.markdown("<p class='eyebrow' style='margin-top:14px'>Bugün</p>", unsafe_allow_html=True)
    if day["exercises"]:
        load = P.day_load(day)
        chips = "".join(f"<span class='chip'>{g}</span>" for g in P.day_groups(day))
        st.markdown(
            f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 30%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 14%,var(--surface)), var(--surface) 78%); border:1px solid color-mix(in srgb,{color} 28%,var(--line))'>"
            f"<div class='kick' style='color:{color}'>● {day['tag']}</div>"
            f"<h2>{day['name']}</h2><div class='chiprow'>{chips}</div>"
            f"<div style='color:var(--muted);font-size:13px;margin-top:8px'>{load['exercises']} egzersiz · {load['sets']} set · ~{load['minutes']} dk</div></div>",
            unsafe_allow_html=True,
        )
        st.button("▶ Antrenmana git", type="primary", use_container_width=True, on_click=navigate, args=("workout",))
    else:
        st.markdown(
            f"<div class='hero' style='background:linear-gradient(165deg, color-mix(in srgb,{color} 12%,var(--surface)), var(--surface) 80%);border:1px solid var(--line)'>"
            f"<div class='kick' style='color:{color}'>● {day['tag'] or 'Bugün'}</div>"
            f"<h2>{day['name']}</h2><div style='color:var(--muted);font-size:13px;margin-top:6px'>{day.get('note','')}</div></div>",
            unsafe_allow_html=True,
        )

    # weight
    w, _ = latest_weight()
    if w is not None:
        df = weights_df()
        delta = df["w"].iloc[-1] - df["w"].iloc[0] if len(df) > 1 else 0
        dcls = "good" if delta < 0 else "bad" if delta > 0 else ""
        st.markdown(
            f"<div class='fcard'><div class='eyebrow'>Vücut ağırlığı</div>"
            f"<div style='display:flex;align-items:flex-end;gap:10px'>"
            f"<span style='font-family:Nunito;font-weight:900;font-size:36px;line-height:.95'>{w:.1f}</span>"
            f"<span style='color:var(--faint);font-weight:700'>kg</span>"
            f"<span class='{dcls}' style='margin-inline-start:auto;font-weight:700;font-size:13px'>{'↓' if delta<0 else '↑' if delta>0 else '–'} {abs(delta):.1f} kg bu hafta</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )


def _week_strip():
    done = {w["date"] for w in S["workouts"]}
    pad = set(S["padel"])
    cells = []
    for i in range(7):
        d = WEEK_START + dt.timedelta(days=i)
        iso = d.strftime("%Y-%m-%d")
        day = P.DAYS[i]
        color = P.FOCUS_COLOR[day["focus"]]
        is_today = d == TODAY
        dot = "var(--green)" if iso in done or iso in pad else (color if day["focus"] != "rest" else "transparent")
        border = f"1px solid {color}" if is_today else "1px solid var(--line)"
        cells.append(
            f"<div style='flex:1;text-align:center;background:var(--surface);border:{border};border-radius:12px;padding:8px 0'>"
            f"<div style='font-size:10px;color:var(--faint);font-weight:700'>{DOW[i]}</div>"
            f"<div style='font-size:15px;font-weight:800;margin-top:3px;{'color:'+color if is_today else ''}'>{d.day}</div>"
            f"<div style='width:5px;height:5px;border-radius:50%;margin:5px auto 0;background:{dot}'></div></div>"
        )
    st.markdown(f"<div style='display:flex;gap:4px;margin-bottom:14px'>{''.join(cells)}</div>", unsafe_allow_html=True)


def page_plan():
    st.markdown(f"<h1 style='margin:0'>Plan</h1><div class='muted' style='font-size:13px;margin-bottom:14px'>{WEEK_START.day} {MON[WEEK_START.month-1]}–{(WEEK_START+dt.timedelta(days=6)).day} {MON[(WEEK_START+dt.timedelta(days=6)).month-1]} · {P.SESSIONS_PER_WEEK} antrenman</div>", unsafe_allow_html=True)
    _week_strip()
    today_day = P.day_for(TODAY.weekday())

    # today hero with exercise list
    if today_day["exercises"]:
        color = P.FOCUS_COLOR[today_day["focus"]]
        load = P.day_load(today_day)
        chips = "".join(f"<span class='chip'>{g}</span>" for g in P.day_groups(today_day))
        rows = "".join(
            f"<div style='display:flex;align-items:center;gap:10px;padding:9px 0;border-top:1px solid var(--line)'>"
            f"<span style='width:22px;height:22px;border-radius:7px;background:color-mix(in srgb,{color} 18%,transparent);color:{color};font-weight:800;font-size:12px;display:flex;align-items:center;justify-content:center'>{i+1}</span>"
            f"<span style='flex:1;font-weight:600;font-size:14px'>{e['name']}</span>"
            f"<span class='muted' style='font-size:13px;font-weight:600'>{e['sets']}×{e['reps']}</span></div>"
            for i, e in enumerate(P.day_details(today_day))
        )
        st.markdown(
            f"<p class='eyebrow'>Bugün</p>"
            f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 28%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 13%,var(--surface)), var(--surface) 80%);border:1px solid color-mix(in srgb,{color} 26%,var(--line))'>"
            f"<div class='kick' style='color:{color}'>● {today_day['tag']}</div><h2>{today_day['name']}</h2>"
            f"<div class='chiprow'>{chips}</div>"
            f"<div style='color:var(--muted);font-size:13px;margin:8px 0 6px'>{load['exercises']} egzersiz · {load['sets']} set · ~{load['minutes']} dk</div>"
            f"{rows}</div>",
            unsafe_allow_html=True,
        )
        st.button("▶ Antrenmana git", type="primary", use_container_width=True, on_click=navigate, args=("workout",))

    # upcoming days
    st.markdown("<p class='eyebrow' style='margin-top:16px'>Haftanın geri kalanı</p>", unsafe_allow_html=True)
    for i in range(7):
        if i == TODAY.weekday():
            continue
        day = P.DAYS[i]
        color = P.FOCUS_COLOR[day["focus"]]
        sub = (f"{P.day_load(day)['exercises']} egzersiz · ~{P.day_load(day)['minutes']} dk" if day["exercises"] else day.get("note", ""))
        chips = "".join(f"<span class='chip' style='font-size:11px'>{g}</span>" for g in P.day_groups(day)) if day["exercises"] else ""
        chips = f"<div class='chiprow' style='margin:7px 0 0'>{chips}</div>" if chips else ""
        st.markdown(
            f"<div style='display:flex;background:var(--surface);border:1px solid var(--line);border-radius:16px;overflow:hidden;margin-bottom:9px'>"
            f"<div style='width:5px;background:{color}'></div>"
            f"<div style='padding:12px 14px;flex:1'>"
            f"<div style='font-weight:800;font-size:14px'>{DOW_LONG[i]} "
            f"<span style='font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:{color};background:color-mix(in srgb,{color} 15%,transparent);padding:2px 7px;border-radius:6px;margin-inline-start:4px'>{day['tag'] or 'Dinlenme'}</span></div>"
            f"<div class='muted' style='font-size:12.5px;margin-top:3px'>{sub}</div>{chips}</div></div>",
            unsafe_allow_html=True,
        )


def _exercise_box(i, e, color, day_key, date_iso):
    """A functional exercise box: a set-progress ring, the move, set-complete buttons, and a
    tap-to-reveal muscle map. The ring fills as sets are marked done."""
    key = f"{date_iso}|{day_key}|{e['id']}"
    total = int(e["sets"])
    done = S["setlog"].get(key, 0)
    finished = done >= total
    with st.container(border=True):
        c1, c2 = st.columns([1, 3.2])
        with c1:
            ringcol = "var(--green)" if finished else color
            st.markdown(
                f"<div style='text-align:center'>{ui.ring_svg(done / total if total else 0, ringcol, 54)}"
                f"<div style='font-family:Nunito;font-weight:800;font-size:13px;margin-top:2px'>{done}/{total}</div></div>",
                unsafe_allow_html=True,
            )
        with c2:
            chips = "".join(f"<span class='chip' style='font-size:10.5px;padding:3px 8px'>{data.tr_muscle(m)}</span>" for m in e["primary"][:3])
            st.markdown(
                f"<div style='font-weight:700;font-size:15px'>{i}. {e['name']} {'✅' if finished else ''}</div>"
                f"<div style='font-family:Nunito;font-weight:800;color:{color};font-size:14px;margin:2px 0 4px'>{e['sets']}×{e['reps']}</div>"
                f"<div class='chiprow'>{chips}</div>",
                unsafe_allow_html=True,
            )
        b1, b2, _ = st.columns([1.3, 1, 2])
        if b1.button("✓ Set", key=f"s_{key}", use_container_width=True, disabled=finished):
            S["setlog"][key] = min(total, done + 1)
            st.rerun()
        if b2.button("↺", key=f"r_{key}", use_container_width=True, disabled=done == 0):
            S["setlog"][key] = 0
            st.rerun()
        with st.expander("Hangi kası çalıştırır?"):
            st.markdown(f"<div class='muted' style='font-size:12.5px;margin:-4px 0 6px'>{data.tr_eq(e.get('eq',''))}</div>", unsafe_allow_html=True)
            st.markdown(bodymap.body_map(e["primary"], e["secondary"]) + ui.legend(color), unsafe_allow_html=True)
            st.markdown(f"<div class='muted' style='font-size:12.5px;margin-top:8px'>💡 {e.get('tip','')}</div>", unsafe_allow_html=True)


def page_workout():
    st.markdown("<h1 style='margin:0 0 10px'>Antrenman</h1>", unsafe_allow_html=True)
    training = P.TRAINING_DAYS
    names = [d["name"] for d in training]
    today = P.day_for(TODAY.weekday())
    default = today["name"] if today in training else names[0]
    if not (today["exercises"]):
        st.info(f"Bugün **{today['name']}** — {today.get('note','')}. İstersen aşağıdan bir antrenman seç ve çalış.")
    choice = st.segmented_control("Antrenman", names, default=default, key="wsel") or default
    day = next(d for d in training if d["name"] == choice)
    color = P.FOCUS_COLOR[day["focus"]]
    load = P.day_load(day)
    st.markdown(
        f"<div class='muted' style='font-size:13px;margin:2px 0 12px'>{day['note']} · {load['exercises']} egzersiz · {load['sets']} set · ~{load['minutes']} dk</div>",
        unsafe_allow_html=True,
    )
    done_iso = TODAY.strftime("%Y-%m-%d")
    done_sets = sum(S["setlog"].get(f"{done_iso}|{day['key']}|{e['id']}", 0) for e in day["exercises"])
    st.markdown(
        f"<div class='fcard' style='padding:10px 14px;display:flex;align-items:center;gap:10px'>"
        f"<div style='flex:1'><div style='height:8px;border-radius:5px;background:var(--surface-2);overflow:hidden'>"
        f"<div style='height:100%;width:{round(done_sets/load['sets']*100) if load['sets'] else 0}%;background:{color};border-radius:5px'></div></div></div>"
        f"<div style='font-family:Nunito;font-weight:800;font-size:13px'>{done_sets}/{load['sets']} set</div></div>",
        unsafe_allow_html=True,
    )
    for i, e in enumerate(P.day_details(day), 1):
        _exercise_box(i, e, color, day["key"], done_iso)

    already = any(w["date"] == done_iso and w.get("key") == day["key"] for w in S["workouts"])
    if already:
        st.success("Bugün bu antrenman tamamlandı ✓")
    elif st.button("✅ Bu antrenmanı tamamladım", type="primary", use_container_width=True):
        prim, sec = P.day_muscles(day)
        S["workouts"].append({"date": done_iso, "key": day["key"], "name": day["name"], "primary": prim, "secondary": sec})
        st.success(f"{day['name']} kaydedildi (bu oturumda).")
        st.rerun()

    with st.expander("🔎 Egzersiz ara (hangi kası çalıştırır)"):
        q = st.text_input("Ara", placeholder="örn. shoulder press", label_visibility="collapsed", key="exq")
        if q:
            for ex in data.search(q, limit=8):
                p = [m for m in [ex.get("tg"), ex.get("mg")] if m]
                s = [m for m in (ex.get("sm") or []) if m not in p]
                st.markdown(f"**{ex['n']}** · {data.tr_bp(ex['bp'])}", unsafe_allow_html=True)
                st.markdown(bodymap.body_map(p, s), unsafe_allow_html=True)


def page_stats():
    st.markdown("<h1 style='margin:0 0 10px'>İstatistik</h1>", unsafe_allow_html=True)
    period = st.segmented_control("Dönem", ["Hafta", "Ay"], default="Hafta", key="sp") or "Hafta"
    days = 7 if period == "Hafta" else 30
    start = (TODAY - dt.timedelta(days=days - 1)).strftime("%Y-%m-%d")
    wk = [w for w in S["workouts"] if w["date"] >= start]
    ndf = S["nutrition"]
    # Nutrition habit is read from the last up-to-30 LOGGED days (imports are historical, so a
    # calendar window can be empty); weight/workouts follow the chosen period.
    recent = ndf.tail(30) if ndf is not None and not ndf.empty else pd.DataFrame()
    avg_prot = round(recent["protein"].mean()) if not recent.empty else 0
    avg_kcal = round(recent["kcal"].mean()) if not recent.empty else 0
    met = int((recent["protein"] >= S["targets"]["protein"]).sum()) if not recent.empty else 0
    wdf = weights_df()
    wwin = wdf[wdf["date"] >= pd.Timestamp(start)] if not wdf.empty else wdf
    wdelta = (wwin["w"].iloc[-1] - wwin["w"].iloc[0]) if len(wwin) > 1 else 0
    weight_kg = latest_weight()[0]
    deficit = (S["tdee"] - avg_kcal) if avg_kcal else None  # positive = daily deficit vs maintenance
    tiles = "".join([
        ui.tile("Antrenman", str(len(wk)), f"{days} günde"),
        ui.tile("Protein ort.", f"{avg_prot}<small> g</small>", f"{met}/{len(recent)} gün hedefte" if not recent.empty else "veri yok", "good" if met else ""),
        ui.tile("Kalori ort.", (f"{avg_kcal}" if avg_kcal else "–"), "son kayıtlar", ""),
        ui.tile("Kilo", f"{wdelta:+.1f}", "kg", "good" if wdelta < 0 else "bad" if wdelta > 0 else ""),
    ])
    st.markdown(f"<div class='tiles'>{tiles}</div>", unsafe_allow_html=True)

    # ---- evidence-based targets ----
    gkg = metrics.protein_per_kg(avg_prot, weight_kg)
    loss = metrics.weekly_loss_pct(wwin if len(wwin) > 1 else wdf)
    # avg weekly sets across trained muscle groups, from the program
    vol = {}
    for d in P.TRAINING_DAYS:
        for e in P.day_details(d):
            if e["primary"]:
                g = data.group_of(e["primary"][0])
                if g and g != "Kardiyo":
                    vol[g] = vol.get(g, 0) + int(e["sets"])
    avg_sets = round(sum(vol.values()) / len(vol)) if vol else 0

    rows = []
    s = metrics.band(gkg, *metrics.PROTEIN_GKG)
    cls, word = metrics.verdict(s, "düşük", "yüksek")
    rows.append(ui.metric_row("Protein (g/kg)", f"{gkg if gkg else '–'} g/kg",
                              f"{metrics.PROTEIN_GKG[0]}–{metrics.PROTEIN_GKG[1]}", cls, word,
                              "Wegovy'de kası korumanın #1 kaldıracı; açıkta en kritik sayı."))
    s = metrics.band(loss, *metrics.LOSS_PCT_WK)
    cls, word = metrics.verdict(s, "yavaş", "hızlı (kas riski)")
    rows.append(ui.metric_row("Kilo kaybı hızı", f"{loss if loss is not None else '–'} %/hafta",
                              f"%{metrics.LOSS_PCT_WK[0]}–{metrics.LOSS_PCT_WK[1]}", cls, word,
                              "Çok hızlı kayıp kasını da götürür; yavaş ve istikrarlı daha iyi."))
    s = metrics.band(avg_sets, *metrics.SETS_PER_MUSCLE)
    cls, word = metrics.verdict(s, "düşük", "yüksek")
    rows.append(ui.metric_row("Haftalık set / kas", f"~{avg_sets} set",
                              f"{metrics.SETS_PER_MUSCLE[0]}–{metrics.SETS_PER_MUSCLE[1]}", cls, word,
                              "Kas başına haftalık efektif set — büyüme/koruma için."))
    s = metrics.band(deficit, *metrics.DEFICIT_KCAL)
    cls, word = metrics.verdict(s, "küçük", "büyük (kas riski)")
    rows.append(ui.metric_row("Kalori açığı", f"{deficit if deficit is not None else '–'} kcal",
                              f"{metrics.DEFICIT_KCAL[0]}–{metrics.DEFICIT_KCAL[1]}", cls, word,
                              "Orta düzey açık yağı eritir, kası korur (~0,5–1%/hafta)."))
    # smart coach note (Gemini if a key is set, else rule-based) — the headline of Stats
    payload = {"gkg": gkg, "protein_target": S["targets"]["protein"], "avg_protein": avg_prot,
               "loss_pct_week": loss, "avg_sets_per_muscle": avg_sets, "deficit_kcal": deficit,
               "avg_kcal": avg_kcal, "weight_kg": weight_kg}
    note, used_ai = _coach_note(json.dumps(payload, sort_keys=True))
    st.markdown("<div class='eyebrow' style='margin-top:14px'>Akıllı özet" + ("  ·  Gemini" if used_ai else "") + "</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='fcard' style='border-color:color-mix(in srgb,var(--blue) 26%,var(--line))'>"
        f"<div style='font-size:14px;line-height:1.6'>💬 {note}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='eyebrow' style='margin-top:14px'>Kanıta dayalı hedefler</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='fcard' style='padding:4px 16px 14px'>{''.join(rows)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='eyebrow' style='margin-top:16px'>Kilo trendi</div>", unsafe_allow_html=True)
    if not wdf.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=wdf["date"], y=wdf["w"], mode="markers", marker=dict(size=6, color="#30d158"), name="Tartım"))
        if len(wdf) >= 3:
            ma = wdf["w"].rolling(7, min_periods=1).mean()
            fig.add_trace(go.Scatter(x=wdf["date"], y=ma, mode="lines", line=dict(color="#30d158", width=3), name="7-gün ort."))
        fig.update_layout(height=210, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#9aa1ae"), showlegend=False)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", ticksuffix=" kg")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Çizgi: 7 günlük hareketli ortalama (günlük dalgalanmayı yumuşatır).")

    with st.expander("Haftalık hacim (kas grubu)"):
        vol: dict[str, int] = {}
        for d in P.TRAINING_DAYS:
            for e in P.day_details(d):
                if e["primary"]:
                    g = data.group_of(e["primary"][0])
                    if g:
                        vol[g] = vol.get(g, 0) + int(e["sets"])
        if vol:
            mx = max(vol.values())
            order = ["Göğüs", "Sırt", "Omuz", "Kol", "Bacak", "Baldır", "Karın"]
            bars = "".join(ui.bar(g, f"{vol[g]} set", vol[g] / mx * 100, "var(--blue)") for g in order if g in vol)
            st.markdown(f"<div class='bars'>{bars}</div>", unsafe_allow_html=True)

    with st.expander("Kas haritası · bu hafta"):
        if wk:
            prim = [m for w in wk for m in w.get("primary", [])]
            sec = [m for w in wk for m in w.get("secondary", [])]
            cap = "Kayıtlı antrenmanlara göre"
        else:
            prim, sec = [], []
            for d in P.TRAINING_DAYS:
                p, s = P.day_muscles(d)
                prim += p
                sec += s
            cap = "Programa göre (henüz kayıt yok)"
        st.markdown(bodymap.body_map(prim, sec) + ui.legend("var(--blue)"), unsafe_allow_html=True)
        st.caption(cap)

    with st.expander("ℹ️ Hedefler neye dayanıyor?"):
        st.markdown(
            "- **Protein 1,6–2,2 g/kg:** açıkta kas kaybını azaltır (Helms ve ark.; Examine özetleri).\n"
            "- **Kayıp %0,5–1/hafta:** daha hızlısı yağla birlikte kası da götürür.\n"
            "- **Kas başına 10–20 set/hafta:** hipertrofi için genel aralık (yeni başlayanlar alt uçta).\n"
            "- **GLP-1'de (Wegovy):** kaybın büyük kısmı yağ olsa da yağsız kütle riski var; **protein + ağırlık antrenmanı** bunu azaltır.\n\n"
            "_Genel bilgilendirme; tıbbi tavsiye değildir._"
        )


def page_nutrition():
    st.markdown("<h1 style='margin:0 0 10px'>Beslenme</h1>", unsafe_allow_html=True)
    up = st.file_uploader("Cronometer dailysummary.csv yükle", type="csv")
    if up is not None:
        try:
            S["nutrition"] = nutrition.parse_cronometer(up)
            st.success(f"{len(S['nutrition'])} gün yüklendi.")
        except Exception as e:  # noqa: BLE001
            st.error(f"Okunamadı: {e}")

    nt = nutrition_today()
    t = S["targets"]
    if nt:
        ds = nutrition.day_summary(nt, t)
        kc = ds["kcal"]
        pct = min(1, (kc["consumed"] / kc["target"]) if kc["target"] else 0)
        st.markdown(
            "<div class='fcard'><div style='display:flex;align-items:center;gap:18px'>"
            + ui.ring_svg(pct, "var(--green)", size=84)
            + f"<div><div style='font-family:Nunito;font-weight:900;font-size:28px'>{int(kc['consumed'])} <small style='color:var(--faint);font-size:15px'>/ {int(kc['target'])}</small></div>"
            f"<div class='muted' style='font-size:13px'>kcal · {int(kc['remaining'])} kaldı</div></div></div></div>",
            unsafe_allow_html=True,
        )
        bars = "".join([
            ui.bar("Protein", f"{int(ds['protein']['consumed'])} / {ds['protein']['target']} g", ds['protein']['pct'] or 0, "var(--orange)", primary=True),
            ui.bar("Karbonhidrat", f"{int(ds['carbs']['consumed'])} / {ds['carbs']['target']} g", ds['carbs']['pct'] or 0, "var(--teal)"),
            ui.bar("Yağ", f"{int(ds['fat']['consumed'])} / {ds['fat']['target']} g", ds['fat']['pct'] or 0, "var(--purple)"),
        ])
        st.markdown(f"<div class='fcard'><div class='eyebrow'>Makrolar · bugün</div><div class='bars'>{bars}</div></div>", unsafe_allow_html=True)
        # 7-day protein
        last7 = S["nutrition"].tail(7)
        if len(last7) > 1:
            fig = go.Figure(go.Bar(x=last7["date"], y=last7["protein"], marker_color="#ff9f0a"))
            fig.add_hline(y=t["protein"], line_dash="dot", line_color="#9aa1ae")
            fig.update_layout(height=180, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#9aa1ae"))
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", ticksuffix=" g")
            st.markdown("<div class='eyebrow'>Son günler · protein</div>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Cronometer'dan **dailysummary.csv** yükle; kalori, protein ve makroları burada özetlerim. Protein, Wegovy'de kas koruma için öncelikli.")

    st.markdown("<div class='eyebrow' style='margin-top:6px'>Kilo kaydet</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    nw = c1.number_input("kg", min_value=40.0, max_value=250.0, value=float(latest_weight()[0] or 100.0), step=0.1, label_visibility="collapsed")
    if c2.button("Kaydet", use_container_width=True):
        iso = TODAY.strftime("%Y-%m-%d")
        S["weights"] = [x for x in S["weights"] if x["date"] != iso] + [{"date": iso, "w": round(nw, 1)}]
        st.success("Kaydedildi (bu oturumda).")
        st.rerun()

    t = S["targets"]
    wkg = latest_weight()[0] or 100.0
    st.markdown(
        f"<div class='fcard' style='margin-top:8px'><div class='eyebrow'>Senin için hesaplanan hedef</div>"
        f"<div style='font-size:13.5px;line-height:1.7'><b>{t['protein']} g protein</b> (~{PROTEIN_PER_KG} g/kg · kas koruma)"
        f"&nbsp;·&nbsp;<b>{t['kcal']} kcal</b> (TDEE ~{S['tdee']} − {S['body']['deficit']} açık)"
        f"&nbsp;·&nbsp;{t['carbs']} g karb · {t['fat']} g yağ</div></div>",
        unsafe_allow_html=True,
    )
    with st.expander("⚙️ Hedef ayarları (yaş, boy, aktivite, açık)"):
        b = S["body"]
        bd = st.date_input("Doğum tarihi", value=dt.date.fromisoformat(b.get("birth", "1992-03-12")),
                           min_value=dt.date(1940, 1, 1), max_value=TODAY, format="DD.MM.YYYY")
        b["birth"] = bd.isoformat()
        st.caption(f"Yaş: {age_from(b['birth'])}")
        b["height"] = st.number_input("Boy (cm)", 120, 220, int(b["height"]))
        acts = ["light", "moderate", "high"]
        b["activity"] = st.selectbox("Aktivite düzeyi", acts, index=acts.index(b["activity"]),
                                     format_func=lambda x: {"light": "Az hareketli (masa başı)", "moderate": "Orta", "high": "Yüksek"}[x])
        b["deficit"] = st.number_input("Günlük kalori açığı", 0, 1000, int(b["deficit"]), step=50)
        st.caption("Protein 1,8 g/kg'de sabit (kas koruma); kilo değiştikçe hedefler otomatik güncellenir. Genel bilgilendirme, tıbbi tavsiye değil.")


# ---------------- nav (top) + routing ----------------
NAV = [("plan", "🗓"), ("workout", "🏋️"), ("home", "🏠"), ("stats", "📊"), ("nutrition", "🔥")]
LABEL = {"plan": "Plan", "workout": "Antrenman", "home": "Ana Sayfa", "stats": "İstatistik", "nutrition": "Beslenme"}
PAGES = {"home": page_home, "plan": page_plan, "workout": page_workout, "stats": page_stats, "nutrition": page_nutrition}

cols = st.columns([1, 1, 1.25, 1, 1])
for col, (key, icon) in zip(cols, NAV):
    with col:
        st.button(icon, key=f"nav_{key}", use_container_width=True,
                  type="primary" if S["page"] == key else "secondary",
                  on_click=navigate, args=(key,))
st.markdown(f"<div style='text-align:center;color:var(--faint);font-size:11px;margin:1px 0 10px'>{LABEL[S['page']]}</div>", unsafe_allow_html=True)

PAGES[S["page"]]()
st.caption("Tasarım önizlemesi · program sana özel · veriler şimdilik oturum içinde")
