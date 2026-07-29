"""Utilidades de fecha y hora en zona horaria de Guatemala (UTC-6)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import DAY_NAMES, MONTH_NAMES, TIMEZONE

GT = ZoneInfo(TIMEZONE)
UTC = ZoneInfo("UTC")


def now_gt() -> datetime:
    """Momento actual en hora de Guatemala."""
    return datetime.now(GT)


def today_gt() -> date:
    return now_gt().date()


def to_gt(value) -> datetime | None:
    """Convierte un timestamp de Supabase (ISO 8601, UTC) a hora de Guatemala."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        # Postgres devuelve microsegundos de longitud variable; los normalizamos.
        if "." in text:
            head, _, tail = text.partition(".")
            digits = ""
            rest = ""
            for i, ch in enumerate(tail):
                if ch.isdigit():
                    digits += ch
                else:
                    rest = tail[i:]
                    break
            digits = (digits + "000000")[:6]
            text = f"{head}.{digits}{rest}"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(GT)


def gt_to_utc_iso(dt: datetime) -> str:
    """Convierte un datetime local de Guatemala al ISO en UTC que espera Supabase."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=GT)
    return dt.astimezone(UTC).isoformat()


def combine_gt(day: date, moment: time) -> datetime:
    return datetime.combine(day, moment).replace(tzinfo=GT)


def is_missing(value) -> bool:
    """True para None, NaN y NaT (pandas convierte columnas mixtas a NaT)."""
    if value is None:
        return True
    try:
        return bool(value != value)
    except Exception:
        return False


def hhmm(value, fallback: str = "—") -> str:
    """Hora en formato 24 h, tolerante a valores faltantes de pandas."""
    if is_missing(value):
        return fallback
    try:
        return value.strftime("%H:%M")
    except Exception:
        return fallback


def fmt_time(dt: datetime | None) -> str:
    """08:05 a.m."""
    if is_missing(dt):
        return "—"
    return dt.strftime("%I:%M %p").lstrip("0").replace("AM", "a.m.").replace("PM", "p.m.")


def fmt_datetime(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return f"{fmt_date(dt.date())} · {fmt_time(dt)}"


def fmt_date(d: date | None) -> str:
    """5 de abril de 2026"""
    if d is None:
        return "—"
    return f"{d.day} de {MONTH_NAMES[d.month].lower()} de {d.year}"


def fmt_date_short(d: date | None) -> str:
    if d is None:
        return "—"
    return d.strftime("%d/%m/%Y")


def day_name(d: date) -> str:
    return DAY_NAMES[d.isoweekday()]


def parse_time(value) -> time | None:
    """Convierte '09:00:00' o '09:00' en un objeto time."""
    if value is None:
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M", "%H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    return None


def parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def minutes_to_hhmm(minutes: int | float | None) -> str:
    """480 → '8h 00m'"""
    if minutes is None:
        return "—"
    minutes = int(round(float(minutes)))
    sign = "-" if minutes < 0 else ""
    minutes = abs(minutes)
    return f"{sign}{minutes // 60}h {minutes % 60:02d}m"


def minutes_to_decimal(minutes: int | float | None) -> float:
    if minutes is None:
        return 0.0
    return round(float(minutes) / 60.0, 2)


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def month_bounds(d: date) -> tuple[date, date]:
    first = d.replace(day=1)
    if first.month == 12:
        last = first.replace(year=first.year + 1, month=1) - timedelta(days=1)
    else:
        last = first.replace(month=first.month + 1) - timedelta(days=1)
    return first, last
