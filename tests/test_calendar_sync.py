from datetime import date
from unittest.mock import MagicMock, patch

from lib import calendar_sync


def test_unfold_ics():
    folded = "SUMMARY:Padel Match with \r\n Friends \r\n at Peak"
    lines = calendar_sync.unfold_ics(folded)
    assert len(lines) == 1
    assert lines[0] == "SUMMARY:Padel Match with Friends at Peak"


def test_parse_dt():
    d, t, _ = calendar_sync._parse_dt("DTSTART;VALUE=DATE:20261024")
    assert d == "2026-10-24"
    assert t is None

    d2, t2, _ = calendar_sync._parse_dt("DTSTART;TZID=Europe/Amsterdam:20261022T193000")
    assert d2 == "2026-10-22"
    assert t2 == "19:30"


def test_is_padel_summary():
    assert calendar_sync.is_padel_summary("Padel") is True
    assert calendar_sync.is_padel_summary("🎾 Padel Maçı - Peak") is True
    assert calendar_sync.is_padel_summary("Tennis Doubles") is True
    assert calendar_sync.is_padel_summary("Şirket Toplantısı") is False
    assert calendar_sync.is_padel_summary("") is False


def test_parse_ics_extracts_events():
    sample_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
BEGIN:VEVENT
DTSTART:20261024T180000
DTEND:20261024T193000
SUMMARY:Padel Maçı
LOCATION:Peak Padel Club
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART:20261025T090000
DTEND:20261025T100000
SUMMARY:Proje Görüşmesi
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
DTSTART:20261026T170000
DTEND:20261026T180000
SUMMARY:Padel İptal
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""

    events = calendar_sync.parse_ics(sample_ics)
    assert len(events) == 2  # Cancelled event omitted

    padel_ev = next(e for e in events if e["summary"] == "Padel Maçı")
    assert padel_ev["date"] == "2026-10-24"
    assert padel_ev["start_time"] == "18:00"
    assert padel_ev["end_time"] == "19:30"
    assert padel_ev["is_padel"] is True
    assert padel_ev["location"] == "Peak Padel Club"

    non_padel = next(e for e in events if e["summary"] == "Proje Görüşmesi")
    assert non_padel["is_padel"] is False


def test_parse_ics_recurring_rrule():
    # Tuesday weekly recurring padel
    ref = date(2026, 10, 22)  # Thursday
    sample_ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART:20261006T190000
DTEND:20261006T203000
RRULE:FREQ=WEEKLY;BYDAY=TU
SUMMARY:Salı Padel Grubu
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

    events = calendar_sync.parse_ics(sample_ics, ref_date=ref, window_days_past=14, window_days_future=14)
    assert len(events) >= 2
    for ev in events:
        assert ev["is_padel"] is True
        assert ev["start_time"] == "19:00"
        d = date.fromisoformat(ev["date"])
        assert d.weekday() == 1  # Tuesday


def test_get_calendar_url():
    # From secrets dict
    secrets = {"GOOGLE_CALENDAR_ICAL_URL": "https://calendar.google.com/ical/test.ics"}
    assert calendar_sync.get_calendar_url(secrets=secrets) == "https://calendar.google.com/ical/test.ics"

    # From GCAL_ICAL_URL alias
    secrets_alias = {"GCAL_ICAL_URL": "https://calendar.google.com/ical/alias.ics"}
    assert calendar_sync.get_calendar_url(secrets=secrets_alias) == "https://calendar.google.com/ical/alias.ics"

    # From session_state
    session = {"settings": {"gcal_url": "https://calendar.google.com/ical/session.ics"}}
    assert calendar_sync.get_calendar_url(secrets={}, session_state=session) == "https://calendar.google.com/ical/session.ics"

    # Fallback to None
    assert calendar_sync.get_calendar_url(secrets={}, session_state={}) is None


def test_fetch_calendar_events_graceful_fallback():
    # Missing / None URL
    assert calendar_sync.fetch_calendar_events(url=None, secrets={}) == []

    # Network failure or invalid URL
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        assert calendar_sync.fetch_calendar_events(url="https://invalid.local/calendar.ics") == []


def test_padel_helpers():
    events = [
        {"date": "2026-10-22", "summary": "Padel", "start_time": "18:00", "is_padel": True},
        {"date": "2026-10-23", "summary": "Toplantı", "start_time": "10:00", "is_padel": False},
        {"date": "2026-10-25", "summary": "Padel Maçı", "start_time": "11:00", "is_padel": True},
    ]
    dates = calendar_sync.padel_dates_from_events([e for e in events if e["is_padel"]])
    assert dates == {"2026-10-22", "2026-10-25"}

    ev_today = calendar_sync.padel_event_for_date("2026-10-22", events)
    assert ev_today is not None and ev_today["summary"] == "Padel"

    ev_none = calendar_sync.padel_event_for_date("2026-10-24", events)
    assert ev_none is None
