"""
Tests for Cron Expression Parser.

These tests ARE the spec — if an LLM regenerates the parser in any
language, these cases define correctness.
"""

import pytest
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from parser import (
    parse, describe, next_runs, validate, CronError,
    _parse_field, FIELD_RANGES,
)


# --- Helpers ---

def ref_time(year=2026, month=3, day=15, hour=13, minute=45):
    """Fixed reference time to make tests deterministic."""
    return datetime(year, month, day, hour, minute, 0)


# ============================================================
# 1. Parsing each field type
# ============================================================

class TestParseNumbers:
    def test_single_number(self):
        assert _parse_field("5", "minute") == [5]

    def test_single_zero(self):
        assert _parse_field("0", "minute") == [0]

    def test_max_minute(self):
        assert _parse_field("59", "minute") == [59]

    def test_max_hour(self):
        assert _parse_field("23", "hour") == [23]

    def test_day_of_month_1(self):
        assert _parse_field("1", "day-of-month") == [1]

    def test_day_of_month_31(self):
        assert _parse_field("31", "day-of-month") == [31]


class TestParseWildcards:
    def test_minute_star(self):
        result = _parse_field("*", "minute")
        assert result == list(range(0, 60))

    def test_hour_star(self):
        result = _parse_field("*", "hour")
        assert result == list(range(0, 24))

    def test_dom_star(self):
        result = _parse_field("*", "day-of-month")
        assert result == list(range(1, 32))

    def test_month_star(self):
        result = _parse_field("*", "month")
        assert result == list(range(1, 13))

    def test_dow_star(self):
        result = _parse_field("*", "day-of-week")
        assert result == list(range(0, 7))


class TestParseRanges:
    def test_minute_range(self):
        assert _parse_field("1-5", "minute") == [1, 2, 3, 4, 5]

    def test_hour_range(self):
        assert _parse_field("9-17", "hour") == list(range(9, 18))

    def test_single_value_range(self):
        assert _parse_field("5-5", "minute") == [5]

    def test_dow_range(self):
        assert _parse_field("1-5", "day-of-week") == [1, 2, 3, 4, 5]


class TestParseSteps:
    def test_star_step(self):
        assert _parse_field("*/5", "minute") == [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]

    def test_star_step_15(self):
        assert _parse_field("*/15", "minute") == [0, 15, 30, 45]

    def test_range_step(self):
        assert _parse_field("1-30/2", "minute") == [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29]

    def test_star_step_hours(self):
        assert _parse_field("*/2", "hour") == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]

    def test_range_step_hours(self):
        assert _parse_field("9-17/2", "hour") == [9, 11, 13, 15, 17]


class TestParseLists:
    def test_minute_list(self):
        assert _parse_field("1,3,5", "minute") == [1, 3, 5]

    def test_hour_list(self):
        assert _parse_field("0,12", "hour") == [0, 12]

    def test_dom_list(self):
        assert _parse_field("1,15", "day-of-month") == [1, 15]

    def test_mixed_list_and_range(self):
        assert _parse_field("1,3-5,10", "minute") == [1, 3, 4, 5, 10]

    def test_list_with_step(self):
        assert _parse_field("0,30,*/20", "minute") == [0, 20, 30, 40]


class TestParseNames:
    def test_dow_names_full_range(self):
        assert _parse_field("MON-FRI", "day-of-week") == [1, 2, 3, 4, 5]

    def test_dow_single_name(self):
        assert _parse_field("SUN", "day-of-week") == [0]

    def test_dow_name_list(self):
        assert _parse_field("MON,WED,FRI", "day-of-week") == [1, 3, 5]

    def test_dow_sat(self):
        assert _parse_field("SAT", "day-of-week") == [6]

    def test_month_names(self):
        assert _parse_field("JAN", "month") == [1]

    def test_month_name_range(self):
        assert _parse_field("JAN-MAR", "month") == [1, 2, 3]

    def test_month_name_list(self):
        assert _parse_field("JAN,APR,JUL,OCT", "month") == [1, 4, 7, 10]

    def test_dow_7_is_sunday(self):
        assert _parse_field("7", "day-of-week") == [0]

    def test_dow_0_is_sunday(self):
        assert _parse_field("0", "day-of-week") == [0]


class TestParseFullExpression:
    def test_every_minute(self):
        result = parse("* * * * *")
        assert result["minute"] == list(range(0, 60))
        assert result["hour"] == list(range(0, 24))

    def test_every_15_minutes(self):
        result = parse("*/15 * * * *")
        assert result["minute"] == [0, 15, 30, 45]

    def test_weekday_morning(self):
        result = parse("0 9 * * MON-FRI")
        assert result["minute"] == [0]
        assert result["hour"] == [9]
        assert result["day_of_week"] == [1, 2, 3, 4, 5]

    def test_first_of_month(self):
        result = parse("0 0 1 * *")
        assert result["minute"] == [0]
        assert result["hour"] == [0]
        assert result["day_of_month"] == [1]


# ============================================================
# 2. Plain English description accuracy
# ============================================================

class TestDescriptions:
    def test_every_minute(self):
        assert describe("* * * * *") == "Every minute"

    def test_every_hour(self):
        assert describe("0 * * * *") == "Every hour, at minute 0"

    def test_every_day_at_nine(self):
        assert describe("0 9 * * *") == "Every day at 09:00"

    def test_weekday_at_nine(self):
        assert describe("0 9 * * MON-FRI") == "Every weekday at 09:00"

    def test_midnight_first_of_month(self):
        assert describe("0 0 1 * *") == "At midnight on the 1st of every month"

    def test_early_morning_two_days(self):
        assert describe("30 4 1,15 * *") == "At 04:30 on the 1st and 15th of every month"

    def test_weekday_evening(self):
        assert describe("0 22 * * 1-5") == "Every weekday at 22:00"

    def test_every_10_min_business_hours_weekdays(self):
        assert describe("*/10 9-17 * * MON-FRI") == (
            "Every 10 minutes, 09:00\u201317:59, Monday through Friday"
        )

    def test_every_5_minutes(self):
        assert describe("*/5 * * * *") == "Every 5 minutes"

    def test_twice_daily(self):
        desc = describe("0 6,18 * * *")
        assert "06:00" in desc
        assert "18:00" in desc

    def test_every_2_hours(self):
        desc = describe("0 */2 * * *")
        assert "2 hours" in desc

    def test_sunday_midnight(self):
        desc = describe("0 0 * * 0")
        assert "Sunday" in desc

    def test_jan_first_midnight(self):
        desc = describe("0 0 1 1 *")
        assert "January" in desc

    def test_every_30_minutes(self):
        assert describe("*/30 * * * *") == "Every 30 minutes"

    def test_quarter_hourly(self):
        desc = describe("0,15,30,45 * * * *")
        # Should recognize the pattern or list the minutes
        assert "minute" in desc.lower() or "15" in desc


# ============================================================
# 3. Next-run calculation correctness
# ============================================================

class TestNextRuns:
    def test_every_minute(self):
        ref = ref_time(2026, 3, 15, 13, 45)
        runs = next_runs("* * * * *", n=3, after=ref)
        assert len(runs) == 3
        assert runs[0] == datetime(2026, 3, 15, 13, 46)
        assert runs[1] == datetime(2026, 3, 15, 13, 47)
        assert runs[2] == datetime(2026, 3, 15, 13, 48)

    def test_every_15_minutes(self):
        ref = ref_time(2026, 3, 15, 13, 50)
        runs = next_runs("*/15 * * * *", n=5, after=ref)
        assert runs[0] == datetime(2026, 3, 15, 14, 0)
        assert runs[1] == datetime(2026, 3, 15, 14, 15)
        assert runs[2] == datetime(2026, 3, 15, 14, 30)
        assert runs[3] == datetime(2026, 3, 15, 14, 45)
        assert runs[4] == datetime(2026, 3, 15, 15, 0)

    def test_daily_at_nine(self):
        ref = ref_time(2026, 3, 15, 10, 0)
        runs = next_runs("0 9 * * *", n=3, after=ref)
        # Already past 9:00 on Mar 15, so next is Mar 16
        assert runs[0] == datetime(2026, 3, 16, 9, 0)
        assert runs[1] == datetime(2026, 3, 17, 9, 0)
        assert runs[2] == datetime(2026, 3, 18, 9, 0)

    def test_daily_at_nine_before(self):
        ref = ref_time(2026, 3, 15, 8, 0)
        runs = next_runs("0 9 * * *", n=2, after=ref)
        # Before 9:00 on Mar 15, so next is today
        assert runs[0] == datetime(2026, 3, 15, 9, 0)
        assert runs[1] == datetime(2026, 3, 16, 9, 0)

    def test_weekday_only(self):
        # Mar 15, 2026 is a Sunday
        ref = ref_time(2026, 3, 15, 0, 0)
        runs = next_runs("0 9 * * MON-FRI", n=5, after=ref)
        # Next weekday is Mon Mar 16
        assert runs[0] == datetime(2026, 3, 16, 9, 0)
        assert runs[4] == datetime(2026, 3, 20, 9, 0)
        # All results should be weekdays (Mon-Fri)
        for r in runs:
            assert r.weekday() in range(0, 5)  # Mon=0..Fri=4

    def test_first_of_month(self):
        ref = ref_time(2026, 3, 15, 0, 0)
        runs = next_runs("0 0 1 * *", n=3, after=ref)
        assert runs[0] == datetime(2026, 4, 1, 0, 0)
        assert runs[1] == datetime(2026, 5, 1, 0, 0)
        assert runs[2] == datetime(2026, 6, 1, 0, 0)

    def test_specific_after_date(self):
        after = datetime(2026, 6, 1, 0, 0)
        runs = next_runs("0 0 1 * *", n=3, after=after)
        assert runs[0] == datetime(2026, 7, 1, 0, 0)
        assert runs[1] == datetime(2026, 8, 1, 0, 0)
        assert runs[2] == datetime(2026, 9, 1, 0, 0)

    def test_end_of_day_rollover(self):
        ref = datetime(2026, 3, 15, 23, 55)
        runs = next_runs("0 0 * * *", n=2, after=ref)
        assert runs[0] == datetime(2026, 3, 16, 0, 0)
        assert runs[1] == datetime(2026, 3, 17, 0, 0)

    def test_returns_correct_count(self):
        ref = ref_time()
        runs = next_runs("* * * * *", n=10, after=ref)
        assert len(runs) == 10

    def test_runs_are_ascending(self):
        ref = ref_time()
        runs = next_runs("*/5 * * * *", n=20, after=ref)
        for i in range(len(runs) - 1):
            assert runs[i] < runs[i + 1]


# ============================================================
# 4. Month boundary edge cases
# ============================================================

class TestMonthBoundaries:
    def test_feb_28_non_leap(self):
        # 2027 is not a leap year
        ref = datetime(2027, 2, 27, 0, 0)
        runs = next_runs("0 0 28 * *", n=1, after=ref)
        assert runs[0] == datetime(2027, 2, 28, 0, 0)

    def test_feb_29_leap_year(self):
        # 2028 is a leap year
        ref = datetime(2028, 2, 28, 0, 0)
        runs = next_runs("0 0 29 * *", n=1, after=ref)
        assert runs[0] == datetime(2028, 2, 29, 0, 0)

    def test_feb_30_never_fires_in_feb(self):
        # Feb never has 30 days — should skip to next month with 30 days
        ref = datetime(2026, 2, 1, 0, 0)
        runs = next_runs("0 0 30 * *", n=1, after=ref)
        # March has 30 days
        assert runs[0].month >= 3
        assert runs[0].day == 30

    def test_feb_31_skips_to_march(self):
        ref = datetime(2026, 2, 1, 0, 0)
        runs = next_runs("0 0 31 * *", n=3, after=ref)
        # Only months with 31 days
        for r in runs:
            assert r.day == 31
            assert r.month in (1, 3, 5, 7, 8, 10, 12)

    def test_month_with_30_days(self):
        # April has 30 days
        ref = datetime(2026, 4, 29, 0, 0)
        runs = next_runs("0 0 30 * *", n=1, after=ref)
        assert runs[0] == datetime(2026, 4, 30, 0, 0)

    def test_year_boundary(self):
        ref = datetime(2026, 12, 31, 23, 0)
        runs = next_runs("0 0 * * *", n=2, after=ref)
        assert runs[0] == datetime(2027, 1, 1, 0, 0)


# ============================================================
# 5. Day-of-week edge cases
# ============================================================

class TestDayOfWeek:
    def test_sunday_is_0(self):
        parsed = parse("0 0 * * 0")
        assert 0 in parsed["day_of_week"]

    def test_sunday_is_7(self):
        parsed = parse("0 0 * * 7")
        assert 0 in parsed["day_of_week"]

    def test_sunday_0_and_7_equivalent(self):
        runs_0 = next_runs("0 9 * * 0", n=3, after=ref_time())
        runs_7 = next_runs("0 9 * * 7", n=3, after=ref_time())
        assert runs_0 == runs_7

    def test_saturday_is_6(self):
        parsed = parse("0 0 * * 6")
        assert parsed["day_of_week"] == [6]

    def test_weekday_runs_are_weekdays(self):
        ref = ref_time(2026, 3, 15, 0, 0)
        runs = next_runs("0 12 * * 1-5", n=10, after=ref)
        for r in runs:
            assert r.weekday() in range(0, 5)

    def test_weekend_runs_are_weekends(self):
        ref = ref_time(2026, 3, 15, 0, 0)
        runs = next_runs("0 12 * * 0,6", n=10, after=ref)
        for r in runs:
            # Python: Mon=0..Sun=6. Sat=5, Sun=6
            assert r.weekday() in (5, 6)


# ============================================================
# 6. Invalid expressions
# ============================================================

class TestValidation:
    def test_too_few_fields(self):
        ok, err = validate("* * *")
        assert ok is False
        assert "3" in err  # mentions the field count

    def test_too_many_fields(self):
        ok, err = validate("* * * * * *")
        assert ok is False
        assert "6" in err

    def test_out_of_range_minute(self):
        ok, err = validate("60 * * * *")
        assert ok is False
        assert "minute" in err.lower()

    def test_out_of_range_hour(self):
        ok, err = validate("0 24 * * *")
        assert ok is False
        assert "hour" in err.lower()

    def test_out_of_range_dom(self):
        ok, err = validate("0 0 32 * *")
        assert ok is False
        assert "day" in err.lower()

    def test_out_of_range_month(self):
        ok, err = validate("0 0 * 13 *")
        assert ok is False
        assert "month" in err.lower()

    def test_out_of_range_dow(self):
        ok, err = validate("0 0 * * 8")
        assert ok is False
        assert "day-of-week" in err.lower()

    def test_dom_zero(self):
        ok, err = validate("0 0 0 * *")
        assert ok is False
        assert "day" in err.lower()

    def test_month_zero(self):
        ok, err = validate("0 0 * 0 *")
        assert ok is False
        assert "month" in err.lower()

    def test_malformed_range(self):
        ok, err = validate("5-2 * * * *")
        assert ok is False

    def test_malformed_step(self):
        ok, err = validate("*/abc * * * *")
        assert ok is False

    def test_negative_step(self):
        ok, err = validate("*/-1 * * * *")
        assert ok is False

    def test_zero_step(self):
        ok, err = validate("*/0 * * * *")
        assert ok is False

    def test_non_standard_L(self):
        ok, err = validate("0 0 L * *")
        assert ok is False
        assert "non-standard" in err.lower() or "L" in err

    def test_non_standard_W(self):
        ok, err = validate("0 0 15W * *")
        assert ok is False

    def test_non_standard_hash(self):
        ok, err = validate("0 0 * * 1#2")
        assert ok is False

    def test_empty_expression(self):
        ok, err = validate("")
        assert ok is False

    def test_valid_expression(self):
        ok, err = validate("*/15 * * * *")
        assert ok is True
        assert err == ""

    def test_valid_complex(self):
        ok, err = validate("0,30 9-17 1,15 JAN-JUN MON-FRI")
        assert ok is True

    def test_parse_raises_cron_error(self):
        with pytest.raises(CronError):
            parse("60 * * * *")

    def test_double_comma(self):
        ok, err = validate("1,,3 * * * *")
        assert ok is False


# ============================================================
# 7. CLI output format
# ============================================================

class TestCLI:
    def test_basic_output(self):
        result = subprocess.run(
            [sys.executable, "parser.py", "*/15 * * * *", "--next", "3",
             "--after", "2026-03-15 13:50"],
            capture_output=True, text=True,
            cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Expression: */15 * * * *" in result.stdout
        assert "Description:" in result.stdout
        assert "Next 3 runs:" in result.stdout
        assert "2026-03-15 14:00:00" in result.stdout

    def test_explain_only(self):
        result = subprocess.run(
            [sys.executable, "parser.py", "0 9 * * MON-FRI", "--explain"],
            capture_output=True, text=True,
            cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Description:" in result.stdout
        assert "Next" not in result.stdout

    def test_validate_valid(self):
        result = subprocess.run(
            [sys.executable, "parser.py", "*/15 * * * *", "--validate"],
            capture_output=True, text=True,
            cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Valid" in result.stdout

    def test_validate_invalid(self):
        result = subprocess.run(
            [sys.executable, "parser.py", "0 0 * * 8", "--validate"],
            capture_output=True, text=True,
            cwd=_TOOL_DIR,
        )
        assert result.returncode != 0

    def test_after_flag(self):
        result = subprocess.run(
            [sys.executable, "parser.py", "0 0 1 * *", "--next", "3",
             "--after", "2026-06-01"],
            capture_output=True, text=True,
            cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "2026-07-01 00:00:00" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
