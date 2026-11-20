# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta

_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_TIME_FORMATS = (
    ("%Y-%m-%dT%H:%M:%SZ", "second"),
    ("%Y-%m-%dT%H:%MZ", "minute"),
    ("%Y-%m-%dT%HZ", "hour"),
    ("%Y-%m-%d", "day"),
    ("%Y-%m", "month"),
    ("%Y", "year"),
)


def _parse_instant(token):
    token = (token or "").strip()
    for fmt, unit in _TIME_FORMATS:
        try:
            return datetime.strptime(token, fmt), unit
        except ValueError:
            continue
    raise ValueError("Bad parameter time")


def _advance(value, unit):
    if unit == "second":
        return value + timedelta(seconds=1)
    if unit == "minute":
        return value + timedelta(minutes=1)
    if unit == "hour":
        return value + timedelta(hours=1)
    if unit == "day":
        return value + timedelta(days=1)
    if unit == "month":
        month = value.month + 1
        year = value.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        return value.replace(year=year, month=month)
    if unit == "year":
        return value.replace(year=value.year + 1)
    raise ValueError("Bad parameter time")


def is_time_field_name(name):
    return bool(_FIELD_NAME.match(name or ""))


def parse_wms_time(value):
    """
    WMS TIME instant or start/end range, as a half-open interval [start, end).
    The end token is included for its whole step (day, hour, ...).
    """
    raw = (value or "").strip()
    if not raw:
        raise ValueError("Bad parameter time")
    parts = raw.split("/")
    if len(parts) > 2:
        raise ValueError("Bad parameter time")
    start, start_unit = _parse_instant(parts[0])
    if len(parts) == 1:
        return start, _advance(start, start_unit)
    end, end_unit = _parse_instant(parts[1])
    end_exclusive = _advance(end, end_unit)
    if end_exclusive <= start:
        raise ValueError("Bad parameter time")
    return start, end_exclusive
