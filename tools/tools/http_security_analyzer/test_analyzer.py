"""Tests for the HTTP security analyzer toolshed module."""

import pytest
from analyzer import (
    parse_csp, check_hsts, check_cors, analyze_headers,
    format_report, Severity, SourceType,
)


# ============================================================
# CSP Parser Tests
# ============================================================

class TestCSPParser:
    def test_empty_csp(self):
        p = parse_csp("")
        assert any(f.severity == Severity.ERROR for f in p.all_findings)

    def test_default_src_self(self):
        p = parse_csp("default-src 'self'")
        assert p.has_directive("default-src")
        assert p.directives[0].sources[0].source_type == SourceType.SELF

    def test_unsafe_inline_critical(self):
        p = parse_csp("script-src 'unsafe-inline'")
        assert any(f.severity == Severity.CRITICAL for f in p.all_findings)

    def test_unsafe_eval_critical(self):
        p = parse_csp("script-src 'unsafe-eval'")
        assert any(f.severity == Severity.CRITICAL for f in p.all_findings)

    def test_data_scheme_critical(self):
        p = parse_csp("script-src data:")
        assert any(f.severity == Severity.CRITICAL for f in p.all_findings)

    def test_wildcard_critical(self):
        p = parse_csp("default-src *")
        assert any(f.severity == Severity.CRITICAL for f in p.all_findings)

    def test_nonce_source(self):
        p = parse_csp("script-src 'nonce-YWJjZGVmZ2hpamtsbW5vcA=='")
        assert p.directives[0].sources[0].source_type == SourceType.NONCE

    def test_hash_source(self):
        p = parse_csp("script-src 'sha256-RFWPLDbv2BY+rCkDzsE+0fr8ylGr2R2faWMhq4lfEQc='")
        assert p.directives[0].sources[0].source_type == SourceType.HASH

    def test_host_source(self):
        p = parse_csp("script-src https://cdn.example.com")
        assert p.directives[0].sources[0].source_type == SourceType.HOST

    def test_scheme_source(self):
        p = parse_csp("img-src https:")
        assert p.directives[0].sources[0].source_type == SourceType.SCHEME

    def test_unquoted_self_invalid(self):
        p = parse_csp("default-src self")
        assert any(not s.is_valid for d in p.directives for s in d.sources)

    def test_multiple_directives(self):
        p = parse_csp("default-src 'none'; script-src 'self'; style-src 'self'")
        assert len(p.directives) == 3

    def test_missing_default_src_warning(self):
        p = parse_csp("script-src 'self'")
        assert any("default-src" in f.message.lower() for f in p.findings)

    def test_well_configured_no_critical(self):
        p = parse_csp("default-src 'none'; script-src 'self'; style-src 'self'; "
                       "img-src 'self'; object-src 'none'; base-uri 'self'")
        critical = [f for f in p.all_findings if f.severity == Severity.CRITICAL]
        assert len(critical) == 0


# ============================================================
# HSTS Tests
# ============================================================

class TestHSTS:
    def test_missing(self):
        r = check_hsts(None)
        assert any(f.severity == Severity.CRITICAL for f in r.findings)

    def test_valid(self):
        r = check_hsts("max-age=63072000; includeSubDomains; preload")
        assert r.is_valid
        assert r.is_preload_eligible

    def test_short_max_age(self):
        r = check_hsts("max-age=3600")
        assert any(f.severity == Severity.WARNING for f in r.findings)

    def test_missing_max_age(self):
        r = check_hsts("includeSubDomains")
        assert not r.is_valid

    def test_preload_without_subdomains(self):
        r = check_hsts("max-age=63072000; preload")
        assert not r.is_preload_eligible
        assert any("includeSubDomains" in f.message for f in r.findings)


# ============================================================
# CORS Tests
# ============================================================

class TestCORS:
    def test_no_cors(self):
        r = check_cors({})
        assert not r.has_cors

    def test_wildcard_origin(self):
        r = check_cors({"Access-Control-Allow-Origin": "*"})
        assert r.has_cors
        assert any(f.severity == Severity.WARNING for f in r.findings)

    def test_null_origin_critical(self):
        r = check_cors({"Access-Control-Allow-Origin": "null"})
        assert any(f.severity == Severity.CRITICAL for f in r.findings)

    def test_credentials_with_wildcard(self):
        r = check_cors({
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        })
        assert any(f.severity == Severity.CRITICAL for f in r.findings)

    def test_dangerous_methods(self):
        r = check_cors({
            "Access-Control-Allow-Origin": "https://example.com",
            "Access-Control-Allow-Methods": "GET, PUT, DELETE",
        })
        assert any("Dangerous" in f.message for f in r.findings)


# ============================================================
# Full Analyzer Tests
# ============================================================

class TestAnalyzer:
    def test_empty_headers_f(self):
        r = analyze_headers({})
        assert r["grade"] == "F"

    def test_well_configured_a(self):
        headers = {
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }
        r = analyze_headers(headers)
        assert r["grade"] in ("A+", "A")

    def test_dangerous_csp_low_grade(self):
        headers = {
            "Content-Security-Policy": "default-src * 'unsafe-inline' 'unsafe-eval'",
        }
        r = analyze_headers(headers)
        assert r["grade"] in ("F", "D", "C")

    def test_format_report(self):
        r = analyze_headers({})
        report = format_report(r, url="https://example.com")
        assert "Grade:" in report
        assert "https://example.com" in report

    def test_findings_have_suggestions(self):
        r = analyze_headers({})
        for f in r["findings"]:
            if f.severity in (Severity.CRITICAL, Severity.ERROR, Severity.WARNING):
                assert f.suggestion, f"Finding missing suggestion: {f.message}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
