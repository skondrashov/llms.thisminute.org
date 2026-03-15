"""
Cron Expression Parser — Schedule Verifier for Agents

Parses standard 5-field cron expressions (minute, hour, day-of-month, month,
day-of-week), explains them in plain English, and computes the next N
scheduled run times.  Agents constantly set up scheduled tasks and need to
verify cron expressions — LLMs frequently make mistakes with complex cron
syntax.

SUPPORTED SYNTAX
================
Each of the five fields accepts:
  - Numbers:          5, 30
  - Ranges:           1-5, 9-17
  - Steps:            */5, 1-30/2
  - Lists:            1,3,5  or  MON,WED,FRI
  - Wildcards:        *
  - Day-of-week names:  SUN(0)..SAT(6);  7 also accepted as Sunday
  - Month names:      JAN(1)..DEC(12)

Non-standard extensions (L, W, #) are NOT evaluated but are documented in
validation error messages so callers know why they were rejected.

DAY-OF-MONTH / DAY-OF-WEEK SEMANTICS
=====================================
When both day-of-month and day-of-week are restricted (not ``*``), this
parser uses **AND** semantics — the schedule fires only when *both*
conditions are met.  This matches systemd timer behavior.  POSIX (Vixie)
cron uses OR semantics instead.  Choose the right tool for your scheduler.

Pure Python, no external dependencies.
"""

import calendar
import sys
from datetime import datetime, timedelta


# --- Constants ---

FIELD_NAMES = ("minute", "hour", "day-of-month", "month", "day-of-week")

FIELD_RANGES = {
    "minute":       (0, 59),
    "hour":         (0, 23),
    "day-of-month": (1, 31),
    "month":        (1, 12),
    "day-of-week":  (0, 6),
}

MONTH_NAMES = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

DOW_NAMES = {
    "SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6,
}

MONTH_NAMES_LIST = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

DOW_NAMES_LIST = [
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday",
]

NON_STANDARD_CHARS = {"L", "W", "#"}


# --- Exceptions ---

class CronError(ValueError):
    """Raised when a cron expression is invalid."""
    pass


# --- Parsing ---

def _replace_names(token, name_map):
    """Replace name aliases (JAN, MON, etc.) with their numeric equivalents."""
    upper = token.upper()
    for name, val in name_map.items():
        upper = upper.replace(name, str(val))
    return upper


def _parse_field(raw, field_name):
    """
    Parse a single cron field into a sorted list of matching integer values.

    Raises CronError with a descriptive message on invalid input.
    """
    lo, hi = FIELD_RANGES[field_name]

    # Substitute month/day-of-week names BEFORE checking for non-standard
    # characters, since names like JUL contain 'L' and WED contains 'W'.
    if field_name == "month":
        raw = _replace_names(raw, MONTH_NAMES)
    elif field_name == "day-of-week":
        raw = _replace_names(raw, DOW_NAMES)

    # Check for non-standard characters (after name substitution)
    for ch in NON_STANDARD_CHARS:
        if ch in raw.upper():
            raise CronError(
                f"Field '{field_name}': '{raw}' uses non-standard character "
                f"'{ch}'. Only standard cron syntax is supported (L, W, # "
                f"are extensions found in Quartz/Spring but not POSIX cron)."
            )

    values = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            raise CronError(
                f"Field '{field_name}': empty element in list (double comma or trailing comma)."
            )

        # Handle step: base/step
        if "/" in part:
            pieces = part.split("/")
            if len(pieces) != 2:
                raise CronError(
                    f"Field '{field_name}': '{part}' has multiple '/' characters."
                )
            base_str, step_str = pieces

            try:
                step = int(step_str)
            except ValueError:
                raise CronError(
                    f"Field '{field_name}': step value '{step_str}' is not an integer."
                )
            if step <= 0:
                raise CronError(
                    f"Field '{field_name}': step value must be > 0, got {step}."
                )

            # Determine the range for the base
            if base_str == "*":
                start, end = lo, hi
            elif "-" in base_str:
                start, end = _parse_range_pair(base_str, field_name, lo, hi)
            else:
                try:
                    start = int(base_str)
                except ValueError:
                    raise CronError(
                        f"Field '{field_name}': '{base_str}' is not a valid number or range."
                    )
                end = hi

            _validate_value(start, field_name, lo, hi)
            _validate_value(end, field_name, lo, hi)

            for v in range(start, end + 1, step):
                values.add(v)

        elif "-" in part:
            start, end = _parse_range_pair(part, field_name, lo, hi)
            _validate_value(start, field_name, lo, hi)
            _validate_value(end, field_name, lo, hi)
            for v in range(start, end + 1):
                values.add(v)

        elif part == "*":
            for v in range(lo, hi + 1):
                values.add(v)

        else:
            try:
                val = int(part)
            except ValueError:
                raise CronError(
                    f"Field '{field_name}': '{part}' is not a valid value."
                )
            # Special case: day-of-week 7 is treated as Sunday (0)
            if field_name == "day-of-week" and val == 7:
                val = 0
            _validate_value(val, field_name, lo, hi)
            values.add(val)

    if not values:
        raise CronError(f"Field '{field_name}': produced no valid values.")

    return sorted(values)


def _parse_range_pair(s, field_name, lo, hi):
    """Parse 'start-end' into (start, end) integers."""
    parts = s.split("-")
    if len(parts) != 2:
        raise CronError(
            f"Field '{field_name}': '{s}' is not a valid range (expected start-end)."
        )
    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError:
        raise CronError(
            f"Field '{field_name}': range '{s}' contains non-integer values."
        )
    if start > end:
        raise CronError(
            f"Field '{field_name}': range start ({start}) is greater than end ({end})."
        )
    return start, end


def _validate_value(val, field_name, lo, hi):
    """Raise CronError if val is outside the allowed range for the field."""
    if val < lo or val > hi:
        raise CronError(
            f"Field '{field_name}': value {val} is out of range ({lo}-{hi})."
        )


def parse(expression):
    """
    Parse a 5-field cron expression.

    Returns a dict with keys: 'minute', 'hour', 'day_of_month', 'month',
    'day_of_week' — each a sorted list of valid integer values.

    Raises CronError on invalid input.
    """
    fields = expression.strip().split()
    if len(fields) != 5:
        raise CronError(
            f"Expected 5 fields (minute hour day-of-month month day-of-week), "
            f"got {len(fields)}: '{expression}'"
        )

    result = {}
    for raw, name in zip(fields, FIELD_NAMES):
        result[name.replace("-", "_")] = _parse_field(raw, name)

    return result


# --- Description ---

def _ordinal(n):
    """Return ordinal string for n: 1 -> '1st', 2 -> '2nd', etc."""
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _format_list(items, name_list=None):
    """Format a list of integers into a human-readable string."""
    if name_list:
        names = [name_list[i] for i in items]
    else:
        names = [str(i) for i in items]

    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def _is_full_range(values, lo, hi):
    """Check if values cover every integer in [lo, hi]."""
    return values == list(range(lo, hi + 1))


def _detect_step(values, lo, hi):
    """If values form a regular step pattern from lo, return the step size; else None."""
    if len(values) < 2:
        return None
    step = values[1] - values[0]
    if step <= 1:
        return None
    expected = list(range(values[0], hi + 1, step))
    if values == expected:
        if values[0] == lo:
            return step
    return None


def _is_contiguous(values):
    """Check if values form a contiguous range."""
    if len(values) < 2:
        return True
    return values[-1] - values[0] == len(values) - 1


def describe(expression):
    """
    Generate a plain English description of a cron expression.

    Returns a string like "Every 15 minutes" or "Every weekday at 09:00".
    """
    parsed = parse(expression)
    minutes = parsed["minute"]
    hours = parsed["hour"]
    dom = parsed["day_of_month"]
    months = parsed["month"]
    dow = parsed["day_of_week"]

    all_minutes = _is_full_range(minutes, 0, 59)
    all_hours = _is_full_range(hours, 0, 23)
    all_dom = _is_full_range(dom, 1, 31)
    all_months = _is_full_range(months, 1, 12)
    all_dow = _is_full_range(dow, 0, 6)

    parts = []

    # --- Frequency / time component ---

    if all_minutes and all_hours:
        parts.append("Every minute")
    elif all_minutes and not all_hours:
        # Every minute during certain hours
        parts.append("Every minute")
        parts.append(_describe_hours_range(hours))
    elif len(minutes) > 1:
        step = _detect_step(minutes, 0, 59)
        if step:
            parts.append(f"Every {step} minutes")
        else:
            parts.append(f"At minutes {_format_list(minutes)}")
        if not all_hours:
            parts.append(_describe_hours_range(hours))
    else:
        # Single minute
        minute_val = minutes[0]
        if all_hours:
            parts.append(f"Every hour, at minute {minute_val}")
        elif len(hours) == 1:
            parts.append(f"At {hours[0]:02d}:{minute_val:02d}")
        else:
            hour_step = _detect_step(hours, 0, 23)
            if hour_step:
                parts.append(f"At minute {minute_val} every {hour_step} hours")
            else:
                time_strs = [f"{h:02d}:{minute_val:02d}" for h in hours]
                parts.append(f"At {_format_list(time_strs)}")

    # --- Day component ---

    weekdays = list(range(1, 6))  # MON-FRI

    if not all_dom:
        dom_strs = [_ordinal(d) for d in dom]
        parts.append(f"on the {_format_list(dom_strs)}")

    if not all_dow:
        if dow == weekdays:
            # Check if time part already says "Every ..." — we prefix with "Every weekday"
            # Rebuild: replace leading "At HH:MM" with "Every weekday at HH:MM"
            pass  # handled below
        elif len(dow) == 1:
            parts.append(f"on {DOW_NAMES_LIST[dow[0]]}")
        elif _is_contiguous(dow):
            parts.append(f"{DOW_NAMES_LIST[dow[0]]} through {DOW_NAMES_LIST[dow[-1]]}")
        else:
            parts.append(f"on {_format_list(dow, DOW_NAMES_LIST)}")

    # --- Month component ---

    if not all_months:
        if len(months) == 1:
            parts.append(f"in {MONTH_NAMES_LIST[months[0]]}")
        else:
            parts.append(f"in {_format_list(months, MONTH_NAMES_LIST)}")

    # --- Combine and refine ---

    desc = ", ".join(parts)

    # Special-case rewrites for common patterns
    # "Every weekday at HH:MM"
    if dow == weekdays and all_dom and all_months:
        if len(minutes) == 1 and len(hours) == 1:
            return f"Every weekday at {hours[0]:02d}:{minutes[0]:02d}"
        if len(minutes) > 1:
            step = _detect_step(minutes, 0, 59)
            if step and not all_hours:
                hr_range = _describe_hours_range(hours)
                return f"Every {step} minutes, {hr_range}, Monday through Friday"
            elif step:
                return f"Every {step} minutes, Monday through Friday"

    # "At midnight on the Nth of every month"
    if (len(minutes) == 1 and minutes[0] == 0 and
            len(hours) == 1 and hours[0] == 0 and
            not all_dom and all_months and all_dow):
        dom_strs = [_ordinal(d) for d in dom]
        return f"At midnight on the {_format_list(dom_strs)} of every month"

    # "Every day at HH:MM"
    if (len(minutes) == 1 and len(hours) == 1 and
            all_dom and all_months and all_dow):
        return f"Every day at {hours[0]:02d}:{minutes[0]:02d}"

    # "At HH:MM on the Nth ... of every month"
    if (len(minutes) == 1 and len(hours) == 1 and
            not all_dom and all_months and all_dow):
        dom_strs = [_ordinal(d) for d in dom]
        return f"At {hours[0]:02d}:{minutes[0]:02d} on the {_format_list(dom_strs)} of every month"

    return desc


def _describe_hours_range(hours):
    """Describe a set of hours as a range string like '09:00-17:59'."""
    if _is_contiguous(hours):
        return f"{hours[0]:02d}:00\u2013{hours[-1]:02d}:59"
    step = _detect_step(hours, 0, 23)
    if step:
        return f"every {step} hours"
    return f"during hours {_format_list(hours)}"


# --- Next-run calculation ---

def next_runs(expression, n=5, after=None):
    """
    Compute the next N scheduled run times for a cron expression.

    Parameters
    ----------
    expression : str
        A 5-field cron expression.
    n : int
        Number of future runs to compute.
    after : datetime or None
        Start searching from this time. Defaults to now.

    Returns
    -------
    list[datetime]
        The next N run times as datetime objects.
    """
    parsed = parse(expression)
    minutes = set(parsed["minute"])
    hours = set(parsed["hour"])
    dom_set = set(parsed["day_of_month"])
    months = set(parsed["month"])
    dow_set = set(parsed["day_of_week"])

    if after is None:
        after = datetime.now().replace(second=0, microsecond=0)

    # Start one minute after `after` to avoid returning `after` itself
    # unless after is exactly on a boundary (which we skip)
    current = after.replace(second=0, microsecond=0) + timedelta(minutes=1)

    results = []
    # Safety limit to avoid infinite loops on impossible expressions
    # (e.g., Feb 31 — valid parse but never fires)
    max_iterations = 366 * 24 * 60  # one full year of minutes

    iterations = 0
    while len(results) < n and iterations < max_iterations:
        iterations += 1

        # Fast-forward month if not in set
        if current.month not in months:
            # Jump to next valid month
            current = _advance_to_next_month(current, months)
            continue

        # Check day-of-month validity (e.g., skip Feb 30)
        days_in_month = calendar.monthrange(current.year, current.month)[1]

        # Check day-of-week (Python weekday: Mon=0..Sun=6; cron: Sun=0..Sat=6)
        cron_dow = (current.weekday() + 1) % 7  # convert to cron convention

        if current.day not in dom_set or current.day > days_in_month:
            current = _advance_day(current)
            continue

        if cron_dow not in dow_set:
            current = _advance_day(current)
            continue

        if current.hour not in hours:
            current = _advance_hour(current)
            continue

        if current.minute not in minutes:
            current += timedelta(minutes=1)
            continue

        results.append(current)
        current += timedelta(minutes=1)

    return results


def _advance_to_next_month(dt, valid_months):
    """Advance dt to the first day of the next valid month."""
    year = dt.year
    month = dt.month

    while True:
        month += 1
        if month > 12:
            month = 1
            year += 1
        if month in valid_months:
            return datetime(year, month, 1, 0, 0)
        # Safety: don't loop more than 12 times
        if year > dt.year + 5:
            return datetime(year, month, 1, 0, 0)


def _advance_day(dt):
    """Advance to the start of the next day."""
    return (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _advance_hour(dt):
    """Advance to the start of the next hour."""
    return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)


# --- Validation ---

def validate(expression):
    """
    Validate a cron expression.

    Returns (True, "") on success.
    Returns (False, error_message) on failure.
    """
    try:
        parse(expression)
        return True, ""
    except CronError as e:
        return False, str(e)


# --- CLI ---

def main():
    """CLI entry point for cron expression parsing."""
    import argparse

    parser_cli = argparse.ArgumentParser(
        description="Parse and explain cron expressions.",
        usage="python parser.py EXPRESSION [options]",
    )
    parser_cli.add_argument(
        "expression",
        help='Cron expression in quotes, e.g. "*/15 * * * *"',
    )
    parser_cli.add_argument(
        "--next", type=int, default=5, dest="count",
        help="Number of next runs to show (default: 5)",
    )
    parser_cli.add_argument(
        "--after", type=str, default=None,
        help="Show runs after this datetime (YYYY-MM-DD or YYYY-MM-DD HH:MM)",
    )
    parser_cli.add_argument(
        "--explain", action="store_true",
        help="Show only the plain English description",
    )
    parser_cli.add_argument(
        "--validate", action="store_true", dest="validate_only",
        help="Validate the expression and exit (non-zero on error)",
    )

    args = parser_cli.parse_args()

    # Validate-only mode
    if args.validate_only:
        ok, err = validate(args.expression)
        if ok:
            print(f"Valid: {args.expression}")
            sys.exit(0)
        else:
            print(f"Invalid: {err}", file=sys.stderr)
            sys.exit(1)

    # Parse (will raise on invalid)
    try:
        desc = describe(args.expression)
    except CronError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Explain-only mode
    if args.explain:
        print(f"Expression: {args.expression}")
        print(f"Description: {desc}")
        return

    # Full output
    after = None
    if args.after:
        try:
            if " " in args.after:
                after = datetime.strptime(args.after, "%Y-%m-%d %H:%M")
            else:
                after = datetime.strptime(args.after, "%Y-%m-%d")
        except ValueError:
            print(
                f"Error: could not parse --after date '{args.after}'. "
                f"Use YYYY-MM-DD or 'YYYY-MM-DD HH:MM'.",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        runs = next_runs(args.expression, n=args.count, after=after)
    except CronError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Expression: {args.expression}")
    print(f"Description: {desc}")
    print(f"Next {len(runs)} runs:")
    for r in runs:
        print(f"  {r.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
