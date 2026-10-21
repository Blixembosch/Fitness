"""Fitness — our own Streamlit interface over the openGym exercise data.
5 pages, Home far-left in the nav + dynamic Dark/Light theme switcher. The training program is
auto-generated for the user's profile (lib/program.py); Plan and Antrenman render it as a unified
1..N sequence including Eliptik warm-up, strength lifts, Rower fat-burn, and Eliptik finisher."""
from __future__ import annotations
import datetime as dt
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from lib import data, nutrition, bodymap, ui, program as P, metrics, insight, sheets, cronometer, store

st.set_page_config(page_title="Fitness", page_icon="💪", layout="wide", initial_sidebar_state="collapsed")

# ---------------- state & persistence ----------------
S = st.session_state
S.setdefault("page", "home")
# Body stats drive the targets. `protein_mode="adjusted"` uses adjusted bodyweight (BMI > 25) so
# the daily protein target sits in a sustainable 150–180 g muscle-preservation band on Wegovy.
S.setdefault("body", {"birth": "1992-03-12", "height": 178, "sex": "male", "activity": "light",
                      "deficit": 500, "kcal_goal": 1900, "protein_mode": "adjusted", "theme": "dark"})
WEGOVY_DOSES = [0.25, 0.5, 1.0, 1.7, 2.4]
WEGOVY_SITES = ["Sol karın", "Sağ karın", "Sol üst bacak", "Sağ üst bacak", "Sol üst kol", "Sağ üst kol"]
S.setdefault("wegovy", {"dose_mg": 0.25, "inj_weekday": 5, "logs": []})  # default Saturday (5)

PROTEIN_PER_KG = 1.8
FIBER_TARGET = 28           # g/day — key for GI comfort on GLP-1 (Wegovy)
PROGRAM_WEEKS = 12          # the plan runs as a 12-week block from the baseline
PADEL_TARGET = 2            # planned padel days/week (actual can exceed it)
STRENGTH_TARGET = 3         # planned strength sessions/week (Üst A / Alt A / Üst B)
S.setdefault("weights", [{"date": "2026-10-12", "w": 101.1}, {"date": "2026-10-16", "w": 101.1}, {"date": "2026-10-19", "w": 100.5}])
S.setdefault("workouts", [])          # [{date, key, name, primary, secondary}]
S.setdefault("padel", [])             # [iso date]
S.setdefault("cron_ex", [])           # Cronometer exercises rows [{date,type,cat,padel,minutes,kcal}]
S.setdefault("active_kcal", {})       # {date: kcal} daily active energy from Cronometer exercises
S.setdefault("setlog", {})            # "date|daykey|exid" -> completed set count
S.setdefault("loadlog", {})           # "exid" -> last used dumbbell/machine load in kg
S.setdefault("nutrition", None)       # DataFrame or None

# Hydrate from local SQLite (data/fitness.db) + optional private Gist once per browser session
store.hydrate_session(S)
S["body"].setdefault("theme", "dark")
ui.inject(S["body"].get("theme", "dark"))

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
def _save():
    """Persist current session state to SQLite (and optional cloud Gist)."""
    store.persist_session(S)


def toggle_theme():
    cur = S["body"].get("theme", "dark")
    S["body"]["theme"] = "light" if cur == "dark" else "dark"
    _save()


def wegovy_status(today: dt.date = TODAY) -> dict:
    """Compute Wegovy injection schedule, site rotation, and 48-hour post-injection RPE/GI window."""
    w = S.get("wegovy") or {}
    dose = float(w.get("dose_mg") or 0.25)
    inj_wd = int(w.get("inj_weekday", 5)) % 7
    logs = sorted(w.get("logs") or [], key=lambda x: x.get("date", ""))
    last_log = logs[-1] if logs else None
    last_date = dt.date.fromisoformat(last_log["date"]) if (last_log and last_log.get("date")) else None
    days_since = (today - last_date).days if last_date else None

    if last_log and last_log.get("site") in WEGOVY_SITES:
        idx = (WEGOVY_SITES.index(last_log["site"]) + 1) % len(WEGOVY_SITES)
        next_site = WEGOVY_SITES[idx]
    else:
        next_site = WEGOVY_SITES[0]

    days_until = (inj_wd - today.weekday()) % 7
    logged_today = days_since == 0
    logged_this_week = days_since is not None and 0 <= days_since <= 6 and days_until != 0
    in_48h = (days_since in (0, 1)) if days_since is not None else (days_until == 0 or ((today.weekday() - inj_wd) % 7 == 1))

    if logged_today:
        sched_lbl = "Bugün vuruldu ✓"
    elif days_until == 0:
        sched_lbl = "Bugün enjeksiyon günü"
    elif days_until == 1:
        sched_lbl = f"Yarın · {DOW_LONG[inj_wd]}"
    else:
        sched_lbl = f"{days_until} gün sonra · {DOW_LONG[inj_wd]}"

    return {
        "dose_mg": dose,
        "inj_weekday": inj_wd,
        "inj_day_name": DOW_LONG[inj_wd],
        "last_log": last_log,
        "days_since": days_since,
        "days_until": days_until,
        "logged_today": logged_today,
        "logged_this_week": logged_this_week,
        "next_site": next_site,
        "in_48h": in_48h,
        "sched_lbl": sched_lbl,
    }


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
    """Cronometer workout sessions as a DataFrame [date, type, cat, padel, minutes, kcal]."""
    cols = ["date", "type", "cat", "padel", "minutes", "kcal"]
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
    """(kg, Timestamp) nearest the 2026-10-31 baseline: first weigh-in on/after it, else the first
    recorded weigh-in before it so pre-baseline progress is also visible."""
    df = weights_df()
    if df.empty:
        return (None, None)
    after = df[df["date"] >= pd.Timestamp(START_DATE)]
    row = after.iloc[0] if not after.empty else df.iloc[0]
    return (round(float(row["w"]), 1), row["date"])


def progress_since_start():
    """(delta_kg, started). started becomes True once a weigh-in on/after the baseline exists;
    before that we still compute the actual pre-start delta if >=2 weigh-ins exist."""
    df = weights_df()
    base, _ = baseline_weight()
    latest, ldate = latest_weight()
    started = base is not None and ldate is not None and ldate >= pd.Timestamp(START_DATE)
    if base is not None and latest is not None and len(df) >= 2:
        delta = round(latest - base, 1)
    else:
        delta = 0.0
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


def cardio_dates_all():
    """Every date with a non-padel, non-strength cardio session (Rowing, Elliptical, Cycling, etc.)."""
    s = set()
    cx = cron_ex_df()
    if not cx.empty:
        if "cat" in cx:
            s |= set(cx[cx["cat"] == "cardio"]["date"])
        elif "padel" in cx:
            s |= set(cx[~cx["padel"]]["date"])
    for k, v in S.get("setlog", {}).items():
        if v and ("cardio_" in k or "|warmup" in k or "|finisher" in k):
            s.add(k.split("|")[0])
    return s


def week_counts(week_iso: str):
    """(strength_sessions, padel_sessions) for the 7-day week starting week_iso."""
    end = (dt.date.fromisoformat(week_iso) + dt.timedelta(days=6)).strftime("%Y-%m-%d")
    win = lambda ds: sum(1 for d in ds if week_iso <= d <= end)
    return win(strength_dates_all()), win(padel_dates_all())


def program_week_grid(week_start: dt.date):
    """Per-day plan vs actual for a week: [{dow, day, iso, name, color, kind, planned, done}]."""
    strv, padv, crdv = strength_dates_all(), padel_dates_all(), cardio_dates_all()
    grid = []
    for i in range(7):
        d = week_start + dt.timedelta(days=i)
        iso = d.strftime("%Y-%m-%d")
        day = P.DAYS[i]
        is_padel = "padel" in day["key"].lower()
        is_lift = day["focus"] in ("upper", "lower", "full")
        is_cardio = bool(P.day_cardio(day))
        kind = "padel" if is_padel else "lift" if is_lift else "cardio" if is_cardio else day["focus"]
        color = "var(--teal)" if is_padel else P.FOCUS_COLOR.get(day["focus"], "var(--line)")
        done = (iso in strv) if is_lift else (iso in padv) if is_padel else (iso in crdv) if is_cardio else False
        grid.append({"dow": DOW[i], "day": d.day, "iso": iso, "name": day["name"], "color": color,
                     "kind": kind, "planned": is_lift or is_padel or is_cardio, "done": done})
    return grid


def build_heatmap_records() -> dict[str, dict]:
    """Build per-day records (0..4 intensity + rich Turkish summary tooltip) across all data sources
    for the GitHub-style contribution heatmap in Stats."""
    records: dict[str, dict] = {}
    str_dates = strength_dates_all()
    pad_dates = padel_dates_all()
    crd_dates = cardio_dates_all()
    daily_act = activity_daily()
    prot_floor = S.get("protein_band", {}).get("min") or S.get("targets", {}).get("protein") or 150
    weg_logs = {x["date"]: x for x in (S.get("wegovy", {}).get("logs") or []) if x.get("date")}

    # Index weigh-ins by date so weigh-in days also appear on the heatmap
    w_by_date: dict[str, float] = {}
    for x in _sheet_data()[0]:
        w_by_date[x["date"]] = float(x["w"])
    for x in S.get("weights", []):
        w_by_date[x["date"]] = float(x["w"])

    # Index workouts by date
    wo_names: dict[str, list[str]] = {}
    for w in S["workouts"]:
        wo_names.setdefault(w["date"], []).append(w.get("name", "Güç"))

    # Index Cronometer exercises by date
    cx = cron_ex_df()
    cx_by_date: dict[str, list[str]] = {}
    if not cx.empty:
        for d, grp in cx.groupby("date"):
            cx_by_date[str(d)] = [f"{r['type']} ({int(r['minutes'])} dk)" for _, r in grp.iterrows()]

    # Index nutrition by date
    ndf = S.get("nutrition")
    nut_by_date: dict[str, dict] = {}
    if isinstance(ndf, pd.DataFrame) and not ndf.empty:
        for _, r in ndf.iterrows():
            nut_by_date[str(r["date"])] = {"kcal": int(r.get("kcal", 0)), "protein": int(r.get("protein", 0))}

    # Collect all known dates
    all_dates = (
        set(str_dates) | set(pad_dates) | set(crd_dates) | set(w_by_date.keys())
        | set(daily_act.keys()) | set(nut_by_date.keys()) | set(weg_logs.keys())
    )
    for k, v in S.get("setlog", {}).items():
        if v:
            all_dates.add(k.split("|")[0])

    for iso in all_dates:
        has_str = iso in str_dates
        has_pad = iso in pad_dates
        has_crd = iso in crd_dates
        nut = nut_by_date.get(iso)
        act = daily_act.get(iso, {})
        prot_ok = bool(nut and nut["protein"] >= prot_floor)
        has_sets = any(v > 0 for k, v in S.get("setlog", {}).items() if k.startswith(f"{iso}|"))
        wlog = weg_logs.get(iso)
        wval = w_by_date.get(iso)

        # Compute 0..4 GitHub intensity level
        score = 0
        if has_str or has_pad:
            score += 2
        elif has_crd or has_sets:
            score += 1
        if prot_ok:
            score += 2 if not (has_str or has_pad) else 1
        elif nut:
            score += 1
        if act.get("steps", 0) >= 8000 or act.get("active_kcal", 0) >= 450:
            score += 1
        elif act.get("steps", 0) > 0 or act.get("active_kcal", 0) > 0 or wlog or wval is not None:
            score = max(score, 1)
        level = min(4, score)

        parts = []
        if wlog:
            parts.append(f"💉 Wegovy {wlog.get('dose', '')}mg ({wlog.get('site', '')})")
        if iso in wo_names:
            parts.append("🏋️ " + ", ".join(wo_names[iso]))
        elif has_str:
            parts.append("🏋️ Güç antrenmanı")
        if has_pad and "Padel" not in " ".join(cx_by_date.get(iso, [])):
            parts.append("🎾 Padel")
        if iso in cx_by_date:
            parts.append(" · ".join(cx_by_date[iso]))
        elif has_sets and not has_str:
            parts.append("🏋️ Set/Kardiyo kaydı")
        if nut:
            parts.append(f"🥩 {nut['protein']}g protein · {nut['kcal']} kcal")
        if wval is not None:
            parts.append(f"⚖️ {wval:.1f} kg")
        if act.get("steps"):
            parts.append(f"👟 {int(act['steps'])} adım")

        records[iso] = {
            "level": level,
            "summary": " · ".join(parts) if parts else "Aktivite kaydı",
            "strength": has_str,
            "padel": has_pad,
            "cardio": has_crd,
            "protein_ok": prot_ok,
        }
    return records


def current_phase():
    """(phase, extra_sets) for wherever we are in the 12-week block (Phase 1 before it starts)."""
    phase = P.phase_for(program_progress()["week"])
    return phase, P.phase_extra_sets(phase)


def program_adjustment():
    """Dynamic weekly guidance on top of the fixed phase plan: returns (status, html_lines[])."""
    pp = program_progress()
    wdf = weights_df()
    wkg = latest_weight()[0]
    ws = wegovy_status()
    lines, status = [], "good"
    if not pp["started"]:
        status = ""
        lines.append(f"🗓 Başlangıca <b>{pp['days_to_start']} gün</b>. İlk blok <i>Temel · Adaptasyon</i>: "
                     "hareketleri oturt, protein ve uykuyu baz al. 31 Ekim'de resmi 12 haftalık sayaç başlıyor.")
    if ws["in_48h"]:
        lines.append(
            f"💉 <b>Wegovy ({ws['dose_mg']:g} mg) 48s penceresi:</b> Enjeksiyon sonrası ilk 24–48 saatte iştah/enerji "
            "dalgalanması normaldir; bugün antrenmanda <b>RPE'yi ~1 puan esnet</b>, su ve elektroliti artır."
        )
    loss = metrics.weekly_loss_pct(wdf) if (wdf is not None and len(wdf) > 1) else None
    if loss is not None and wkg:
        if loss > 1.0:
            status = "bad"
            lines.append(f"📉 Kayıp <b>%{loss}/hafta</b> — hızlı (kas riski). Kaloriyi ~150–200 artır ya da ekstra kardiyoyu kıs; protein ve ağırlığı koru.")
        elif loss < 0.4:
            lines.append(f"📉 Kayıp <b>%{loss}/hafta</b> — yavaş. Hedefe sadık kal; istikrar sürerse açığı ~100–150 artırabilirsin.")
        else:
            lines.append(f"📉 Kayıp <b>%{loss}/hafta</b> — ideal bantta (%0,5–1). Aynen devam.")
    elif pp["started"]:
        lines.append("📉 Kilo trendi için birkaç tartım gerekli (Cronometer biometrics yükle).")
    strv, pad = week_counts(WEEK_ISO)
    if strv < STRENGTH_TARGET:
        if status == "good":
            status = "warn"
        lines.append(f"🏋️ Bu hafta <b>{strv}/{STRENGTH_TARGET}</b> antrenman — kalan güç günlerini tamamla (kas koruma önceliği).")
    if pad < PADEL_TARGET:
        lines.append(f"🎾 Padel <b>{pad}/{PADEL_TARGET}</b> — hedefe ulaşmaya çalış (ekstrası serbest).")
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
    """Targets derived from the latest bodyweight + body stats, so they track as weight changes."""
    w = latest_weight()[0] or 100.0
    b = S["body"]
    age = age_from(b["birth"]) if b.get("birth") else b.get("age", 35)
    pmode = b.get("protein_mode", "adjusted")
    pband = nutrition.protein_band(w, b["height"], mode=pmode)
    t = nutrition.estimate_targets(w, b["height"], age, b["sex"], b["activity"], b["deficit"],
                                   floor=1500, protein_per_kg=PROTEIN_PER_KG, kcal=b.get("kcal_goal"))
    prot_target = pband["target"]
    fat_target = t["fat"]
    carbs_target = max(0, round((t["kcal"] - prot_target * 4 - fat_target * 9) / 4))
    S["targets"] = {"kcal": t["kcal"], "protein": prot_target, "carbs": carbs_target, "fat": fat_target}
    S["protein_band"] = pband
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
    m = json.loads(payload_key)
    model = None
    try:
        model = st.secrets.get("GEMINI_MODEL")
    except Exception:  # noqa: BLE001
        model = None
    return insight.coach_note(m, _gemini_key() if has_key else None, model)


# ---------------- pages ----------------
def _counter_card():
    pp = program_progress()
    if not pp["started"]:
        n = pp["days_to_start"]
        return (
            "<div class='counter'>"
            f"<div><div class='big'>{n}<small> gün</small></div><div class='lbl'>Başlangıca · 31 Ekim</div></div>"
            "<div style='flex:1;min-width:140px'><div style='font-weight:800;font-size:16px;color:var(--fg)'>12 haftalık program · Hazırlık Fazı</div>"
            "<div class='muted' style='font-size:13.5px;margin-top:4px'>Resmi 12 haftalık sayaç 31 Ekim'de başlıyor; bu süreçteki tüm antrenman ve tartımların kaydediliyor.</div></div>"
            "</div>"
        )
    grid = program_week_grid(WEEK_START)
    dots = "".join(f"<i class='{'on' if g['done'] else ''}'></i>" for g in grid if g["planned"])
    pct = round(pp["pct"] * 100)
    return (
        "<div class='counter'>"
        f"<div><div class='big'>{pp['week']}<small>/{PROGRAM_WEEKS}</small></div><div class='lbl'>Hafta · 12 haftalık program</div></div>"
        "<div style='flex:1;min-width:160px'>"
        f"<div style='font-weight:800;font-size:14px;color:var(--fg)'>Bu hafta planı</div><div class='weekdots'>{dots}</div>"
        f"<div style='height:7px;border-radius:5px;background:var(--surface-2);margin-top:10px;overflow:hidden'>"
        f"<div style='height:100%;width:{pct}%;background:var(--blue);border-radius:5px'></div></div></div>"
        "</div>"
    )


def page_home():
    st.markdown(
        f"<h1 style='margin:0 0 2px;font-size:28px'>{GREET}, Anıl</h1>"
        f"<div class='muted' style='font-size:13.5px;margin-bottom:14px'>{DOW_LONG[TODAY.weekday()]} · {TODAY.day} {MON[TODAY.month-1]}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(_counter_card(), unsafe_allow_html=True)

    nt = nutrition_today()
    prot = int(nt["protein"]) if nt else 0
    kcal = int(nt["kcal"]) if nt else 0
    t = S["targets"]
    pband = S["protein_band"]
    strv, pad = week_counts(WEEK_ISO)

    r1 = ui.ring(strv / STRENGTH_TARGET if strv else 0, "var(--blue)", f"{strv}<small>/{STRENGTH_TARGET}</small>", "Antrenman", 50)
    r2 = ui.ring(pad / PADEL_TARGET if PADEL_TARGET else 0, "var(--teal)", f"{pad}<small>/{PADEL_TARGET}</small>", "Padel", 50)
    r3 = ui.ring(prot / t["protein"] if t["protein"] else 0, "var(--orange)", f"{prot}<small>/{t['protein']}</small>", f"Protein ({pband['min']}–{pband['max']}g)", 50)
    r4 = ui.ring(kcal / t["kcal"] if t["kcal"] else 0, "var(--green)", f"{kcal}<small>/{t['kcal']}</small>", "Kalori", 50)
    st.markdown(f"<div class='rings'>{r1}{r2}{r3}{r4}</div>", unsafe_allow_html=True)

    left, right = st.columns([1.35, 1], gap="medium")

    with left:
        day = P.day_for(TODAY.weekday())
        color = P.FOCUS_COLOR[day["focus"]]
        st.markdown("<p class='eyebrow'>Bugün</p>", unsafe_allow_html=True)
        phase, pextra = current_phase()
        ws = wegovy_status()
        rpe_lbl = f"RPE {phase['rpe']}" + (" · 💉 48s esnek" if ws["in_48h"] else "")
        if day["exercises"]:
            load = P.day_load(day, pextra)
            steps = P.workout_steps(day, pextra)
            chips = "".join(f"<span class='chip'>{g}</span>" for g in P.day_groups(day))
            chips += "<span class='chip' style='color:var(--green)'>🏃 Eliptik 5+10 dk</span>"
            chips += "<span class='chip' style='color:var(--orange)'>🚣 Kürek 10 dk</span>"
            st.markdown(
                f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 30%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 14%,var(--surface)), var(--surface) 78%); border:1px solid color-mix(in srgb,{color} 35%,var(--line))'>"
                f"<div class='kick' style='color:{color}'>● {day['tag']} · {rpe_lbl}</div>"
                f"<h2>{day['name']}</h2><div class='chiprow'>{chips}</div>"
                f"<div class='muted' style='font-size:13px;margin-top:8px'>{len(steps)} adım ({load['exercises']} güç + Eliptik & Kürek) · {load['sets']} güç seti + 25 dk yağ yakım kardiyo</div></div>",
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
                f"<h2>{day['name']}</h2><div class='muted' style='font-size:13px;margin-top:6px'>{day.get('note','')}</div>{extra}</div>",
                unsafe_allow_html=True,
            )

    with right:
        w, _ = latest_weight()
        if w is not None:
            delta, started = progress_since_start()
            if delta != 0:
                dcls = "good" if delta < 0 else "bad"
                lbl = "başlangıçtan" if started else "ilk kayıttan (baz: 31 Eki)"
                note = f"<span class='{dcls}' style='margin-inline-start:auto;font-weight:700;font-size:13px'>{'↓' if delta<0 else '↑'} {abs(delta):.1f} kg {lbl}</span>"
            else:
                note = "<span style='margin-inline-start:auto;color:var(--muted);font-weight:700;font-size:13px'>baz: 31 Eki</span>"
            st.markdown(
                f"<div class='fcard' style='margin-bottom:10px'><div class='eyebrow'>Vücut ağırlığı</div>"
                f"<div style='display:flex;align-items:flex-end;gap:10px'>"
                f"<span style='font-family:Nunito;font-weight:900;font-size:36px;line-height:.95;color:var(--fg)'>{w:.1f}</span>"
                f"<span style='color:var(--muted);font-weight:700'>kg</span>{note}"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        # Wegovy Dose & Injection Mini-Card
        ws = wegovy_status()
        w_badge_col = "var(--green)" if ws["logged_today"] else ("var(--orange)" if ws["days_until"] == 0 else "var(--purple)")
        w_tip = (
            "<div style='font-size:12px;color:var(--orange);margin-top:6px'>⚡ İlk 48s penceresi: antrenmanda RPE'yi ~1 puan esnet, su tüketimini artır.</div>"
            if ws["in_48h"] else
            f"<div class='muted' style='font-size:12px;margin-top:4px'>Sıradaki önerilen bölge: <b style='color:var(--fg)'>{ws['next_site']}</b></div>"
        )
        st.markdown(
            f"<div class='fcard' style='margin-bottom:10px;border-color:color-mix(in srgb,{w_badge_col} 35%,var(--line))'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center'>"
            f"<div class='eyebrow' style='margin:0'>💉 Wegovy · GLP-1</div>"
            f"<span class='chip' style='color:{w_badge_col};font-size:11px'>{ws['sched_lbl']}</span></div>"
            f"<div style='display:flex;align-items:baseline;gap:8px;margin-top:6px'>"
            f"<span style='font-family:Nunito;font-weight:900;font-size:24px;color:var(--fg)'>{ws['dose_mg']:g} mg</span>"
            f"<span class='muted' style='font-size:12.5px'>· her {ws['inj_day_name']}</span></div>"
            f"{w_tip}</div>",
            unsafe_allow_html=True,
        )
        if ws["days_until"] == 0 and not ws["logged_today"]:
            if st.button(f"💉 Bugünkü dozu vurdum ({ws['dose_mg']:g} mg · {ws['next_site']})", use_container_width=True):
                iso = TODAY.strftime("%Y-%m-%d")
                logs = [x for x in S["wegovy"].get("logs", []) if x.get("date") != iso]
                logs.append({"date": iso, "dose": ws["dose_mg"], "site": ws["next_site"]})
                S["wegovy"]["logs"] = logs
                _save()
                st.rerun()

        act = today_activity()
        if act:
            st.markdown(
                "<div class='fcard' style='margin-bottom:10px'><div class='eyebrow'>Aktivite · son gün</div>"
                "<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:12px;text-align:center'>"
                f"<div><div style='font-family:Nunito;font-weight:900;font-size:21px;color:var(--fg)'>{int(act['steps'])}</div><div class='muted' style='font-size:11px'>adım</div></div>"
                f"<div><div style='font-family:Nunito;font-weight:900;font-size:21px;color:var(--fg)'>{int(act['active_kcal'])}</div><div class='muted' style='font-size:11px'>aktif kcal</div></div>"
                f"<div><div style='font-family:Nunito;font-weight:900;font-size:21px;color:var(--fg)'>{int(act['exercise_min'])}</div><div class='muted' style='font-size:11px'>egz. dk</div></div>"
                f"<div><div style='font-family:Nunito;font-weight:900;font-size:21px;color:var(--fg)'>{act['distance_km']:.1f}</div><div class='muted' style='font-size:11px'>km</div></div>"
                "</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='fcard' style='border-style:dashed'><div class='eyebrow'>Aktivite</div>"
                "<div class='muted' style='font-size:13px;line-height:1.6'>Cronometer verini (exercises · dailysummary · biometrics) "
                "<b style='color:var(--fg)'>Beslenme</b> sekmesinden yükle; adım, aktif kcal, egzersiz dakikası ve mesafe burada görünür.</div></div>",
                unsafe_allow_html=True,
            )
        pp2 = program_progress()
        phz = P.phase_for(pp2["week"])
        wk_txt = f"Hafta {pp2['week']}/{P.PROGRAM_WEEKS}" if pp2["started"] else f"Başlangıca {pp2['days_to_start']} gün"
        st.markdown(
            f"<div class='fcard' style='margin-bottom:0'><div class='eyebrow'>Program fazı</div>"
            f"<div style='font-family:Nunito;font-weight:900;font-size:18px;color:var(--fg)'>{phz['name']}</div>"
            f"<div class='muted' style='font-size:12.5px;margin-top:3px'>{wk_txt} · {phz['base_sets']} set · RPE {phz['rpe']}</div></div>",
            unsafe_allow_html=True,
        )


def _plan_step_box(i: int, e: dict, day_color: str) -> str:
    """Unified numbered Plan card (1..N) for both cardio steps (Eliptik / Kürek) and strength lifts."""
    is_cardio = e.get("kind") == "cardio"
    badge_col = "var(--orange)" if e.get("type") == "Kürek" else ("var(--green)" if is_cardio else day_color)
    role_chip = (
        f"<span class='chip' style='font-size:10.5px;padding:2px 8px;color:{badge_col}'>"
        f"{P.CARDIO_ICON.get(e.get('type'), '🔥')} {e.get('role', 'Kardiyo')}</span>"
        if is_cardio else ""
    )
    chips = role_chip + "".join(
        f"<span class='chip' style='font-size:10.5px;padding:3px 8px'>{data.tr_muscle(m)}</span>"
        for m in e.get("primary", [])[:2]
    )
    right_lbl = e["reps"] if is_cardio else f"{e['sets']}×{e['reps']}"
    title_txt = e["name"] if is_cardio else e["name"].title()
    sub_tip = f"<div class='muted' style='font-size:11.5px;margin-top:4px;line-height:1.4'>{e.get('tip','')}</div>" if is_cardio else ""
    return (
        f"<div class='exrow' style='align-items:flex-start'>"
        f"<div style='width:34px;height:34px;border-radius:50%;background:color-mix(in srgb,{badge_col} 22%,var(--surface-2));color:{badge_col};"
        f"font-family:Nunito;font-weight:900;font-size:14px;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px'>{i}</div>"
        f"<div style='flex:1;min-width:0'><div style='font-weight:800;font-size:14.5px;color:var(--fg)'>{title_txt}</div>"
        f"<div class='chiprow' style='margin-top:4px'>{chips}</div>{sub_tip}</div>"
        f"<div style='font-family:Nunito;font-weight:800;color:{badge_col};font-size:15px;flex-shrink:0'>{right_lbl}</div></div>"
    )


def _cardio_box(c):
    """Cardio action card for the standalone Saturday Cardio day."""
    icon = P.CARDIO_ICON.get(c.get("type"), "🔥")
    role = f"<span class='chip' style='font-size:10px;padding:2px 7px;color:var(--green)'>{c['role']}</span>" if c.get("role") else ""
    return (
        f"<div class='exrow' style='align-items:flex-start'>"
        f"<div style='width:38px;height:38px;border-radius:50%;background:color-mix(in srgb,var(--green) 18%,var(--surface-2));"
        f"display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:19px'>{icon}</div>"
        f"<div style='flex:1;min-width:0'>"
        f"<div style='display:flex;align-items:baseline;gap:8px;flex-wrap:wrap'><div style='font-weight:800;font-size:14.5px;color:var(--fg)'>{c['name']}</div>"
        f"<div style='font-family:Nunito;font-weight:800;color:var(--green);font-size:14px'>{c['minutes']} dk</div>{role}</div>"
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
    wk_txt = f"Hafta {pp['week']}/{P.PROGRAM_WEEKS}" if pp["started"] else "Hazırlık"
    body = "".join(f"<div style='font-size:13.5px;line-height:1.6;margin-top:5px;color:var(--fg)'>{l}</div>" for l in lines)
    st.markdown(
        f"<div class='fcard' style='border-color:color-mix(in srgb,{tint} 38%,var(--line))'>"
        f"<div style='display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap'>"
        f"<div class='eyebrow' style='margin:0'>Program durumu</div>"
        f"<div style='font-size:12.5px;font-weight:800;color:{tint}'>{phase['name']} · {wk_txt} · RPE {phase['rpe']}</div></div>"
        f"<div class='muted' style='font-size:13px;margin-top:6px'>{phase['note']}</div>{body}</div>",
        unsafe_allow_html=True,
    )
    sel = int(S.get("plan_day", TODAY.weekday()))
    done = strength_dates_all()
    pad = padel_dates_all()

    cols = st.columns(7)
    for i, col in enumerate(cols):
        d = WEEK_START + dt.timedelta(days=i)
        iso = d.strftime("%Y-%m-%d")
        day = P.DAYS[i]
        color = P.FOCUS_COLOR[day["focus"]]
        dot = "var(--green)" if (iso in done or iso in pad) else (color if day["focus"] != "rest" else "var(--line)")
        with col:
            st.markdown(
                f"<div style='text-align:center;font-size:11px;color:var(--muted);font-weight:700'>{DOW[i]}"
                f"<span style='display:inline-block;width:6px;height:6px;border-radius:50%;background:{dot};margin-inline-start:4px;vertical-align:middle'></span></div>",
                unsafe_allow_html=True,
            )
            st.button(str(d.day), key=f"pd_{i}", use_container_width=True,
                      type="primary" if i == sel else "secondary", on_click=lambda i=i: S.__setitem__("plan_day", i))

    day = P.DAYS[sel]
    color = P.FOCUS_COLOR[day["focus"]]
    title = "Bugün" if sel == TODAY.weekday() else DOW_LONG[sel]
    st.markdown(f"<p class='eyebrow' style='margin-top:14px'>{title}</p>", unsafe_allow_html=True)

    if day["exercises"]:
        load = P.day_load(day, extra)
        steps = P.workout_steps(day, extra)
        chips = "".join(f"<span class='chip'>{g}</span>" for g in P.day_groups(day))
        chips += "<span class='chip' style='color:var(--green)'>🏃 Eliptik 5+10 dk</span>"
        chips += "<span class='chip' style='color:var(--orange)'>🚣 Kürek 10 dk</span>"
        st.markdown(
            f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 28%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 13%,var(--surface)), var(--surface) 80%);border:1px solid color-mix(in srgb,{color} 32%,var(--line))'>"
            f"<div class='kick' style='color:{color}'>● {day['tag']} · RPE {phase['rpe']}</div><h2>{day['name']}</h2>"
            f"<div class='chiprow'>{chips}</div>"
            f"<div class='muted' style='font-size:13px;margin-top:8px'>{len(steps)} numaralı adım ({load['exercises']} güç + Eliptik ısınma + Kürek & Eliptik yağ yakım) · ~{load['minutes']+25} dk</div></div>",
            unsafe_allow_html=True,
        )
        boxes = "".join(_plan_step_box(i, e, color) for i, e in enumerate(steps, 1))
        st.markdown(f"<div class='exgrid'>{boxes}</div>", unsafe_allow_html=True)
        if sel == TODAY.weekday():
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            c = st.columns([1, 1, 1])[0]
            c.button("▶ Antrenmana git", type="primary", use_container_width=True, on_click=navigate, args=("workout",))
    elif P.day_cardio(day):
        cl = P.cardio_load(day)
        st.markdown(
            f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 24%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 12%,var(--surface)), var(--surface) 80%);border:1px solid color-mix(in srgb,{color} 28%,var(--line))'>"
            f"<div class='kick' style='color:{color}'>● {day['tag']}</div><h2>{day['name']}</h2>"
            f"<div class='muted' style='font-size:13px;margin-top:6px'>{day.get('note','')} · {cl['min_lo']}–{cl['min_hi']} dk</div></div>",
            unsafe_allow_html=True,
        )
        boxes = "".join(_cardio_box(c) for c in P.day_cardio(day))
        st.markdown(f"<div class='exgrid'>{boxes}</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div class='hero' style='background:linear-gradient(165deg, color-mix(in srgb,{color} 12%,var(--surface)), var(--surface) 80%);border:1px solid var(--line)'>"
            f"<div class='kick' style='color:{color}'>● {day['tag'] or 'Dinlenme'}</div><h2>{day['name']}</h2>"
            f"<div class='muted' style='font-size:13px;margin-top:6px'>{day.get('note','')}</div></div>",
            unsafe_allow_html=True,
        )

    with st.expander("📋 Program mantığı — neden her güç gününde Eliptik + Kürek var? (GLP-1 / Wegovy)"):
        st.markdown(
            "**İkili Hedef (Yağ Yakımı + Kas Koruma/Artırma):** Mevcut kilonda Wegovy ile yağ yakarken kas kütleni "
            "koruyup artırmak için her antrenman günü **3 aşamalı numaralı akış** olarak kurgulandı:\n\n"
            "1. **Adım 1 — Eliptik Isınma (5 dk):** Düşük eklem yüküyle nabzı ve eklemleri hazırlar, ağırlık öncesi kasları yormaz.\n"
            "2. **Adım 2..N-2 — Güç & Kas Koruma (Ağırlık):** Glikojen depoların doluyken tüm enerjini dambıl/bench hareketlerine verirsin (kas koruma & hipertrofi sinyali).\n"
            "3. **Son 2 Adım — Kürek (10 dk) + Eliptik (10 dk) Yağ Yakım Bitirişi:** Ağırlık bittikten hemen sonra glikojen azalmışken "
            "önce **Su Küreği (Rower)** ile tam-vücut (sırt + bacak + core) metabolik yağ yakımı, ardından **Eliptik** ile Zone-2 yağ oksidasyonu ve aktif soğuma yapılır."
        )


def _exercise_box(i: int, e: dict, day_color: str, day_key: str, date_iso: str, day_obj=None, all_steps=None):
    """Unified 3-column workout card for BOTH cardio steps (1. Eliptik, Kürek, Eliptik finisher)
    and strength exercises. All share identical card height, numbering, progress ring, and muscle map."""
    key = f"{date_iso}|{day_key}|{e['id']}"
    is_cardio = e.get("kind") == "cardio"
    total = int(e["sets"])
    done = S["setlog"].get(key, 0)
    finished = done >= total
    accent = "var(--orange)" if e.get("type") == "Kürek" else ("var(--green)" if is_cardio else day_color)
    ringcol = "var(--green)" if finished else accent

    role_chip = (
        f"<span class='chip' style='font-size:10.5px;padding:2px 8px;color:{accent}'>"
        f"{P.CARDIO_ICON.get(e.get('type'), '🔥')} {e.get('role', 'Kardiyo')}</span>"
        if is_cardio else ""
    )
    chips = role_chip + "".join(
        f"<span class='chip' style='font-size:10.5px;padding:3px 8px'>{data.tr_muscle(m)}</span>"
        for m in e.get("primary", [])[:2]
    )
    last_kg = S.get("loadlog", {}).get(e["id"]) if not is_cardio else None
    kg_badge = f"<span class='chip' style='font-size:10.5px;padding:2px 7px;color:var(--fg)'>⚖️ {last_kg:g} kg</span>" if last_kg else ""
    meta_txt = e["reps"] if is_cardio else f"{e['sets']}×{e['reps']}"
    title_txt = e["name"] if is_cardio else e["name"].title()

    badge_bg = "var(--green)" if finished else f"color-mix(in srgb,{accent} 22%,var(--surface-2))"
    badge_fg = "#ffffff" if finished else accent
    badge_content = "✓" if finished else str(i)
    badge_border = "var(--green)" if finished else f"color-mix(in srgb,{accent} 45%,transparent)"

    with st.container(border=True):
        st.markdown(
            f"<div style='display:flex;align-items:flex-start;gap:12px;min-height:78px;margin-bottom:6px'>"
            f"<div style='display:flex;flex-direction:column;align-items:center;flex-shrink:0;width:38px'>"
            f"<div style='width:36px;height:36px;border-radius:50%;background:{badge_bg};color:{badge_fg};"
            f"border:1.5px solid {badge_border};font-family:Nunito;font-weight:900;font-size:15px;"
            f"display:flex;align-items:center;justify-content:center'>{badge_content}</div>"
            f"<div style='font-family:Nunito;font-weight:800;font-size:11px;margin-top:3px;color:{ringcol};text-align:center'>{done}/{total}</div>"
            f"</div>"
            f"<div style='flex:1;min-width:0'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:6px'>"
            f"<div style='font-weight:800;font-size:14.5px;color:var(--fg);line-height:1.25;flex:1'>{title_txt}</div>"
            f"<div style='font-family:Nunito;font-weight:800;color:{accent};font-size:14px;flex-shrink:0'>{meta_txt}</div>"
            f"</div>"
            f"<div class='chiprow' style='margin:4px 0 0'>{chips}{kg_badge}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns([2.2, 1])
        btn_lbl = "✓ Tamamla" if is_cardio else "✓ Set"
        if b1.button(btn_lbl, key=f"s_{key}", use_container_width=True, disabled=finished):
            S["setlog"][key] = min(total, done + 1)
            if day_obj and all_steps:
                lift_steps = [ex for ex in all_steps if ex.get("kind") == "lift"]
                all_done = all(
                    S["setlog"].get(f"{date_iso}|{day_key}|{ex['id']}", 0) >= int(ex["sets"])
                    for ex in lift_steps
                )
                already = any(w["date"] == date_iso and w.get("key") == day_key for w in S["workouts"])
                if all_done and not already:
                    prim, sec = P.day_muscles(day_obj)
                    S["workouts"].append({"date": date_iso, "key": day_key, "name": day_obj["name"], "primary": prim, "secondary": sec})
            _save()
            st.rerun()
        if b2.button("↺", key=f"r_{key}", use_container_width=True, disabled=done == 0):
            S["setlog"][key] = 0
            _save()
            st.rerun()
        with st.expander("Hangi kası çalıştırır?"):
            st.markdown(f"<div class='muted' style='font-size:12.5px;margin:-4px 0 6px'>{data.tr_eq(e.get('eq',''))}</div>", unsafe_allow_html=True)
            st.markdown(bodymap.body_map(e["primary"], e["secondary"]) + ui.legend(accent), unsafe_allow_html=True)
            st.markdown(f"<div class='muted' style='font-size:12.5px;margin-top:8px'>💡 {e.get('tip','')}</div>", unsafe_allow_html=True)
            if not is_cardio:
                cur_kg = float(S.get("loadlog", {}).get(e["id"]) or 0.0)
                new_kg = st.number_input("Çalışma ağırlığı (kg)", min_value=0.0, max_value=200.0, value=cur_kg, step=2.5, key=f"kg_{key}")
                if new_kg != cur_kg:
                    S.setdefault("loadlog", {})[e["id"]] = round(new_kg, 1)
                    _save()


def page_workout():
    st.markdown("<h1 style='margin:0 0 10px'>Antrenman</h1>", unsafe_allow_html=True)
    training = P.TRAINING_DAYS
    names = [d["name"] for d in training]
    today = P.day_for(TODAY.weekday())
    default = today["name"] if today in training else names[0]
    if P.day_cardio(today):
        boxes = "".join(_cardio_box(c) for c in P.day_cardio(today))
        st.markdown(f"<p class='eyebrow'>Bugün · {today['name']}</p>", unsafe_allow_html=True)
        st.markdown(f"<div class='exgrid' style='margin-bottom:10px'>{boxes}</div>", unsafe_allow_html=True)
        st.caption("Kürek/eliptik/bisiklet Apple Health'ten Crono'ya düşünce İstatistik'te otomatik işaretlenir. Aşağıdan bir güç antrenmanı da seçebilirsin.")
    elif not today["exercises"]:
        st.info(f"Bugün **{today['name']}** — {today.get('note','')}. İstersen aşağıdan bir antrenman seç ve çalış.")
    choice = st.segmented_control("Antrenman", names, default=default, key="wsel", label_visibility="collapsed") or default
    day = next(d for d in training if d["name"] == choice)
    color = P.FOCUS_COLOR[day["focus"]]
    phase, extra = current_phase()
    load = P.day_load(day, extra)
    steps = P.workout_steps(day, extra)
    ws = wegovy_status()
    weg_note = f" · 💉 Wegovy ({ws['dose_mg']:g} mg) 48s esnek RPE" if ws["in_48h"] else ""
    done_iso = TODAY.strftime("%Y-%m-%d")
    total_units = sum(int(e["sets"]) for e in steps)
    done_units = sum(S["setlog"].get(f"{done_iso}|{day['key']}|{e['id']}", 0) for e in steps)
    done_pct = round(done_units / total_units * 100) if total_units else 0

    chips = "".join(f"<span class='chip'>{g}</span>" for g in P.day_groups(day))
    chips += "<span class='chip' style='color:var(--green)'>🏃 Eliptik 5+10 dk</span>"
    chips += "<span class='chip' style='color:var(--orange)'>🚣 Kürek 10 dk</span>"

    st.markdown(
        f"<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,{color} 28%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,{color} 13%,var(--surface)), var(--surface) 80%);border:1.5px solid color-mix(in srgb,{color} 36%,var(--line));box-shadow:var(--shadow);margin-bottom:14px'>"
        f"<div class='kick' style='color:{color}'>● {day['tag']} · RPE {phase['rpe']}{weg_note}</div>"
        f"<h2>{day['name']}</h2>"
        f"<div class='chiprow'>{chips}</div>"
        f"<div class='muted' style='font-size:13px;margin:8px 0 12px'>{len(steps)} numaralı adım ({load['exercises']} güç + Eliptik ısınma + Kürek & Eliptik yağ yakım) · {load['sets']} güç seti + 25 dk kardiyo</div>"
        f"<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap'>"
        f"<div style='flex:1;min-width:180px'><div style='height:8px;border-radius:5px;background:var(--surface-2);overflow:hidden'>"
        f"<div style='height:100%;width:{done_pct}%;background:{color};border-radius:5px;transition:width .3s'></div></div></div>"
        f"<div style='font-family:Nunito;font-weight:800;font-size:13px;color:var(--fg)'>{done_units}/{total_units} adım/set tamamlandı ({done_pct}%)</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )
    # Render all numbered steps (1..N: Eliptik warm-up -> Lifts -> Rower -> Eliptik finisher) in a cohesive 3-col grid
    for row in range(0, len(steps), 3):
        cols = st.columns(3, gap="medium")
        for col, (i, e) in zip(cols, enumerate(steps[row:row + 3], row + 1)):
            with col:
                _exercise_box(i, e, color, day["key"], done_iso, day_obj=day, all_steps=steps)

    already = any(w["date"] == done_iso and w.get("key") == day["key"] for w in S["workouts"])
    if already:
        st.success("Bugün bu antrenman tamamlandı ✓")
    elif st.button("✅ Tüm antrenmanı (güç + kürek + eliptik) tamamladım", type="primary", use_container_width=True):
        prim, sec = P.day_muscles(day)
        for ex in steps:
            S["setlog"][f"{done_iso}|{day['key']}|{ex['id']}"] = int(ex["sets"])
        S["workouts"].append({"date": done_iso, "key": day["key"], "name": day["name"], "primary": prim, "secondary": sec})
        _save()
        st.success(f"{day['name']} kalıcı olarak kaydedildi ✓")
        st.rerun()

    st.markdown("<div class='section-divider'><span>Ek Seçenekler & Egzersiz Rehberi</span></div>", unsafe_allow_html=True)

    cardio_day = next((d for d in P.DAYS if P.day_cardio(d)), None)
    if cardio_day:
        with st.expander("🚴 Cumartesi özel kardiyo günü seçenekleri (kürek · eliptik · bisiklet)"):
            boxes = "".join(_cardio_box(c) for c in P.day_cardio(cardio_day))
            st.markdown(f"<div class='exgrid'>{boxes}</div>", unsafe_allow_html=True)
            st.caption("Güç günlerindeki 25 dk (Eliptik + Kürek) kombinasyonuna ek olarak Cumartesi tam kondisyon günüdür.")

    with st.expander("🔎 Egzersiz ara (hangi kası çalıştırır)"):
        q = st.text_input("Ara", placeholder="örn. shoulder press", label_visibility="collapsed", key="exq")
        if q:
            for ex in data.search(q, limit=8):
                p = [m for m in [ex.get("tg"), ex.get("mg")] if m]
                s = [m for m in (ex.get("sm") or []) if m not in p]
                st.markdown(f"**{ex['n'].title()}** · {data.tr_bp(ex['bp'])}", unsafe_allow_html=True)
                st.markdown(bodymap.body_map(p, s), unsafe_allow_html=True)


def _render_period_plan_view(period: str):
    """Render the period-specific target & calendar breakdown so switching between 'Hafta', 'Ay',
    and '3 Ay' in Stats transforms the calendar/target view dynamically."""
    today_iso = TODAY.strftime("%Y-%m-%d")
    if period == "Hafta":
        strv, padv = week_counts(WEEK_ISO)
        grid = program_week_grid(WEEK_START)
        cells = ""
        for g in grid:
            is_today = g["iso"] == today_iso
            cls = "wk-day" + (" today" if is_today else "") + (" done" if g["done"] else "")
            if g["kind"] == "rest":
                badge = "<span style='color:var(--muted);font-size:12px'>Dinlenme</span>"
                icon = "·"
            else:
                icon = "✅" if g["done"] else ("●" if is_today else "○")
                badge = f"<span style='color:{g['color']};font-weight:800;font-size:11.5px'>{g['name']}</span>"
            cells += (
                f"<div class='{cls}'>"
                f"<div style='font-size:11px;color:var(--muted);font-weight:700'>{g['dow']} · {g['day']}</div>"
                f"<div style='margin:4px 0 2px'>{badge}</div>"
                f"<div style='font-size:13px;color:var(--fg)'>{icon}</div></div>"
            )
        st.markdown(
            f"<div class='fcard'><div style='display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px'>"
            f"<div class='eyebrow' style='margin:0'>Haftalık Plan & Gerçekleşen ({WEEK_START.day}–{(WEEK_START+dt.timedelta(days=6)).day} {MON[TODAY.month-1]})</div>"
            f"<div style='font-size:12.5px;font-weight:800'>"
            f"<span style='color:var(--blue)'>● {strv}/{STRENGTH_TARGET} güç</span> &nbsp;·&nbsp; "
            f"<span style='color:var(--teal)'>● {padv}/{PADEL_TARGET} padel</span></div></div>"
            f"<div class='wk-strip'>{cells}</div></div>",
            unsafe_allow_html=True,
        )
    elif period == "Ay":
        # 4-week (28-day) calendar matrix ending this week
        start_mon = WEEK_START - dt.timedelta(weeks=3)
        headers = "".join(f"<div style='text-align:center;font-size:11px;font-weight:800;color:var(--muted)'>{d}</div>" for d in DOW)
        cells = ""
        tot_str = tot_pad = tot_crd = 0
        for w in range(4):
            w_mon = start_mon + dt.timedelta(weeks=w)
            for g in program_week_grid(w_mon):
                is_today = g["iso"] == today_iso
                cls = "mo-cell" + (" today" if is_today else "") + (" done" if g["done"] else "")
                if g["done"] and g["kind"] == "lift":
                    tot_str += 1
                elif g["done"] and g["kind"] == "padel":
                    tot_pad += 1
                elif g["done"] and g["kind"] == "cardio":
                    tot_crd += 1
                dt_obj = dt.date.fromisoformat(g["iso"])
                status_mark = "✅" if g["done"] else ("●" if is_today else "")
                cells += (
                    f"<div class='{cls}'>"
                    f"<div style='font-weight:800;font-size:11px;color:var(--muted)'>{dt_obj.day} {MON[dt_obj.month-1]}</div>"
                    f"<div style='color:{g['color']};font-weight:800;font-size:11px;margin-top:2px'>{g['name']} {status_mark}</div>"
                    f"</div>"
                )
        bars = "".join([
            ui.bar("Aylık Güç Antrenmanı (Hedef: 12 seans)", f"{tot_str} / 12 seans", tot_str / 12 * 100, "var(--blue)"),
            ui.bar("Aylık Padel (Hedef: 8 seans)", f"{tot_pad} / 8 seans", tot_pad / 8 * 100, "var(--teal)"),
            ui.bar("Aylık Kardiyo Günü (Hedef: 4 seans)", f"{tot_crd} / 4 seans", tot_crd / 4 * 100, "var(--green)"),
        ])
        st.markdown(
            f"<div class='fcard'><div style='display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px'>"
            f"<div class='eyebrow' style='margin:0'>Aylık Takvim & Hedef Takibi (Son 4 Hafta · 28 Gün)</div>"
            f"<div style='font-size:12.5px;font-weight:800'>"
            f"<span style='color:var(--blue)'>● {tot_str}/12 güç</span> &nbsp;·&nbsp; "
            f"<span style='color:var(--teal)'>● {tot_pad}/8 padel</span> &nbsp;·&nbsp; "
            f"<span style='color:var(--green)'>● {tot_crd}/4 kardiyo</span></div></div>"
            f"<div class='mo-grid' style='margin-bottom:14px'>{headers}{cells}</div>"
            f"<div class='bars'>{bars}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        # 3 Ay (12-Week Periodized Block View)
        pp = program_progress()
        cur_wk = pp["week"] if pp["started"] else 1
        wk_cards = ""
        for w in range(1, PROGRAM_WEEKS + 1):
            ph = P.phase_for(w)
            w_start = START_DATE + dt.timedelta(weeks=w - 1)
            w_end = w_start + dt.timedelta(days=6)
            iso_week = w_start.isocalendar()[1]
            w_iso = w_start.strftime("%Y-%m-%d")
            s_cnt, p_cnt = week_counts(w_iso)
            is_cur = (w == cur_wk and pp["started"])
            b_col = "var(--blue)" if w <= 4 else ("var(--purple)" if w <= 8 else "var(--orange)")
            cls = "mo-cell" + (" today" if is_cur else "") + (" done" if (s_cnt >= STRENGTH_TARGET) else "")
            wk_cards += (
                f"<div class='{cls}' style='padding:10px 8px'>"
                f"<div style='font-size:10.5px;font-weight:800;color:{b_col};text-transform:uppercase'>"
                f"Hafta {iso_week} · Blok H{w}</div>"
                f"<div style='font-weight:800;font-size:12.5px;margin:3px 0;color:var(--fg)'>{w_start.day} {MON[w_start.month-1]}–{w_end.day} {MON[w_end.month-1]}</div>"
                f"<div style='font-size:11px;color:var(--muted);margin-bottom:2px'>{ph['name'].split('·')[0].strip()} · RPE {ph['rpe']}</div>"
                f"<div class='muted' style='font-size:10.5px;font-weight:700'>{s_cnt}/{STRENGTH_TARGET} güç · {p_cnt}/{PADEL_TARGET} padel</div>"
                f"</div>"
            )
        st.markdown(
            "<div class='fcard'><div class='eyebrow'>3 Aylık (12 Hafta) Wegovy Dönemselleştirme Blok Takibi (Yılın Haftaları)</div>"
            f"<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:8px'>{wk_cards}</div></div>",
            unsafe_allow_html=True,
        )


def page_stats():
    st.markdown("<h1 style='margin:0 0 10px'>İstatistik & Hedef Takibi</h1>", unsafe_allow_html=True)

    # ---- GitHub-style full-year activity & target heatmap ----
    hm_records = build_heatmap_records()
    st.markdown(ui.github_heatmap(TODAY, hm_records, weeks=52), unsafe_allow_html=True)

    # ---- Modern Weekly, Monthly & 3-Month Target Overview ----
    period = st.segmented_control("Dönem görünümü", ["Hafta", "Ay", "3 Ay"], default="Hafta", key="sp") or "Hafta"
    days = 7 if period == "Hafta" else 30 if period == "Ay" else 90
    start = (TODAY - dt.timedelta(days=days - 1)).strftime("%Y-%m-%d")

    str_all = strength_dates_all()
    pad_all = padel_dates_all()
    wk_in_period = [d for d in str_all if d >= start]
    pad_in_period = [d for d in pad_all if d >= start]

    ndf = S["nutrition"]
    if ndf is not None and not ndf.empty:
        win_ndf = ndf[ndf["date"] >= start]
        recent = win_ndf if not win_ndf.empty else ndf.tail(days)
    else:
        recent = pd.DataFrame()
    avg_prot = round(recent["protein"].mean()) if not recent.empty else 0
    avg_kcal = round(recent["kcal"].mean()) if not recent.empty else 0
    pband = S["protein_band"]
    prot_floor = pband["min"]
    met = int((recent["protein"] >= prot_floor).sum()) if not recent.empty else 0

    wdf = weights_df()
    wwin = wdf[wdf["date"] >= pd.Timestamp(start)] if not wdf.empty else wdf
    weight_kg = latest_weight()[0]
    deficit = (S["tdee"] - avg_kcal) if avg_kcal else None

    # Compute weight delta specific to the selected period (7d / 30d / 90d)
    if len(wwin) >= 2:
        period_wdelta = round(float(wwin["w"].iloc[-1] - wwin["w"].iloc[0]), 1)
        w_sub = f"son {days} günde ({len(wwin)} tartım)"
    else:
        period_wdelta, _ = progress_since_start()
        w_sub = f"son {days} günde {len(wwin)} tartım · toplam değişim"

    weeks_factor = 1 if period == "Hafta" else 4 if period == "Ay" else 12
    str_goal_period = STRENGTH_TARGET * weeks_factor
    pad_goal_period = PADEL_TARGET * weeks_factor

    tiles = "".join([
        ui.tile(f"Güç ({period})", f"{len(wk_in_period)}<small>/{str_goal_period}</small>", f"son {days} gün · {len(pad_in_period)}/{pad_goal_period} padel", "good" if len(wk_in_period) >= str_goal_period else ""),
        ui.tile(f"Protein Ort. ({period})", f"{avg_prot}<small> g</small>", f"{met}/{len(recent)} gün bantta (≥{prot_floor}g)" if not recent.empty else f"hedef bant {pband['min']}–{pband['max']} g", "good" if met else ""),
        ui.tile(f"Kalori Ort. ({period})", (f"{avg_kcal}<small> kcal</small>" if avg_kcal else f"{S['targets']['kcal']}<small> hedef</small>"), f"hedef {S['targets']['kcal']} kcal/gün" if avg_kcal else "Cronometer CSV bekliyor", ""),
        ui.tile(f"Kilo ({period})", f"{period_wdelta:+.1f}<small> kg</small>" if period_wdelta != 0 else (f"{weight_kg:.1f}<small> kg</small>" if weight_kg else "–"),
                w_sub, "good" if period_wdelta < 0 else "bad" if period_wdelta > 0 else ""),
    ])
    st.markdown(f"<div class='tiles'>{tiles}</div>", unsafe_allow_html=True)

    # Render dynamic Week / Month / 3-Month calendar & target view
    _render_period_plan_view(period)

    # ---- evidence-based targets ----
    eff_w = pband["eff_weight"] if pband.get("mode") == "adjusted" else weight_kg
    gkg = metrics.protein_per_kg(avg_prot, eff_w)
    loss = metrics.weekly_loss_pct(wwin) if metrics.weekly_loss_pct(wwin) is not None else metrics.weekly_loss_pct(wdf)
    _, extra = current_phase()
    vol = {}
    for d in P.TRAINING_DAYS:
        for e in P.day_details(d, extra):
            if e["primary"]:
                g = data.group_of(e["primary"][0])
                if g and g != "Kardiyo":
                    vol[g] = vol.get(g, 0) + int(e["sets"])
    avg_sets = round(sum(vol.values()) / len(vol)) if vol else 0

    rows = []
    s = metrics.band(gkg, *metrics.PROTEIN_GKG)
    cls, word = metrics.verdict(s, "düşük", "yüksek")
    prot_note = (f"Düzeltilmiş ağırlık ({eff_w} kg) bazlı kas koruma bandı: {pband['min']}–{pband['max']} g/gün."
                 if pband.get("mode") == "adjusted" else
                 "Wegovy'de kası korumanın #1 kaldıracı; açıkta en kritik sayı.")
    rows.append(ui.metric_row("Protein (g/kg)", f"{gkg if gkg else '–'} g/kg",
                              f"{metrics.PROTEIN_GKG[0]}–{metrics.PROTEIN_GKG[1]}", cls, word, prot_note))
    s = metrics.band(loss, *metrics.LOSS_PCT_WK)
    cls, word = metrics.verdict(s, "yavaş", "hızlı (kas riski)")
    rows.append(ui.metric_row("Kilo kaybı hızı (Tartım Trendi)", f"{loss if loss is not None else '–'} %/hafta",
                              f"%{metrics.LOSS_PCT_WK[0]}–{metrics.LOSS_PCT_WK[1]}", cls, word,
                              "Tartıdaki gerçek değişimden hesaplanır (en az 7 günlük trend). Hedef kalori (1900/2100) ise teorik 'Tahmini Kayıp'ı belirler."))
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
    payload = {"gkg": gkg, "protein_target": S["targets"]["protein"], "avg_protein": avg_prot,
               "loss_pct_week": loss, "avg_sets_per_muscle": avg_sets, "deficit_kcal": deficit,
               "avg_kcal": avg_kcal, "weight_kg": weight_kg}
    note, used_ai = _coach_note(json.dumps(payload, sort_keys=True), bool(_gemini_key()))
    st.markdown("<div class='eyebrow' style='margin-top:14px'>Akıllı özet" + ("  ·  Gemini" if used_ai else "") + "</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='fcard' style='border-color:color-mix(in srgb,var(--blue) 32%,var(--line))'>"
        f"<div style='font-size:14px;line-height:1.6;color:var(--fg)'>💬 {note}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div class='eyebrow' style='margin-top:14px'>Kanıta dayalı hedefler</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='fcard' style='padding:4px 16px 14px'>{''.join(rows)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='eyebrow' style='margin-top:16px'>Kilo trendi</div>", unsafe_allow_html=True)
    if not wdf.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=wdf["date"], y=wdf["w"], mode="markers", marker=dict(size=7, color="#34d399"), name="Tartım"))
        if len(wdf) >= 2:
            ma = wdf["w"].rolling(7, min_periods=1).mean()
            fig.add_trace(go.Scatter(x=wdf["date"], y=ma, mode="lines", line=dict(color="#34d399", width=3), name="7-gün ort."))
        fig.update_layout(height=210, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"), showlegend=False)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="rgba(148,163,184,.12)", ticksuffix=" kg")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.caption("Çizgi: 7 günlük hareketli ortalama (günlük dalgalanmayı yumuşatır).")

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
                    f"<span style='font-family:Nunito;font-weight:800;font-size:13px;width:52px;color:var(--muted)'>{d.day} {MON[d.month-1]}</span>"
                    f"<span style='flex:1;font-weight:700;font-size:13.5px;color:var(--fg)'>{r['type']}</span>"
                    f"<span class='muted' style='font-size:12.5px'>{int(r['minutes'])} dk · {int(r['kcal'])} kcal</span></div>",
                    unsafe_allow_html=True,
                )

    with st.expander("Haftalık hacim (kas grubu)"):
        if vol:
            mx = max(vol.values())
            order = ["Göğüs", "Sırt", "Omuz", "Kol", "Bacak", "Baldır", "Karın"]
            bars = "".join(ui.bar(g, f"{vol[g]} set", vol[g] / mx * 100, "var(--blue)") for g in order if g in vol)
            st.markdown(f"<div class='bars'>{bars}</div>", unsafe_allow_html=True)

    with st.expander("Kas haritası · seçili dönem"):
        wk_logged = [w for w in S["workouts"] if w["date"] >= start]
        if wk_logged:
            prim = [m for w in wk_logged for m in w.get("primary", [])]
            sec = [m for w in wk_logged for m in w.get("secondary", [])]
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
            "- **Düzeltilmiş ağırlıkta protein bandı (150–180 g / 1,6–2,2 g/kg):** BMI > 25 iken ham ağırlık yerine düzeltilmiş ağırlık baz alınır; Wegovy'de iştah baskılanırken kası koruyacak en sürdürülebilir aralıktır (Helms ve ark.; Examine).\n"
            "- **Kayıp %0,5–1/hafta:** daha hızlısı yağla birlikte kası da götürür.\n"
            "- **Kas başına 10–20 set/hafta:** hipertrofi için genel aralık (yeni başlayanlar alt uçta).\n"
            "- **GLP-1'de (Wegovy):** kaybın büyük kısmı yağ olsa da yağsız kütle riski var; **protein + ağırlık + kürek/eliptik kombinasyonu** kası korurken yağ yakımını hızlandırır.\n\n"
            "_Genel bilgilendirme; tıbbi tavsiye değildir._"
        )


def page_nutrition():
    st.markdown("<h1 style='margin:0 0 10px'>Beslenme & Wegovy</h1>", unsafe_allow_html=True)
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
        compute_targets()
        _save()
        st.success("Yüklendi ve kalıcı veritabanına kaydedildi → " + " · ".join(msgs))

    nt = nutrition_today()
    t = S["targets"]
    pband = S["protein_band"]
    if nt:
        ds = nutrition.day_summary(nt, t)
        kc = ds["kcal"]
        pct = min(1, (kc["consumed"] / kc["target"]) if kc["target"] else 0)
        st.markdown(
            "<div class='fcard'><div style='display:flex;align-items:center;gap:18px'>"
            + ui.ring_svg(pct, "var(--green)", size=84)
            + f"<div><div style='font-family:Nunito;font-weight:900;font-size:28px;color:var(--fg)'>{int(kc['consumed'])} <small style='color:var(--muted);font-size:15px'>/ {int(kc['target'])}</small></div>"
            f"<div class='muted' style='font-size:13px'>kcal · {int(kc['remaining'])} kaldı</div></div></div></div>",
            unsafe_allow_html=True,
        )
        fib_val = round(float(nt.get("fiber") or 0))
        fib_pct = round(fib_val / FIBER_TARGET * 100) if FIBER_TARGET else 0
        bars = "".join([
            ui.bar(f"Protein (hedef bant {pband['min']}–{pband['max']}g)", f"{int(ds['protein']['consumed'])} / {ds['protein']['target']} g", ds['protein']['pct'] or 0, "var(--orange)", primary=True),
            ui.bar("Karbonhidrat", f"{int(ds['carbs']['consumed'])} / {ds['carbs']['target']} g", ds['carbs']['pct'] or 0, "var(--teal)"),
            ui.bar("Yağ", f"{int(ds['fat']['consumed'])} / {ds['fat']['target']} g", ds['fat']['pct'] or 0, "var(--purple)"),
            ui.bar("Lif (Wegovy sindirim desteği)", f"{fib_val} / {FIBER_TARGET} g", fib_pct, "var(--green)"),
        ])
        st.markdown(f"<div class='fcard'><div class='eyebrow'>Makrolar · bugün</div><div class='bars'>{bars}</div></div>", unsafe_allow_html=True)
        last7 = S["nutrition"].tail(7)
        if len(last7) > 1:
            fig = go.Figure(go.Bar(x=last7["date"], y=last7["protein"], marker_color="#fb923c"))
            fig.add_hline(y=pband["min"], line_dash="dot", line_color="#34d399", annotation_text=f"Alt sınır ({pband['min']}g)")
            fig.add_hline(y=t["protein"], line_dash="dash", line_color="#94a3b8", annotation_text=f"Hedef ({t['protein']}g)")
            fig.update_layout(height=180, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"))
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(gridcolor="rgba(148,163,184,.12)", ticksuffix=" g")
            st.markdown("<div class='eyebrow'>Son günler · protein</div>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Cronometer'dan **dailysummary.csv** yükle; kalori, protein, lif ve makroları burada özetlerim. Protein, Wegovy'de kas koruma için öncelikli.")

    st.markdown("<div class='eyebrow' style='margin-top:6px'>Kilo kaydet</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    nw = c1.number_input("kg", min_value=40.0, max_value=250.0, value=float(latest_weight()[0] or 100.0), step=0.1, label_visibility="collapsed")
    if c2.button("Kaydet", use_container_width=True):
        iso = TODAY.strftime("%Y-%m-%d")
        S["weights"] = [x for x in S["weights"] if x["date"] != iso] + [{"date": iso, "w": round(nw, 1)}]
        compute_targets()
        _save()
        st.success("Kalıcı olarak kaydedildi ✓")
        st.rerun()

    ws = wegovy_status()
    with st.expander(f"💉 Wegovy doz & enjeksiyon takibi ({ws['dose_mg']:g} mg · her {ws['inj_day_name']})", expanded=ws["days_until"] == 0):
        wc1, wc2, wc3 = st.columns([1.2, 1.3, 1.5])
        cur_dose = ws["dose_mg"] if ws["dose_mg"] in WEGOVY_DOSES else 0.25
        new_dose = wc1.selectbox("Mevcut doz (mg)", WEGOVY_DOSES, index=WEGOVY_DOSES.index(cur_dose),
                                 format_func=lambda x: f"{x:g} mg")
        new_wd = wc2.selectbox("Haftalık enjeksiyon günü", list(range(7)), index=ws["inj_weekday"],
                               format_func=lambda i: DOW_LONG[i])
        sel_site = wc3.selectbox("Enjeksiyon bölgesi (rotasyon)", WEGOVY_SITES,
                                 index=WEGOVY_SITES.index(ws["next_site"]))
        if new_dose != S["wegovy"].get("dose_mg") or new_wd != S["wegovy"].get("inj_weekday"):
            S["wegovy"]["dose_mg"] = float(new_dose)
            S["wegovy"]["inj_weekday"] = int(new_wd)
            _save()
            st.rerun()
        lc1, lc2 = st.columns([2, 1])
        inj_date = lc1.date_input("Enjeksiyon tarihi", value=TODAY, max_value=TODAY, format="DD.MM.YYYY", key="weg_dt")
        if lc2.button("💉 Dozu kaydet", use_container_width=True, type="primary"):
            iso_d = inj_date.isoformat()
            logs = [x for x in S["wegovy"].get("logs", []) if x.get("date") != iso_d]
            logs.append({"date": iso_d, "dose": float(new_dose), "site": sel_site})
            S["wegovy"]["logs"] = sorted(logs, key=lambda x: x["date"])
            _save()
            st.success(f"{iso_d} · {new_dose:g} mg ({sel_site}) kaydedildi ✓")
            st.rerun()
        logs = S["wegovy"].get("logs") or []
        if logs:
            recent_logs = " · ".join(f"**{x['date']}** ({x['dose']:g} mg, {x.get('site','')})" for x in reversed(logs[-4:]))
            st.caption(f"Son kayıtlar: {recent_logs}")
        st.caption("💡 Standart titrasyon: 4 haftada bir 0.25 → 0.5 → 1.0 → 1.7 → 2.4 mg (hekim kontrolünde). Enjeksiyon sonrası ilk 48 saatte uygulama RPE hedefini otomatik esnetir.")

    cx = cron_ex_df()
    if not cx.empty or S["nutrition"] is not None or S["weights"]:
        nd = len(S["nutrition"]) if S["nutrition"] is not None else 0
        npad = int(cx["padel"].sum()) if not cx.empty and "padel" in cx else 0
        st.caption(f"📄 Cronometer: {nd} gün beslenme · {len(S['weights'])} kilo · {len(cx)} seans ({npad} padel) · {len(S['active_kcal'])} gün aktif enerji")
    else:
        st.caption("📄 Cronometer'dan dışa aktardığın dosyaları yukarıdan yükle — tek kaynak.")

    wkg = latest_weight()[0] or 100.0
    with st.expander("⚙️ Hedef ayarları (kalori, protein yöntemi, yaş, boy, aktivite)"):
        b = S["body"]
        prev_snapshot = json.dumps(b, sort_keys=True)
        use_manual = st.checkbox("Kaloriyi elle belirle", value=b.get("kcal_goal") is not None,
                                 help="Kapalıyken hedef, TDEE − açık ile otomatik hesaplanır.")
        if use_manual:
            b["kcal_goal"] = int(st.number_input("Günlük kalori hedefi (kcal)", 1200, 3500,
                                                 int(b.get("kcal_goal") or 1900), step=50))
            st.caption(f"~0,5–1%/hafta (bu kiloda ~{wkg*0.005:.1f}–{wkg*0.01:.1f} kg) kas koruma için ideal bant.")
        else:
            b["kcal_goal"] = None
            b["deficit"] = int(st.number_input("Günlük kalori açığı (TDEE'den)", 0, 1200, int(b.get("deficit") or 500), step=50))
        pmodes = ["adjusted", "strict"]
        cur_pm = b.get("protein_mode", "adjusted")
        b["protein_mode"] = st.selectbox(
            "Protein hedefi hesaplama yöntemi",
            pmodes,
            index=pmodes.index(cur_pm if cur_pm in pmodes else "adjusted"),
            format_func=lambda m: (
                "Düzeltilmiş ağırlık bandı (150–180g · Wegovy için sürdürülebilir — Önerilen)"
                if m == "adjusted" else
                "Tam vücut ağırlığı × 1.8 g/kg (Katı hedef)"
            ),
        )
        bd = st.date_input("Doğum tarihi", value=dt.date.fromisoformat(b.get("birth", "1992-03-12")),
                           min_value=dt.date(1940, 1, 1), max_value=TODAY, format="DD.MM.YYYY")
        b["birth"] = bd.isoformat()
        st.caption(f"Yaş: {age_from(b['birth'])}")
        b["height"] = int(st.number_input("Boy (cm)", 120, 220, int(b["height"])))
        acts = ["light", "moderate", "high"]
        b["activity"] = st.selectbox("Aktivite düzeyi", acts, index=acts.index(b["activity"]),
                                     format_func=lambda x: {"light": "Az hareketli (masa başı)", "moderate": "Orta", "high": "Yüksek"}[x])
        if json.dumps(b, sort_keys=True) != prev_snapshot:
            compute_targets()
            _save()
            st.toast("Hedef ayarların kalıcı olarak kaydedildi ✓")
        st.caption("Kilo değiştikçe hedefler otomatik güncellenir ve yerel SQLite veritabanında saklanır.")

    t = S["targets"]
    pband = S["protein_band"]
    wl = S.get("weekly_loss", 0.0)
    wlpct = (wl / wkg * 100) if wkg else 0
    manual = S["body"].get("kcal_goal") is not None
    src = "elle seçtiğin hedef" if manual else f"TDEE ~{S['tdee']} − {S['body']['deficit']} açık"
    prot_desc = (
        f"<b>{t['protein']} g protein</b> (kas koruma bandı: <b>{pband['min']}–{pband['max']} g</b> · düzeltilmiş {pband['eff_weight']} kg)"
        if pband.get("mode") == "adjusted" else
        f"<b>{t['protein']} g protein</b> (~{PROTEIN_PER_KG} g/kg tam ağırlık)"
    )
    st.markdown(
        f"<div class='fcard' style='margin-top:8px'><div class='eyebrow'>Senin için hesaplanan hedef</div>"
        f"<div style='font-size:14px;line-height:1.7;color:var(--fg)'><b>{t['kcal']} kcal/gün</b> ({src})"
        f"&nbsp;·&nbsp;{prot_desc}"
        f"&nbsp;·&nbsp;{t['carbs']} g karb · {t['fat']} g yağ · {FIBER_TARGET} g lif</div>"
        f"<div style='margin-top:8px;font-size:13.5px;color:var(--fg)'>📉 Tahmini kayıp: <b class='good'>~{wl:.2f} kg/hafta</b> "
        f"(<span class='muted'>%{wlpct:.2f}/hafta · günde ~{S.get('deficit_now',0)} kcal açık</span>)</div></div>",
        unsafe_allow_html=True,
    )


# ---------------- nav (top bar - automatic system theme) ----------------
NAV = [("home", "🏠"), ("plan", "🗓"), ("workout", "🏋️"), ("stats", "📈"), ("nutrition", "🔥")]
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
st_info = store.status_info()
st.caption(f"Tasarım · program sana özel · 💾 {st_info['label']}")
