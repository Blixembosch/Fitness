"""A simplified front/back muscle map rendered as inline SVG. This is OUR drawing (not the
licensed Gym-Visual media), so it is free to use. Given a set of muscles, it tints the matching
zones by intensity — the "which muscle does this move work" view the user asked to keep."""
from __future__ import annotations

# dataset muscle name -> body-map zone(s)
MUSCLE_ZONES = {
    "chest": ["chest"], "pectorals": ["chest"], "upper chest": ["chest"], "serratus anterior": ["chest"],
    "shoulders": ["shoulderL", "shoulderR"], "delts": ["shoulderL", "shoulderR"],
    "rear deltoids": ["shoulderL", "shoulderR"], "rotator cuff": ["shoulderL", "shoulderR"],
    "biceps": ["bicepL", "bicepR"], "brachialis": ["bicepL", "bicepR"],
    "triceps": ["tricepL", "tricepR"],
    "forearms": ["faL", "faR"],
    "abs": ["absU", "absL"], "core": ["absU", "absL"], "lower abs": ["absL"], "obliques": ["absL"],
    "quads": ["quadL", "quadR"], "quadriceps": ["quadL", "quadR"], "adductors": ["quadL", "quadR"],
    "calves": ["calfL", "calfR"], "soleus": ["calfL", "calfR"],
    "lats": ["lats"], "upper back": ["lats", "traps"], "rhomboids": ["lats", "traps"],
    "traps": ["traps"], "trapezius": ["traps"],
    "lower back": ["lower"], "spine": ["lower"],
    "glutes": ["gluteL", "gluteR"], "abductors": ["gluteL", "gluteR"],
    "hamstrings": ["hamL", "hamR"],
}

_FRONT = {
    "shoulderL": "M20 20 q-6 1 -8 8 q6 -2 10 -2 z", "shoulderR": "M52 20 q6 1 8 8 q-6 -2 -10 -2 z",
    "chest": "M26 21 h20 q2 10 -3 15 q-7 3 -14 0 q-5 -5 -3 -15 z",
    "absU": "M31 37 h10 v7 h-10 z", "absL": "M31 45 h10 v9 h-10 z",
    "bicepL": "M18 29 q-4 7 -3 15 l5 -1 q0 -8 2 -14 z", "bicepR": "M54 29 q4 7 3 15 l-5 -1 q0 -8 -2 -14 z",
    "faL": "M15 45 q-2 8 -1 14 l5 -1 q0 -7 1 -13 z", "faR": "M57 45 q2 8 1 14 l-5 -1 q0 -7 -1 -13 z",
    "quadL": "M28 56 q-3 14 -1 26 l8 -1 q1 -14 0 -25 z", "quadR": "M44 56 q3 14 1 26 l-8 -1 q-1 -14 0 -25 z",
    "calfL": "M28 84 q-1 12 1 20 l6 -1 q1 -11 0 -19 z", "calfR": "M44 84 q1 12 -1 20 l-6 -1 q-1 -11 0 -19 z",
}
_BACK = {
    "traps": "M27 19 h18 q-2 8 -9 9 q-7 -1 -9 -9 z",
    "shoulderL": "M20 20 q-6 1 -8 8 q6 -2 10 -2 z", "shoulderR": "M52 20 q6 1 8 8 q-6 -2 -10 -2 z",
    "lats": "M25 29 h22 q2 11 -4 17 q-7 2 -14 0 q-6 -6 -4 -17 z",
    "lower": "M31 47 h10 v8 h-10 z",
    "tricepL": "M18 29 q-4 7 -3 15 l5 -1 q0 -8 2 -14 z", "tricepR": "M54 29 q4 7 3 15 l-5 -1 q0 -8 -2 -14 z",
    "gluteL": "M29 55 q-3 6 -2 12 l9 0 q0 -7 -1 -12 z", "gluteR": "M43 55 q3 6 2 12 l-9 0 q0 -7 1 -12 z",
    "hamL": "M28 67 q-2 11 0 18 l8 -1 q1 -9 0 -17 z", "hamR": "M44 67 q2 11 0 18 l-8 -1 q-1 -9 0 -17 z",
    "calfL": "M28 86 q-1 11 1 18 l6 -1 q1 -10 0 -17 z", "calfR": "M44 86 q1 11 -1 18 l-6 -1 q-1 -10 0 -17 z",
}
_OUTLINE = ("M36 2 q10 0 10 11 q6 2 9 10 q3 10 2 18 q6 10 5 24 q3 16 0 40 "
            "M36 2 q-10 0 -10 11 q-6 2 -9 10 q-3 10 -2 18 q-6 10 -5 24 q-3 16 0 40")

_FILL = {0: "var(--track)", 1: "var(--map1)", 2: "var(--map2)", 3: "var(--map3)"}


def _svg(zones: dict, weights: dict) -> str:
    out = ['<svg viewBox="0 0 72 108" width="46%" style="max-width:150px;height:auto">']
    out.append(f'<path d="{_OUTLINE}" fill="none" stroke="var(--line)" stroke-width="1.2"/>')
    for k, d in zones.items():
        out.append(f'<path d="{d}" fill="{_FILL.get(weights.get(k, 0), _FILL[0])}"/>')
    out.append("</svg>")
    return "".join(out)


def weights_for(primary: list[str], secondary: list[str]) -> dict:
    """zone -> intensity 1..3 from primary (3) / secondary (2) muscle lists."""
    w: dict[str, int] = {}
    for m in secondary or []:
        for z in MUSCLE_ZONES.get(m, []):
            w[z] = max(w.get(z, 0), 2)
    for m in primary or []:
        for z in MUSCLE_ZONES.get(m, []):
            w[z] = 3
    return w


def body_map(primary: list[str], secondary: list[str]) -> str:
    """Front + back SVG pair with the given muscles tinted. Wrap in a flex row."""
    w = weights_for(primary, secondary)
    return (
        '<div style="display:flex;gap:8px;justify-content:center;align-items:flex-start">'
        + _svg(_FRONT, w) + _svg(_BACK, w) + "</div>"
    )
