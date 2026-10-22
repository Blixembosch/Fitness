"""Google Calendar iCal (.ics) integration for ATES FAM Fitness.

Fetches the user's private Google Calendar feed over HTTPS (RFC 5545 iCalendar)
without complex OAuth or service account setups — matching the same zero-auth,
resilient pattern used in lib/sheets.py.

Detects Padel sessions dynamically (summary keywords: padel, tennis, racquet)
including match times, locations, and weekly recurring events (RRULE).
"""
from __future__ import annotations

import re
import urllib.request
from datetime import date, datetime, timedelta, timezone

_PADEL_KEYWORDS = ("padel", "tennis", "tenis", "raket", "racquet")
_DAY_MAP = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def get_calendar_url(secrets=None, session_state=None) -> str | None:
    """Retrieve Google Calendar private iCal URL from secrets or session state."""
    if secrets is not None:
        try:
            url = secrets.get("GOOGLE_CALENDAR_ICAL_URL") or secrets.get("GCAL_ICAL_URL")
            if url and str(url).strip():
                return str(url).strip()
        except Exception:
            pass

    if session_state is not None:
        try:
            url = (
                session_state.get("settings", {}).get("gcal_url")
                or session_state.get("gcal_url")
            )
            if url and str(url).strip():
                return str(url).strip()
        except Exception:
            pass

    return None


def unfold_ics(text: str) -> list[str]:
    """Unfold lines per RFC 5545 (lines beginning with space or tab continue previous line)."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw.startswith(" ") or raw.startswith("\t"):
            if lines:
                lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _unescape_ics(s: str) -> str:
    """Unescape backslash-escaped characters in ICS strings."""
    return (
        s.replace(r"\,", ",")
        .replace(r"\;", ";")
        .replace(r"\n", " ")
        .replace(r"\N", " ")
        .replace(r"\\", "\\")
        .strip()
    )


def _parse_dt(dt_str: str) -> tuple[str | None, str | None, datetime | None]:
    """Parse date and optional time from an ICS DTSTART/DTEND string.

    Returns (iso_date 'YYYY-MM-DD', time_str 'HH:MM' or None, parsed_dt or None).
    """
    if not dt_str:
        return None, None, None
    val = dt_str.split(":")[-1].strip()
    m_date = re.match(r"^(\d{4})(\d{2})(\d{2})", val)
    if not m_date:
        return None, None, None
    y, m, d = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3))
    iso_date = f"{y:04d}-{m:02d}-{d:02d}"

    m_time = re.search(r"T(\d{2})(\d{2})", val)
    if not m_time:
        return iso_date, None, datetime(y, m, d)

    hh, mm = int(m_time.group(1)), int(m_time.group(2))
    if val.endswith("Z"):
        try:
            dt_utc = datetime(y, m, d, hh, mm, tzinfo=timezone.utc)
            dt_local = dt_utc.astimezone()
            iso_date = dt_local.strftime("%Y-%m-%d")
            time_str = dt_local.strftime("%H:%M")
            return iso_date, time_str, dt_local
        except Exception:
            return iso_date, f"{hh:02d}:{mm:02d}", datetime(y, m, d, hh, mm)

    return iso_date, f"{hh:02d}:{mm:02d}", datetime(y, m, d, hh, mm)


def is_padel_summary(summary: str) -> bool:
    """Check if event summary matches padel or racquet activity."""
    s = (summary or "").lower()
    return any(k in s for k in _PADEL_KEYWORDS)


def _expand_weekly_rrule(
    start_dt: datetime,
    rrule_str: str,
    window_start: date,
    window_end: date,
) -> list[str]:
    """Expand weekly RRULE into a list of ISO date strings within [window_start, window_end]."""
    bydays: list[str] = []
    until_date: date | None = None

    for part in rrule_str.split(";"):
        if part.startswith("BYDAY="):
            bydays = [d.strip().upper() for d in part[6:].split(",")]
        elif part.startswith("UNTIL="):
            u_str = part[6:].strip()
            m_u = re.match(r"^(\d{4})(\d{2})(\d{2})", u_str)
            if m_u:
                until_date = date(int(m_u.group(1)), int(m_u.group(2)), int(m_u.group(3)))

    start_d = start_dt.date() if isinstance(start_dt, datetime) else start_dt
    if not bydays:
        bydays = [list(_DAY_MAP.keys())[start_d.weekday()]]

    target_wds = [_DAY_MAP[d] for d in bydays if d in _DAY_MAP]
    cur = window_start
    expanded: list[str] = []
    while cur <= window_end:
        if until_date and cur > until_date:
            break
        if cur.weekday() in target_wds and cur >= start_d:
            expanded.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return expanded


def parse_ics(
    ics_text: str,
    ref_date: date | None = None,
    window_days_past: int = 35,
    window_days_future: int = 35,
) -> list[dict]:
    """Parse RFC 5545 iCalendar text into a structured list of events.

    Returns:
        [
            {
                "summary": str,
                "date": "YYYY-MM-DD",
                "start_time": "HH:MM" | None,
                "end_time": "HH:MM" | None,
                "is_padel": bool,
                "location": str,
            },
            ...
        ]
    """
    if not ics_text or not ics_text.strip():
        return []

    if ref_date is None:
        ref_date = date.today()
    w_start = ref_date - timedelta(days=window_days_past)
    w_end = ref_date + timedelta(days=window_days_future)

    lines = unfold_ics(ics_text)
    events: list[dict] = []
    in_event = False
    current: dict[str, str] = {}

    for line in lines:
        line_clean = line.strip()
        if line_clean == "BEGIN:VEVENT":
            in_event = True
            current = {}
            continue
        if line_clean == "END:VEVENT":
            in_event = False
            status = current.get("STATUS", "").upper()
            if status == "CANCELLED":
                continue

            summary = _unescape_ics(current.get("SUMMARY", ""))
            location = _unescape_ics(current.get("LOCATION", ""))
            is_padel = is_padel_summary(summary)

            dtstart_raw = current.get("DTSTART", "")
            dtend_raw = current.get("DTEND", "")
            iso_d, start_t, dt_obj = _parse_dt(dtstart_raw)
            _, end_t, _ = _parse_dt(dtend_raw)

            if not iso_d:
                continue

            rrule = current.get("RRULE", "")
            if "FREQ=WEEKLY" in rrule and dt_obj:
                dates = _expand_weekly_rrule(dt_obj, rrule, w_start, w_end)
                for d_str in dates:
                    events.append({
                        "summary": summary,
                        "date": d_str,
                        "start_time": start_t,
                        "end_time": end_t,
                        "is_padel": is_padel,
                        "location": location,
                    })
            else:
                events.append({
                    "summary": summary,
                    "date": iso_d,
                    "start_time": start_t,
                    "end_time": end_t,
                    "is_padel": is_padel,
                    "location": location,
                })
            continue

        if in_event and ":" in line:
            prop_key = line.split(":", 1)[0].split(";")[0].upper().strip()
            # Store full property specification if needed, or key value
            if prop_key in ("SUMMARY", "LOCATION", "STATUS", "RRULE"):
                current[prop_key] = line.split(":", 1)[1]
            elif prop_key in ("DTSTART", "DTEND"):
                current[prop_key] = line

    return sorted(events, key=lambda e: (e["date"], e["start_time"] or ""))


def fetch_calendar_events(
    url: str | None = None,
    timeout: int = 8,
    secrets=None,
    session_state=None,
) -> list[dict]:
    """Fetch and parse events from Google Calendar iCal feed URL with tolerant fallback."""
    if not url:
        url = get_calendar_url(secrets=secrets, session_state=session_state)
    if not url:
        return []

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) ATES_FAM_Fitness/1.0"
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
        return parse_ics(raw)
    except Exception:
        return []


def fetch_padel_events(
    url: str | None = None,
    timeout: int = 8,
    secrets=None,
    session_state=None,
) -> list[dict]:
    """Fetch only Padel / racquet events from Google Calendar."""
    events = fetch_calendar_events(
        url=url,
        timeout=timeout,
        secrets=secrets,
        session_state=session_state,
    )
    return [e for e in events if e.get("is_padel")]


def padel_dates_from_events(events: list[dict]) -> set[str]:
    """Extract set of ISO dates ('YYYY-MM-DD') from a list of calendar events."""
    return {e["date"] for e in events if e.get("date")}


def padel_event_for_date(target_date_iso: str, events: list[dict]) -> dict | None:
    """Return the first padel event dict matching target_date_iso, or None."""
    for e in events:
        if e.get("date") == target_date_iso:
            return e
    return None
