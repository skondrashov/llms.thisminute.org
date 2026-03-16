"""
Timezone Converter — Convert times between timezones with DST awareness.

Zone conversion, DST transition detection, overlap window calculation,
and abbreviation resolution. Pure Python, stdlib only (zoneinfo).

CAPABILITIES
============
1. Time Conversion: any zone to any zone, naive or aware datetimes
2. DST Detection: is_dst, next transition, all transitions in year
3. Overlap Windows: find shared work hours across multiple timezones
4. Abbreviation Resolution: 60+ abbreviations, ambiguity handling, UTC offsets
5. Multi-format parsing: ISO, US, EU, time-only formats
"""

from __future__ import annotations

from datetime import datetime, date, time, timezone, timedelta
from zoneinfo import ZoneInfo, available_timezones


# ═══════════════════════════════════════════════════════════════════
# Abbreviation resolution
# ═══════════════════════════════════════════════════════════════════

ABBREVIATION_MAP: dict[str, str] = {
    "EST": "America/New_York", "EDT": "America/New_York",
    "CST": "America/Chicago", "CDT": "America/Chicago",
    "MST": "America/Denver", "MDT": "America/Denver",
    "PST": "America/Los_Angeles", "PDT": "America/Los_Angeles",
    "AKST": "America/Anchorage", "AKDT": "America/Anchorage",
    "HST": "Pacific/Honolulu", "AST": "America/Halifax",
    "GMT": "Europe/London", "BST": "Europe/London",
    "CET": "Europe/Berlin", "CEST": "Europe/Berlin",
    "EET": "Europe/Bucharest", "EEST": "Europe/Bucharest",
    "WET": "Europe/Lisbon", "WEST": "Europe/Lisbon",
    "MSK": "Europe/Moscow", "IST": "Asia/Kolkata",
    "JST": "Asia/Tokyo", "KST": "Asia/Seoul",
    "CST_CHINA": "Asia/Shanghai", "HKT": "Asia/Hong_Kong",
    "SGT": "Asia/Singapore", "PHT": "Asia/Manila",
    "ICT": "Asia/Bangkok", "WIB": "Asia/Jakarta",
    "WITA": "Asia/Makassar", "WIT": "Asia/Jayapura",
    "NPT": "Asia/Kathmandu",
    "IST_INDIA": "Asia/Kolkata", "IST_IRELAND": "Europe/Dublin", "IST_ISRAEL": "Asia/Jerusalem",
    "PKT": "Asia/Karachi", "BDT": "Asia/Dhaka", "MMT": "Asia/Yangon",
    "AEST": "Australia/Sydney", "AEDT": "Australia/Sydney",
    "ACST": "Australia/Adelaide", "ACDT": "Australia/Adelaide",
    "AWST": "Australia/Perth",
    "NZST": "Pacific/Auckland", "NZDT": "Pacific/Auckland",
    "FJT": "Pacific/Fiji",
    "BRT": "America/Sao_Paulo", "BRST": "America/Sao_Paulo",
    "ART": "America/Argentina/Buenos_Aires",
    "CLT": "America/Santiago", "CLST": "America/Santiago",
    "COT": "America/Bogota", "PET": "America/Lima", "VET": "America/Caracas",
    "CAT": "Africa/Harare", "EAT": "Africa/Nairobi",
    "WAT": "Africa/Lagos", "SAST": "Africa/Johannesburg",
    "UTC": "UTC", "Z": "UTC",
}

AMBIGUOUS_ABBREVIATIONS: dict[str, dict[str, str]] = {
    "CST": {"US Central": "America/Chicago", "China": "Asia/Shanghai", "Cuba": "America/Havana"},
    "IST": {"India": "Asia/Kolkata", "Ireland": "Europe/Dublin", "Israel": "Asia/Jerusalem"},
    "BST": {"British Summer": "Europe/London", "Bangladesh": "Asia/Dhaka"},
    "AST": {"Atlantic": "America/Halifax", "Arabia": "Asia/Riyadh"},
    "GST": {"Gulf": "Asia/Dubai", "South Georgia": "Atlantic/South_Georgia"},
    "CDT": {"US Central Daylight": "America/Chicago", "Cuba Daylight": "America/Havana"},
    "EST": {"US Eastern": "America/New_York", "Australia Eastern": "Australia/Brisbane"},
}


def is_ambiguous(abbreviation: str) -> bool:
    return abbreviation.upper() in AMBIGUOUS_ABBREVIATIONS


def get_alternatives(abbreviation: str) -> dict[str, str] | None:
    return AMBIGUOUS_ABBREVIATIONS.get(abbreviation.upper())


def resolve_abbreviation(abbreviation: str) -> str | None:
    return ABBREVIATION_MAP.get(abbreviation.upper())


def parse_utc_offset(offset_str: str) -> timezone | None:
    s = offset_str.strip()
    if not s:
        return None
    if s.upper().startswith("UTC"):
        s = s[3:]
    if not s:
        return timezone.utc
    if s[0] not in ("+", "-"):
        return None
    sign = 1 if s[0] == "+" else -1
    s = s[1:]
    hours = minutes = 0
    if ":" in s:
        parts = s.split(":")
        if len(parts) != 2:
            return None
        try:
            hours, minutes = int(parts[0]), int(parts[1])
        except ValueError:
            return None
    elif len(s) == 4 and s.isdigit():
        hours, minutes = int(s[:2]), int(s[2:])
    elif len(s) == 3 and s.isdigit():
        hours, minutes = int(s[0]), int(s[1:])
    elif s.isdigit():
        hours = int(s)
    else:
        return None
    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        return None
    total_minutes = sign * (hours * 60 + minutes)
    if abs(total_minutes) > 24 * 60:
        return None
    return timezone(timedelta(minutes=total_minutes))


def resolve_timezone(zone_str: str) -> ZoneInfo | timezone:
    zone_str = zone_str.strip()
    if not zone_str:
        raise ValueError("Empty timezone string")
    iana_name = resolve_abbreviation(zone_str)
    if iana_name is not None:
        try:
            return ZoneInfo(iana_name)
        except (KeyError, Exception):
            pass
    if zone_str[0] in ("+", "-") or zone_str.upper().startswith("UTC"):
        tz = parse_utc_offset(zone_str)
        if tz is not None:
            return tz
    try:
        return ZoneInfo(zone_str)
    except (KeyError, Exception):
        pass
    raise ValueError(
        f"Unknown timezone: '{zone_str}'. "
        f"Use IANA names (e.g., 'America/New_York'), "
        f"UTC offsets (e.g., '+05:30'), "
        f"or common abbreviations (e.g., 'EST')."
    )


def list_abbreviations() -> dict[str, str]:
    return dict(ABBREVIATION_MAP)


def list_available_zones(filter_str: str | None = None) -> list[str]:
    zones = sorted(available_timezones())
    if filter_str:
        fl = filter_str.lower()
        zones = [z for z in zones if fl in z.lower()]
    return zones


# ═══════════════════════════════════════════════════════════════════
# Time conversion
# ═══════════════════════════════════════════════════════════════════

def convert_time(
    dt: datetime,
    from_zone: ZoneInfo | timezone,
    to_zone: ZoneInfo | timezone,
) -> datetime:
    """Convert a datetime from one timezone to another."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=from_zone)
    else:
        dt = dt.astimezone(from_zone)
    return dt.astimezone(to_zone)


def convert_time_str(
    time_str: str,
    from_zone_str: str,
    to_zone_str: str,
    fmt: str = "%Y-%m-%d %H:%M",
) -> datetime:
    """Convert a time string from one timezone to another."""
    from_zone = resolve_timezone(from_zone_str)
    to_zone = resolve_timezone(to_zone_str)
    try:
        dt = datetime.strptime(time_str, fmt)
    except ValueError as e:
        raise ValueError(f"Cannot parse '{time_str}' with format '{fmt}': {e}")
    return convert_time(dt, from_zone, to_zone)


def now_in_zones(zone_strs: list[str]) -> list[tuple[str, datetime]]:
    """Get the current time in multiple timezones."""
    now_utc = datetime.now(timezone.utc)
    results = []
    for zone_str in zone_strs:
        tz = resolve_timezone(zone_str)
        results.append((zone_str, now_utc.astimezone(tz)))
    return results


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S %Z (UTC%z)") -> str:
    return dt.strftime(fmt)


def get_utc_offset(dt: datetime) -> timedelta:
    if dt.tzinfo is None:
        raise ValueError("Cannot get UTC offset of naive datetime")
    offset = dt.utcoffset()
    if offset is None:
        raise ValueError("Timezone returned None for utcoffset()")
    return offset


def format_offset(offset: timedelta) -> str:
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def parse_datetime(time_str: str, formats: list[str] | None = None) -> datetime:
    """Try to parse a datetime string using multiple formats."""
    if formats is None:
        formats = [
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
            "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M",
            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
            "%H:%M:%S", "%H:%M",
        ]
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse '{time_str}'. Supported formats: " + ", ".join(formats))


# ═══════════════════════════════════════════════════════════════════
# DST transitions
# ═══════════════════════════════════════════════════════════════════

def is_dst(zone_str: str, dt: datetime | None = None) -> bool:
    """Check if DST is currently active in a timezone."""
    tz = resolve_timezone(zone_str)
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(tz)
    dst_offset = local_dt.dst()
    if dst_offset is None:
        return False
    return dst_offset != timedelta(0)


def get_dst_info(zone_str: str, dt: datetime | None = None) -> dict:
    """Get comprehensive DST information for a timezone."""
    tz = resolve_timezone(zone_str)
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone(tz)
    utc_offset = local_dt.utcoffset() or timedelta(0)
    dst_offset = local_dt.dst() or timedelta(0)
    abbreviation = local_dt.tzname() or ""
    iana_name = str(tz) if isinstance(tz, ZoneInfo) else ""
    observes_dst = _zone_observes_dst(tz, dt)
    total_seconds = int(utc_offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    abs_seconds = abs(total_seconds)
    hours = abs_seconds // 3600
    minutes = (abs_seconds % 3600) // 60
    offset_str = f"UTC{sign}{hours:02d}:{minutes:02d}"
    return {
        "zone": zone_str, "iana_name": iana_name,
        "is_dst": dst_offset != timedelta(0),
        "utc_offset": offset_str, "utc_offset_td": utc_offset,
        "dst_offset": dst_offset, "abbreviation": abbreviation,
        "observes_dst": observes_dst,
    }


def _zone_observes_dst(tz: ZoneInfo | timezone, reference_dt: datetime) -> bool:
    if not isinstance(tz, ZoneInfo):
        return False
    ref_year = reference_dt.year if hasattr(reference_dt, "year") else datetime.now().year
    offsets = set()
    for month in range(1, 13):
        try:
            sample = datetime(ref_year, month, 15, 12, 0, 0, tzinfo=tz)
            offset = sample.utcoffset()
            if offset is not None:
                offsets.add(offset)
        except Exception:
            continue
    return len(offsets) > 1


def find_next_transition(zone_str: str, after: datetime | None = None,
                         search_days: int = 400) -> dict | None:
    """Find the next DST transition for a timezone."""
    tz = resolve_timezone(zone_str)
    if not isinstance(tz, ZoneInfo):
        return None
    if after is None:
        after = datetime.now(timezone.utc)
    if after.tzinfo is None:
        after = after.replace(tzinfo=timezone.utc)
    current_local = after.astimezone(tz)
    current_offset = current_local.utcoffset()
    transition_start = transition_end = None
    check_time = after
    for _ in range(search_days):
        check_time += timedelta(days=1)
        local = check_time.astimezone(tz)
        new_offset = local.utcoffset()
        if new_offset != current_offset:
            transition_start = check_time - timedelta(days=1)
            transition_end = check_time
            break
        current_offset = new_offset
    if transition_start is None:
        return None
    low, high = transition_start, transition_end
    before_offset = low.astimezone(tz).utcoffset()
    while (high - low) > timedelta(minutes=1):
        mid = low + (high - low) / 2
        if mid.astimezone(tz).utcoffset() == before_offset:
            low = mid
        else:
            high = mid
    transition_utc = high
    before_local = (transition_utc - timedelta(minutes=1)).astimezone(tz)
    after_local = (transition_utc + timedelta(minutes=1)).astimezone(tz)
    offset_before = before_local.utcoffset() or timedelta(0)
    offset_after = after_local.utcoffset() or timedelta(0)
    diff_minutes = int((offset_after - offset_before).total_seconds() / 60)
    direction = "spring-forward" if diff_minutes > 0 else "fall-back"
    return {
        "transition_time_utc": transition_utc,
        "transition_time_local_before": before_local,
        "transition_time_local_after": after_local,
        "offset_before": offset_before, "offset_after": offset_after,
        "direction": direction, "gap_or_overlap_minutes": abs(diff_minutes),
    }


def find_transitions_in_year(zone_str: str, year: int | None = None) -> list[dict]:
    """Find all DST transitions in a given year."""
    if year is None:
        year = datetime.now().year
    transitions = []
    search_start = datetime(year, 1, 1, tzinfo=timezone.utc)
    search_end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    current = search_start
    while current < search_end:
        transition = find_next_transition(zone_str, after=current, search_days=366)
        if transition is None:
            break
        t_utc = transition["transition_time_utc"]
        if t_utc >= search_end:
            break
        transitions.append(transition)
        current = t_utc + timedelta(days=1)
    return transitions


def format_transition(transition: dict | None) -> str:
    if transition is None:
        return "This timezone does not observe DST."
    direction = transition["direction"]
    t_utc = transition["transition_time_utc"]
    before = transition["transition_time_local_before"]
    after = transition["transition_time_local_after"]
    offset_before = transition["offset_before"]
    offset_after = transition["offset_after"]
    gap = transition["gap_or_overlap_minutes"]

    def fmt_offset(td):
        total = int(td.total_seconds())
        s = "+" if total >= 0 else "-"
        total = abs(total)
        return f"UTC{s}{total // 3600:02d}:{(total % 3600) // 60:02d}"

    return "\n".join([
        f"Next transition: {direction}",
        f"  UTC: {t_utc.strftime('%Y-%m-%d %H:%M')}",
        f"  Before: {before.strftime('%Y-%m-%d %H:%M')} ({fmt_offset(offset_before)})",
        f"  After:  {after.strftime('%Y-%m-%d %H:%M')} ({fmt_offset(offset_after)})",
        f"  Clocks {'advance' if direction == 'spring-forward' else 'go back'} {gap} minutes",
    ])


def format_dst_info(info: dict) -> str:
    lines = [f"Timezone: {info['zone']}"]
    if info["iana_name"]:
        lines.append(f"  IANA name: {info['iana_name']}")
    lines.extend([
        f"  UTC offset: {info['utc_offset']}",
        f"  Abbreviation: {info['abbreviation']}",
        f"  DST active: {'Yes' if info['is_dst'] else 'No'}",
        f"  Observes DST: {'Yes' if info['observes_dst'] else 'No'}",
    ])
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Overlap windows
# ═══════════════════════════════════════════════════════════════════

def find_overlap(
    zone_strs: list[str],
    start_hour: int = 9,
    end_hour: int = 17,
    reference_date: date | None = None,
) -> list[dict]:
    """Find overlapping work hours across multiple timezones."""
    if not zone_strs:
        raise ValueError("At least one timezone is required")
    if start_hour < 0 or start_hour > 23:
        raise ValueError(f"start_hour must be 0-23, got {start_hour}")
    if end_hour < 0 or end_hour > 24:
        raise ValueError(f"end_hour must be 0-24, got {end_hour}")
    if start_hour >= end_hour:
        raise ValueError(f"start_hour ({start_hour}) must be less than end_hour ({end_hour})")
    if reference_date is None:
        reference_date = date.today()
    zones = [(zs, resolve_timezone(zs)) for zs in zone_strs]
    utc_windows = []
    for zone_str, tz in zones:
        local_start = datetime.combine(reference_date, time(start_hour, 0), tzinfo=tz)
        local_end = datetime.combine(reference_date, time(end_hour, 0), tzinfo=tz)
        utc_windows.append((zone_str, local_start.astimezone(timezone.utc),
                            local_end.astimezone(timezone.utc)))
    overlap_start = max(w[1] for w in utc_windows)
    overlap_end = min(w[2] for w in utc_windows)
    if overlap_start >= overlap_end:
        return []
    duration = (overlap_end - overlap_start).total_seconds() / 3600
    local_times = {}
    for zone_str, tz in zones:
        local_times[zone_str] = (overlap_start.astimezone(tz), overlap_end.astimezone(tz))
    return [{"utc_start": overlap_start, "utc_end": overlap_end,
             "duration_hours": duration, "local_times": local_times}]


def format_overlap(overlap_results: list[dict]) -> str:
    if not overlap_results:
        return "No overlapping work hours found."
    lines = []
    for result in overlap_results:
        hours = result["duration_hours"]
        lines.append(f"Overlap window: {hours:.1f} hours")
        lines.append(f"  UTC: {result['utc_start'].strftime('%H:%M')} - {result['utc_end'].strftime('%H:%M')}")
        lines.append("")
        for zone_str, (ls, le) in result["local_times"].items():
            offset = ls.strftime("%z")
            lines.append(f"  {zone_str}: {ls.strftime('%H:%M')} - {le.strftime('%H:%M')} (UTC{offset[:3]}:{offset[3:]})")
    return "\n".join(lines)


def get_zone_work_hours(zone_str: str, start_hour: int = 9, end_hour: int = 17,
                        reference_date: date | None = None) -> dict:
    if reference_date is None:
        reference_date = date.today()
    tz = resolve_timezone(zone_str)
    local_start = datetime.combine(reference_date, time(start_hour, 0), tzinfo=tz)
    local_end = datetime.combine(reference_date, time(end_hour, 0), tzinfo=tz)
    return {
        "zone": zone_str,
        "local_start": local_start, "local_end": local_end,
        "utc_start": local_start.astimezone(timezone.utc),
        "utc_end": local_end.astimezone(timezone.utc),
        "offset": local_start.strftime("%z"),
    }
