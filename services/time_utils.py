"""
Time zone utilities. Match times in the DB are ET (Eastern).
In June 2026 both zones observe DST: EDT = UTC-4, PDT = UTC-7 → offset = -3 h.
"""
from datetime import datetime, timedelta, date as _date


def et_to_pt(date_str: str, et_time: str) -> datetime:
    """Return a PT datetime given an ET date string (YYYY-MM-DD) and HH:MM time."""
    dt = datetime.strptime(f"{date_str} {et_time}", "%Y-%m-%d %H:%M")
    return dt - timedelta(hours=3)


def fmt_match_time(date_str: str, et_time: str) -> str:
    """Return display string like '12 PM · 11 June' or '4:30 PM · 27 June' in PT."""
    dt_pt = et_to_pt(date_str, et_time)
    hour = dt_pt.hour
    minute = dt_pt.minute
    am_pm = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    time_part = f"{display_hour}:{minute:02d} {am_pm}" if minute else f"{display_hour} {am_pm}"
    return f"{time_part} · {dt_pt.day} {dt_pt.strftime('%B')}"


def fmt_date(date_str: str) -> str:
    """Return '11 June' from a YYYY-MM-DD string."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.day} {dt.strftime('%B')}"


def pt_date_str(date_str: str, et_time: str) -> str:
    """Return the PT calendar date as 'YYYY-MM-DD' (may differ from ET for midnight matches)."""
    return et_to_pt(date_str, et_time).strftime("%Y-%m-%d")


def today_pt() -> _date:
    """Current calendar date in Pacific Time (UTC-7 in June/July during DST).
    Use this instead of date.today() so Streamlit Cloud (UTC) shows the correct day.
    """
    return (datetime.utcnow() - timedelta(hours=7)).date()
