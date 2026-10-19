"""Fitness — our own Streamlit interface over the openGym exercise data.
Keeps what matters from the fork (which move works which muscle) and drops the old UI.
Phase 1: runs on Streamlit Cloud with session data + Cronometer CSV + manual weight.
Persistence (Google Sheets) and Apple Health auto-sync come next."""
from __future__ import annotations
import datetime as dt
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from lib import data, nutrition, bodymap, ui

st.set_page_config(page_title="Fitness", page_icon="💪", layout="centered", initial_sidebar_state="collapsed")
ui.inject()

# ---------------- state ----------------
S = st.session_state
S.setdefault("targets", {"kcal": 1810, "protein": 152, "carbs": 166, "fat": 60})
S.setdefault("weights", [  # sample seed; replace by logging
    {"date": "2026-10-12", "w": 101.1}, {"date": "2026-10-16", "w": 101.1}, {"date": "2026-10-19", "w": 100.5},
])
S.setdefault("workouts", [])          # [{date, name, entries:[{id,n,primary,secondary,sets:[{kg,reps}]}]}]
S.setdefault("nutrition", None)       # DataFrame or None
S.setdefault("session_ex", [])        # exercises added to the in-progress workout

TODAY = dt.date.today()
GREET = ("İyi geceler" if TODAY and dt.datetime.now().hour < 6 else
         "Günaydın" if dt.datetime.now().hour < 12 else
         "İyi günler" if dt.datetime.now().hour < 18 else "İyi akşamlar")
MON_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
DAY_TR = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


# ---------------- helpers ----------------
def primary_secondary(ex: dict):
    primary = [m for m in [ex.get("tg"), ex.get("mg")] if m]
    secondary = [m for m in (ex.get("sm") or []) if m not in primary]
    return primary, secondary


def weights_df():
    df = pd.DataFrame(S["weights"])
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def latest_weight():
    df = weights_df()
    return (df["w"].iloc[-1], df["date"].iloc[-1]) if not df.empty else (None, None)


def nutrition_today():
    df = S["nutrition"]
    if df is None or df.empty:
        return None
    iso = TODAY.strftime("%Y-%m-%d")
    row = df[df["date"] == iso]
    return (row.iloc[0] if not row.empty else df.iloc[-1]).to_dict()


def workouts_this_week():
    start = (TODAY - dt.timedelta(days=TODAY.weekday())).strftime("%Y-%m-%d")
    return [w for w in S["workouts"] if w["date"] >= start]


# ---------------- header ----------------
st.markdown(
    f"<div style='display:flex;justify-content:space-between;align-items:flex-start'>"
    f"<div><h1 style='margin:0;font-size:28px'>{GREET}, Anıl</h1>"
    f"<div style='color:var(--muted);font-size:13.5px;margin-top:3px'>{DAY_TR[TODAY.weekday()]} · {TODAY.day} {MON_TR[TODAY.month-1]}</div></div>"
    f"<div style='font-size:30px'>💪</div></div>",
    unsafe_allow_html=True,
)

tabs = st.tabs(["🏠 Ana Sayfa", "🗓 Plan", "🏋️ Antrenman", "📊 İstatistik", "🔥 Beslenme", "📚 Egzersizler"])

# ===================== ANA SAYFA =====================
with tabs[0]:
    nt = nutrition_today()
    prot = int(nt["protein"]) if nt else 0
    kcal = int(nt["kcal"]) if nt else 0
    t = S["targets"]
    wk_done = len(workouts_this_week())
    wk_target = 4
    deficit = kcal - t["kcal"] if nt else None
    r1 = ui.ring(wk_done / wk_target if wk_target else 0, "var(--blue)", f"{wk_done}<small>/{wk_target}</small>", "Antrenman")
    r2 = ui.ring(prot / t["protein"] if t["protein"] else 0, "var(--orange)", f"{prot}<small>/{t['protein']} g</small>", "Protein")
    kcal_lbl = f"Kalori{' · ' + ('+' if deficit > 0 else '') + str(deficit) if deficit is not None else ''}"
    r3 = ui.ring(kcal / t["kcal"] if t["kcal"] else 0, "var(--green)", f"{kcal}<small>/{t['kcal']}</small>", kcal_lbl)
    st.markdown(f"<div class='rings'>{r1}{r2}{r3}</div>", unsafe_allow_html=True)

    st.markdown("<p class='eyebrow'>Bugün</p>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hero' style='background:radial-gradient(130% 90% at 100% 0%, color-mix(in srgb,var(--blue) 30%,transparent), transparent 60%), linear-gradient(165deg, color-mix(in srgb,var(--blue) 14%,var(--surface)), var(--surface) 78%); border:1px solid color-mix(in srgb,var(--blue) 28%,var(--line))'>"
        "<div class='kick' style='color:var(--blue)'>● Üst Vücut · A</div>"
        "<h2>Üst A</h2>"
        "<div class='chiprow'><span class='chip'>Göğüs</span><span class='chip'>Sırt</span><span class='chip'>Omuz</span><span class='chip'>Kol</span></div>"
        "<div style='color:var(--muted);font-size:13px;margin-top:8px'>6 egzersiz · ~50 dk</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Antrenmana başlamak için **🏋️ Antrenman** sekmesi.")

    w, wd = latest_weight()
    if w is not None:
        df = weights_df()
        delta = df["w"].iloc[-1] - df["w"].iloc[0] if len(df) > 1 else 0
        dcls = "good" if delta < 0 else ("bad" if delta > 0 else "")
        st.markdown(
            f"<div class='fcard'><div class='eyebrow'>Vücut ağırlığı</div>"
            f"<div style='display:flex;align-items:flex-end;gap:10px'>"
            f"<span style='font-family:Nunito;font-weight:900;font-size:36px;line-height:.95'>{w:.1f}</span>"
            f"<span style='color:var(--faint);font-weight:700'>kg</span>"
            f"<span class='{dcls}' style='margin-inline-start:auto;font-weight:700;font-size:13px'>{'↓' if delta<0 else '↑' if delta>0 else '–'} {abs(delta):.1f} kg</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

# ===================== PLAN =====================
with tabs[1]:
    st.markdown("<p class='eyebrow'>Bu hafta · 4 antrenman</p>", unsafe_allow_html=True)
    plan = [
        ("Pazartesi", "Üst · A", "var(--blue)", "6 egzersiz · ~50 dk", ["Göğüs", "Sırt", "Omuz"]),
        ("Salı", "Padel", "var(--green)", "Saha günü", []),
        ("Çarşamba", "Alt · A", "var(--purple)", "5 egzersiz · ~45 dk", ["Ön bacak", "Kalça", "Baldır"]),
        ("Cuma", "Üst · B", "var(--blue)", "6 egzersiz · ~50 dk", ["Sırt", "Omuz", "Kol"]),
        ("Cumartesi", "Kardiyo", "var(--green)", "Kürek · ~30 dk", []),
        ("Pazar", "Dinlenme", "var(--faint)", "", []),
    ]
    for day, tag, color, sub, chips in plan:
        ch = "".join(f"<span class='chip'>{c}</span>" for c in chips)
        ch = f"<div class='chiprow'>{ch}</div>" if ch else ""
        st.markdown(
            f"<div style='display:flex;background:var(--surface);border:1px solid var(--line);border-radius:18px;overflow:hidden;margin-bottom:10px'>"
            f"<div style='width:5px;background:{color}'></div>"
            f"<div style='padding:13px 15px;flex:1'>"
            f"<div style='font-weight:800;font-size:15px'>{day} "
            f"<span style='font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:{color};background:color-mix(in srgb,{color} 15%,transparent);padding:2px 7px;border-radius:6px;margin-inline-start:4px'>{tag}</span></div>"
            f"<div style='color:var(--muted);font-size:12.5px;margin-top:3px'>{sub}</div>{ch}</div></div>",
            unsafe_allow_html=True,
        )
    st.caption("Planı düzenlenebilir hale getirmek sıradaki adımlardan.")

# ===================== ANTRENMAN =====================
with tabs[2]:
    st.subheader("Antrenman")
    exs = data.all_exercises()
    names = {f"{e['n']}  ·  {data.tr_bp(e['bp'])}": e["id"] for e in data.search(limit=400)}
    pick = st.selectbox("Egzersiz ekle", ["—"] + list(names.keys()), index=0, key="addpick")
    if pick != "—" and st.button("➕ Ekle", use_container_width=True):
        eid = names[pick]
        ex = data.by_id()[eid]
        p, s = primary_secondary(ex)
        S["session_ex"].append({"id": eid, "n": ex["n"], "primary": p, "secondary": s,
                                "sets": [{"kg": 20.0, "reps": 10}, {"kg": 20.0, "reps": 10}, {"kg": 20.0, "reps": 10}]})
        st.rerun()

    if not S["session_ex"]:
        st.info("Egzersiz ekleyerek bugünkü antrenmanı kur. Her egzersizin hangi kası çalıştırdığını kas haritasında göreceksin.")
    for i, se in enumerate(S["session_ex"]):
        with st.container(border=True):
            st.markdown(f"**{se['n']}**")
            muscles = ", ".join(data.tr_muscle(m) for m in (se["primary"] + se["secondary"])[:4])
            st.caption(muscles)
            st.markdown(bodymap.body_map(se["primary"], se["secondary"]) + ui.legend("var(--blue)"), unsafe_allow_html=True)
            edited = st.data_editor(
                pd.DataFrame(se["sets"]), num_rows="dynamic", use_container_width=True, key=f"sets{i}",
                column_config={"kg": st.column_config.NumberColumn("kg", min_value=0.0, step=2.5),
                               "reps": st.column_config.NumberColumn("tekrar", min_value=0, step=1)},
            )
            S["session_ex"][i]["sets"] = edited.to_dict("records")
            if st.button("Kaldır", key=f"rm{i}"):
                S["session_ex"].pop(i)
                st.rerun()

    if S["session_ex"] and st.button("✅ Antrenmanı bitir", type="primary", use_container_width=True):
        S["workouts"].append({"date": TODAY.strftime("%Y-%m-%d"), "name": "Antrenman", "entries": list(S["session_ex"])})
        S["session_ex"] = []
        st.success("Antrenman kaydedildi (bu oturumda). Kalıcı kayıt sıradaki adım.")
        st.rerun()

# ===================== İSTATİSTİK =====================
with tabs[3]:
    period = st.segmented_control("Dönem", ["Hafta", "Ay"], default="Hafta", key="ovper") or "Hafta"
    days = 7 if period == "Hafta" else 30
    start = TODAY - dt.timedelta(days=days - 1)
    wk = [w for w in S["workouts"] if w["date"] >= start.strftime("%Y-%m-%d")]
    ndf = S["nutrition"]
    nwin = ndf[ndf["date"] >= start.strftime("%Y-%m-%d")] if ndf is not None and not ndf.empty else pd.DataFrame()
    ad = nutrition.protein_adherence(nwin, S["targets"]["protein"]) if not nwin.empty else {"days": 0, "met": 0, "avg_protein": 0, "avg_kcal": 0}
    wdf = weights_df()
    wwin = wdf[wdf["date"] >= pd.Timestamp(start)] if not wdf.empty else wdf
    wdelta = (wwin["w"].iloc[-1] - wwin["w"].iloc[0]) if len(wwin) > 1 else 0
    deficit = (ad["avg_kcal"] - S["targets"]["kcal"]) if ad["days"] else None
    t1 = ui.tile("Antrenman", str(len(wk)), f"{days} günde", "")
    t2 = ui.tile("Protein ort.", f"{ad['avg_protein']}<small> g</small>", f"{ad['met']}/{ad['days']} gün hedefte" if ad["days"] else "veri yok", "good" if ad["met"] else "")
    t3 = ui.tile("Kalori açığı", (f"{deficit:+d}" if deficit is not None else "–"), "hedefe göre", "good" if (deficit or 0) <= 0 else "bad")
    t4 = ui.tile("Kilo", f"{wdelta:+.1f}", "kg", "good" if wdelta < 0 else ("bad" if wdelta > 0 else ""))
    st.markdown(f"<div class='tiles'>{t1}{t2}{t3}{t4}</div>", unsafe_allow_html=True)

    st.markdown("<div class='eyebrow' style='margin-top:14px'>Kilo trendi</div>", unsafe_allow_html=True)
    if not wdf.empty:
        fig = go.Figure(go.Scatter(x=wdf["date"], y=wdf["w"], mode="lines+markers",
                                   line=dict(color="#30d158", width=3), marker=dict(size=6)))
        fig.update_layout(height=220, margin=dict(l=0, r=0, t=6, b=0), paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#9aa1ae"))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="rgba(255,255,255,.06)", ticksuffix=" kg")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # muscle balance from logged workouts in window
    st.markdown("<div class='eyebrow' style='margin-top:6px'>Kas dengesi · çalışılan kaslar</div>", unsafe_allow_html=True)
    prim: dict[str, int] = {}
    for w in wk:
        for e in w["entries"]:
            for m in e["primary"]:
                prim[m] = prim.get(m, 0) + 1
            for m in e["secondary"]:
                prim[m] = prim.get(m, 0) + 0  # secondary shown lighter via body map below
    primary_list = [m for m, _ in sorted(prim.items(), key=lambda x: -x[1])]
    secondary_list = [m for w in wk for e in w["entries"] for m in e["secondary"]]
    st.markdown(bodymap.body_map(primary_list, secondary_list) + ui.legend("var(--blue)"), unsafe_allow_html=True)
    if not wk:
        st.caption("Bu dönemde kayıtlı antrenman yok. Antrenman sekmesinden logla, kas haritası dolsun.")

# ===================== BESLENME =====================
with tabs[4]:
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
            f"<div style='color:var(--muted);font-size:13px'>kcal · {int(kc['remaining'])} kaldı</div></div></div></div>",
            unsafe_allow_html=True,
        )
        bars = "".join([
            ui.bar("Protein", f"{int(ds['protein']['consumed'])} / {ds['protein']['target']} g", ds['protein']['pct'] or 0, "var(--orange)", primary=True),
            ui.bar("Karbonhidrat", f"{int(ds['carbs']['consumed'])} / {ds['carbs']['target']} g", ds['carbs']['pct'] or 0, "var(--teal)"),
            ui.bar("Yağ", f"{int(ds['fat']['consumed'])} / {ds['fat']['target']} g", ds['fat']['pct'] or 0, "var(--purple)"),
        ])
        st.markdown(f"<div class='fcard'><div class='eyebrow'>Makrolar</div><div class='bars'>{bars}</div></div>", unsafe_allow_html=True)
    else:
        st.info("Cronometer CSV yükle ya da aşağıdan kiloyu gir. Protein, Wegovy'de kas koruma için öncelikli.")

    st.markdown("<div class='eyebrow' style='margin-top:6px'>Kilo kaydet</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    nw = c1.number_input("kg", min_value=40.0, max_value=250.0, value=float(latest_weight()[0] or 100.0), step=0.1, label_visibility="collapsed")
    if c2.button("Kaydet", use_container_width=True):
        S["weights"] = [x for x in S["weights"] if x["date"] != TODAY.strftime("%Y-%m-%d")]
        S["weights"].append({"date": TODAY.strftime("%Y-%m-%d"), "w": round(nw, 1)})
        st.success("Kaydedildi (bu oturumda).")
        st.rerun()

# ===================== EGZERSİZLER =====================
with tabs[5]:
    q = st.text_input("Ara", placeholder="Hareket ara…", label_visibility="collapsed")
    c1, c2 = st.columns(2)
    bp_opts = ["Tümü"] + data.body_parts()
    eq_opts = ["Tümü"] + data.equipment()
    bp_sel = c1.selectbox("Bölge", bp_opts, format_func=lambda x: "Tümü" if x == "Tümü" else data.tr_bp(x))
    eq_sel = c2.selectbox("Ekipman", eq_opts, format_func=lambda x: "Tümü" if x == "Tümü" else data.tr_eq(x))
    results = data.search(q, None if bp_sel == "Tümü" else bp_sel, None if eq_sel == "Tümü" else eq_sel, limit=40)
    st.caption(f"{len(results)} sonuç" + (" (ilk 40)" if len(results) == 40 else ""))
    labels = {f"{e['n']} · {data.tr_bp(e['bp'])}": e["id"] for e in results}
    sel = st.radio("Sonuçlar", list(labels.keys()), label_visibility="collapsed") if labels else None
    if sel:
        ex = data.by_id()[labels[sel]]
        p, s = primary_secondary(ex)
        st.markdown(f"### {ex['n']}")
        st.caption(f"{data.tr_eq(ex.get('eq',''))} · {data.tr_bp(ex['bp'])}")
        st.markdown(bodymap.body_map(p, s) + ui.legend("var(--blue)"), unsafe_allow_html=True)
        rows = [ui.bar(data.tr_muscle(m), "Birincil", 100, "var(--blue)") for m in p]
        rows += [ui.bar(data.tr_muscle(m), "İkincil", 55, "var(--map2)") for m in s]
        st.markdown(f"<div class='fcard'><div class='bars'>{''.join(rows)}</div></div>", unsafe_allow_html=True)
