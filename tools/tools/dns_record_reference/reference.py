"""
DNS Record Reference & Validator — Look up, validate, explain, and generate DNS records.

Covers all common record types (A, AAAA, CNAME, MX, TXT, SRV, SOA, NS, PTR, CAA).
Validates SPF, DKIM, and DMARC record syntax according to their RFCs.
Generates common records. Explains records in plain English.

Pure Python, no external dependencies.

Usage:
    python reference.py lookup A
    python reference.py validate SPF "v=spf1 include:_spf.google.com ~all"
    python reference.py explain DMARC "v=DMARC1; p=reject; rua=mailto:dmarc@example.com"
    python reference.py generate A example.com 93.184.216.34
    python reference.py list
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════
# Registry — DNS record type reference data
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RecordType:
    """A DNS record type with full reference information."""
    name: str
    code: int
    rfc: list[str]
    description: str
    syntax: str
    purpose: str
    examples: list[str]
    common: bool = True
    obsolete: bool = False
    category: str = "general"


_RECORD_TYPES: dict[str, RecordType] = {}


def _register(rt: RecordType) -> RecordType:
    _RECORD_TYPES[rt.name.upper()] = rt
    return rt


A = _register(RecordType(
    name="A", code=1, rfc=["RFC 1035"],
    description="Maps a domain name to an IPv4 address.",
    syntax="<name> <TTL> IN A <IPv4-address>",
    purpose="Point a hostname to a server's IPv4 address.",
    examples=["example.com. 300 IN A 93.184.216.34"],
    category="address",
))

AAAA = _register(RecordType(
    name="AAAA", code=28, rfc=["RFC 3596"],
    description="Maps a domain name to an IPv6 address.",
    syntax="<name> <TTL> IN AAAA <IPv6-address>",
    purpose="Point a hostname to a server's IPv6 address.",
    examples=["example.com. 300 IN AAAA 2606:2800:220:1:248:1893:25c8:1946"],
    category="address",
))

CNAME = _register(RecordType(
    name="CNAME", code=5, rfc=["RFC 1035"],
    description="Creates an alias from one domain name to another (the canonical name).",
    syntax="<alias> <TTL> IN CNAME <canonical-name>",
    purpose="Point one hostname to another. Cannot coexist with other record types at the same name.",
    examples=["www.example.com. 3600 IN CNAME example.com."],
    category="alias",
))

MX = _register(RecordType(
    name="MX", code=15, rfc=["RFC 1035", "RFC 7505"],
    description="Specifies mail servers responsible for receiving email for the domain.",
    syntax="<name> <TTL> IN MX <priority> <mail-server>",
    purpose="Route email to the correct mail servers. Lower priority = preferred.",
    examples=["example.com. 3600 IN MX 10 mail1.example.com."],
    category="mail",
))

TXT = _register(RecordType(
    name="TXT", code=16, rfc=["RFC 1035", "RFC 7208", "RFC 6376", "RFC 7489"],
    description="Holds arbitrary text data. Used for SPF, DKIM, DMARC, domain verification.",
    syntax='<name> <TTL> IN TXT "<text>"',
    purpose="Store text-based metadata. Most commonly used for email authentication.",
    examples=['example.com. 3600 IN TXT "v=spf1 include:_spf.google.com ~all"'],
    category="text",
))

SRV = _register(RecordType(
    name="SRV", code=33, rfc=["RFC 2782"],
    description="Specifies the location of a service (host and port) for a domain.",
    syntax="_<service>._<protocol>.<name> <TTL> IN SRV <priority> <weight> <port> <target>",
    purpose="Locate services like SIP, XMPP, LDAP.",
    examples=["_sip._tcp.example.com. 3600 IN SRV 10 60 5060 sip1.example.com."],
    category="service",
))

SOA = _register(RecordType(
    name="SOA", code=6, rfc=["RFC 1035"],
    description="Start of Authority. Contains administrative information about the zone.",
    syntax="<name> <TTL> IN SOA <primary-ns> <admin-email> (<serial> <refresh> <retry> <expire> <minimum>)",
    purpose="Define zone authority. Every DNS zone must have exactly one SOA record.",
    examples=["example.com. 3600 IN SOA ns1.example.com. admin.example.com. (2024010101 3600 900 604800 86400)"],
    category="authority",
))

NS = _register(RecordType(
    name="NS", code=2, rfc=["RFC 1035"],
    description="Delegates a DNS zone to the specified authoritative nameservers.",
    syntax="<name> <TTL> IN NS <nameserver>",
    purpose="Specify which nameservers are authoritative for a zone.",
    examples=["example.com. 86400 IN NS ns1.example.com."],
    category="authority",
))

PTR = _register(RecordType(
    name="PTR", code=12, rfc=["RFC 1035"],
    description="Maps an IP address back to a domain name (reverse DNS).",
    syntax="<reversed-ip>.in-addr.arpa. <TTL> IN PTR <domain-name>",
    purpose="Reverse DNS lookup. Required for email deliverability.",
    examples=["34.216.184.93.in-addr.arpa. 3600 IN PTR example.com."],
    category="pointer",
))

CAA = _register(RecordType(
    name="CAA", code=257, rfc=["RFC 8659"],
    description="Certificate Authority Authorization. Specifies which CAs may issue certificates.",
    syntax='<name> <TTL> IN CAA <flags> <tag> "<value>"',
    purpose="Control which CAs can issue SSL/TLS certificates for your domain.",
    examples=['example.com. 3600 IN CAA 0 issue "letsencrypt.org"'],
    category="security",
))

SPF_TYPE = _register(RecordType(
    name="SPF", code=99, rfc=["RFC 7208"],
    description="Sender Policy Framework (deprecated as standalone type; use TXT).",
    syntax='<name> <TTL> IN TXT "v=spf1 <mechanisms> <qualifier>"',
    purpose="Prevent email spoofing by specifying authorized senders.",
    examples=['"v=spf1 ip4:192.168.1.0/24 include:_spf.google.com -all"'],
    category="email-auth", obsolete=True,
))

DKIM_TYPE = _register(RecordType(
    name="DKIM", code=0, rfc=["RFC 6376"],
    description="DomainKeys Identified Mail. Stores the public key for DKIM signature verification.",
    syntax='<selector>._domainkey.<domain> <TTL> IN TXT "v=DKIM1; k=rsa; p=<base64-key>"',
    purpose="Verify email was sent by an authorized server and not tampered with.",
    examples=['selector1._domainkey.example.com. 3600 IN TXT "v=DKIM1; k=rsa; p=MIGfMA0..."'],
    category="email-auth",
))

DMARC_TYPE = _register(RecordType(
    name="DMARC", code=0, rfc=["RFC 7489"],
    description="Domain-based Message Authentication, Reporting, and Conformance.",
    syntax='_dmarc.<domain> <TTL> IN TXT "v=DMARC1; p=<policy>; <optional-tags>"',
    purpose="Tell receivers what to do when SPF or DKIM checks fail.",
    examples=['"v=DMARC1; p=reject; rua=mailto:dmarc@example.com"'],
    category="email-auth",
))

TLSA_TYPE = _register(RecordType(
    name="TLSA", code=52, rfc=["RFC 6698"],
    description="DANE TLS certificate association. Binds a TLS certificate to "
                "a domain name and port.",
    syntax="_<port>._<protocol>.<name> <TTL> IN TLSA <usage> <selector> <matching-type> <data>",
    purpose="Part of DANE. Associates a TLS certificate or public key with a "
            "service, enabling certificate pinning via DNS.",
    examples=["_443._tcp.example.com. 3600 IN TLSA 3 1 1 <hex-hash>"],
    category="security",
    common=False,
))


def get_record_type(name: str) -> RecordType | None:
    return _RECORD_TYPES.get(name.upper())


def list_record_types(*, common_only: bool = False, category: str | None = None) -> list[RecordType]:
    result = []
    for rt in _RECORD_TYPES.values():
        if common_only and not rt.common:
            continue
        if category and rt.category != category:
            continue
        result.append(rt)
    return sorted(result, key=lambda r: (r.code if r.code > 0 else 9999, r.name))


def search_record_types(query: str) -> list[RecordType]:
    q = query.lower()
    return sorted(
        [rt for rt in _RECORD_TYPES.values()
         if q in rt.name.lower() or q in rt.description.lower()
         or q in rt.purpose.lower() or q in rt.category.lower()],
        key=lambda r: (r.code if r.code > 0 else 9999, r.name),
    )


# ═══════════════════════════════════════════════════════════════════
# Validator — SPF, DKIM, DMARC, and general record types
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    valid: bool
    record_type: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parsed: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.valid and not self.errors

    def __str__(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        lines = [f"{self.record_type}: {status}"]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return "\n".join(lines)


_SPF_MECHANISMS = {"all", "include", "a", "mx", "ptr", "ip4", "ip6", "exists"}
_SPF_QUALIFIERS = {"+", "-", "~", "?"}
_SPF_MODIFIERS = {"redirect", "exp"}


def _is_valid_domain(s: str) -> bool:
    if not s:
        return False
    if "%" in s:
        return True
    if s.endswith("."):
        s = s[:-1]
    if not s:
        return False
    for label in s.split("."):
        if not label or len(label) > 63:
            return False
        if not re.match(r'^[a-zA-Z0-9_]([a-zA-Z0-9_-]*[a-zA-Z0-9_])?$', label):
            return False
    return True


def validate_spf(record: str) -> ValidationResult:
    """Validate an SPF record (RFC 7208)."""
    result = ValidationResult(valid=True, record_type="SPF")
    record = record.strip()
    if record.startswith('"') and record.endswith('"'):
        record = record[1:-1]

    if not record.startswith("v=spf1"):
        result.valid = False
        result.errors.append("SPF record must start with 'v=spf1'")
        return result

    remainder = record[6:].strip()
    if not remainder:
        result.warnings.append("SPF record has no mechanisms or modifiers")
        result.parsed = {"version": "spf1", "mechanisms": [], "modifiers": {}, "dns_lookups": 0}
        return result

    terms = remainder.split()
    mechanisms = []
    modifiers = {}
    dns_lookups = 0
    all_seen = False
    all_index = -1

    for i, term in enumerate(terms):
        if "=" in term and not term.startswith("v="):
            key, _, value = term.partition("=")
            kl = key.lower()
            if kl in _SPF_MODIFIERS:
                if kl in modifiers:
                    result.errors.append(f"Duplicate modifier: '{kl}'")
                    result.valid = False
                elif not value:
                    result.errors.append(f"Modifier '{kl}' requires a value")
                    result.valid = False
                modifiers[kl] = value
            else:
                result.errors.append(f"Unknown modifier: '{key}'")
                result.valid = False
            continue

        qualifier = "+"
        mech_str = term
        if term[0] in _SPF_QUALIFIERS:
            qualifier = term[0]
            mech_str = term[1:]

        if not mech_str:
            result.errors.append(f"Empty mechanism after qualifier '{qualifier}'")
            result.valid = False
            continue

        if ":" in mech_str:
            mech_name, _, mech_arg = mech_str.partition(":")
        elif "/" in mech_str:
            mech_name, _, cidr = mech_str.partition("/")
            mech_arg = "/" + cidr if cidr else ""
        else:
            mech_name = mech_str
            mech_arg = ""

        mn = mech_name.lower()

        if mn not in _SPF_MECHANISMS:
            result.errors.append(f"Unknown mechanism: '{mech_name}'")
            result.valid = False
            continue

        if mn == "all":
            all_seen = True
            all_index = i
            if mech_arg:
                result.errors.append("'all' mechanism does not take an argument")
                result.valid = False
        elif mn == "include":
            dns_lookups += 1
            if not mech_arg:
                result.errors.append("'include' mechanism requires a domain argument")
                result.valid = False
            elif not _is_valid_domain(mech_arg):
                result.errors.append(f"'include' has invalid domain: '{mech_arg}'")
                result.valid = False
        elif mn == "a":
            dns_lookups += 1
        elif mn == "mx":
            dns_lookups += 1
        elif mn == "ptr":
            dns_lookups += 1
            result.warnings.append("'ptr' mechanism is discouraged (RFC 7208 Section 5.5)")
        elif mn == "ip4":
            if not mech_arg:
                result.errors.append("'ip4' mechanism requires an address argument")
                result.valid = False
            else:
                addr = mech_arg.split("/")[0] if "/" in mech_arg else mech_arg
                try:
                    ipaddress.IPv4Address(addr)
                except (ipaddress.AddressValueError, ValueError):
                    result.errors.append(f"Invalid IPv4 address: '{addr}'")
                    result.valid = False
                if "/" in mech_arg:
                    try:
                        cidr = int(mech_arg.split("/")[1])
                        if not (0 <= cidr <= 32):
                            result.errors.append(f"IPv4 CIDR prefix length must be 0-32, got {cidr}")
                            result.valid = False
                    except ValueError:
                        result.errors.append(f"Invalid CIDR prefix length")
                        result.valid = False
        elif mn == "ip6":
            if not mech_arg:
                result.errors.append("'ip6' mechanism requires an address argument")
                result.valid = False
            else:
                addr = mech_arg.split("/")[0] if "/" in mech_arg else mech_arg
                try:
                    ipaddress.IPv6Address(addr)
                except (ipaddress.AddressValueError, ValueError):
                    result.errors.append(f"Invalid IPv6 address: '{addr}'")
                    result.valid = False
                if "/" in mech_arg:
                    try:
                        cidr = int(mech_arg.split("/")[1])
                        if not (0 <= cidr <= 128):
                            result.errors.append(f"IPv6 CIDR prefix length must be 0-128, got {cidr}")
                            result.valid = False
                    except ValueError:
                        result.errors.append("Invalid CIDR prefix length")
                        result.valid = False
        elif mn == "exists":
            dns_lookups += 1
            if not mech_arg:
                result.errors.append("'exists' mechanism requires a domain argument")
                result.valid = False

        mechanisms.append({"qualifier": qualifier, "mechanism": mn, "argument": mech_arg})

    # Count redirect as a DNS lookup per RFC 7208 Section 4.6.4
    if "redirect" in modifiers:
        dns_lookups += 1

    if dns_lookups > 10:
        result.errors.append(f"Too many DNS lookups: {dns_lookups} (max 10 per RFC 7208)")
        result.valid = False
    elif dns_lookups > 7:
        result.warnings.append(f"DNS lookup count is {dns_lookups}/10")

    if all_seen and all_index < len(terms) - 1:
        post_all = terms[all_index + 1:]
        if any("=" not in t for t in post_all):
            result.warnings.append("'all' mechanism should be the last mechanism")

    if not all_seen and "redirect" not in modifiers:
        result.warnings.append("SPF record has no 'all' mechanism and no 'redirect' modifier")

    result.parsed = {"version": "spf1", "mechanisms": mechanisms, "modifiers": modifiers, "dns_lookups": dns_lookups}
    return result


_DKIM_KNOWN_TAGS = {"v", "h", "k", "n", "p", "s", "t"}
_DKIM_KEY_TYPES = {"rsa", "ed25519"}
_DKIM_HASH_ALGORITHMS = {"sha1", "sha256"}


def _parse_tags(record: str) -> dict[str, str] | None:
    tags = {}
    for part in record.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            return None
        key, _, value = part.partition("=")
        key = key.strip().lower()
        if not key:
            return None
        tags[key] = value.strip()
    return tags


def validate_dkim(record: str) -> ValidationResult:
    """Validate a DKIM TXT record (RFC 6376)."""
    result = ValidationResult(valid=True, record_type="DKIM")
    record = record.strip()
    if record.startswith('"') and record.endswith('"'):
        record = record[1:-1]
    record = record.replace('" "', '').replace('"', '')

    tags = _parse_tags(record)
    if tags is None:
        result.valid = False
        result.errors.append("Failed to parse DKIM tag-value pairs")
        return result

    result.parsed["tags"] = tags

    if "v" in tags:
        if tags["v"] != "DKIM1":
            result.errors.append(f"DKIM version must be 'DKIM1', got '{tags['v']}'")
            result.valid = False
    else:
        result.warnings.append("Missing 'v=DKIM1' version tag (recommended per RFC 6376)")

    if "p" not in tags:
        result.errors.append("Missing required 'p=' tag (public key)")
        result.valid = False
    else:
        key_data = tags["p"]
        if not key_data:
            result.warnings.append("Empty 'p=' tag indicates this DKIM key has been revoked")
            result.parsed["revoked"] = True
        else:
            key_clean = re.sub(r'\s+', '', key_data)
            if not re.match(r'^[A-Za-z0-9+/=]+$', key_clean):
                result.errors.append("Public key 'p=' contains invalid base64 characters")
                result.valid = False
            elif len(key_clean) < 20:
                result.warnings.append(f"Public key seems very short ({len(key_clean)} chars)")
            result.parsed["revoked"] = False

    if "k" in tags:
        kt = tags["k"].lower()
        if kt not in _DKIM_KEY_TYPES:
            result.errors.append(f"Unknown key type 'k={tags['k']}'")
            result.valid = False
        result.parsed["key_type"] = kt
    else:
        result.parsed["key_type"] = "rsa"

    if "h" in tags:
        algos = [a.strip().lower() for a in tags["h"].split(":")]
        for algo in algos:
            if algo not in _DKIM_HASH_ALGORITHMS:
                result.errors.append(f"Unknown hash algorithm 'h={algo}'")
                result.valid = False
        if "sha1" in algos and "sha256" not in algos:
            result.warnings.append("Only SHA-1 specified. SHA-256 is strongly recommended.")
        result.parsed["hash_algorithms"] = algos

    if "s" in tags:
        result.parsed["service_types"] = [s.strip().lower() for s in tags["s"].split(":")]

    if "t" in tags:
        flags = [f.strip().lower() for f in tags["t"].split(":")]
        if "y" in flags:
            result.warnings.append("Flag 't=y' means this domain is testing DKIM")
        result.parsed["flags"] = flags

    for tag in tags:
        if tag not in _DKIM_KNOWN_TAGS:
            result.warnings.append(f"Unknown tag: '{tag}'")

    return result


_DMARC_POLICIES = {"none", "quarantine", "reject"}
_DMARC_ALIGNMENT = {"r", "s"}
_DMARC_FO_OPTIONS = {"0", "1", "d", "s"}
_DMARC_KNOWN_TAGS = {"v", "p", "sp", "rua", "ruf", "adkim", "aspf", "pct", "rf", "ri", "fo"}


def validate_dmarc(record: str) -> ValidationResult:
    """Validate a DMARC TXT record (RFC 7489)."""
    result = ValidationResult(valid=True, record_type="DMARC")
    record = record.strip()
    if record.startswith('"') and record.endswith('"'):
        record = record[1:-1]

    tags = _parse_tags(record)
    if tags is None:
        result.valid = False
        result.errors.append("Failed to parse DMARC tag-value pairs")
        return result

    result.parsed["tags"] = tags
    raw_tags = [t.strip() for t in record.split(";") if t.strip()]

    if "v" not in tags:
        result.errors.append("Missing required 'v=DMARC1' version tag")
        result.valid = False
    elif tags["v"] != "DMARC1":
        result.errors.append(f"DMARC version must be 'DMARC1', got '{tags['v']}'")
        result.valid = False
    elif raw_tags and not raw_tags[0].strip().startswith("v="):
        result.errors.append("'v=DMARC1' must be the first tag")
        result.valid = False

    if "p" not in tags:
        result.errors.append("Missing required 'p=' policy tag")
        result.valid = False
    else:
        policy = tags["p"].lower()
        if policy not in _DMARC_POLICIES:
            result.errors.append(f"Invalid policy 'p={tags['p']}'")
            result.valid = False
        else:
            result.parsed["policy"] = policy
            if policy == "none":
                result.warnings.append("Policy is 'none' (monitor only)")

    if "sp" in tags:
        sp = tags["sp"].lower()
        if sp not in _DMARC_POLICIES:
            result.errors.append(f"Invalid subdomain policy 'sp={tags['sp']}'")
            result.valid = False
        result.parsed["subdomain_policy"] = sp

    if "rua" in tags:
        uris = [u.strip() for u in tags["rua"].split(",")]
        for uri in uris:
            if not uri.startswith("mailto:"):
                result.errors.append(f"Invalid rua URI: '{uri}'. Must start with 'mailto:'")
                result.valid = False
            elif "@" not in uri[7:]:
                result.errors.append(f"Invalid email in rua URI: '{uri[7:]}'")
                result.valid = False
        result.parsed["rua"] = uris
    else:
        result.warnings.append("No 'rua=' aggregate report URI")

    if "ruf" in tags:
        uris = [u.strip() for u in tags["ruf"].split(",")]
        for uri in uris:
            if not uri.startswith("mailto:"):
                result.errors.append(f"Invalid ruf URI: '{uri}'. Must start with 'mailto:'")
                result.valid = False
            elif "@" not in uri[7:]:
                result.errors.append(f"Invalid email in ruf URI: '{uri[7:]}'")
                result.valid = False
        result.parsed["ruf"] = uris

    if "adkim" in tags:
        adkim = tags["adkim"].lower()
        if adkim not in _DMARC_ALIGNMENT:
            result.errors.append(f"Invalid DKIM alignment 'adkim={tags['adkim']}'")
            result.valid = False
        result.parsed["adkim"] = adkim

    if "aspf" in tags:
        aspf = tags["aspf"].lower()
        if aspf not in _DMARC_ALIGNMENT:
            result.errors.append(f"Invalid SPF alignment 'aspf={tags['aspf']}'")
            result.valid = False
        result.parsed["aspf"] = aspf

    if "pct" in tags:
        try:
            pct = int(tags["pct"])
            if not (0 <= pct <= 100):
                result.errors.append(f"Percentage 'pct={pct}' must be between 0 and 100")
                result.valid = False
            elif pct < 100:
                result.warnings.append(f"Only {pct}% of messages will have the policy applied")
            result.parsed["pct"] = pct
        except ValueError:
            result.errors.append(f"Invalid percentage 'pct={tags['pct']}'")
            result.valid = False

    if "ri" in tags:
        try:
            ri = int(tags["ri"])
            if ri <= 0:
                result.errors.append(f"Report interval 'ri={ri}' must be positive")
                result.valid = False
            result.parsed["ri"] = ri
        except ValueError:
            result.errors.append(f"Invalid report interval 'ri={tags['ri']}'")
            result.valid = False

    if "fo" in tags:
        options = [o.strip() for o in tags["fo"].split(":")]
        for opt in options:
            if opt not in _DMARC_FO_OPTIONS:
                result.errors.append(f"Invalid failure reporting option 'fo={opt}'")
                result.valid = False
        result.parsed["fo"] = options

    for tag in tags:
        if tag not in _DMARC_KNOWN_TAGS:
            result.warnings.append(f"Unknown tag: '{tag}'")

    return result


def validate_a(value: str) -> ValidationResult:
    result = ValidationResult(valid=True, record_type="A")
    try:
        addr = ipaddress.IPv4Address(value.strip())
        result.parsed["address"] = str(addr)
        if addr.is_private:
            result.warnings.append(f"{value.strip()} is a private address")
        if addr.is_loopback:
            result.warnings.append(f"{value.strip()} is a loopback address")
    except (ipaddress.AddressValueError, ValueError) as e:
        result.valid = False
        result.errors.append(f"Invalid IPv4 address: {e}")
    return result


def validate_mx(value: str) -> ValidationResult:
    result = ValidationResult(valid=True, record_type="MX")
    parts = value.strip().split(None, 1)
    if len(parts) < 2:
        result.valid = False
        result.errors.append("MX record must have priority and mail server")
        return result
    try:
        priority = int(parts[0])
        if priority < 0 or priority > 65535:
            result.errors.append(f"MX priority must be 0-65535, got {priority}")
            result.valid = False
        result.parsed["priority"] = priority
    except ValueError:
        result.valid = False
        result.errors.append(f"Invalid MX priority: '{parts[0]}'")
        return result
    server = parts[1].strip()
    result.parsed["server"] = server
    if server == ".":
        result.warnings.append("Null MX (RFC 7505) -- domain does not accept email")
    elif re.match(r'^\d+\.\d+\.\d+\.\d+$', server.rstrip(".")):
        result.errors.append("MX record must point to a hostname, not an IP address")
        result.valid = False
    return result


_TLSA_USAGE = {0: "CA constraint", 1: "Service certificate constraint",
               2: "Trust anchor assertion", 3: "Domain-issued certificate"}
_TLSA_SELECTOR = {0: "Full certificate", 1: "SubjectPublicKeyInfo"}
_TLSA_MATCHING = {0: "No hash (full data)", 1: "SHA-256", 2: "SHA-512"}


def validate_tlsa(value: str) -> ValidationResult:
    """Validate a TLSA record value (RFC 6698).

    Checks usage (0-3), selector (0-1), matching type (0-2), and hex data.
    """
    result = ValidationResult(valid=True, record_type="TLSA")
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    parts = value.split()
    if len(parts) < 4:
        result.valid = False
        result.errors.append(
            "TLSA record must have: usage selector matching-type data. "
            "Example: '3 1 1 <hex-sha256-hash>'"
        )
        return result

    # Parse usage
    try:
        usage = int(parts[0])
        if not (0 <= usage <= 3):
            result.errors.append(f"TLSA usage must be 0-3, got {usage}")
            result.valid = False
        else:
            result.parsed["usage"] = usage
            result.parsed["usage_name"] = _TLSA_USAGE[usage]
    except ValueError:
        result.errors.append(f"Invalid TLSA usage: '{parts[0]}' (must be 0-3)")
        result.valid = False

    # Parse selector
    try:
        selector = int(parts[1])
        if not (0 <= selector <= 1):
            result.errors.append(f"TLSA selector must be 0 or 1, got {selector}")
            result.valid = False
        else:
            result.parsed["selector"] = selector
            result.parsed["selector_name"] = _TLSA_SELECTOR[selector]
    except ValueError:
        result.errors.append(f"Invalid TLSA selector: '{parts[1]}' (must be 0-1)")
        result.valid = False

    # Parse matching type
    try:
        matching = int(parts[2])
        if not (0 <= matching <= 2):
            result.errors.append(f"TLSA matching type must be 0-2, got {matching}")
            result.valid = False
        else:
            result.parsed["matching_type"] = matching
            result.parsed["matching_name"] = _TLSA_MATCHING[matching]
    except ValueError:
        result.errors.append(f"Invalid TLSA matching type: '{parts[2]}' (must be 0-2)")
        result.valid = False

    # Parse certificate association data (hex)
    cert_data = "".join(parts[3:])
    cert_data_clean = cert_data.replace(" ", "")
    result.parsed["data"] = cert_data_clean

    if not re.match(r'^[0-9a-fA-F]+$', cert_data_clean):
        result.errors.append("TLSA certificate data must be a hex string")
        result.valid = False
    else:
        data_len = len(cert_data_clean)
        matching_val = result.parsed.get("matching_type")
        if matching_val == 1 and data_len != 64:
            result.warnings.append(
                f"SHA-256 hash should be 64 hex characters, got {data_len}"
            )
        elif matching_val == 2 and data_len != 128:
            result.warnings.append(
                f"SHA-512 hash should be 128 hex characters, got {data_len}"
            )
        elif matching_val == 0 and data_len < 20:
            result.warnings.append(
                f"Full certificate data seems very short ({data_len} hex chars)"
            )

    # Common configuration advice
    usage_val = result.parsed.get("usage")
    if usage_val == 3:
        result.warnings.append(
            "Usage 3 (DANE-EE) pins a specific certificate. "
            "Remember to update this record BEFORE rotating certificates."
        )

    return result


def validate_record(record_type: str, value: str) -> ValidationResult:
    """Validate a DNS record value for the given type."""
    validators = {
        "SPF": validate_spf,
        "DKIM": validate_dkim,
        "DMARC": validate_dmarc,
        "A": validate_a,
        "MX": validate_mx,
        "TLSA": validate_tlsa,
    }
    rt = record_type.upper()
    validator = validators.get(rt)
    if validator is None:
        raise ValueError(f"No validator for record type '{record_type}'")
    return validator(value)


# ═══════════════════════════════════════════════════════════════════
# Generator — produce correctly formatted DNS records
# ═══════════════════════════════════════════════════════════════════

def _fqdn(domain: str) -> str:
    domain = domain.strip()
    return domain if domain.endswith(".") else domain + "."


def generate_a(domain: str, ip: str, ttl: int = 3600) -> str:
    ipaddress.IPv4Address(ip)
    return f"{_fqdn(domain)} {ttl} IN A {ip}"


def generate_aaaa(domain: str, ip: str, ttl: int = 3600) -> str:
    ipaddress.IPv6Address(ip)
    return f"{_fqdn(domain)} {ttl} IN AAAA {ip}"


def generate_mx(domain: str, server: str, priority: int = 10, ttl: int = 3600) -> str:
    if not (0 <= priority <= 65535):
        raise ValueError(f"MX priority must be 0-65535, got {priority}")
    return f"{_fqdn(domain)} {ttl} IN MX {priority} {_fqdn(server)}"


def generate_spf(domain: str, *, include: list[str] | None = None,
                  ip4: list[str] | None = None, all_qualifier: str = "~",
                  ttl: int = 3600) -> str:
    parts = ["v=spf1"]
    for addr in (ip4 or []):
        parts.append(f"ip4:{addr}")
    for inc in (include or []):
        parts.append(f"include:{inc}")
    parts.append(f"{all_qualifier}all")
    return f'{_fqdn(domain)} {ttl} IN TXT "{" ".join(parts)}"'


def generate_dmarc(domain: str, *, policy: str = "none",
                    rua: str | None = None, ttl: int = 3600) -> str:
    parts = [f"v=DMARC1", f"p={policy}"]
    if rua:
        if not rua.startswith("mailto:"):
            rua = f"mailto:{rua}"
        parts.append(f"rua={rua}")
    return f'{_fqdn("_dmarc." + domain)} {ttl} IN TXT "{"; ".join(parts)}"'


def generate_ptr(ip: str, domain: str, ttl: int = 3600) -> str:
    try:
        addr = ipaddress.IPv4Address(ip)
        octets = str(addr).split(".")
        ptr_name = ".".join(reversed(octets)) + ".in-addr.arpa."
    except (ipaddress.AddressValueError, ValueError):
        addr = ipaddress.IPv6Address(ip)
        expanded = addr.exploded.replace(":", "")
        ptr_name = ".".join(reversed(expanded)) + ".ip6.arpa."
    return f"{ptr_name} {ttl} IN PTR {_fqdn(domain)}"


# ═══════════════════════════════════════════════════════════════════
# Explainer — plain English explanations
# ═══════════════════════════════════════════════════════════════════

_SPF_QUALIFIER_NAMES = {
    "+": "pass (allow)", "-": "fail (reject)",
    "~": "softfail (accept but mark)", "?": "neutral (no opinion)",
}


def explain_record(record_type: str, value: str = "") -> str:
    """Explain a DNS record in plain English."""
    rt = record_type.upper()

    if rt == "SPF" and value:
        return _explain_spf(value)
    if rt == "DMARC" and value:
        return _explain_dmarc(value)

    type_info = get_record_type(rt)
    if type_info is None:
        return f"Unknown record type: '{record_type}'"

    lines = [
        f"DNS Record Type: {type_info.name} (type code {type_info.code})",
        f"  {type_info.description}",
        f"  Purpose: {type_info.purpose}",
        f"  Syntax: {type_info.syntax}",
        f"  RFCs: {', '.join(type_info.rfc)}",
    ]
    if type_info.examples:
        lines.append("  Examples:")
        for ex in type_info.examples:
            lines.append(f"    {ex}")
    return "\n".join(lines)


def _explain_spf(value: str) -> str:
    result = validate_spf(value)
    lines = ["SPF Record Explanation", ""]
    if not result.valid:
        lines.append("  WARNING: This SPF record has errors:")
        for err in result.errors:
            lines.append(f"    - {err}")
        lines.append("")
    lines.append(f"  Record: {value}")
    lines.append("")
    lines.append("  This record specifies which servers are authorized to send")
    lines.append("  email on behalf of your domain.")
    lines.append("")
    for i, mech in enumerate(result.parsed.get("mechanisms", []), 1):
        qual_desc = _SPF_QUALIFIER_NAMES.get(mech["qualifier"], mech["qualifier"])
        name = mech["mechanism"]
        arg = mech["argument"]
        if name == "all":
            lines.append(f"    {i}. {qual_desc.upper()} for everything else")
        elif name == "include":
            lines.append(f"    {i}. Also check SPF for {arg}")
        elif name in ("ip4", "ip6"):
            lines.append(f"    {i}. Allow {name} address: {arg}")
        else:
            lines.append(f"    {i}. {name}" + (f": {arg}" if arg else ""))
    dns_lookups = result.parsed.get("dns_lookups", 0)
    if dns_lookups > 0:
        lines.append(f"  DNS lookups: {dns_lookups}/10")
    return "\n".join(lines)


def _explain_dmarc(value: str) -> str:
    result = validate_dmarc(value)
    lines = ["DMARC Record Explanation", ""]
    if not result.valid:
        lines.append("  WARNING: This DMARC record has errors:")
        for err in result.errors:
            lines.append(f"    - {err}")
        lines.append("")
    lines.append(f"  Record: {value}")
    lines.append("")
    policy = result.parsed.get("policy", "unknown")
    explanations = {
        "none": "Monitor only. Failed emails are still delivered.",
        "quarantine": "Failed emails go to the spam/junk folder.",
        "reject": "Failed emails are bounced (not delivered).",
    }
    lines.append(f"  Policy: {policy}")
    if policy in explanations:
        lines.append(f"    {explanations[policy]}")
    if "rua" in result.parsed:
        lines.append(f"  Aggregate reports sent to: {', '.join(result.parsed['rua'])}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dns-ref",
        description="DNS record reference, validator, explainer, and generator.",
    )
    sub = parser.add_subparsers(dest="command")

    lk = sub.add_parser("lookup", help="Look up a DNS record type")
    lk.add_argument("type")
    lk.add_argument("--json", action="store_true", dest="as_json")

    sub.add_parser("list", help="List all DNS record types")

    se = sub.add_parser("search", help="Search record types")
    se.add_argument("query")

    va = sub.add_parser("validate", help="Validate a DNS record")
    va.add_argument("type")
    va.add_argument("value")

    ex = sub.add_parser("explain", help="Explain a DNS record")
    ex.add_argument("type")
    ex.add_argument("value", nargs="?", default="")

    ge = sub.add_parser("generate", help="Generate a DNS record")
    ge.add_argument("type")
    ge.add_argument("args", nargs="*")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "lookup":
        rt = get_record_type(args.type)
        if rt is None:
            print(f"Unknown: '{args.type}'", file=sys.stderr)
            return 1
        if args.as_json:
            print(json.dumps({"name": rt.name, "code": rt.code, "rfc": rt.rfc,
                              "description": rt.description, "syntax": rt.syntax,
                              "purpose": rt.purpose, "examples": rt.examples}, indent=2))
        else:
            print(f"Type: {rt.name} (code {rt.code})")
            print(f"Description: {rt.description}")
            print(f"Purpose: {rt.purpose}")
            print(f"Syntax: {rt.syntax}")
            print(f"RFCs: {', '.join(rt.rfc)}")
        return 0

    if args.command == "list":
        for rt in list_record_types():
            code = str(rt.code) if rt.code > 0 else "-"
            print(f"  {rt.name:<8} {code:<6} {rt.description[:60]}")
        return 0

    if args.command == "search":
        for rt in search_record_types(args.query):
            print(f"  {rt.name:<8} {rt.description[:60]}")
        return 0

    if args.command == "validate":
        try:
            result = validate_record(args.type, args.value)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        print(str(result))
        return 0 if result.valid else 1

    if args.command == "explain":
        print(explain_record(args.type, args.value))
        return 0

    if args.command == "generate":
        ga = args.args
        rtype = args.type.upper()
        try:
            if rtype == "A":
                print(generate_a(ga[0], ga[1]))
            elif rtype == "AAAA":
                print(generate_aaaa(ga[0], ga[1]))
            elif rtype == "MX":
                print(generate_mx(ga[0], ga[1], int(ga[2]) if len(ga) > 2 else 10))
            elif rtype == "PTR":
                print(generate_ptr(ga[0], ga[1]))
            else:
                print(f"Generator not available for '{args.type}'", file=sys.stderr)
                return 1
            return 0
        except (IndexError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
