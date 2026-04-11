"""
Tests for Timezone Converter.

These tests ARE the spec — zone conversion, DST transitions, overlap
calculation, and abbreviation resolution.
"""

import pytest
from datetime import datetime, timezone, timedelta, date
from zoneinfo import ZoneInfo
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from converter import (
    convert_time, convert_time_str, now_in_zones,
    format_datetime, get_utc_offset, format_offset, parse_datetime,
    is_dst, get_dst_info, find_next_transition, find_transitions_in_year,
    format_transition, format_dst_info, _zone_observes_dst,
    find_overlap, format_overlap, get_zone_work_hours,
    ABBREVIATION_MAP, AMBIGUOUS_ABBREVIATIONS,
    is_ambiguous, get_alternatives, resolve_abbreviation,
    parse_utc_offset, resolve_timezone,
    list_abbreviations, list_available_zones,
)


# ═══════════════════════════════════════════════════════════════════
# 1. Zone Conversion
# ═══════════════════════════════════════════════════════════════════

class TestConvertTime:
    def test_naive_to_aware(self):
        dt = datetime(2024, 6, 15, 12, 0)
        result = convert_time(dt, ZoneInfo("America/New_York"), ZoneInfo("Europe/London"))
        assert result.tzinfo is not None
        assert result.hour == 17

    def test_utc_to_est_winter(self):
        dt = datetime(2024, 1, 15, 17, 0)
        result = convert_time(dt, ZoneInfo("UTC"), ZoneInfo("America/New_York"))
        assert result.hour == 12

    def test_utc_to_edt_summer(self):
        dt = datetime(2024, 7, 15, 17, 0)
        result = convert_time(dt, ZoneInfo("UTC"), ZoneInfo("America/New_York"))
        assert result.hour == 13

    def test_across_midnight(self):
        dt = datetime(2024, 6, 15, 23, 0)
        result = convert_time(dt, ZoneInfo("Europe/London"), ZoneInfo("Asia/Tokyo"))
        assert result.hour == 7
        assert result.day == 16

    def test_half_hour_offset(self):
        dt = datetime(2024, 6, 15, 12, 0)
        result = convert_time(dt, ZoneInfo("UTC"), ZoneInfo("Asia/Kolkata"))
        assert result.hour == 17 and result.minute == 30

    def test_45_minute_offset(self):
        dt = datetime(2024, 6, 15, 12, 0)
        result = convert_time(dt, ZoneInfo("UTC"), ZoneInfo("Asia/Kathmandu"))
        assert result.hour == 17 and result.minute == 45

    def test_round_trip(self):
        dt = datetime(2024, 6, 15, 14, 30)
        ny, lon = ZoneInfo("America/New_York"), ZoneInfo("Europe/London")
        result = convert_time(convert_time(dt, ny, lon), lon, ny)
        assert result.hour == 14 and result.minute == 30

    def test_fixed_offset_source(self):
        dt = datetime(2024, 6, 15, 12, 0)
        result = convert_time(dt, timezone(timedelta(hours=5, minutes=30)), ZoneInfo("UTC"))
        assert result.hour == 6 and result.minute == 30

    def test_preserve_seconds(self):
        dt = datetime(2024, 6, 15, 12, 30, 45)
        result = convert_time(dt, ZoneInfo("UTC"), ZoneInfo("Asia/Tokyo"))
        assert result.second == 45

    def test_same_zone(self):
        dt = datetime(2024, 6, 15, 12, 0)
        zone = ZoneInfo("America/New_York")
        assert convert_time(dt, zone, zone).hour == 12


class TestConvertTimeStr:
    def test_basic_conversion(self):
        result = convert_time_str("2024-03-10 14:00", "US/Eastern", "Europe/London")
        assert result.tzinfo is not None

    def test_pst_to_jst(self):
        result = convert_time_str("2024-06-15 09:00", "PST", "JST")
        assert result.hour == 1 and result.day == 16

    def test_invalid_time_format(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            convert_time_str("not-a-time", "UTC", "EST")

    def test_invalid_zone(self):
        with pytest.raises(ValueError, match="Unknown timezone"):
            convert_time_str("2024-06-15 12:00", "Not/A/Zone", "UTC")


class TestNowInZones:
    def test_multiple_zones(self):
        results = now_in_zones(["UTC", "America/New_York", "Asia/Tokyo"])
        assert len(results) == 3

    def test_all_same_instant(self):
        results = now_in_zones(["UTC", "America/New_York", "Asia/Tokyo"])
        utc_times = [dt.astimezone(timezone.utc) for _, dt in results]
        for i in range(1, len(utc_times)):
            assert abs((utc_times[i] - utc_times[0]).total_seconds()) < 1


class TestFormatOffset:
    def test_zero(self):
        assert format_offset(timedelta(0)) == "+00:00"

    def test_positive(self):
        assert format_offset(timedelta(hours=5)) == "+05:00"

    def test_negative(self):
        assert format_offset(timedelta(hours=-8)) == "-08:00"

    def test_half_hour(self):
        assert format_offset(timedelta(hours=5, minutes=30)) == "+05:30"

    def test_45_minutes(self):
        assert format_offset(timedelta(hours=5, minutes=45)) == "+05:45"


class TestGetUtcOffset:
    def test_utc_is_zero(self):
        dt = datetime(2024, 6, 15, 12, 0, tzinfo=ZoneInfo("UTC"))
        assert get_utc_offset(dt) == timedelta(0)

    def test_ny_summer(self):
        dt = datetime(2024, 6, 15, 12, 0, tzinfo=ZoneInfo("America/New_York"))
        assert get_utc_offset(dt) == timedelta(hours=-4)

    def test_naive_raises(self):
        with pytest.raises(ValueError, match="naive"):
            get_utc_offset(datetime(2024, 6, 15, 12, 0))


class TestParseDatetime:
    def test_iso_format(self):
        result = parse_datetime("2024-06-15 14:30")
        assert result.hour == 14 and result.minute == 30

    def test_time_only(self):
        result = parse_datetime("14:30")
        assert result.hour == 14

    def test_invalid(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_datetime("not-a-time")


ZONE_PAIRS = [
    ("America/New_York", "Europe/London"),
    ("America/New_York", "Asia/Tokyo"),
    ("America/Los_Angeles", "Europe/Berlin"),
    ("Europe/London", "Asia/Kolkata"),
    ("Asia/Tokyo", "Australia/Sydney"),
    ("Pacific/Honolulu", "Asia/Tokyo"),
]


class TestZonePairRoundTrips:
    @pytest.mark.parametrize("from_zone,to_zone", ZONE_PAIRS)
    def test_round_trip_winter(self, from_zone, to_zone):
        dt = datetime(2024, 1, 15, 12, 0)
        fz, tz = ZoneInfo(from_zone), ZoneInfo(to_zone)
        result = convert_time(convert_time(dt, fz, tz), tz, fz)
        assert result.hour == 12 and result.minute == 0

    @pytest.mark.parametrize("from_zone,to_zone", ZONE_PAIRS)
    def test_round_trip_summer(self, from_zone, to_zone):
        dt = datetime(2024, 7, 15, 12, 0)
        fz, tz = ZoneInfo(from_zone), ZoneInfo(to_zone)
        result = convert_time(convert_time(dt, fz, tz), tz, fz)
        assert result.hour == 12 and result.minute == 0


# ═══════════════════════════════════════════════════════════════════
# 2. DST Transitions
# ═══════════════════════════════════════════════════════════════════

class TestIsDst:
    def test_ny_summer_is_dst(self):
        assert is_dst("America/New_York", datetime(2024, 7, 15, 12, 0, tzinfo=timezone.utc)) is True

    def test_ny_winter_not_dst(self):
        assert is_dst("America/New_York", datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)) is False

    def test_tokyo_never_dst(self):
        assert is_dst("Asia/Tokyo", datetime(2024, 7, 15, 12, 0, tzinfo=timezone.utc)) is False

    def test_sydney_january_is_dst(self):
        assert is_dst("Australia/Sydney", datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)) is True

    def test_sydney_july_not_dst(self):
        assert is_dst("Australia/Sydney", datetime(2024, 7, 15, 0, 0, tzinfo=timezone.utc)) is False

    def test_honolulu_never_dst(self):
        assert is_dst("Pacific/Honolulu", datetime(2024, 7, 15, 12, 0, tzinfo=timezone.utc)) is False


class TestGetDstInfo:
    def test_ny_summer_info(self):
        info = get_dst_info("America/New_York", datetime(2024, 7, 15, 12, 0, tzinfo=timezone.utc))
        assert info["is_dst"] is True
        assert info["utc_offset"] == "UTC-04:00"
        assert info["abbreviation"] == "EDT"
        assert info["observes_dst"] is True

    def test_ny_winter_info(self):
        info = get_dst_info("America/New_York", datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc))
        assert info["is_dst"] is False
        assert info["utc_offset"] == "UTC-05:00"
        assert info["abbreviation"] == "EST"

    def test_tokyo_info(self):
        info = get_dst_info("Asia/Tokyo", datetime(2024, 7, 15, 12, 0, tzinfo=timezone.utc))
        assert info["observes_dst"] is False
        assert info["utc_offset"] == "UTC+09:00"

    def test_india_info(self):
        info = get_dst_info("Asia/Kolkata", datetime(2024, 7, 15, 12, 0, tzinfo=timezone.utc))
        assert info["utc_offset"] == "UTC+05:30"
        assert info["observes_dst"] is False

    def test_all_keys_present(self):
        info = get_dst_info("UTC")
        for key in ["zone", "iana_name", "is_dst", "utc_offset", "utc_offset_td",
                     "dst_offset", "abbreviation", "observes_dst"]:
            assert key in info


class TestFindNextTransition:
    def test_ny_spring_forward(self):
        t = find_next_transition("America/New_York", datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc))
        assert t is not None
        assert t["direction"] == "spring-forward"
        assert t["transition_time_utc"].month == 3

    def test_ny_fall_back(self):
        t = find_next_transition("America/New_York", datetime(2024, 7, 15, 0, 0, tzinfo=timezone.utc))
        assert t is not None
        assert t["direction"] == "fall-back"

    def test_tokyo_no_transition(self):
        assert find_next_transition("Asia/Tokyo", datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)) is None

    def test_spring_forward_60_minutes(self):
        t = find_next_transition("America/New_York", datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc))
        assert t["gap_or_overlap_minutes"] == 60

    def test_offset_changes(self):
        t = find_next_transition("America/New_York", datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc))
        assert t["offset_before"] != t["offset_after"]

    def test_fixed_offset_no_transition(self):
        assert find_next_transition("+05:30", datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)) is None


class TestFindTransitionsInYear:
    def test_ny_2024_has_two(self):
        transitions = find_transitions_in_year("America/New_York", 2024)
        assert len(transitions) == 2

    def test_tokyo_no_transitions(self):
        assert len(find_transitions_in_year("Asia/Tokyo", 2024)) == 0

    def test_ny_spring_and_fall(self):
        directions = [t["direction"] for t in find_transitions_in_year("America/New_York", 2024)]
        assert "spring-forward" in directions and "fall-back" in directions


class TestFormatTransition:
    def test_format_none(self):
        assert "does not observe DST" in format_transition(None)

    def test_format_spring(self):
        t = find_next_transition("America/New_York", datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc))
        result = format_transition(t)
        assert "spring-forward" in result and "advance" in result


class TestFormatDstInfo:
    def test_basic(self):
        result = format_dst_info(get_dst_info("America/New_York"))
        assert "America/New_York" in result
        assert "DST active:" in result
        assert "Observes DST:" in result


DST_ZONES = [
    ("America/New_York", True), ("America/Los_Angeles", True),
    ("Europe/London", True), ("Europe/Berlin", True),
    ("Australia/Sydney", True), ("Pacific/Auckland", True),
    ("Asia/Tokyo", False), ("Asia/Kolkata", False),
    ("Asia/Shanghai", False), ("Pacific/Honolulu", False),
]


class TestDstZones:
    @pytest.mark.parametrize("zone,expects_dst", DST_ZONES)
    def test_zone_dst_observation(self, zone, expects_dst):
        info = get_dst_info(zone, datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc))
        assert info["observes_dst"] is expects_dst

    @pytest.mark.parametrize("zone,expects_dst", DST_ZONES)
    def test_zone_transitions_exist(self, zone, expects_dst):
        transitions = find_transitions_in_year(zone, 2024)
        if expects_dst:
            assert len(transitions) >= 2
        else:
            assert len(transitions) == 0


# ═══════════════════════════════════════════════════════════════════
# 3. Overlap Calculation
# ═══════════════════════════════════════════════════════════════════

class TestFindOverlap:
    def test_ny_london_summer_3h(self):
        results = find_overlap(["America/New_York", "Europe/London"], 9, 17, date(2024, 6, 15))
        assert len(results) == 1
        assert abs(results[0]["duration_hours"] - 3.0) < 0.1

    def test_no_overlap_pacific_tokyo(self):
        assert len(find_overlap(["America/Los_Angeles", "Asia/Tokyo"], 9, 17, date(2024, 6, 15))) == 0

    def test_same_zone_full_overlap(self):
        results = find_overlap(["America/New_York", "America/New_York"], 9, 17, date(2024, 6, 15))
        assert abs(results[0]["duration_hours"] - 8.0) < 0.1

    def test_three_zones(self):
        results = find_overlap(["America/New_York", "Europe/London", "Europe/Berlin"], 9, 17, date(2024, 6, 15))
        assert abs(results[0]["duration_hours"] - 2.0) < 0.1

    def test_many_zones_no_overlap(self):
        assert len(find_overlap(["America/Los_Angeles", "Europe/London", "Asia/Tokyo"], 9, 17, date(2024, 6, 15))) == 0

    def test_has_local_times(self):
        results = find_overlap(["America/New_York", "Europe/London"], 9, 17, date(2024, 6, 15))
        assert "America/New_York" in results[0]["local_times"]


class TestFindOverlapValidation:
    def test_empty_zones_raises(self):
        with pytest.raises(ValueError, match="At least one timezone"):
            find_overlap([])

    def test_invalid_start_hour(self):
        with pytest.raises(ValueError, match="start_hour"):
            find_overlap(["UTC"], start_hour=-1, end_hour=17)

    def test_start_equals_end(self):
        with pytest.raises(ValueError, match="start_hour"):
            find_overlap(["UTC"], start_hour=9, end_hour=9)


class TestFormatOverlap:
    def test_no_overlap_message(self):
        assert "No overlapping" in format_overlap([])

    def test_overlap_shows_zones(self):
        results = find_overlap(["America/New_York", "Europe/London"], 9, 17, date(2024, 6, 15))
        text = format_overlap(results)
        assert "America/New_York" in text and "Europe/London" in text


class TestGetZoneWorkHours:
    def test_basic_info(self):
        info = get_zone_work_hours("America/New_York", reference_date=date(2024, 6, 15))
        assert info["local_start"].hour == 9 and info["local_end"].hour == 17

    def test_ny_utc_summer(self):
        info = get_zone_work_hours("America/New_York", reference_date=date(2024, 6, 15))
        assert info["utc_start"].hour == 13


OVERLAP_SCENARIOS = [
    (["America/New_York", "Europe/London"], 9, 17, date(2024, 1, 15), True),
    (["America/Los_Angeles", "Asia/Tokyo"], 9, 17, date(2024, 6, 15), False),
    (["Europe/London", "Europe/Berlin"], 9, 17, date(2024, 6, 15), True),
    (["UTC", "UTC"], 9, 17, date(2024, 6, 15), True),
]


class TestOverlapScenarios:
    @pytest.mark.parametrize("zones,start,end,ref_date,expect_overlap", OVERLAP_SCENARIOS)
    def test_overlap_scenario(self, zones, start, end, ref_date, expect_overlap):
        results = find_overlap(zones, start_hour=start, end_hour=end, reference_date=ref_date)
        if expect_overlap:
            assert len(results) > 0
        else:
            assert len(results) == 0


# ═══════════════════════════════════════════════════════════════════
# 4. Abbreviation Resolution
# ═══════════════════════════════════════════════════════════════════

class TestResolveAbbreviation:
    @pytest.mark.parametrize("abbr,expected", [
        ("EST", "America/New_York"), ("EDT", "America/New_York"),
        ("CST", "America/Chicago"), ("PST", "America/Los_Angeles"),
        ("GMT", "Europe/London"), ("CET", "Europe/Berlin"),
        ("JST", "Asia/Tokyo"), ("KST", "Asia/Seoul"),
        ("IST", "Asia/Kolkata"), ("UTC", "UTC"), ("Z", "UTC"),
        ("AEST", "Australia/Sydney"), ("NZST", "Pacific/Auckland"),
        ("BRT", "America/Sao_Paulo"), ("EAT", "Africa/Nairobi"),
    ])
    def test_abbreviation(self, abbr, expected):
        assert resolve_abbreviation(abbr) == expected

    def test_case_insensitive(self):
        assert resolve_abbreviation("est") == "America/New_York"

    def test_unknown_returns_none(self):
        assert resolve_abbreviation("XYZ") is None

    def test_explicit_disambiguation(self):
        assert resolve_abbreviation("IST_INDIA") == "Asia/Kolkata"
        assert resolve_abbreviation("IST_IRELAND") == "Europe/Dublin"
        assert resolve_abbreviation("CST_CHINA") == "Asia/Shanghai"


class TestIsAmbiguous:
    def test_cst_is_ambiguous(self):
        assert is_ambiguous("CST") is True

    def test_ist_is_ambiguous(self):
        assert is_ambiguous("IST") is True

    def test_pst_is_not_ambiguous(self):
        assert is_ambiguous("PST") is False


class TestGetAlternatives:
    def test_cst_alternatives(self):
        alts = get_alternatives("CST")
        assert alts is not None
        assert "US Central" in alts and "China" in alts

    def test_non_ambiguous_returns_none(self):
        assert get_alternatives("PST") is None


class TestParseUtcOffset:
    def test_plus_five_thirty(self):
        tz = parse_utc_offset("+05:30")
        assert tz.utcoffset(None) == timedelta(hours=5, minutes=30)

    def test_minus_eight(self):
        tz = parse_utc_offset("-08:00")
        assert tz.utcoffset(None) == timedelta(hours=-8)

    def test_utc_plus_five(self):
        tz = parse_utc_offset("UTC+5")
        assert tz.utcoffset(None) == timedelta(hours=5)

    def test_just_utc(self):
        tz = parse_utc_offset("UTC")
        assert tz.utcoffset(None) == timedelta(0)

    def test_compact_format(self):
        tz = parse_utc_offset("+0530")
        assert tz.utcoffset(None) == timedelta(hours=5, minutes=30)

    def test_invalid_no_sign(self):
        assert parse_utc_offset("5") is None

    def test_invalid_empty(self):
        assert parse_utc_offset("") is None

    def test_invalid_minutes_out_of_range(self):
        assert parse_utc_offset("+05:60") is None


class TestResolveTimezone:
    def test_iana_name(self):
        tz = resolve_timezone("America/New_York")
        assert isinstance(tz, ZoneInfo) and str(tz) == "America/New_York"

    def test_abbreviation(self):
        tz = resolve_timezone("EST")
        assert isinstance(tz, ZoneInfo) and str(tz) == "America/New_York"

    def test_utc_offset(self):
        tz = resolve_timezone("+05:30")
        assert isinstance(tz, timezone)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown timezone"):
            resolve_timezone("Not/A/Zone")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Empty timezone"):
            resolve_timezone("")


class TestListFunctions:
    def test_list_abbreviations(self):
        result = list_abbreviations()
        assert isinstance(result, dict) and "EST" in result

    def test_list_abbreviations_is_copy(self):
        result = list_abbreviations()
        result["FAKE"] = "Fake/Zone"
        assert "FAKE" not in ABBREVIATION_MAP

    def test_list_available_zones(self):
        zones = list_available_zones()
        assert len(zones) > 0 and zones == sorted(zones)

    def test_list_filter(self):
        zones = list_available_zones("europe")
        assert all("europe" in z.lower() for z in zones)


class TestAbbreviationMapValidity:
    @pytest.mark.parametrize("abbr,iana", list(ABBREVIATION_MAP.items()))
    def test_maps_to_valid_zone(self, abbr, iana):
        try:
            ZoneInfo(iana)
        except KeyError:
            pytest.fail(f"{abbr} maps to invalid zone: {iana}")
