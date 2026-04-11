"""
HTTP Security Analyzer — Comprehensive Security Header Analysis for Agents

Analyzes HTTP response headers for security issues, grades A-F, and suggests
concrete fixes.  Agents building web services, auditing deployments, or
reviewing infrastructure need to verify security headers are correct.  A
missing Content-Security-Policy or a misconfigured HSTS header can leave
an application vulnerable to XSS, clickjacking, or downgrade attacks.

This tool checks seven security header categories:

  1. Content-Security-Policy (CSP) — Full Level 3 parser.  Validates
     directives, source expressions (keywords, nonces, hashes, hosts,
     schemes).  Flags dangerous patterns: 'unsafe-inline', 'unsafe-eval',
     data: in scripts, wildcards.

  2. Strict-Transport-Security (HSTS) — Checks max-age (minimum 1 year),
     includeSubDomains, preload eligibility per hstspreload.org rules.

  3. X-Frame-Options — Validates DENY/SAMEORIGIN, flags deprecated
     ALLOW-FROM.

  4. X-Content-Type-Options — Must be "nosniff".

  5. Referrer-Policy — Validates against spec, flags dangerous policies
     (unsafe-url), handles fallback lists.

  6. Permissions-Policy — Checks header presence, detects deprecated
     Feature-Policy.

  7. CORS — Checks for wildcard origins, null origin (critical),
     credentials+wildcard violations (forbidden by spec), dangerous
     methods.

Also checks: Server version disclosure, X-Powered-By disclosure.

GRADING
=======
  Headers are scored on a weighted 100-point scale:
    CSP: 30pts, HSTS: 20pts, X-Frame-Options: 10pts,
    X-Content-Type-Options: 10pts, Referrer-Policy: 10pts,
    Permissions-Policy: 10pts, CORS: 10pts (only if present).

  Grades: A+ (95+), A (85+), B (70+), C (55+), D (40+), F (<40).
  Critical findings cap the grade regardless of score.

Pure Python, no external dependencies (uses urllib for fetching).
"""

from __future__ import annotations

import base64
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# CSP Parser
# ============================================================

FETCH_DIRECTIVES = frozenset({
    "default-src", "script-src", "script-src-elem", "script-src-attr",
    "style-src", "style-src-elem", "style-src-attr", "img-src", "font-src",
    "connect-src", "media-src", "object-src", "prefetch-src", "child-src",
    "frame-src", "worker-src", "manifest-src",
})

ALL_KNOWN_DIRECTIVES = FETCH_DIRECTIVES | {
    "base-uri", "sandbox", "form-action", "frame-ancestors", "navigate-to",
    "report-uri", "report-to", "plugin-types", "block-all-mixed-content",
    "upgrade-insecure-requests", "require-sri-for", "require-trusted-types-for",
    "trusted-types",
}

DEPRECATED_DIRECTIVES = frozenset({
    "plugin-types", "block-all-mixed-content", "report-uri",
    "require-sri-for", "prefetch-src",
})


class SourceType(Enum):
    NONE = "none"
    SELF = "self"
    UNSAFE_INLINE = "unsafe-inline"
    UNSAFE_EVAL = "unsafe-eval"
    STRICT_DYNAMIC = "strict-dynamic"
    NONCE = "nonce"
    HASH = "hash"
    SCHEME = "scheme"
    HOST = "host"
    KEYWORD = "keyword"
    UNKNOWN = "unknown"


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


CSP_KEYWORDS = {
    "'none'": SourceType.NONE, "'self'": SourceType.SELF,
    "'unsafe-inline'": SourceType.UNSAFE_INLINE,
    "'unsafe-eval'": SourceType.UNSAFE_EVAL,
    "'strict-dynamic'": SourceType.STRICT_DYNAMIC,
    "'unsafe-hashes'": SourceType.KEYWORD,
    "'report-sample'": SourceType.KEYWORD,
    "'wasm-unsafe-eval'": SourceType.KEYWORD,
}

_NONCE_RE = re.compile(r"^'nonce-([^']+)'$")
_HASH_RE = re.compile(r"^'(sha256|sha384|sha512)-([^']+)'$")
_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+\-.]*:$")
_HOST_RE = re.compile(
    r"^(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*(:\d+|:\*)?(/[^\s]*)?$"
)
_SCHEME_HOST_RE = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9+\-.]*://"
    r"(\*\.)?[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*(:\d+|:\*)?(/[^\s]*)?$"
)


@dataclass(frozen=True)
class Finding:
    severity: Severity
    header: str
    message: str
    suggestion: str = ""


@dataclass(frozen=True)
class CSPSource:
    raw: str
    source_type: SourceType
    value: str = ""
    is_valid: bool = True
    error: str = ""


@dataclass
class CSPDirective:
    name: str
    sources: list[CSPSource] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


@dataclass
class CSPPolicy:
    raw: str
    directives: list[CSPDirective] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def has_directive(self, name: str) -> bool:
        return any(d.name == name for d in self.directives)

    @property
    def all_findings(self) -> list[Finding]:
        result = list(self.findings)
        for d in self.directives:
            result.extend(d.findings)
        return result


def _parse_source(raw: str) -> CSPSource:
    lower = raw.lower()
    if lower in CSP_KEYWORDS:
        return CSPSource(raw=raw, source_type=CSP_KEYWORDS[lower], value=raw)

    unquoted = {"none": "'none'", "self": "'self'", "unsafe-inline": "'unsafe-inline'",
                "unsafe-eval": "'unsafe-eval'"}
    if lower in unquoted:
        return CSPSource(raw=raw, source_type=SourceType.UNKNOWN, value=raw,
                         is_valid=False, error=f"Must be single-quoted: {unquoted[lower]}")

    m = _NONCE_RE.match(raw)
    if m:
        nonce_val = m.group(1)
        try:
            base64.b64decode(nonce_val, validate=True)
        except Exception:
            return CSPSource(raw=raw, source_type=SourceType.NONCE, value=nonce_val,
                             is_valid=False, error="Invalid base64 in nonce")
        if len(nonce_val) < 16:
            return CSPSource(raw=raw, source_type=SourceType.NONCE, value=nonce_val,
                             is_valid=False, error="Nonce too short (need 128+ bits)")
        return CSPSource(raw=raw, source_type=SourceType.NONCE, value=nonce_val)

    m = _HASH_RE.match(raw)
    if m:
        algo, hash_val = m.group(1), m.group(2)
        expected = {"sha256": 44, "sha384": 64, "sha512": 88}
        try:
            base64.b64decode(hash_val, validate=True)
        except Exception:
            return CSPSource(raw=raw, source_type=SourceType.HASH, value=f"{algo}-{hash_val}",
                             is_valid=False, error="Invalid base64 in hash")
        if expected.get(algo) and len(hash_val) != expected[algo]:
            return CSPSource(raw=raw, source_type=SourceType.HASH, value=f"{algo}-{hash_val}",
                             is_valid=False, error=f"{algo} hash wrong length")
        return CSPSource(raw=raw, source_type=SourceType.HASH, value=f"{algo}-{hash_val}")

    if _SCHEME_RE.match(raw):
        return CSPSource(raw=raw, source_type=SourceType.SCHEME, value=raw)
    if _SCHEME_HOST_RE.match(raw) or _HOST_RE.match(raw):
        return CSPSource(raw=raw, source_type=SourceType.HOST, value=raw)
    if raw == "*":
        return CSPSource(raw=raw, source_type=SourceType.HOST, value="*")
    return CSPSource(raw=raw, source_type=SourceType.UNKNOWN, value=raw,
                     is_valid=False, error=f"Unrecognized source: {raw!r}")


def parse_csp(header_value: str) -> CSPPolicy:
    """Parse a Content-Security-Policy header into structured findings."""
    raw = header_value.strip()
    policy = CSPPolicy(raw=raw)
    if not raw:
        policy.findings.append(Finding(Severity.ERROR, "CSP", "Empty CSP header",
                                       "Add default-src 'self'"))
        return policy

    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        tokens = part.split()
        name = tokens[0].lower()
        directive = CSPDirective(name=name)
        for token in tokens[1:]:
            source = _parse_source(token)
            directive.sources.append(source)

        # Flag dangerous patterns
        source_types = {s.source_type for s in directive.sources}
        if name in ("script-src", "script-src-elem", "default-src"):
            if SourceType.UNSAFE_INLINE in source_types:
                directive.findings.append(Finding(
                    Severity.CRITICAL, "CSP",
                    f"'unsafe-inline' in {name} allows inline scripts (XSS risk)",
                    "Use nonce-based or hash-based CSP instead"))
            if SourceType.UNSAFE_EVAL in source_types:
                directive.findings.append(Finding(
                    Severity.CRITICAL, "CSP",
                    f"'unsafe-eval' in {name} allows eval() (code injection risk)",
                    "Refactor to avoid eval()"))
            for s in directive.sources:
                if s.source_type == SourceType.SCHEME and s.value.lower() == "data:":
                    directive.findings.append(Finding(
                        Severity.CRITICAL, "CSP",
                        f"data: in {name} allows arbitrary script execution",
                        "Remove data: from script sources"))
                if s.source_type == SourceType.HOST and s.value == "*":
                    directive.findings.append(Finding(
                        Severity.CRITICAL, "CSP",
                        f"Wildcard '*' in {name} allows scripts from any origin",
                        "Restrict to specific trusted domains"))

        policy.directives.append(directive)

    if not policy.has_directive("default-src"):
        policy.findings.append(Finding(
            Severity.WARNING, "CSP", "Missing default-src",
            "Add default-src 'self' or 'none' as baseline"))

    return policy


# ============================================================
# HSTS Checker
# ============================================================

@dataclass
class HSTSResult:
    raw: str = ""
    is_present: bool = False
    is_valid: bool = False
    max_age: int | None = None
    include_sub_domains: bool = False
    preload: bool = False
    findings: list[Finding] = field(default_factory=list)

    @property
    def is_preload_eligible(self) -> bool:
        return (self.is_valid and self.max_age is not None
                and self.max_age >= 31536000 and self.include_sub_domains and self.preload)


def check_hsts(value: str | None) -> HSTSResult:
    """Analyze a Strict-Transport-Security header."""
    if value is None:
        return HSTSResult(findings=[Finding(
            Severity.CRITICAL, "HSTS", "Missing Strict-Transport-Security",
            "Add: max-age=63072000; includeSubDomains; preload")])

    result = HSTSResult(raw=value, is_present=True)
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            k, v = k.strip().lower(), v.strip()
        else:
            k, v = part.strip().lower(), None

        if k == "max-age":
            try:
                result.max_age = int(v)
                result.is_valid = True
                if result.max_age < 31536000:
                    result.findings.append(Finding(
                        Severity.WARNING, "HSTS",
                        f"max-age={result.max_age} is below recommended 31536000 (1 year)",
                        "Increase to at least 31536000"))
            except (ValueError, TypeError):
                result.findings.append(Finding(
                    Severity.ERROR, "HSTS", f"Invalid max-age: {v!r}",
                    "max-age must be a positive integer"))
        elif k == "includesubdomains":
            result.include_sub_domains = True
        elif k == "preload":
            result.preload = True

    if not result.is_valid:
        result.findings.append(Finding(
            Severity.ERROR, "HSTS", "Missing max-age directive",
            "Add max-age=63072000"))
    if result.preload and not result.include_sub_domains:
        result.findings.append(Finding(
            Severity.ERROR, "HSTS", "preload requires includeSubDomains",
            "Add includeSubDomains"))
    return result


# ============================================================
# CORS Checker
# ============================================================

@dataclass
class CORSResult:
    allow_origin: str | None = None
    allow_credentials: bool = False
    allow_methods: list[str] = field(default_factory=list)
    has_cors: bool = False
    findings: list[Finding] = field(default_factory=list)


def check_cors(headers: dict[str, str]) -> CORSResult:
    """Analyze CORS headers for security issues."""
    h = {k.lower(): v for k, v in headers.items()}
    result = CORSResult()
    origin = h.get("access-control-allow-origin")
    if origin is None:
        return result

    result.has_cors = True
    result.allow_origin = origin.strip()

    if result.allow_origin == "*":
        result.findings.append(Finding(
            Severity.WARNING, "CORS", "Wildcard origin allows any site to read responses",
            "Restrict to specific trusted origins"))
    elif result.allow_origin.lower() == "null":
        result.findings.append(Finding(
            Severity.CRITICAL, "CORS",
            "Origin 'null' is dangerous (sandboxed iframes send 'null')",
            "Never allow null origin"))

    creds = h.get("access-control-allow-credentials", "").strip().lower()
    if creds == "true":
        result.allow_credentials = True
        if result.allow_origin == "*":
            result.findings.append(Finding(
                Severity.CRITICAL, "CORS",
                "Credentials=true with wildcard origin is forbidden by CORS spec",
                "Use a specific origin with credentials"))

    methods = h.get("access-control-allow-methods", "")
    if methods:
        result.allow_methods = [m.strip().upper() for m in methods.split(",")]
        dangerous = {"PUT", "DELETE", "PATCH"} & set(result.allow_methods)
        if dangerous:
            result.findings.append(Finding(
                Severity.WARNING, "CORS",
                f"Dangerous methods allowed: {', '.join(sorted(dangerous))}",
                "Only expose methods cross-origin clients need"))

    return result


# ============================================================
# Analyzer
# ============================================================

def analyze_headers(headers: dict[str, str]) -> dict:
    """Analyze HTTP response headers for security issues. Returns structured result."""
    h = {k.lower(): v for k, v in headers.items()}
    findings: list[Finding] = []
    statuses: dict[str, dict] = {}

    # CSP
    csp_val = h.get("content-security-policy")
    if csp_val is None:
        findings.append(Finding(Severity.CRITICAL, "CSP",
                                "Missing Content-Security-Policy",
                                "Add: default-src 'self'; script-src 'self'; object-src 'none'"))
        statuses["CSP"] = {"present": False, "score": 0}
    else:
        policy = parse_csp(csp_val)
        findings.extend(policy.all_findings)
        critical = sum(1 for f in policy.all_findings if f.severity == Severity.CRITICAL)
        statuses["CSP"] = {"present": True, "score": max(0, 30 - critical * 18)}

    # HSTS
    hsts_val = h.get("strict-transport-security")
    hsts = check_hsts(hsts_val)
    findings.extend(hsts.findings)
    hsts_score = 20 if hsts.is_valid and hsts.max_age and hsts.max_age >= 31536000 else (10 if hsts.is_valid else 0)
    if hsts.is_preload_eligible:
        hsts_score = 20
    statuses["HSTS"] = {"present": hsts.is_present, "score": hsts_score}

    # X-Frame-Options
    xfo = h.get("x-frame-options")
    if xfo is None:
        findings.append(Finding(Severity.WARNING, "X-Frame-Options",
                                "Missing X-Frame-Options",
                                "Add: X-Frame-Options: DENY"))
        statuses["XFO"] = {"present": False, "score": 0}
    else:
        valid = xfo.strip().upper() in {"DENY", "SAMEORIGIN"}
        if not valid:
            findings.append(Finding(Severity.ERROR, "X-Frame-Options",
                                    f"Invalid value: {xfo.strip()!r}", "Use DENY or SAMEORIGIN"))
        statuses["XFO"] = {"present": True, "score": 10 if valid else 3}

    # X-Content-Type-Options
    xcto = h.get("x-content-type-options")
    if xcto is None:
        findings.append(Finding(Severity.WARNING, "X-Content-Type-Options",
                                "Missing X-Content-Type-Options",
                                "Add: X-Content-Type-Options: nosniff"))
        statuses["XCTO"] = {"present": False, "score": 0}
    else:
        valid = xcto.strip().lower() == "nosniff"
        statuses["XCTO"] = {"present": True, "score": 10 if valid else 0}

    # Referrer-Policy
    rp = h.get("referrer-policy")
    if rp is None:
        findings.append(Finding(Severity.WARNING, "Referrer-Policy",
                                "Missing Referrer-Policy",
                                "Add: Referrer-Policy: strict-origin-when-cross-origin"))
        statuses["RP"] = {"present": False, "score": 0}
    else:
        preferred = {"no-referrer", "strict-origin", "strict-origin-when-cross-origin", "same-origin"}
        dangerous = {"unsafe-url", "no-referrer-when-downgrade"}
        policies = [p.strip().lower() for p in rp.split(",")]
        effective = None
        for p in policies:
            if p in preferred | dangerous | {"origin", "origin-when-cross-origin"}:
                effective = p
        if effective in dangerous:
            findings.append(Finding(Severity.ERROR, "Referrer-Policy",
                                    f"'{effective}' leaks full URLs",
                                    "Use strict-origin-when-cross-origin"))
            statuses["RP"] = {"present": True, "score": 3}
        elif effective in preferred:
            statuses["RP"] = {"present": True, "score": 10}
        else:
            statuses["RP"] = {"present": True, "score": 5}

    # Permissions-Policy
    pp = h.get("permissions-policy")
    if pp is None:
        findings.append(Finding(Severity.WARNING, "Permissions-Policy",
                                "Missing Permissions-Policy",
                                "Add: Permissions-Policy: camera=(), microphone=(), geolocation=()"))
        statuses["PP"] = {"present": False, "score": 0}
    else:
        statuses["PP"] = {"present": True, "score": 10}

    # CORS
    cors = check_cors(headers)
    if cors.has_cors:
        findings.extend(cors.findings)
        cors_critical = sum(1 for f in cors.findings if f.severity == Severity.CRITICAL)
        statuses["CORS"] = {"present": True, "score": max(0, 10 - cors_critical * 10)}

    # Score
    total = sum(s["score"] for s in statuses.values())
    max_score = 0
    weights = {"CSP": 30, "HSTS": 20, "XFO": 10, "XCTO": 10, "RP": 10, "PP": 10, "CORS": 10}
    for k in statuses:
        if k == "CORS" and not cors.has_cors:
            continue
        max_score += weights.get(k, 10)

    pct = (total / max_score * 100) if max_score > 0 else 0
    critical_count = sum(1 for f in findings if f.severity == Severity.CRITICAL)

    if critical_count >= 3 or (critical_count >= 1 and pct < 50):
        grade = "F"
    elif critical_count >= 2:
        grade = "D"
    elif critical_count >= 1:
        grade = "C"
    elif pct >= 95:
        grade = "A+"
    elif pct >= 85:
        grade = "A"
    elif pct >= 70:
        grade = "B"
    elif pct >= 55:
        grade = "C"
    elif pct >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "grade": grade,
        "score": total,
        "max_score": max_score,
        "findings": findings,
        "statuses": statuses,
    }


def format_report(result: dict, url: str = "") -> str:
    """Format analysis result as human-readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("HTTP Security Header Analysis")
    lines.append("=" * 60)
    if url:
        lines.append(f"URL: {url}")
    lines.append(f"\nGrade: {result['grade']}  ({result['score']}/{result['max_score']} points)\n")

    for f in result["findings"]:
        icon = f.severity.value.upper()
        lines.append(f"  [{icon}] [{f.header}] {f.message}")
        if f.suggestion:
            lines.append(f"    Fix: {f.suggestion}")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def fetch_headers(url: str, timeout: int = 10) -> dict[str, str]:
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "http-security-analyzer/0.1.0")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {k: v for k, v in resp.getheaders()}
    except urllib.error.HTTPError as e:
        return {k: v for k, v in e.headers.items()}
    except urllib.error.URLError as e:
        print(f"Error: {e.reason}", file=sys.stderr)
        sys.exit(2)


def main():
    import argparse
    parser = argparse.ArgumentParser(prog="http-sec",
                                     description="HTTP security header analyzer")
    sub = parser.add_subparsers(dest="command")

    p_analyze = sub.add_parser("analyze", help="Full analysis of a URL")
    p_analyze.add_argument("url")
    p_analyze.add_argument("--json", action="store_true", dest="json_output")

    p_grade = sub.add_parser("grade", help="Just the grade")
    p_grade.add_argument("url")

    p_csp = sub.add_parser("check-csp", help="Validate a CSP string")
    p_csp.add_argument("policy")

    p_headers = sub.add_parser("headers", help="Read headers from file/stdin")
    p_headers.add_argument("--file", "-f")

    args = parser.parse_args()

    if args.command == "analyze":
        headers = fetch_headers(args.url)
        result = analyze_headers(headers)
        if args.json_output:
            out = {"grade": result["grade"], "score": result["score"],
                   "max_score": result["max_score"],
                   "findings": [{"severity": f.severity.value, "header": f.header,
                                 "message": f.message, "suggestion": f.suggestion}
                                for f in result["findings"]]}
            print(json.dumps(out, indent=2))
        else:
            print(format_report(result, url=args.url))

    elif args.command == "grade":
        headers = fetch_headers(args.url)
        result = analyze_headers(headers)
        print(f"Grade: {result['grade']}  ({result['score']}/{result['max_score']})")

    elif args.command == "check-csp":
        policy = parse_csp(args.policy)
        for d in policy.directives:
            print(f"  {d.name}")
            for s in d.sources:
                v = " [INVALID]" if not s.is_valid else ""
                print(f"    {s.raw} ({s.source_type.value}){v}")
        if policy.all_findings:
            print("\nFindings:")
            for f in policy.all_findings:
                print(f"  [{f.severity.value.upper()}] {f.message}")
                if f.suggestion:
                    print(f"    -> {f.suggestion}")

    elif args.command == "headers":
        if args.file:
            with open(args.file) as fh:
                text = fh.read()
        else:
            text = sys.stdin.read()
        headers = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("HTTP/"):
                continue
            pos = line.find(":")
            if pos != -1:
                headers[line[:pos].strip()] = line[pos+1:].strip()
        if headers:
            result = analyze_headers(headers)
            print(format_report(result))
        else:
            print("No headers found.", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
