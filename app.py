"""Fitness — our own Streamlit interface over the openGym exercise data.
5 pages, Home far-left in the nav. The training program is auto-generated for the user's profile
(lib/program.py); Plan and Antrenman render it (no manual building). Cronometer CSV is the single
data source: dailysummary = nutrition, biometrics = weight, exercises = cardio/padel/active energy
(it already mirrors Apple Health). 2026-10-31 is the baseline date progress is measured from."""
from __future__ import annotations
import datetime as dt
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from lib import data, nutrition, bodymap, ui, program as P, metrics, insight, sheets, cronometer

st.set_page_config(page_title="Fitness", page_icon="💪", layout="wide", initial_sidebar_state="collapsed")
ui.inject()

# ---------------- state ----------------
S = st.session_state
S.setdefault("page", "home")
# Body stats drive the targets. Age is an editable assumption (not in the data); everything else
# we know. Protein is fixed at a muscle-preservation 1.8 g/kg; calories = TDEE − deficit.
S.setdefault("body", {"birth": "1992-03-12", "height": 178, "sex": "male", "activity": "light",
                      "deficit": 500, "kcal_goal": 1900})
PROTEIN_PER_KG = 1.8
PROGRAM_WEEKS = 12          # the plan runs as a 12-week block from the baseline
PADEL_TARGET = 2           # planned padel days/week (actual can exceed it)
STRENGTH_TARGET = 3        # planned strength sessions/week (Üst A / Alt A / Üst B)
S.setdefault("weights", [{"date": "2026-10-12", "w": 101.1}, {"date": "2026-10-16", "w": 101.1}, {"date": "2026-10-19", "w": 100.5}])
S.setdefault("workouts", [])          # [{date, key, name, muscles:(primary,secondary)}]
S.setdefault("padel", [])             # [iso date]
S.setdefault("cron_ex", [])           # Cronometer exercises rows [{date,type,padel,minutes,kcal}]
S.setdefault("active_kcal", {})       # {date: kcal} daily active energy from Cronometer exercises
S.setdefault("setlog", {})            # "date|daykey|exid" -> completed set count
S.setdefault("nutrition", None)       # DataFrame or None

START_DATE = dt.date(2026, 10, 31)    # baseline: progress (weight, streak) is measured from here
START_ISO = START_DATE.strftime("%Y-%m-%d")

TODAY = dt.date.today()
NOW = dt.datetime.now()
GREET = "İyi geceler" if NOW.hour < 6 else "Günaydın" if NOW.hour < 12 else "İyi günler" if NOW.hour < 18 else "İyi akşamlar"
MON = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DOW = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
DOW_LONG = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
WEEK_START = TODAY - dt.timedelta(days=TODAY.weekday())
WEEK_ISO = WEEK_START.strftime("%Y-%m-%d")


# ---------------- helpers ----------------
def _sheet_id():
    try:
        return st.secrets.get("SHEET_ID") or sheets.DEFAULT_SHEET_ID
    except Exception:  # noqa: BLE001
        return sheets.DEFAULT_SHEET_ID


@st.cache_data(ttl=300, show_spinner=False)
def _sheet(sheet_id: str):
    """(weights, padel_dates, workout_count, daily_dict) from the Google Sheet. Cached 5 min."""
    w = sheets.parse_weights(sheets.fetch_tab(sheet_id, "Weight"))
    wo = sheets.parse_workouts(sheets.fetch_tab(sheet_id, "Workouts"))
    daily = sheets.parse_daily(sheets.fetch_tab(sheet_id, "Daily"))
    return w, sheets.padel_dates(wo), int(len(wo)), daily


def _sheet_data():
    try:
        return _sheet(_sheet_id())
    except Exception:  # noqa: BLE001
        return [], [], 0, {}


def cron_ex_df():
    """Cronometer workout sessions as a DataFrame [date, type, padel, minutes, kcal]."""
    cols = ["date", "type", "padel", "minutes", "kcal"]
    return pd.DataFrame(S["cron_ex"]) if S["cron_ex"] else pd.DataFrame(columns=cols)


def activity_daily():
    """Merged daily activity: steps/distance from the Sheet, active-kcal + exercise-minutes from
    Cronometer (its exercises export mirrors Apple Health). {date: {steps,active_kcal,exercise_min,distance_km}}."""
    daily = {k: dict(v) for k, v in (_sheet_data()[3] or {}).items()}

    def rec(d):
        return daily.setdefault(d, {"steps": 0, "active_kcal": 0, "exercise_min": 0, "distance_km": 0.0})

    cx = cron_ex_df()
    if not cx.empty:
        for d, m in cx.groupby("date")["minutes"].sum().items():
            r = rec(d)
            r["exercise_min"] = max(r.get("exercise_min", 0) or 0, round(float(m)))
    for d, k in S["active_kcal"].items():
        r = rec(d)
        r["active_kcal"] = max(r.get("active_kcal", 0) or 0, int(k))
    return daily


def today_activity():
    """Today's activity (steps/active kcal/exercise min/distance), or the latest logged day."""
    daily = activity_daily()
    if not daily:
        return None
    iso = TODAY.strftime("%Y-%m-%d")
    return daily.get(iso) or daily[sorted(daily)[-1]]


def weights_df():
    # Google-Sheet weigh-ins (Apple Health) merged with any manual entries; manual wins per day.
    rows = {x["date"]: x["w"] for x in _sheet_data()[0]}
    for x in S["weights"]:
        rows[x["date"]] = x["w"]
    df = pd.DataFrame([{"date": d, "w": w} for d, w in rows.items()])
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


def padel_dates_all():
    """Every known padel date (manual + Sheet + Cronometer 'padel' flag)."""
    allp = set(S["padel"]) | set(_sheet_data()[1])
    cx = cron_ex_df()
    if not cx.empty and "padel" in cx:
        allp |= set(cx[cx["padel"]]["date"])
    return allp


def padel_week():
    return [d for d in padel_dates_all() if d >= WEEK_ISO]


def baseline_weight():
    """(kg, Timestamp) nearest the 2026-10-31 baseline: first weigh-in on/after it, else the last
    one before it (provisional until the baseline date arrives)."""
    df = weights_df()
    if df.empty:
        return (None, None)
    after = df[df["date"] >= pd.Timestamp(START_DATE)]
    row = after.iloc[0] if not after.empty else df.iloc[-1]
    return (round(float(row["w"]), 1), row["date"])


def progress_since_start():
    """(delta_kg, started). started becomes True once a weigh-in on/after the baseline exists;
    before that we're still counting down and delta is 0."""
    base, _ = baseline_weight()
    latest, ldate = latest_weight()
    started = base is not None and ldate is not None and ldate >= pd.Timestamp(START_DATE)
    delta = round(latest - base, 1) if (started and base is not None and latest is not None) else 0.0
    return (delta, started)


def cardio_summary(days: int):
    """Cardio/padel/activity rollup over the last `days` of LOGGED sessions (anchored to the latest
    logged date, since Cronometer imports are historical). None when there's nothing logged."""
    cx = cron_ex_df()
    if cx.empty:
        return None
    anchor = pd.to_datetime(cx["date"]).max()
    start = (anchor - pd.Timedelta(days=days - 1)).strftime("%Y-%m-%d")
    win = cx[cx["date"] >= start]
    if win.empty:
        return None
    by_type = (win.groupby("type")
               .agg(sessions=("type", "size"), minutes=("minutes", "sum"), kcal=("kcal", "sum"))
               .reset_index().sort_values("minutes", ascending=False))
    return {
        "sessions": int(len(win)), "minutes": int(win["minutes"].sum()), "kcal": int(win["kcal"].sum()),
        "by_type": by_type, "recent": win.sort_values("date", ascending=False).head(6),
        "span": f"{pd.to_datetime(start).day} {MON[pd.to_datetime(start).month-1]}–{anchor.day} {MON[anchor.month-1]}",
    }


def program_progress():
    """Where we are in the 12-week block from the 2026-10-31 baseline.
    Before the baseline: {started:False, days_to_start:n}. After: week 1..12 + a 0..1 pct."""
    d = (TODAY - START_DATE).days
    if d < 0:
        return {"started": False, "week": 0, "pct": 0.0, "days_to_start": -d}
    week = min(PROGRAM_WEEKS, d // 7 + 1)
    return {"started": True, "week": week, "pct": min(1.0, (d + 1) / (PROGRAM_WEEKS * 7)), "days_to_start": 0}


def strength_dates_all():
    """Every date with a strength session: in-app logged workouts + Cronometer strength-category
    sessions (Apple Health 'Functional/Traditional Strength Training')."""
    s = {w["date"] for w in S["workouts"]}
    cx = cron_ex_df()
    if not cx.empty and "cat" in cx:
        s |= set(cx[cx["cat"] == "strength"]["date"])
    return s


def week_counts(week_iso: str):
    """(strength_sessions, padel_sessions) for the 7-day week starting week_iso. Actual counts,
    uncapped — play padel 4× and it reads 4 even though the target is 2."""
    end = (pd.Timestamp(week_iso) + pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    win = lambda ds: sum(1 for d in ds if week_iso <= d <= end)
    return win(strength_dates_all()), win(padel_dates_all())


def program_week_grid(week_start: dt.date):
    """Per-day plan vs actual for a week: [{dow, day, name, color, kind, planned, done}]. 'done'
    means a matching session landed that day (strength session for lift days, a padel session for
    padel days)."""
    strv, padv = strength_dates_all(), padel_dates_all()
    grid = []
    for i in range(7):
        d = week_start + dt.timedelta(days=i)
        iso = d.strftime("%Y-%m-%d")
        day = P.DAYS[i]
        is_padel = "padel" in day["key"].lower()
        is_lift = day["focus"] in ("upper", "lower", "full")
        kind = "padel" if is_padel else "lift" if is_lift else day["focus"]
        color = "var(--teal)" if is_padel else P.FOCUS_COLOR.get(day["focus"], "var(--line)")
        done = (iso in strv) if is_lift else (iso in padv) if is_padel else False
        grid.append({"dow": DOW[i], "day": d.day, "name": day["name"], "color": color,
                     "kind": kind, "planned": is_lift or is_padel, "done": done})
    return grid


def current_phase():
    """(phase, extra_sets) for wherever we are in the 12-week block (Phase 1 before it starts)."""
    phase = P.phase_for(program_progress()["week"])
    return phase, P.phase_extra_sets(phase)


def program_adjustment():
    """Dynamic weekly guidance on top of the fixed phase plan: reads the weight-loss rate and this
    week's adherence and returns (status, lines[]). 'status' tints the card (good/warn/bad/'')."""
    pp = program_progress()
    if not pp["started"]:
        return ("", [f"Başlangıca **{pp['days_to_start']} gün**. İlk blok *Temel · Adaptasyon*: "
                     "hareketleri oturt, protein ve uykuyu baz al. 31 Ekim'de ağırlık ve seri sayacı başlıyor."])
    wdf = weights_df()
    wkg = latest_weight()[0]
    lines, status = [], "good"
    loss = metrics.weekly_loss_pct(wdf) if (wdf is not None and len(wdf) > 1) else None
    if loss is not None and wkg:
        if loss > 1.0:
            status = "bad"
            lines.append(f"📉 Kayıp **%{loss}/hafta** — hızlı (kas riski). Kaloriyi ~150–200 artır ya da ekstra kardiyoyu kıs; protein ve ağırlığı koru.")
        elif loss < 0.4:
            lines.append(f"📉 Kayıp **%{loss}/hafta** — yavaş. Hedefe sadık kal; istikrar sürerse açığı ~100–150 artırabilirsin.")
        else:
            lines.append(f"📉 Kayıp **%{loss}/hafta** — ideal bantta (%0,5–1). Aynen devam.")
    else:
        lines.append("📉 Kilo trendi için birkaç tartım gerekli (Cronometer biometrics yükle).")
    strv, pad = week_counts(WEEK_ISO)
    if strv < STRENGTH_TARGET:
        if status == "good":
            status = "warn"
        lines.append(f"🏋️ Bu hafta **{strv}/{STRENGTH_TARGET}** antrenman — kalan güç günlerini tamamla (kas koruma önceliği).")
    if pad < PADEL_TARGET:
        lines.append(f"🎾 Padel **{pad}/{PADEL_TARGET}** — hedefe ulaşmaya çalış (ekstrası serbest).")
    return (status, lines)


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
    Protein at 1.8 g/kg (muscle preservation in a deficit). Calories follow a manual goal when set
    (kcal_goal), otherwise TDEE − deficit. We also keep the implied daily deficit + weekly loss."""
    w = latest_weight()[0] or 100.0
    b = S["body"]
    age = age_from(b["birth"]) if b.get("birth") else b.get("age", 35)
    t = nutrition.estimate_targets(w, b["height"], age, b["sex"], b["activity"], b["deficit"],
                                   floor=1500, protein_per_kg=PROTEIN_PER_KG, kcal=b.get("kcal_goal"))
    S["targets"] = {k: t[k] for k in ("kcal", "protein", "carbs", "fat")}
    S["tdee"] = t["tdee"]
    S["deficit_now"] = t["deficit"]
    S["weekly_loss"] = nutrition.weekly_loss(t["deficit"])


compute_targets()


def _gemini_key():
    try:
        return st.secrets.get("GEMINI_API_KEY")
    except Exception:  # noqa: BLE001 — no secrets configured
        return None


@st.cache_data(show_spinner=False, ttl=1800)
def _coach_note(payload_key: str, has_key: bool):
    """Cached so Gemini is called at most once per unique metric set. `has_key` is part of the
    cache key so adding/removing the API key refreshes the note."""
    m = json.loads(payload_key)
    model = None
    try:
        model = st.secrets.get("GEMINI_MODEL")  # optional pin; auto-detect if unset
    except Exception:  # noqa: BLE001
        model = None
    return insight.coach_note(m, _gemini_key() if has_key else None, model)


# ---------------- pages ----------------
def _counter_card():
    """Top-of-Home hero: a countdown to the 2026-10-31 baseline, then Week X/12 + this week's
    plan dots once the block has started."""
    pp = program_progress()
    if not pp["started"]:
        n = pp["days_to_start"]
        return (
            "<div class='counter'>"
            f"<div><div class='big'>{n}<small> gün</small></div><div class='lbl'>Başlangıca · 31 Ekim</div></div>"
            "<div style='flex:1;min-width:140px'><div style='font-weight:800;font-size:15px'>12 haftalık program</div>"
            "<div class='muted' style='font-size:13px;margin-top:3px'>Baz ağırlık ve seri 31 Ekim'de başlıyor; o güne kadar hazırlık.</div></div>"
            "</div>"
        )
    grid = program_week_grid(WEEK_START)
    dots = "".join(f"<i class='{'on' if g['done'] else ''}'></i>" for g in grid if g["planned"])
    pct = round(pp["pct"] * 100)
    return (
        "<div class='counter'>"
        f"<div><div class='big'>{pp['week']}<small>/{PROGRAM_WEEKS}</small></div><div class='lbl'>Hafta · 12 haftalık program</div></div>"
        "<div style='flex:1;min-width:160px'>"
        f"<div style='font-weight:800;font-size:14px'>Bu hafta planı</div><div class='weekdots'>{dots}</div>"
        f"<div style='height:7px;border-radius:5px;background:var(--surface-2);margin-top:10px;overflow:hidden'>"
        f"<div style='height:100%;width:{pct}%;background:var(--blue);border-radius:5px'></div></div></div>"
        "</div>"
    )


def page_home():
    st.markdown(
        f"<h1 style='margin:0 0 2px;font-size:28px'>{GREET}, Anıl</h1>"
        f"<div style='color:var(--muted);font-size:13.5px;margin-bottom:14px'>{DOW_LONG[TODAY.weekday()]} · {TODAY.day} {MON[TODAY.month-1]}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_counter_card(), unsafe_allow_html=True)

    nt = nutrition_today()
    prot = int(nt["protein"]) if nt else 0
    kcal = int(nt["kcal"]) if nt else 0
    t = S["targets"]
    strv, pad = week_counts(WEEK_ISO)

    # four rings = the week at a glance (antrenman / padel / protein / kalori). Padel shows the
    # real count against a target of 2 but isn't capped — 4 played reads 4/2.
    r1 = ui.ring(strv / STRENGTH_TARGET if strv else 0, "var(--blue)", f"{strv}<small>/{STRENGTH_TARGET}</small>", "Antrenman", 50)
    r2 = ui.ring(pad / PADEL_TARGET if PADEL_TARGET else 0, "var(--teal)", f"{pad}<small>/{PADEL_TARGET}</small>", "Padel", 50)
    r3 = ui.ring(prot / t["protein"] if t["protein"] else 0, "var(--orange)", f"{prot}<small>/{t['protein']}</small>", "Protein", 50)
    r4 = ui.ring(kcal / t["kcal"] if t["kcal"] else 0, "var(--green)", f"{kcal}<small>/{t['kcal']}</small>", "Kalori", 50)
    st.markdown(f"<div class='rings'>{r1}{r2}{r3}{r4}</div>", unsafe_allow_html=True)

    # desktop: today's workout on the left, weight + activity on the right
    left, right = st.columns([1.35, 1], gap="medium")

    with left:
        day = P.day_for(TODAY.weekday())
        color = P.FOCUS_COLOR[day["focus"]]
        st.markdown("<p class='eyebrow'>Bugün</p>", unsafe_allow_html=True)
        phase, pextra = current_phase()
        if day["exercises"]:
            load = P.day_load(day, pextra)
            chips = "".join(f"<span class='chip'>{g}</span>" for g in P.day_groups(day))
            chips += f"<span class='chip' style='color:var(--green)'>🏃 Eliptik/kürek {phase['ell']} dk</span>"
            st.markdown(
                f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 30%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 14%,var(--surface)), var(--surface) 78%); border:1px solid color-mix(in srgb,{color} 28%,var(--line))'>"
                f"<div class='kick' style='color:{color}'>● {day['tag']} · RPE {phase['rpe']}</div>"
                f"<h2>{day['name']}</h2><div class='chiprow'>{chips}</div>"
                f"<div style='color:var(--muted);font-size:13px;margin-top:8px'>{load['exercises']} egzersiz · {load['sets']} set · +{phase['ell']} dk eliptik/kürek</div></div>",
                unsafe_allow_html=True,
            )
            st.button("▶ Antrenmana git", type="primary", use_container_width=True, on_click=navigate, args=("workout",))
        else:
            cardio = P.day_cardio(day)
            extra = ""
            if cardio:
                chips = "".join(f"<span class='chip'>{P.CARDIO_ICON.get(c['type'],'🔥')} {c['name']} · {c['minutes']} dk</span>" for c in cardio)
                extra = f"<div class='chiprow' style='margin-top:10px'>{chips}</div>"
            st.markdown(
                f"<div class='hero' style='background:linear-gradient(165deg, color-mix(in srgb,{color} 12%,var(--surface)), var(--surface) 80%);border:1px solid var(--line)'>"
                f"<div class='kick' style='color:{color}'>● {day['tag'] or 'Bugün'}</div>"
                f"<h2>{day['name']}</h2><div style='color:var(--muted);font-size:13px;margin-top:6px'>{day.get('note','')}</div>{extra}</div>",
                unsafe_allow_html=True,
            )

    with right:
        w, _ = latest_weight()
        if w is not None:
            delta, started = progress_since_start()
            if started:
                dcls = "good" if delta < 0 else "bad" if delta > 0 else ""
                note = f"<span class='{dcls}' style='margin-inline-start:auto;font-weight:700;font-size:13px'>{'↓' if delta<0 else '↑' if delta>0 else '–'} {abs(delta):.1f} kg başlangıçtan</span>"
            else:
                note = "<span style='margin-inline-start:auto;color:var(--faint);font-weight:700;font-size:13px'>baz: 31 Eki</span>"
            st.markdown(
                f"<div class='fcard' style='margin-bottom:10px'><div class='eyebrow'>Vücut ağırlığı</div>"
                f"<div style='display:flex;align-items:flex-end;gap:10px'>"
                f"<span style='font-family:Nunito;font-weight:900;font-size:36px;line-height:.95'>{w:.1f}</span>"
                f"<span style='color:var(--faint);font-weight:700'>kg</span>{note}"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        act = today_activity()
        if act:
            st.markdown(
                "<div class='fcard' style='margin-bottom:10px'><div class='eyebrow'>Aktivite · son gün</div>"
                "<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:12px;text-align:center'>"
                f"<div><div style='font-family:Nunito;font-weight:900;font-size:21px'>{int(act['steps'])}</div><div class='muted' style='font-size:11px'>adım</div></div>"
                f"<div><div style='font-family:Nunito;font-weight:900;font-size:21px'>{int(act['active_kcal'])}</div><div class='muted' style='font-size:11px'>aktif kcal</div></div>"
                f"<div><div style='font-family:Nunito;font-weight:900;font-size:21px'>{int(act['exercise_min'])}</div><div class='muted' style='font-size:11px'>egz. dk</div></div>"
                f"<div><div style='font-family:Nunito;font-weight:900;font-size:21px'>{act['distance_km']:.1f}</div><div class='muted' style='font-size:11px'>km</div></div>"
                "</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='fcard' style='border-style:dashed'><div class='eyebrow'>Aktivite</div>"
                "<div class='muted' style='font-size:13px;line-height:1.6'>Cronometer verini (exercises · dailysummary · biometrics) "
                "<b>Beslenme</b> sekmesinden yükle; adım, aktif kcal, egzersiz dakikası ve mesafe burada görünür.</div></div>",
                unsafe_allow_html=True,
            )
        # phase mini-card (not a duplicate of the rings — shows where we are in the 12-week block)
        pp2 = program_progress()
        phz = P.phase_for(pp2["week"])
        wk_txt = f"Hafta {pp2['week']}/{P.PROGRAM_WEEKS}" if pp2["started"] else f"Başlangıca {pp2['days_to_start']} gün"
        st.markdown(
            f"<div class='fcard' style='margin-bottom:0'><div class='eyebrow'>Program fazı</div>"
            f"<div style='font-family:Nunito;font-weight:900;font-size:18px'>{phz['name']}</div>"
            f"<div class='muted' style='font-size:12.5px;margin-top:3px'>{wk_txt} · {phz['base_sets']} set · RPE {phz['rpe']}</div></div>",
            unsafe_allow_html=True,
        )


def _plan_exercise_box(i, e, color):
    """Plan overview card (HTML only, so it tiles in a responsive grid): round number badge +
    move + muscle chips + sets×reps."""
    chips = "".join(f"<span class='chip' style='font-size:10.5px;padding:3px 8px'>{data.tr_muscle(m)}</span>" for m in e["primary"][:3])
    return (
        f"<div class='exrow'>"
        f"<div style='width:34px;height:34px;border-radius:50%;background:color-mix(in srgb,{color} 20%,var(--surface-2));color:{color};"
        f"font-family:Nunito;font-weight:800;font-size:14px;display:flex;align-items:center;justify-content:center;flex-shrink:0'>{i}</div>"
        f"<div style='flex:1;min-width:0'><div style='font-weight:700;font-size:14px'>{e['name']}</div>"
        f"<div class='chiprow' style='margin-top:4px'>{chips}</div></div>"
        f"<div style='font-family:Nunito;font-weight:800;color:{color};font-size:15px;flex-shrink:0'>{e['sets']}×{e['reps']}</div></div>"
    )


def _cardio_box(c):
    """Cardio action card (HTML only, tiles in the grid): icon + name + duration badge + how-to."""
    icon = P.CARDIO_ICON.get(c.get("type"), "🔥")
    return (
        f"<div class='exrow' style='align-items:flex-start'>"
        f"<div style='width:38px;height:38px;border-radius:50%;background:color-mix(in srgb,var(--green) 18%,var(--surface-2));"
        f"display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:19px'>{icon}</div>"
        f"<div style='flex:1;min-width:0'>"
        f"<div style='display:flex;align-items:baseline;gap:8px'><div style='font-weight:700;font-size:14px'>{c['name']}</div>"
        f"<div style='font-family:Nunito;font-weight:800;color:var(--green);font-size:14px'>{c['minutes']} dk</div></div>"
        f"<div class='muted' style='font-size:12px;margin-top:4px;line-height:1.5'>{c.get('tip','')}</div></div></div>"
    )


def page_plan():
    end = WEEK_START + dt.timedelta(days=6)
    st.markdown(
        f"<h1 style='margin:0'>Plan</h1><div class='muted' style='font-size:13px;margin-bottom:12px'>"
        f"{WEEK_START.day} {MON[WEEK_START.month-1]}–{end.day} {MON[end.month-1]} · {P.SESSIONS_PER_WEEK} antrenman</div>",
        unsafe_allow_html=True,
    )
    phase, extra = current_phase()
    pp = program_progress()
    status, lines = program_adjustment()
    tint = {"good": "var(--green)", "warn": "var(--orange)", "bad": "var(--red)", "": "var(--blue)"}[status]
    wk_txt = f"Hafta {pp['week']}/{P.PROGRAM_WEEKS}" if pp["started"] else "Başlamadı"
    body = "".join(f"<div style='font-size:13px;line-height:1.6;margin-top:4px'>{l}</div>" for l in lines)
    st.markdown(
        f"<div class='fcard' style='border-color:color-mix(in srgb,{tint} 34%,var(--line))'>"
        f"<div style='display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap'>"
        f"<div class='eyebrow' style='margin:0'>Program durumu</div>"
        f"<div style='font-size:12px;font-weight:800;color:{tint}'>{phase['name']} · {wk_txt} · RPE {phase['rpe']}</div></div>"
        f"<div class='muted' style='font-size:12.5px;margin-top:6px'>{phase['note']}</div>{body}</div>",
        unsafe_allow_html=True,
    )
    sel = int(S.get("plan_day", TODAY.weekday()))
    done = {w["date"] for w in S["workouts"]}
    pad = set(S["padel"])

    # clickable day strip — pick any day to see its plan
    cols = st.columns(7)
    for i, col in enumerate(cols):
        d = WEEK_START + dt.timedelta(days=i)
        iso = d.strftime("%Y-%m-%d")
        day = P.DAYS[i]
        color = P.FOCUS_COLOR[day["focus"]]
        dot = "var(--green)" if (iso in done or iso in pad) else (color if day["focus"] != "rest" else "var(--line)")
        with col:
            st.markdown(
                f"<div style='text-align:center;font-size:10px;color:var(--faint);font-weight:700'>{DOW[i]}"
                f"<span style='display:inline-block;width:5px;height:5px;border-radius:50%;background:{dot};margin-inline-start:4px;vertical-align:middle'></span></div>",
                unsafe_allow_html=True,
            )
            st.button(str(d.day), key=f"pd_{i}", use_container_width=True,
                      type="primary" if i == sel else "secondary", on_click=lambda i=i: S.__setitem__("plan_day", i))

    day = P.DAYS[sel]
    color = P.FOCUS_COLOR[day["focus"]]
    sel_date = WEEK_START + dt.timedelta(days=sel)
    title = "Bugün" if sel == TODAY.weekday() else DOW_LONG[sel]
    st.markdown(f"<p class='eyebrow' style='margin-top:14px'>{title}</p>", unsafe_allow_html=True)

    if day["exercises"]:
        load = P.day_load(day, extra)
        fin = P.lifting_finisher(day, phase["ell"])
        chips = "".join(f"<span class='chip'>{g}</span>" for g in P.day_groups(day))
        st.markdown(
            f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 28%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 13%,var(--surface)), var(--surface) 80%);border:1px solid color-mix(in srgb,{color} 26%,var(--line))'>"
            f"<div class='kick' style='color:{color}'>● {day['tag']} · RPE {phase['rpe']}</div><h2>{day['name']}</h2>"
            f"<div class='chiprow'>{chips}</div>"
            f"<div style='color:var(--muted);font-size:13px;margin-top:8px'>{load['exercises']} egzersiz · {load['sets']} set · +{phase['ell']} dk eliptik/kürek · ~{load['minutes']+phase['ell']} dk</div></div>",
            unsafe_allow_html=True,
        )
        boxes = "".join(_plan_exercise_box(i, e, color) for i, e in enumerate(P.day_details(day, extra), 1))
        if fin:
            boxes += _cardio_box(fin)
        st.markdown(f"<div class='exgrid'>{boxes}</div>", unsafe_allow_html=True)
        if sel == TODAY.weekday():
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            c = st.columns([1, 1, 1])[0]
            c.button("▶ Antrenmana git", type="primary", use_container_width=True, on_click=navigate, args=("workout",))
    elif P.day_cardio(day):
        cl = P.cardio_load(day)
        st.markdown(
            f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 24%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 12%,var(--surface)), var(--surface) 80%);border:1px solid color-mix(in srgb,{color} 24%,var(--line))'>"
            f"<div class='kick' style='color:{color}'>● {day['tag']}</div><h2>{day['name']}</h2>"
            f"<div style='color:var(--muted);font-size:13px;margin-top:6px'>{day.get('note','')} · {cl['min_lo']}–{cl['min_hi']} dk</div></div>",
            unsafe_allow_html=True,
        )
        boxes = "".join(_cardio_box(c) for c in P.day_cardio(day))
        st.markdown(f"<div class='exgrid'>{boxes}</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div class='hero' style='background:linear-gradient(165deg, color-mix(in srgb,{color} 12%,var(--surface)), var(--surface) 80%);border:1px solid var(--line)'>"
            f"<div class='kick' style='color:{color}'>● {day['tag'] or 'Dinlenme'}</div><h2>{day['name']}</h2>"
            f"<div style='color:var(--muted);font-size:13px;margin-top:6px'>{day.get('note','')}</div></div>",
            unsafe_allow_html=True,
        )

    with st.expander("📋 Program mantığı — neden böyle? (GLP-1 / Wegovy)"):
        st.markdown(
            "**Hedef:** Wegovy ile hızlı kilo verirken kası korumak. GLP-1'de kaybın bir kısmı yağsız "
            "kütleden olur; bunu **yüksek protein + direnç antrenmanı** ciddi biçimde azaltır.\n\n"
            "**Haftalık yapı (4 seans):** 3 güç günü (Üst A / Alt A / Üst B) üst vücut + core ağırlıklı — "
            "sırt, göğüs, omuz, karın önde (senin hedef bölgelerin). Her güç günü **sonunda** 10–15 dk "
            "**eliptik veya kürek** bitiriş (önce ağırlık → sonra kardiyo); ayrıca Sal/Per **padel** ve 1 ayrı "
            "**kardiyo** günü (kürek/eliptik/bisiklet).\n\n"
            "**12 haftalık dönemselleştirme (periodization):**\n"
            "- **Hafta 1–4 Temel:** 3 set, RPE 6–7 — teknik ve adaptasyon, eklem/tendon hazırlığı.\n"
            "- **Hafta 5–8 Gelişim:** 4 set, RPE 7–8 — öncelikli kaslarda hacim; tekrar sabit (8/10/12), hedefi RPE'de tutturunca yükü artır.\n"
            "- **Hafta 9–12 Koruma:** 4 set, RPE 8 — büyüyen açıkta yoğunluğu tut; gerekirse 1 hafta deload.\n\n"
            "**Dinamik güncelleme:** Yukarıdaki *Program durumu* kartı her hafta gerçek verinle (kilo kaybı hızı, "
            "antrenman/padel tamamlama, protein) kendini ayarlar — kayıp %1/haftayı aşarsa kaloriyi artırmanı, "
            "yavaşsa açığı sıkmanı önerir.\n\n"
            "**Kanıt temelli sabitler:** protein **1,6–2,2 g/kg**, kayıp **%0,5–1/hafta**, kas başına "
            "**10–20 set/hafta**. _Genel bilgilendirme; tıbbi tavsiye değildir — Wegovy dozu/beslenme için hekimine danış._"
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
        b1, b2 = st.columns([2, 1])
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
    # today is a cardio day → show the cardio actions up top (they auto-track via Apple Health → Crono)
    if P.day_cardio(today):
        boxes = "".join(_cardio_box(c) for c in P.day_cardio(today))
        st.markdown(f"<p class='eyebrow'>Bugün · {today['name']}</p>", unsafe_allow_html=True)
        st.markdown(f"<div class='exgrid' style='margin-bottom:10px'>{boxes}</div>", unsafe_allow_html=True)
        st.caption("Kürek/eliptik/bisiklet Apple Health'ten Crono'ya düşünce İstatistik'te otomatik işaretlenir. Aşağıdan bir güç antrenmanı da seçebilirsin.")
    elif not today["exercises"]:
        st.info(f"Bugün **{today['name']}** — {today.get('note','')}. İstersen aşağıdan bir antrenman seç ve çalış.")
    choice = st.segmented_control("Antrenman", names, default=default, key="wsel") or default
    day = next(d for d in training if d["name"] == choice)
    color = P.FOCUS_COLOR[day["focus"]]
    phase, extra = current_phase()
    load = P.day_load(day, extra)
    fin = P.lifting_finisher(day, phase["ell"])
    st.markdown(
        f"<div class='muted' style='font-size:13px;margin:2px 0 12px'>{phase['name']} · RPE {phase['rpe']} · "
        f"{load['exercises']} egzersiz · {load['sets']} set · +{phase['ell']} dk eliptik/kürek</div>",
        unsafe_allow_html=True,
    )
    done_iso = TODAY.strftime("%Y-%m-%d")
    details = P.day_details(day, extra)
    done_sets = sum(S["setlog"].get(f"{done_iso}|{day['key']}|{e['id']}", 0) for e in details)
    st.markdown(
        f"<div class='fcard' style='padding:10px 14px;display:flex;align-items:center;gap:10px'>"
        f"<div style='flex:1'><div style='height:8px;border-radius:5px;background:var(--surface-2);overflow:hidden'>"
        f"<div style='height:100%;width:{round(done_sets/load['sets']*100) if load['sets'] else 0}%;background:{color};border-radius:5px'></div></div></div>"
        f"<div style='font-family:Nunito;font-weight:800;font-size:13px'>{done_sets}/{load['sets']} set</div></div>",
        unsafe_allow_html=True,
    )
    for row in range(0, len(details), 3):
        cols = st.columns(3, gap="medium")
        for col, (i, e) in zip(cols, enumerate(details[row:row + 3], row + 1)):
            with col:
                _exercise_box(i, e, color, day["key"], done_iso)
    if fin:
        st.markdown(f"<div class='exgrid' style='margin-top:4px'>{_cardio_box(fin)}</div>", unsafe_allow_html=True)

    already = any(w["date"] == done_iso and w.get("key") == day["key"] for w in S["workouts"])
    if already:
        st.success("Bugün bu antrenman tamamlandı ✓")
    elif st.button("✅ Bu antrenmanı tamamladım", type="primary", use_container_width=True):
        prim, sec = P.day_muscles(day)
        S["workouts"].append({"date": done_iso, "key": day["key"], "name": day["name"], "primary": prim, "secondary": sec})
        st.success(f"{day['name']} kaydedildi (bu oturumda).")
        st.rerun()

    cardio_day = next((d for d in P.DAYS if P.day_cardio(d)), None)
    if cardio_day:
        with st.expander("🚴 Kardiyo seçenekleri (kürek · eliptik · bisiklet)"):
            boxes = "".join(_cardio_box(c) for c in P.day_cardio(cardio_day))
            st.markdown(f"<div class='exgrid'>{boxes}</div>", unsafe_allow_html=True)
            st.caption("Padel'e ek haftada 1 kardiyo hedefi. Hangisini yaparsan yap Apple Health → Crono üzerinden İstatistik'e düşer.")

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
        (lambda pd_, st_: ui.tile("Kilo", f"{pd_:+.1f}" if st_ else (f"{weight_kg:.1f}" if weight_kg else "–"),
                                  "kg · başlangıçtan" if st_ else "kg · başlangıç 31 Eki",
                                  "good" if (st_ and pd_ < 0) else "bad" if (st_ and pd_ > 0) else ""))(*progress_since_start()),
    ])
    st.markdown(f"<div class='tiles'>{tiles}</div>", unsafe_allow_html=True)

    # ---- program this week: plan vs actual (strength sessions + padel land here) ----
    strv, padv = week_counts(WEEK_ISO)
    grid = program_week_grid(WEEK_START)
    cells = ""
    for g in grid:
        if g["kind"] in ("rest", "cardio"):
            mark = "<span style='color:var(--faint);font-size:16px'>·</span>"
            pill = "Dinlenme" if g["kind"] == "rest" else "Kardiyo"
            pc = "var(--faint)"
        else:
            mark = (f"<span style='color:{g['color']};font-size:15px'>✓</span>" if g["done"]
                    else "<span style='color:var(--faint);font-size:15px'>○</span>")
            pill, pc = g["name"], g["color"]
        cells += (
            f"<div style='flex:1;text-align:center'>"
            f"<div style='font-size:10.5px;color:var(--faint);font-weight:700'>{g['dow']}</div>"
            f"<div style='font-family:Nunito;font-weight:800;font-size:13px;margin:1px 0 4px'>{g['day']}</div>"
            f"<div style='font-size:10px;font-weight:700;color:{pc};white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{pill}</div>"
            f"<div style='margin-top:3px'>{mark}</div></div>"
        )
    st.markdown(
        f"<div class='fcard'><div class='eyebrow'>Program · bu hafta &nbsp;·&nbsp; "
        f"<span style='color:var(--blue)'>{strv}/{STRENGTH_TARGET} antrenman</span> &nbsp; "
        f"<span style='color:var(--teal)'>{padv}/{PADEL_TARGET} padel</span></div>"
        f"<div style='display:flex;gap:4px'>{cells}</div>"
        f"<div class='muted' style='font-size:11.5px;margin-top:10px'>✓ = o gün eşleşen seans var (güç antrenmanı Apple Health'ten Crono'ya düşünce otomatik işaretlenir).</div></div>",
        unsafe_allow_html=True,
    )

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
    note, used_ai = _coach_note(json.dumps(payload, sort_keys=True), bool(_gemini_key()))
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

    # ---- cardio & activity (from Cronometer exercises — padel, bike, rowing…) ----
    cs = cardio_summary(days)
    if cs:
        st.markdown(f"<div class='eyebrow' style='margin-top:16px'>Kardiyo & aktivite · {cs['span']}</div>", unsafe_allow_html=True)
        ctiles = "".join([
            ui.tile("Seans", str(cs["sessions"]), "kardiyo + padel"),
            ui.tile("Süre", f"{cs['minutes']}<small> dk</small>", f"~{round(cs['minutes']/max(cs['sessions'],1))} dk/seans"),
            ui.tile("Yakılan", f"{cs['kcal']}<small> kcal</small>", "tahmini"),
        ])
        st.markdown(f"<div class='tiles'>{ctiles}</div>", unsafe_allow_html=True)
        bt = cs["by_type"]
        mx = float(bt["minutes"].max()) or 1.0
        COLZ = {"Padel": "var(--teal)", "Bisiklet": "var(--blue)", "Eliptik": "var(--purple)",
                "Kürek": "var(--orange)", "Kardiyo": "var(--green)"}
        bars = "".join(
            ui.bar(r["type"], f"{int(r['minutes'])} dk · {int(r['sessions'])}×", r["minutes"] / mx * 100,
                   COLZ.get(r["type"], "var(--blue)"))
            for _, r in bt.iterrows()
        )
        st.markdown(f"<div class='fcard'><div class='eyebrow'>Türe göre süre</div><div class='bars'>{bars}</div></div>", unsafe_allow_html=True)
        with st.expander("Son seanslar"):
            for _, r in cs["recent"].iterrows():
                d = pd.to_datetime(r["date"])
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--line)'>"
                    f"<span style='font-family:Nunito;font-weight:800;font-size:13px;width:52px;color:var(--faint)'>{d.day} {MON[d.month-1]}</span>"
                    f"<span style='flex:1;font-weight:700;font-size:13.5px'>{r['type']}</span>"
                    f"<span style='color:var(--muted);font-size:12.5px'>{int(r['minutes'])} dk · {int(r['kcal'])} kcal</span></div>",
                    unsafe_allow_html=True,
                )

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
    ups = st.file_uploader("Cronometer CSV yükle (dailysummary · biometrics · exercises)",
                           type="csv", accept_multiple_files=True)
    if ups:
        msgs = []
        for f in ups:
            raw = f.getvalue()
            head = raw[:600].decode("utf-8-sig", "replace")
            kind = cronometer.detect(head)
            try:
                if kind == "nutrition":
                    S["nutrition"] = nutrition.parse_cronometer(raw)
                    msgs.append(f"beslenme {len(S['nutrition'])} gün")
                elif kind == "biometrics":
                    bw = cronometer.parse_biometrics(raw)
                    rows = {x["date"]: x["w"] for x in S["weights"]}
                    for x in bw:
                        rows[x["date"]] = x["w"]
                    S["weights"] = [{"date": k, "w": v} for k, v in rows.items()]
                    msgs.append(f"kilo {len(bw)} ölçüm")
                elif kind == "exercises":
                    ex = cronometer.parse_exercises(raw)
                    S["cron_ex"] = ex.to_dict("records")
                    S["active_kcal"] = {r["date"]: r["kcal"] for r in cronometer.parse_active_energy(raw)}
                    npad = int(ex["padel"].sum()) if not ex.empty and "padel" in ex else 0
                    msgs.append(f"spor {len(ex)} seans ({npad} padel)")
                else:
                    msgs.append(f"{f.name}: tanınmadı")
            except Exception:  # noqa: BLE001
                msgs.append(f"{f.name}: okunamadı")
        st.success("Yüklendi → " + " · ".join(msgs))
        st.rerun()

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

    cx = cron_ex_df()
    if not cx.empty or S["nutrition"] is not None or S["weights"]:
        nd = len(S["nutrition"]) if S["nutrition"] is not None else 0
        npad = int(cx["padel"].sum()) if not cx.empty and "padel" in cx else 0
        st.caption(f"📄 Cronometer: {nd} gün beslenme · {len(S['weights'])} kilo · {len(cx)} seans ({npad} padel) · {len(S['active_kcal'])} gün aktif enerji")
    else:
        st.caption("📄 Cronometer'dan dışa aktardığın dosyaları yukarıdan yükle — tek kaynak.")
    sw, spd, swo, sdaily = _sheet_data()
    if sw or spd or swo or sdaily:
        st.caption(f"🔗 Google Sheet (opsiyonel): {len(sw)} kilo · {len(spd)} padel · {swo} workout · {len(sdaily)} günlük")
        if st.button("🔄 Sheet'i yenile", use_container_width=True):
            _sheet.clear()
            st.rerun()

    t = S["targets"]
    wkg = latest_weight()[0] or 100.0
    wl = S.get("weekly_loss", 0.0)
    wlpct = (wl / wkg * 100) if wkg else 0
    manual = S["body"].get("kcal_goal") is not None
    src = "elle seçtiğin hedef" if manual else f"TDEE ~{S['tdee']} − {S['body']['deficit']} açık"
    st.markdown(
        f"<div class='fcard' style='margin-top:8px'><div class='eyebrow'>Senin için hesaplanan hedef</div>"
        f"<div style='font-size:13.5px;line-height:1.7'><b>{t['kcal']} kcal/gün</b> ({src})"
        f"&nbsp;·&nbsp;<b>{t['protein']} g protein</b> (~{PROTEIN_PER_KG} g/kg · kas koruma)"
        f"&nbsp;·&nbsp;{t['carbs']} g karb · {t['fat']} g yağ</div>"
        f"<div style='margin-top:8px;font-size:13px'>📉 Tahmini kayıp: <b class='good'>~{wl:.2f} kg/hafta</b> "
        f"(%{wlpct:.2f}/hafta · günde ~{S.get('deficit_now',0)} kcal açık)</div></div>",
        unsafe_allow_html=True,
    )
    with st.expander("⚙️ Hedef ayarları (kalori, yaş, boy, aktivite)"):
        b = S["body"]
        use_manual = st.checkbox("Kaloriyi elle belirle", value=b.get("kcal_goal") is not None,
                                 help="Kapalıyken hedef, TDEE − açık ile otomatik hesaplanır.")
        if use_manual:
            b["kcal_goal"] = st.number_input("Günlük kalori hedefi (kcal)", 1200, 3500,
                                             int(b.get("kcal_goal") or 1900), step=50)
            st.caption(f"~0,5–1%/hafta (bu kiloda ~{wkg*0.005:.1f}–{wkg*0.01:.1f} kg) kas koruma için ideal bant.")
        else:
            b["kcal_goal"] = None
            b["deficit"] = st.number_input("Günlük kalori açığı (TDEE'den)", 0, 1200, int(b.get("deficit") or 500), step=50)
        bd = st.date_input("Doğum tarihi", value=dt.date.fromisoformat(b.get("birth", "1992-03-12")),
                           min_value=dt.date(1940, 1, 1), max_value=TODAY, format="DD.MM.YYYY")
        b["birth"] = bd.isoformat()
        st.caption(f"Yaş: {age_from(b['birth'])}")
        b["height"] = st.number_input("Boy (cm)", 120, 220, int(b["height"]))
        acts = ["light", "moderate", "high"]
        b["activity"] = st.selectbox("Aktivite düzeyi", acts, index=acts.index(b["activity"]),
                                     format_func=lambda x: {"light": "Az hareketli (masa başı)", "moderate": "Orta", "high": "Yüksek"}[x])
        st.caption("Protein 1,8 g/kg'de sabit (kas koruma); kilo değiştikçe hedefler otomatik güncellenir. Genel bilgilendirme, tıbbi tavsiye değil.")


# ---------------- nav (bottom bar) + routing ----------------
# Home sits far-left; the rest follow in flow order.
NAV = [("home", "🏠"), ("plan", "🗓"), ("workout", "🏋️"), ("stats", "📊"), ("nutrition", "🔥")]
LABEL = {"home": "Ana Sayfa", "plan": "Plan", "workout": "Antrenman", "stats": "İstatistik", "nutrition": "Beslenme"}
PAGES = {"home": page_home, "plan": page_plan, "workout": page_workout, "stats": page_stats, "nutrition": page_nutrition}

cols = st.columns(5)
for col, (key, icon) in zip(cols, NAV):
    with col:
        st.button(f"{icon}  {LABEL[key]}", key=f"nav_{key}", use_container_width=True,
                  type="primary" if S["page"] == key else "secondary",
                  on_click=navigate, args=(key,))
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

PAGES[S["page"]]()
st.caption("Tasarım önizlemesi · program sana özel · veriler şimdilik oturum içinde")
