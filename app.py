"""Fitness — our own Streamlit interface over the openGym exercise data.
5 pages, Home centered. The training program is auto-generated for the user's profile
(lib/program.py); Plan and Antrenman render it (no manual building). Phase 1: session data +
Cronometer CSV + manual weight. Persistence (Google Sheets) + Apple Health sync come next."""
from __future__ import annotations
import datetime as dt
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from lib import data, nutrition, bodymap, ui, program as P

st.set_page_config(page_title="Fitness", page_icon="💪", layout="centered", initial_sidebar_state="collapsed")
ui.inject()

# ---------------- state ----------------
S = st.session_state
S.setdefault("page", "home")
S.setdefault("targets", {"kcal": 1810, "protein": 152, "carbs": 166, "fat": 60})
S.setdefault("weights", [{"date": "2026-10-12", "w": 101.1}, {"date": "2026-10-16", "w": 101.1}, {"date": "2026-10-19", "w": 100.5}])
S.setdefault("workouts", [])          # [{date, key, name, muscles:(primary,secondary)}]
S.setdefault("padel", [])             # [iso date]
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

    # written summary line
    st.markdown(
        f"<div class='fcard' style='padding:13px 16px'><div style='font-size:13px;line-height:1.7'>"
        f"<b>Bu hafta:</b> {wk}/3 antrenman&nbsp;·&nbsp;{pad} padel&nbsp;·&nbsp;"
        f"protein {prot}/{t['protein']} g&nbsp;·&nbsp;{kcal}/{t['kcal']} kcal</div></div>",
        unsafe_allow_html=True,
    )
    deficit = kcal - t["kcal"] if nt else None
    r1 = ui.ring(wk / 3 if wk else 0, "var(--blue)", f"{wk}<small>/3</small>", "Antrenman")
    r2 = ui.ring(prot / t["protein"] if t["protein"] else 0, "var(--orange)", f"{prot}<small>/{t['protein']} g</small>", "Protein")
    klbl = f"Kalori{' · ' + ('+' if deficit > 0 else '') + str(deficit) if deficit is not None else ''}"
    r3 = ui.ring(kcal / t["kcal"] if t["kcal"] else 0, "var(--green)", f"{kcal}<small>/{t['kcal']}</small>", klbl)
    st.markdown(f"<div class='rings'>{r1}{r2}{r3}</div>", unsafe_allow_html=True)
    if st.button("🎾 Padel yaptım", use_container_width=True):
        iso = TODAY.strftime("%Y-%m-%d")
        if iso not in S["padel"]:
            S["padel"].append(iso)
        st.rerun()

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
    # streak
    st.markdown(
        f"<div class='fcard' style='display:flex;align-items:center;gap:14px'>"
        f"<div style='width:42px;height:42px;border-radius:12px;background:color-mix(in srgb,var(--orange) 16%,var(--surface-2));color:var(--orange);display:flex;align-items:center;justify-content:center;font-size:20px'>🔥</div>"
        f"<div><div style='font-family:Nunito;font-weight:900;font-size:19px'>{len(S['workouts'])} antrenman kayıtlı</div>"
        f"<div class='muted' style='font-size:13px'>Bu hafta {len(workouts_week())}/3 · {len(padel_week())} padel</div></div></div>",
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


def _exercise_card(e, color):
    chips = "".join(f"<span class='chip' style='font-size:11px'>{data.tr_muscle(m)}</span>" for m in (e["primary"] + e["secondary"])[:5])
    st.markdown(
        f"<div class='fcard' style='margin-bottom:10px'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:8px'>"
        f"<div><div style='font-weight:700;font-size:15px'>{e['name']}</div>"
        f"<div class='muted' style='font-size:12px;margin-top:2px'>{data.tr_eq(e.get('eq',''))}</div></div>"
        f"<div style='text-align:right;flex-shrink:0'><div style='font-family:Nunito;font-weight:900;font-size:18px;color:{color}'>{e['sets']}×{e['reps']}</div>"
        f"<div class='muted' style='font-size:11px'>set × tekrar</div></div></div>"
        f"<div style='margin:10px 0 4px'>{bodymap.body_map(e['primary'], e['secondary'])}</div>"
        + ui.legend(color)
        + f"<div class='chiprow' style='margin-top:10px'>{chips}</div>"
        f"<div class='muted' style='font-size:12.5px;margin-top:8px'>💡 {e.get('tip','')}</div></div>",
        unsafe_allow_html=True,
    )


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
    for e in P.day_details(day):
        _exercise_card(e, color)

    done_iso = TODAY.strftime("%Y-%m-%d")
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
    nwin = ndf[ndf["date"] >= start] if ndf is not None and not ndf.empty else pd.DataFrame()
    ad = nutrition.protein_adherence(nwin, S["targets"]["protein"]) if not nwin.empty else {"days": 0, "met": 0, "avg_protein": 0, "avg_kcal": 0}
    wdf = weights_df()
    wwin = wdf[wdf["date"] >= pd.Timestamp(start)] if not wdf.empty else wdf
    wdelta = (wwin["w"].iloc[-1] - wwin["w"].iloc[0]) if len(wwin) > 1 else 0
    deficit = (ad["avg_kcal"] - S["targets"]["kcal"]) if ad["days"] else None
    tiles = "".join([
        ui.tile("Antrenman", str(len(wk)), f"{days} günde"),
        ui.tile("Protein ort.", f"{ad['avg_protein']}<small> g</small>", f"{ad['met']}/{ad['days']} gün hedefte" if ad["days"] else "veri yok", "good" if ad["met"] else ""),
        ui.tile("Kalori açığı", (f"{deficit:+d}" if deficit is not None else "–"), "günlük ort.", "good" if (deficit or 0) <= 0 else "bad"),
        ui.tile("Kilo", f"{wdelta:+.1f}", "kg", "good" if wdelta < 0 else "bad" if wdelta > 0 else ""),
    ])
    st.markdown(f"<div class='tiles'>{tiles}</div>", unsafe_allow_html=True)

    st.markdown("<div class='eyebrow' style='margin-top:16px'>Kilo trendi</div>", unsafe_allow_html=True)
    if not wdf.empty:
        fig = go.Figure(go.Scatter(x=wdf["date"], y=wdf["w"], mode="lines+markers", line=dict(color="#30d158", width=3), marker=dict(size=6)))
        fig.update_layout(height=200, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#9aa1ae"))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", ticksuffix=" kg")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # weekly planned volume by muscle group (from the program) — always informative
    st.markdown("<div class='eyebrow' style='margin-top:6px'>Haftalık planlanan hacim</div>", unsafe_allow_html=True)
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
        st.markdown(f"<div class='fcard'><div class='bars'>{bars}</div></div>", unsafe_allow_html=True)

    # muscle map of what the week's program (or logged) trains
    st.markdown("<div class='eyebrow'>Kas haritası · bu hafta</div>", unsafe_allow_html=True)
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


# ---------------- nav + routing ----------------
PAGES = {"home": page_home, "plan": page_plan, "workout": page_workout, "stats": page_stats, "nutrition": page_nutrition}
PAGES[S["page"]]()

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
NAV = [("plan", "🗓", "Plan"), ("workout", "🏋️", "Antrenman"), ("home", "🏠", "Ana Sayfa"), ("stats", "📊", "İstatistik"), ("nutrition", "🔥", "Beslenme")]
cols = st.columns([1, 1, 1.3, 1, 1])
for col, (key, icon, label) in zip(cols, NAV):
    with col:
        st.button(f"{icon}\n\n{label}" if key == "home" else f"{icon} {label}",
                  key=f"nav_{key}", use_container_width=True,
                  type="primary" if S["page"] == key else "secondary",
                  on_click=navigate, args=(key,))
st.caption("Tasarım önizlemesi · program sana özel otomatik oluşturuldu · veriler şimdilik oturum içinde")
