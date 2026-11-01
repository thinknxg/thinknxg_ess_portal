"""Shift-window arithmetic. Pure functions: no frappe imports."""
from datetime import date, datetime, time, timedelta


def to_time(v):
    """Frappe returns Time fields as timedelta from SQL and as 'HH:MM:SS' strings from documents."""
    if v is None or v == "":
        return None
    if isinstance(v, time):
        return v
    if isinstance(v, timedelta):
        secs = int(v.total_seconds()) % 86400
        return time(secs // 3600, (secs % 3600) // 60, secs % 60)
    if isinstance(v, datetime):
        return v.time()
    parts = [int(float(p)) for p in str(v).split(":")]
    while len(parts) < 3:
        parts.append(0)
    return time(parts[0] % 24, parts[1], parts[2])


def window(day, start, end, early_min=0, late_min=0):
    """Concrete datetimes for a shift on `day`. Overnight shifts end the next day."""
    st, et = to_time(start), to_time(end)
    if st is None or et is None:
        return None
    s = datetime.combine(day, st)
    e = datetime.combine(day, et)
    overnight = e <= s
    if overnight:
        e += timedelta(days=1)
    return {"date": day, "start": s, "end": e, "open": s - timedelta(minutes=int(early_min or 0)),
            "close": e + timedelta(minutes=int(late_min or 0)), "overnight": overnight,
            "hours": round((e - s).total_seconds() / 3600, 2)}


def current(windows, ts):
    live = [w for w in windows if w and w["open"] <= ts <= w["close"]]
    if not live:
        return None
    return min(live, key=lambda w: abs((w["start"] - ts).total_seconds()))


def upcoming(windows, ts):
    later = [w for w in windows if w and w["open"] > ts]
    return min(later, key=lambda w: w["open"]) if later else None


def day_range(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def as_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])
